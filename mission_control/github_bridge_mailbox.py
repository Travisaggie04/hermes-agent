"""Manual-start GitHub issue/comment bridge mailbox for Mission Control.

This module intentionally does not run as a daemon, timer, worker, or hidden
dispatch path. It parses a dedicated GitHub issue's comments, stores bounded
bridge messages as append-only Mission Control records, and can append exactly
one response record after an operator chooses a request.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from mission_control.records import GitHubBridgeMailboxStatusRecord, GitHubBridgeMessageRecord, JsonlRecordStore


GITHUB_BRIDGE_MARKER = "<!-- hermes-github-bridge -->"
DEFAULT_GITHUB_BRIDGE_REPO = "Travisaggie04/hermes-agent"
DEFAULT_GITHUB_BRIDGE_ISSUE = 79
DEFAULT_NOTIFY_SSH_TARGET = "jenny@100.115.125.111"
DEFAULT_NOTIFY_REMOTE_RUNTIME = "/home/jenny/.hermes/hermes-runtime-github-bridge-mailbox-944411a"
DEFAULT_HERMES_BIN = ""
DEFAULT_MISSION_CONTROL_PROJECT_ID = "project-hermes-mission-control"
PENDING_STATUSES = {"queued", "retry_requested"}
REPLIED_STATUSES = {"replied", "closed"}
DEFAULT_LIMIT = 25
INERT_METADATA = {
    "manual_start_only": True,
    "dispatch_enabled": False,
    "session_send_enabled": False,
    "execution_enabled": False,
    "worker_enabled": False,
    "timer_enabled": False,
    "daemon_enabled": False,
    "discord_automation_enabled": False,
    "model_routing_enabled": False,
}


@dataclass(frozen=True)
class PendingGitHubBridgeMessage:
    record_index: int
    record: GitHubBridgeMessageRecord


class HermesResponderError(RuntimeError):
    """Raised when Hermes did not return a usable chat response."""


def record_store_path() -> Path:
    return get_hermes_home() / "mission-control" / "records.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _store(path: Path | None = None) -> JsonlRecordStore:
    return JsonlRecordStore(path or record_store_path())


def _runtime_path() -> str:
    try:
        return str(Path.cwd())
    except OSError:
        return ""


def _runtime_head() -> str:
    git_path = Path(".git")
    try:
        if git_path.is_file():
            pointer = git_path.read_text(encoding="utf-8").strip()
            if pointer.startswith("gitdir:"):
                git_path = Path(pointer.removeprefix("gitdir:").strip())
        head_path = git_path / "HEAD"
        raw = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if raw.startswith("ref: "):
        ref_path = git_path / raw.removeprefix("ref: ").strip()
        try:
            return ref_path.read_text(encoding="utf-8").strip()
        except OSError:
            return raw
    return raw


def _bounded_text(value: Any, *, max_chars: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) > max_chars:
        raise ValueError("bridge field is too large")
    return text


def _message_payload(
    *,
    request_id: str,
    project_id: str,
    from_agent: str,
    to_agent: str,
    status: str,
    message: str,
    created_at: str = "",
) -> dict[str, str]:
    request_id = _bounded_text(request_id, max_chars=120)
    project_id = _bounded_text(project_id, max_chars=120)
    from_agent = _bounded_text(from_agent, max_chars=80)
    to_agent = _bounded_text(to_agent, max_chars=80)
    status = _bounded_text(status, max_chars=80) or "queued"
    message = _bounded_text(message, max_chars=4000)
    created_at = _bounded_text(created_at, max_chars=80) or utc_now()
    if not request_id:
        raise ValueError("request_id is required")
    if not project_id:
        raise ValueError("project_id is required")
    if not from_agent:
        raise ValueError("from_agent is required")
    if not to_agent:
        raise ValueError("to_agent is required")
    if not message:
        raise ValueError("message is required")
    return {
        "request_id": request_id,
        "project_id": project_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "status": status,
        "message": message,
        "created_at": created_at,
    }


def bridge_comment_body(payload: dict[str, str]) -> str:
    clean = _message_payload(**payload)
    return f"{GITHUB_BRIDGE_MARKER}\n```json\n{json.dumps(clean, sort_keys=True)}\n```"


def response_comment_body(
    *,
    request_id: str,
    project_id: str,
    from_agent: str = "jenny",
    to_agent: str = "codex",
    message: str,
    created_at: str = "",
) -> str:
    return bridge_comment_body(
        _message_payload(
            request_id=request_id,
            project_id=project_id,
            from_agent=from_agent,
            to_agent=to_agent,
            status="replied",
            message=message,
            created_at=created_at or utc_now(),
        )
    )


def _extract_json_block(body: str) -> dict[str, Any] | None:
    if GITHUB_BRIDGE_MARKER not in body:
        return None
    after = body.split(GITHUB_BRIDGE_MARKER, 1)[1]
    if "```" in after:
        parts = after.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
            raw = raw.strip()
        else:
            raw = after.strip()
    else:
        raw = after.strip()

    candidates = [raw]
    if '\\"' in raw:
        candidates.append(raw.replace('\\"', '"'))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_bridge_comments(comments: list[dict[str, Any]], *, repo: str, issue_number: int) -> list[GitHubBridgeMessageRecord]:
    records: list[GitHubBridgeMessageRecord] = []
    for comment in comments:
        body = str(comment.get("body") or "")
        payload = _extract_json_block(body)
        if not payload:
            continue
        clean = _message_payload(
            request_id=payload.get("request_id", ""),
            project_id=payload.get("project_id", ""),
            from_agent=payload.get("from_agent", ""),
            to_agent=payload.get("to_agent", ""),
            status=payload.get("status", "queued"),
            message=payload.get("message", ""),
            created_at=payload.get("created_at") or comment.get("created_at") or utc_now(),
        )
        records.append(
            GitHubBridgeMessageRecord(
                **clean,
                github_repo=repo,
                github_issue_number=int(issue_number),
                github_comment_id=str(comment.get("id") or ""),
                metadata={
                    **INERT_METADATA,
                    "source": "github_issue_comment_bridge",
                    "github_comment_id": comment.get("id") or "",
                    "github_user": ((comment.get("user") or {}).get("login") if isinstance(comment.get("user"), dict) else "") or "",
                },
            )
        )
    return records


def append_status(
    *,
    status: str,
    repo: str = "",
    issue_number: int = 0,
    pending_count: int = 0,
    new_message_count: int = 0,
    handled_request_id: str = "",
    handled_response_id: str = "",
    last_error: str = "",
    mode: str = "manual",
    operator: str = "manual",
    path: Path | None = None,
) -> tuple[int, GitHubBridgeMailboxStatusRecord]:
    record = GitHubBridgeMailboxStatusRecord(
        status_id=f"github-bridge-status-{uuid.uuid4().hex[:12]}",
        bridge_id="manual-github-issue-mailbox",
        repo=repo,
        issue_number=int(issue_number or 0),
        mode=mode,
        status=status,
        pending_count=max(0, int(pending_count)),
        new_message_count=max(0, int(new_message_count)),
        handled_request_id=handled_request_id,
        handled_response_id=handled_response_id,
        last_error=last_error,
        runtime_path=_runtime_path(),
        head=_runtime_head(),
        operator=operator or "manual",
        created_at=utc_now(),
        metadata=dict(INERT_METADATA),
    )
    index = _store(path).append(record)
    return index, record


def existing_request_ids(path: Path | None = None, *, repo: str = "", issue_number: int = 0) -> set[str]:
    return {
        record.request_id
        for record in _store(path).read_all(GitHubBridgeMessageRecord)
        if (not repo or record.github_repo == repo) and (not issue_number or record.github_issue_number == int(issue_number))
    }


def response_request_ids(path: Path | None = None, *, repo: str = "", issue_number: int = 0) -> set[str]:
    return {
        record.request_id
        for record in _store(path).read_all(GitHubBridgeMessageRecord)
        if (not repo or record.github_repo == repo)
        and (not issue_number or record.github_issue_number == int(issue_number))
        if record.status in REPLIED_STATUSES or record.from_agent == "jenny"
    }


def poll_comments(
    comments: list[dict[str, Any]],
    *,
    repo: str,
    issue_number: int,
    path: Path | None = None,
    operator: str = "manual",
    append_poll_status: bool = True,
) -> dict[str, Any]:
    store = _store(path)
    known_comment_ids = {
        record.github_comment_id
        for record in store.read_all(GitHubBridgeMessageRecord)
        if record.github_repo == repo and record.github_issue_number == int(issue_number)
    }
    known_pending_request_ids = {
        record.request_id
        for record in store.read_all(GitHubBridgeMessageRecord)
        if record.github_repo == repo
        and record.github_issue_number == int(issue_number)
        and record.status in PENDING_STATUSES
        and record.to_agent == "jenny"
    }
    known_response_request_ids = {
        record.request_id
        for record in store.read_all(GitHubBridgeMessageRecord)
        if record.github_repo == repo
        and record.github_issue_number == int(issue_number)
        and (record.status in REPLIED_STATUSES or record.from_agent == "jenny")
    }
    parsed = parse_bridge_comments(comments, repo=repo, issue_number=issue_number)
    appended: list[dict[str, Any]] = []
    for record in parsed:
        if record.github_comment_id and record.github_comment_id in known_comment_ids:
            continue
        if record.status in PENDING_STATUSES and record.to_agent == "jenny" and record.request_id in known_pending_request_ids:
            continue
        if (record.status in REPLIED_STATUSES or record.from_agent == "jenny") and record.request_id in known_response_request_ids:
            continue
        index = store.append(record)
        appended.append({"record_index": index, "record_type": record.record_type, "record": record.to_dict()})
        known_comment_ids.add(record.github_comment_id)
        if record.status in PENDING_STATUSES and record.to_agent == "jenny":
            known_pending_request_ids.add(record.request_id)
        if record.status in REPLIED_STATUSES or record.from_agent == "jenny":
            known_response_request_ids.add(record.request_id)
    pending = list_pending_messages(path=path, repo=repo, issue_number=issue_number)
    status_record: GitHubBridgeMailboxStatusRecord | None = None
    if append_poll_status:
        _status_index, status_record = append_status(
            status="poll_completed",
            repo=repo,
            issue_number=issue_number,
            pending_count=len(pending),
            new_message_count=len(appended),
            operator=operator,
            path=path,
        )
    return {
        **_inert_response_flags(),
        "stored": True,
        "new_message_count": len(appended),
        "pending_count": len(pending),
        "messages": appended,
        "status_record": status_record.to_dict() if status_record else {},
    }


def list_pending_messages(
    *,
    path: Path | None = None,
    repo: str = "",
    issue_number: int = 0,
    to_agent: str = "jenny",
    limit: int = DEFAULT_LIMIT,
) -> list[PendingGitHubBridgeMessage]:
    responses = response_request_ids(path, repo=repo, issue_number=issue_number)
    latest_by_request_id: dict[str, PendingGitHubBridgeMessage] = {}
    for index, record in _store(path).read_latest(GitHubBridgeMessageRecord, limit=max(limit, DEFAULT_LIMIT) * 4):
        if repo and record.github_repo != repo:
            continue
        if issue_number and record.github_issue_number != int(issue_number):
            continue
        latest_by_request_id[record.request_id] = PendingGitHubBridgeMessage(index, record)
    pending = [
        item
        for item in sorted(latest_by_request_id.values(), key=lambda item: item.record_index)
        if item.record.status in PENDING_STATUSES
        and item.record.to_agent == to_agent
        and item.record.request_id not in responses
    ]
    return pending[-limit:]


def _preflight_response(
    *,
    request_id: str,
    project_id: str,
    message: str,
    repo: str,
    issue_number: int,
    path: Path | None = None,
    operator: str = "manual",
) -> tuple[GitHubBridgeMessageRecord | None, int | None, GitHubBridgeMailboxStatusRecord | None]:
    """Validate a single response before any external GitHub POST.

    Response dedupe is scoped to repo + issue_number + request_id. The request_id
    may repeat in another bridge mailbox without making this mailbox look replied.
    """
    request_id = _bounded_text(request_id, max_chars=120)
    project_id = _bounded_text(project_id, max_chars=120)
    message = _bounded_text(message, max_chars=4000)
    if not request_id:
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, last_error="request_id is required", operator=operator, path=path)
        raise ValueError(status_record.last_error)
    if not project_id:
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, handled_request_id=request_id, last_error="project_id is required", operator=operator, path=path)
        raise ValueError(status_record.last_error)
    if not message:
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, handled_request_id=request_id, last_error="message is required", operator=operator, path=path)
        raise ValueError(status_record.last_error)

    scoped_records = [
        record
        for record in _store(path).read_all(GitHubBridgeMessageRecord)
        if record.github_repo == repo and record.github_issue_number == int(issue_number) and record.request_id == request_id
    ]
    if not scoped_records:
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, handled_request_id=request_id, last_error="request_id not found", operator=operator, path=path)
        raise ValueError(status_record.last_error)
    if not any(record.project_id == project_id for record in scoped_records):
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, handled_request_id=request_id, last_error="project_id does not match request", operator=operator, path=path)
        raise ValueError(status_record.last_error)
    request = next((record for record in reversed(scoped_records) if record.project_id == project_id and record.status in PENDING_STATUSES), None)
    if request is None:
        _idx, status_record = append_status(status="error", repo=repo, issue_number=issue_number, handled_request_id=request_id, last_error="request_id not pending", operator=operator, path=path)
        raise ValueError(status_record.last_error)
    if request_id in response_request_ids(path, repo=repo, issue_number=issue_number):
        status_index, status_record = append_status(
            status="skipped_duplicate",
            repo=repo,
            issue_number=issue_number,
            handled_request_id=request_id,
            pending_count=len(list_pending_messages(path=path, repo=repo, issue_number=issue_number)),
            operator=operator,
            path=path,
        )
        return None, status_index, status_record
    return request, None, None


def append_response(
    *,
    request_id: str,
    project_id: str,
    message: str,
    repo: str,
    issue_number: int,
    github_comment_id: int | str = "",
    path: Path | None = None,
    operator: str = "manual",
) -> tuple[int, GitHubBridgeMessageRecord | None, GitHubBridgeMailboxStatusRecord]:
    request, status_index, status_record = _preflight_response(
        request_id=request_id,
        project_id=project_id,
        message=message,
        repo=repo,
        issue_number=issue_number,
        path=path,
        operator=operator,
    )
    if request is None:
        if status_index is None or status_record is None:
            raise RuntimeError("invalid response preflight result")
        return status_index, None, status_record
    record = GitHubBridgeMessageRecord(
        request_id=_bounded_text(request_id, max_chars=120),
        project_id=_bounded_text(project_id, max_chars=120),
        from_agent="jenny",
        to_agent=request.from_agent or "codex",
        status="replied",
        message=_bounded_text(message, max_chars=4000),
        created_at=utc_now(),
        github_repo=repo,
        github_issue_number=int(issue_number),
        github_comment_id=str(github_comment_id or ""),
        metadata={**INERT_METADATA, "source": "github_issue_comment_bridge_response", "external_github_response": True},
    )
    index = _store(path).append(record)
    _status_index, status_record = append_status(
        status="response_appended",
        repo=repo,
        issue_number=issue_number,
        handled_request_id=record.request_id,
        handled_response_id=record.request_id,
        pending_count=len(list_pending_messages(path=path, repo=repo, issue_number=issue_number)),
        operator=operator,
        path=path,
    )
    return index, record, status_record


def github_bridge_status(*, path: Path | None = None, repo: str = "", issue_number: int = 0, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    pending = list_pending_messages(path=path, repo=repo, issue_number=issue_number, limit=limit)
    store = _store(path)
    statuses = list(store.read_latest(GitHubBridgeMailboxStatusRecord, limit=max(1, limit)))
    responses = [record for _idx, record in store.read_latest(GitHubBridgeMessageRecord, limit=max(limit, DEFAULT_LIMIT) * 4) if record.status in REPLIED_STATUSES or record.from_agent == "jenny"]
    latest_status = statuses[-1][1] if statuses else None
    latest_response = responses[-1] if responses else None
    return {
        **_inert_response_flags(),
        "stored": False,
        "pending_count": len(pending),
        "mode": latest_status.mode if latest_status else "manual",
        "foreground_watch_supported": True,
        "foreground_watch_running": latest_status.status.startswith("watch_") and latest_status.status != "watch_stopped" if latest_status else False,
        "last_poll_at": latest_status.created_at if latest_status else "",
        "last_status": latest_status.status if latest_status else "idle",
        "last_response_at": latest_response.created_at if latest_response else "",
        "last_response_request_id": latest_response.request_id if latest_response else "",
        "last_error": latest_status.last_error if latest_status else "",
        "pending_messages": [
            {"record_index": item.record_index, "record_type": item.record.record_type, "record": item.record.to_dict()}
            for item in pending
        ],
        "status_records": [
            {"record_index": index, "record_type": record.record_type, "record": record.to_dict()}
            for index, record in statuses
        ],
    }


def _inert_response_flags() -> dict[str, bool]:
    return {
        "manual_start_only": True,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "discord_automation_enabled": False,
        "model_routing_enabled": False,
    }


def _run_gh_api(args: list[str]) -> Any:
    # Manual-start only. Uses gh's configured auth without reading or printing secrets.
    result = subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "null")


def _run_gh_api_json_lines(args: list[str]) -> list[dict[str, Any]]:
    # gh 2.45 supports --paginate and --jq, but not --slurp.
    result = subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True)
    comments: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("GitHub comments response line must be an object")
        comments.append(parsed)
    return comments


def _github_issue_comments_args(repo: str, issue_number: int) -> list[str]:
    return [f"repos/{repo}/issues/{issue_number}/comments?per_page=100", "--paginate", "--jq", ".[]"]


def _normalize_github_comments_response(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list) and all(isinstance(page, list) for page in response):
        flattened = [comment for page in response for comment in page]
    else:
        flattened = response
    if not isinstance(flattened, list) or not all(isinstance(comment, dict) for comment in flattened):
        raise ValueError("GitHub comments response must be a list")
    return flattened


def _run_ssh(args: list[str]) -> str:
    # Manual foreground operator path only. Does not start a daemon, timer, or worker.
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout


def _parse_utc(value: str) -> datetime | None:
    raw = _bounded_text(value, max_chars=80)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def clean_hermes_response(output: str) -> str:
    text = (output or "").strip()
    bad_markers = ["Hermes Agent", "Available Skills", "browser-cdp", "clarify:", "waha:"]
    if not text:
        return "I received the Mission Control message, but Hermes returned an empty response."
    if any(marker in text[:2500] for marker in bad_markers):
        return (
            "I received the Mission Control message, but Hermes returned a non-chat startup "
            "screen instead of a clean response."
        )
    return _bounded_text(text[-5000:], max_chars=4000)


def hermes_response_error(output: str, returncode: int = 0) -> str:
    text = (output or "").strip()
    if returncode != 0:
        return compactTextForError(text) or f"Hermes responder exited with code {returncode}"
    if not text:
        return "Hermes responder returned an empty response"
    lower = text.lower()
    failure_markers = [
        "codex app-server startup failed",
        "app-server method 'initialize' timed out",
        "api call failed",
        "quota exhausted",
    ]
    if text.startswith("Error:") or any(marker in lower for marker in failure_markers):
        return compactTextForError(text)
    if any(marker in text[:2500] for marker in ["Hermes Agent", "Available Skills", "browser-cdp", "clarify:", "waha:"]):
        return "Hermes responder returned the startup screen instead of a chat response"
    return ""


def compactTextForError(value: str, max_chars: int = 700) -> str:
    normalized = str(value or "").replace("\r", "\n").strip()
    normalized = " ".join(part.strip() for part in normalized.splitlines() if part.strip())
    if not normalized:
        return ""
    return normalized[:max_chars].rstrip()


def mission_control_responder_prompt(record: GitHubBridgeMessageRecord) -> str:
    return (
        "You are Jenny inside Travis's Mission Control OS, replacing Discord for the Hermes / Mission Control project.\n"
        "Act as a strong engineering orchestrator: challenge weak requests, name risks plainly, and give the next safe step.\n"
        "Do not claim you deployed, restarted, switched runtimes, dispatched sessions, used Waha/social/payment actions, "
        "started workers/timers/daemons, or inspected secrets unless the request includes explicit evidence that already happened.\n"
        "Keep the reply concise and useful for the Mission Control chat.\n\n"
        f"Project: {record.project_id}\n"
        f"Request id: {record.request_id}\n"
        f"Message from {record.from_agent or 'operator'}:\n{record.message}"
    )


def run_hermes_responder(
    record: GitHubBridgeMessageRecord,
    *,
    hermes_bin: str = DEFAULT_HERMES_BIN,
    profile_home: str = "",
    cwd: str = "",
    timeout_seconds: int = 240,
    toolsets: str = "file,skills",
) -> str:
    env = {"HERMES_HOME": profile_home} if profile_home else None
    prompt = mission_control_responder_prompt(record)
    command = [hermes_bin] if hermes_bin else [sys.executable, "-m", "hermes_cli.main"]
    proc = subprocess.run(
        command
        + [
            "chat",
            "-Q",
            "-t",
            toolsets,
            "-q",
            prompt,
            "--source",
            "mission-control-github-bridge",
        ],
        cwd=cwd or str(Path.cwd()),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=max(30, int(timeout_seconds)),
        check=False,
    )
    if error := hermes_response_error(proc.stdout, getattr(proc, "returncode", 0)):
        raise HermesResponderError(error)
    return clean_hermes_response(proc.stdout)


def _select_pending_message(
    *,
    path: Path | None,
    repo: str,
    issue_number: int,
    project_id: str,
    request_id: str = "",
    not_before: str = "",
) -> PendingGitHubBridgeMessage | None:
    cutoff = _parse_utc(not_before)
    pending = list_pending_messages(
        path=path,
        repo=repo,
        issue_number=issue_number,
        to_agent="jenny",
        limit=DEFAULT_LIMIT,
    )
    filtered = []
    for item in pending:
        record = item.record
        if project_id and record.project_id != project_id:
            continue
        if request_id and record.request_id != request_id:
            continue
        if cutoff is not None:
            created_at = _parse_utc(record.created_at)
            if created_at is None or created_at < cutoff:
                continue
        filtered.append(item)
    return filtered[-1] if filtered else None


def answer_pending_with_hermes(
    *,
    repo: str = DEFAULT_GITHUB_BRIDGE_REPO,
    issue_number: int = DEFAULT_GITHUB_BRIDGE_ISSUE,
    project_id: str = DEFAULT_MISSION_CONTROL_PROJECT_ID,
    request_id: str = "",
    not_before: str = "",
    path: Path | None = None,
    operator: str = "manual",
    hermes_bin: str = DEFAULT_HERMES_BIN,
    profile_home: str = "",
    cwd: str = "",
    timeout_seconds: int = 240,
    run_hermes_fn: Any | None = None,
    post_response_fn: Any | None = None,
) -> dict[str, Any]:
    selected = _select_pending_message(
        path=path,
        repo=repo,
        issue_number=issue_number,
        project_id=project_id,
        request_id=request_id,
        not_before=not_before,
    )
    if selected is None:
        _idx, status_record = append_status(
            status="hermes_answer_noop",
            repo=repo,
            issue_number=issue_number,
            mode="manual_hermes_answer",
            last_error="no matching pending Mission Control mailbox request",
            operator=operator,
            path=path,
        )
        return {**_inert_response_flags(), "answered": False, "status": status_record.to_dict()}

    record = selected.record
    append_status(
        status="hermes_answer_started",
        repo=repo,
        issue_number=issue_number,
        mode="manual_hermes_answer",
        handled_request_id=record.request_id,
        operator=operator,
        path=path,
    )
    responder = run_hermes_fn or run_hermes_responder
    try:
        response_text = responder(
            record,
            hermes_bin=hermes_bin,
            profile_home=profile_home,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        if error := hermes_response_error(response_text):
            raise HermesResponderError(error)
    except Exception as exc:
        _idx, status_record = append_status(
            status="hermes_answer_error",
            repo=repo,
            issue_number=issue_number,
            mode="manual_hermes_answer",
            handled_request_id=record.request_id,
            last_error=compactTextForError(str(exc)) or "Hermes responder failed",
            pending_count=len(
                list_pending_messages(path=path, repo=repo, issue_number=issue_number)
            ),
            operator=operator,
            path=path,
        )
        return {
            **_inert_response_flags(),
            "answered": False,
            "request": record.to_dict(),
            "response": None,
            "status": status_record.to_dict(),
        }
    poster = post_response_fn or post_github_response
    response = poster(
        request_id=record.request_id,
        project_id=record.project_id,
        message=response_text,
        repo=repo,
        issue_number=issue_number,
        path=path,
        operator=operator,
    )
    _idx, status_record = append_status(
        status="hermes_answer_completed",
        repo=repo,
        issue_number=issue_number,
        mode="manual_hermes_answer",
        handled_request_id=record.request_id,
        pending_count=len(
            list_pending_messages(path=path, repo=repo, issue_number=issue_number)
        ),
        operator=operator,
        path=path,
    )
    return {
        **_inert_response_flags(),
        "answered": True,
        "request": record.to_dict(),
        "response": response,
        "status": status_record.to_dict(),
    }


def poll_github_issue(*, repo: str, issue_number: int, path: Path | None = None, operator: str = "manual") -> dict[str, Any]:
    comments = _run_gh_api_json_lines(_github_issue_comments_args(repo, issue_number))
    return poll_comments(comments, repo=repo, issue_number=issue_number, path=path, operator=operator)


def append_message(
    *,
    request_id: str,
    project_id: str,
    from_agent: str,
    to_agent: str,
    status: str,
    message: str,
    repo: str,
    issue_number: int,
    created_at: str = "",
    github_comment_id: int | str = "",
    path: Path | None = None,
) -> tuple[int, GitHubBridgeMessageRecord]:
    clean = _message_payload(
        request_id=request_id,
        project_id=project_id,
        from_agent=from_agent,
        to_agent=to_agent,
        status=status,
        message=message,
        created_at=created_at,
    )
    record = GitHubBridgeMessageRecord(
        **clean,
        github_repo=repo,
        github_issue_number=int(issue_number),
        github_comment_id=str(github_comment_id or ""),
        metadata={**INERT_METADATA, "source": "github_issue_comment_bridge_manual_send"},
    )
    index = _store(path).append(record)
    return index, record


def post_github_message(
    *,
    request_id: str,
    project_id: str,
    message: str,
    repo: str = DEFAULT_GITHUB_BRIDGE_REPO,
    issue_number: int = DEFAULT_GITHUB_BRIDGE_ISSUE,
    from_agent: str = "codex",
    to_agent: str = "jenny",
    status: str = "queued",
    path: Path | None = None,
    operator: str = "manual",
) -> dict[str, Any]:
    clean = _message_payload(
        request_id=request_id,
        project_id=project_id,
        from_agent=from_agent,
        to_agent=to_agent,
        status=status,
        message=message,
    )
    if clean["request_id"] in existing_request_ids(path, repo=repo, issue_number=issue_number):
        status_index, status_record = append_status(
            status="skipped_duplicate",
            repo=repo,
            issue_number=issue_number,
            handled_request_id=clean["request_id"],
            pending_count=len(list_pending_messages(path=path, repo=repo, issue_number=issue_number)),
            operator=operator,
            path=path,
        )
        return {
            "record_index": status_index,
            "record_type": "GitHubBridgeMailboxStatusRecord",
            "message": None,
            "status": status_record.to_dict(),
        }
    body = bridge_comment_body(clean)
    posted = _run_gh_api([f"repos/{repo}/issues/{issue_number}/comments", "-f", f"body={body}"])
    comment_id = str(posted.get("id") or "") if isinstance(posted, dict) else ""
    index, record = append_message(
        **clean,
        repo=repo,
        issue_number=issue_number,
        github_comment_id=comment_id,
        path=path,
    )
    _status_index, status_record = append_status(
        status="message_posted",
        repo=repo,
        issue_number=issue_number,
        pending_count=len(list_pending_messages(path=path, repo=repo, issue_number=issue_number)),
        new_message_count=1,
        handled_request_id=record.request_id,
        operator=operator,
        path=path,
    )
    return {
        "record_index": index,
        "record_type": record.record_type,
        "message": record.to_dict(),
        "status": status_record.to_dict(),
    }


def remote_poll_bridge_over_ssh(
    *,
    repo: str = DEFAULT_GITHUB_BRIDGE_REPO,
    issue_number: int = DEFAULT_GITHUB_BRIDGE_ISSUE,
    ssh_target: str = DEFAULT_NOTIFY_SSH_TARGET,
    remote_runtime: str = DEFAULT_NOTIFY_REMOTE_RUNTIME,
    ssh_known_hosts: Path | None = None,
    operator: str = "manual",
) -> dict[str, Any]:
    ssh_target = _bounded_text(ssh_target, max_chars=200)
    remote_runtime = _bounded_text(remote_runtime, max_chars=300)
    if not ssh_target:
        raise ValueError("ssh_target is required")
    if not remote_runtime:
        raise ValueError("remote_runtime is required")
    remote_command = " ".join(
        [
            "cd",
            shlex.quote(remote_runtime),
            "&&",
            "python3",
            "-m",
            "mission_control.github_bridge_mailbox",
            "poll",
            "--repo",
            shlex.quote(repo),
            "--issue",
            shlex.quote(str(int(issue_number))),
            "--operator",
            shlex.quote(operator),
        ]
    )
    ssh_args = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "ServerAliveInterval=10",
        "-o",
        "ServerAliveCountMax=2",
    ]
    if ssh_known_hosts is not None:
        ssh_args.extend(["-o", f"UserKnownHostsFile={ssh_known_hosts}"])
    ssh_args.extend([ssh_target, remote_command])
    try:
        stdout = _run_ssh(ssh_args)
    except subprocess.CalledProcessError as exc:
        output = f"{exc.stdout or ''}\n{exc.stderr or ''}"
        last_error = compactTextForError(output) or f"ssh exited with code {exc.returncode}"
        ssh_auth_required = "tailscale ssh requires an additional check" in output.lower()
        return {
            **_inert_response_flags(),
            "ssh_target": ssh_target,
            "remote_runtime": remote_runtime,
            "repo": repo,
            "issue_number": int(issue_number),
            "remote_poll": {
                "stored": False,
                "status": "ssh_auth_required" if ssh_auth_required else "ssh_failed",
                "ssh_auth_required": ssh_auth_required,
                "last_error": last_error,
            },
        }
    except subprocess.TimeoutExpired as exc:
        output = f"{exc.stdout or ''}\n{exc.stderr or ''}"
        return {
            **_inert_response_flags(),
            "ssh_target": ssh_target,
            "remote_runtime": remote_runtime,
            "repo": repo,
            "issue_number": int(issue_number),
            "remote_poll": {
                "stored": False,
                "status": "ssh_timeout",
                "ssh_auth_required": "tailscale ssh requires an additional check" in output.lower(),
                "last_error": compactTextForError(output) or "ssh timed out before remote poll completed",
            },
        }
    try:
        remote_payload = json.loads(stdout)
    except json.JSONDecodeError:
        remote_payload = {"raw_stdout": stdout}
    return {
        **_inert_response_flags(),
        "ssh_target": ssh_target,
        "remote_runtime": remote_runtime,
        "repo": repo,
        "issue_number": int(issue_number),
        "remote_poll": remote_payload,
    }


def notify_jenny_now(
    *,
    request_id: str,
    project_id: str,
    message: str,
    repo: str = DEFAULT_GITHUB_BRIDGE_REPO,
    issue_number: int = DEFAULT_GITHUB_BRIDGE_ISSUE,
    from_agent: str = "codex",
    to_agent: str = "jenny",
    status: str = "queued",
    ssh_target: str = DEFAULT_NOTIFY_SSH_TARGET,
    remote_runtime: str = DEFAULT_NOTIFY_REMOTE_RUNTIME,
    ssh_known_hosts: Path | None = None,
    path: Path | None = None,
    operator: str = "manual",
) -> dict[str, Any]:
    message_result = post_github_message(
        request_id=request_id,
        project_id=project_id,
        from_agent=from_agent,
        to_agent=to_agent,
        status=status,
        message=message,
        repo=repo,
        issue_number=issue_number,
        path=path,
        operator=operator,
    )
    poll_result = remote_poll_bridge_over_ssh(
        repo=repo,
        issue_number=issue_number,
        ssh_target=ssh_target,
        remote_runtime=remote_runtime,
        ssh_known_hosts=ssh_known_hosts,
        operator=operator,
    )
    return {
        **_inert_response_flags(),
        "message_result": message_result,
        "remote_poll_result": poll_result,
    }


def github_bridge_latest(
    *,
    path: Path | None = None,
    repo: str = DEFAULT_GITHUB_BRIDGE_REPO,
    issue_number: int = DEFAULT_GITHUB_BRIDGE_ISSUE,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    status = github_bridge_status(path=path, repo=repo, issue_number=issue_number, limit=limit)
    messages = [
        {"record_index": index, "record_type": record.record_type, "record": record.to_dict()}
        for index, record in _store(path).read_latest(GitHubBridgeMessageRecord, limit=max(1, limit))
        if (not repo or record.github_repo == repo) and (not issue_number or record.github_issue_number == int(issue_number))
    ]
    return {
        **_inert_response_flags(),
        "repo": repo,
        "issue_number": int(issue_number),
        "pending_count": status["pending_count"],
        "last_status": status["last_status"],
        "last_poll_at": status["last_poll_at"],
        "last_response_request_id": status["last_response_request_id"],
        "last_error": status["last_error"],
        "pending_messages": status["pending_messages"],
        "recent_messages": messages,
    }


def _load_watch_comments_batch(comments_json_dir: Path, iteration: int) -> list[dict[str, Any]]:
    candidates = [
        comments_json_dir / f"{iteration:03d}.json",
        comments_json_dir / f"{iteration}.json",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        return []
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError("watch comments JSON batch must be a list")
    return parsed


def watch_github_issue(
    *,
    repo: str,
    issue_number: int,
    interval_seconds: int,
    to_agent: str = "jenny",
    max_iterations: int | None = None,
    path: Path | None = None,
    operator: str = "manual",
    fetch_comments: Any | None = None,
    sleep_fn: Any = time.sleep,
    print_fn: Any = print,
) -> dict[str, Any]:
    if interval_seconds < 2 or interval_seconds > 5:
        raise ValueError("interval-seconds must be between 2 and 5")
    iterations = 0
    total_new_messages = 0
    append_status(status="watch_started", repo=repo, issue_number=issue_number, mode="watch_foreground", operator=operator, path=path)
    seen_printed: set[str] = set()
    try:
        while max_iterations is None or iterations < max_iterations:
            iterations += 1
            try:
                raw_comments = fetch_comments() if fetch_comments is not None else _run_gh_api_json_lines(_github_issue_comments_args(repo, issue_number))
                comments = _normalize_github_comments_response(raw_comments)
                result = poll_comments(
                    comments,
                    repo=repo,
                    issue_number=issue_number,
                    path=path,
                    operator=operator,
                    append_poll_status=False,
                )
                # Replace generic poll status with a foreground-watch status entry for the live relay surface.
                append_status(
                    status="watch_poll_completed",
                    repo=repo,
                    issue_number=issue_number,
                    mode="watch_foreground",
                    pending_count=int(result.get("pending_count", 0)),
                    new_message_count=int(result.get("new_message_count", 0)),
                    operator=operator,
                    path=path,
                )
                total_new_messages += int(result.get("new_message_count", 0))
                for item in list_pending_messages(path=path, repo=repo, issue_number=issue_number, to_agent=to_agent):
                    record = item.record
                    if record.request_id in seen_printed:
                        continue
                    seen_printed.add(record.request_id)
                    print_fn(
                        json.dumps(
                            {
                                "request_id": record.request_id,
                                "project_id": record.project_id,
                                "from_agent": record.from_agent,
                                "to_agent": record.to_agent,
                                "status": record.status,
                                "message": record.message,
                                "created_at": record.created_at,
                            },
                            sort_keys=True,
                        )
                    )
            except Exception as exc:
                append_status(
                    status="error",
                    repo=repo,
                    issue_number=issue_number,
                    mode="watch_foreground",
                    last_error=str(exc),
                    operator=operator,
                    path=path,
                )
                raise
            if max_iterations is not None and iterations >= max_iterations:
                break
            sleep_fn(interval_seconds)
    except KeyboardInterrupt:
        append_status(status="watch_stopped", repo=repo, issue_number=issue_number, mode="watch_foreground", operator=operator, path=path)
        raise
    append_status(status="watch_stopped", repo=repo, issue_number=issue_number, mode="watch_foreground", operator=operator, path=path)
    return {**_inert_response_flags(), "mode": "watch_foreground", "iterations": iterations, "new_message_count": total_new_messages}


def post_github_response(
    *,
    request_id: str,
    project_id: str,
    message: str,
    repo: str,
    issue_number: int,
    path: Path | None = None,
    operator: str = "manual",
) -> dict[str, Any]:
    request, status_index, status_record = _preflight_response(
        request_id=request_id,
        project_id=project_id,
        message=message,
        repo=repo,
        issue_number=issue_number,
        path=path,
        operator=operator,
    )
    if request is None:
        if status_index is None or status_record is None:
            raise RuntimeError("invalid response preflight result")
        return {"record_index": status_index, "record_type": "GitHubBridgeMailboxStatusRecord", "response": None, "status": status_record.to_dict()}
    body = response_comment_body(request_id=request_id, project_id=project_id, message=message)
    posted = _run_gh_api([f"repos/{repo}/issues/{issue_number}/comments", "-f", f"body={body}"])
    comment_id = str(posted.get("id") or "") if isinstance(posted, dict) else ""
    index, record, status_record = append_response(request_id=request_id, project_id=project_id, message=message, repo=repo, issue_number=issue_number, github_comment_id=comment_id, path=path, operator=operator)
    return {"record_index": index, "record_type": record.record_type if record else "GitHubBridgeMailboxStatusRecord", "response": record.to_dict() if record else None, "status": status_record.to_dict()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manual Mission Control GitHub bridge mailbox")
    parser.add_argument("--records", type=Path, default=None, help="Override records.jsonl path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    poll_parser = subparsers.add_parser("poll", help="Manually poll a GitHub bridge issue")
    poll_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    poll_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    poll_parser.add_argument("--operator", default="manual")
    poll_parser.add_argument("--comments-json", type=Path, default=None, help="Test/offline comments JSON file")

    pending_parser = subparsers.add_parser("pending", help="List pending Codex-to-Jenny messages from local records")
    pending_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    pending_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    pending_parser.add_argument("--json", action="store_true")

    status_parser = subparsers.add_parser("status", help="Print GitHub bridge mailbox status")
    status_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    status_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    status_parser.add_argument("--json", action="store_true")

    latest_parser = subparsers.add_parser("latest", help="Print concise local bridge mailbox summary")
    latest_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    latest_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    latest_parser.add_argument("--limit", type=int, default=10)
    latest_parser.add_argument("--json", action="store_true")

    send_parser = subparsers.add_parser("send", help="Post one bounded bridge message to GitHub")
    send_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    send_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    send_parser.add_argument("--request-id", required=True)
    send_parser.add_argument("--project-id", required=True)
    send_parser.add_argument("--from-agent", default="codex")
    send_parser.add_argument("--to-agent", default="jenny")
    send_parser.add_argument("--status", default="queued")
    send_parser.add_argument("--message", required=True)
    send_parser.add_argument("--operator", default="manual")

    notify_parser = subparsers.add_parser("notify-jenny-now", help="Post one bridge message and trigger one remote Jenny poll over SSH")
    notify_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    notify_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    notify_parser.add_argument("--request-id", required=True)
    notify_parser.add_argument("--project-id", required=True)
    notify_parser.add_argument("--from-agent", default="codex")
    notify_parser.add_argument("--to-agent", default="jenny")
    notify_parser.add_argument("--status", default="queued")
    notify_parser.add_argument("--message", required=True)
    notify_parser.add_argument("--ssh-target", default=DEFAULT_NOTIFY_SSH_TARGET)
    notify_parser.add_argument("--remote-runtime", default=DEFAULT_NOTIFY_REMOTE_RUNTIME)
    notify_parser.add_argument("--ssh-known-hosts", type=Path, default=None)
    notify_parser.add_argument("--operator", default="manual")

    respond_parser = subparsers.add_parser("respond", help="Respond to exactly one request through GitHub comments")
    respond_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    respond_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    respond_parser.add_argument("--request-id", required=True)
    respond_parser.add_argument("--project-id", required=True)
    respond_parser.add_argument("--message", required=True)
    respond_parser.add_argument("--operator", default="manual")
    respond_parser.add_argument("--dry-run", action="store_true", help="Append local response record without posting GitHub comment")

    answer_parser = subparsers.add_parser(
        "answer-pending-with-hermes",
        help="Run one foreground Hermes answer for one pending Mission Control mailbox request",
    )
    answer_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    answer_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    answer_parser.add_argument("--project-id", default=DEFAULT_MISSION_CONTROL_PROJECT_ID)
    answer_parser.add_argument("--request-id", default="")
    answer_parser.add_argument(
        "--not-before",
        default="",
        help="Ignore pending requests created before this ISO timestamp",
    )
    answer_parser.add_argument("--operator", default="manual")
    answer_parser.add_argument(
        "--hermes-bin",
        default=DEFAULT_HERMES_BIN,
        help="Optional Hermes executable override; empty uses the active runtime module",
    )
    answer_parser.add_argument("--profile-home", default="")
    answer_parser.add_argument(
        "--cwd",
        default="",
        help="Responder working directory; empty uses the active runtime checkout",
    )
    answer_parser.add_argument("--timeout-seconds", type=int, default=240)

    watch_parser = subparsers.add_parser("watch", help="Foreground-only watch of a GitHub bridge issue")
    watch_parser.add_argument("--repo", default=DEFAULT_GITHUB_BRIDGE_REPO)
    watch_parser.add_argument("--issue", type=int, default=DEFAULT_GITHUB_BRIDGE_ISSUE)
    watch_parser.add_argument("--interval-seconds", type=int, default=3)
    watch_parser.add_argument("--to-agent", default="jenny")
    watch_parser.add_argument("--operator", default="manual")
    watch_parser.add_argument("--max-iterations", type=int, default=None, help="Test-only bound for foreground watch")
    watch_parser.add_argument("--comments-json-dir", type=Path, default=None, help="Test/offline per-iteration comments JSON directory")

    args = parser.parse_args(argv)
    if args.command == "poll":
        if args.comments_json:
            comments = json.loads(args.comments_json.read_text(encoding="utf-8"))
            payload = poll_comments(comments, repo=args.repo, issue_number=args.issue, path=args.records, operator=args.operator)
        else:
            payload = poll_github_issue(repo=args.repo, issue_number=args.issue, path=args.records, operator=args.operator)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "pending":
        pending = list_pending_messages(path=args.records, repo=args.repo, issue_number=args.issue)
        payload = {**_inert_response_flags(), "count": len(pending), "messages": [{"record_index": item.record_index, "record_type": item.record.record_type, "record": item.record.to_dict()} for item in pending]}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps(github_bridge_status(path=args.records, repo=args.repo, issue_number=args.issue), indent=2, sort_keys=True))
        return 0
    if args.command == "latest":
        payload = github_bridge_latest(path=args.records, repo=args.repo, issue_number=args.issue, limit=max(1, args.limit))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"github bridge {payload['repo']}#{payload['issue_number']}")
            print(f"status={payload['last_status']} pending={payload['pending_count']} last_response={payload['last_response_request_id'] or 'none'}")
            if payload["last_error"]:
                print(f"last_error={payload['last_error']}")
            for item in payload["pending_messages"]:
                record = item["record"]
                print(f"pending {record['request_id']} {record['project_id']} from={record['from_agent']}: {record['message']}")
        return 0
    if args.command == "send":
        payload = post_github_message(
            request_id=args.request_id,
            project_id=args.project_id,
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            status=args.status,
            message=args.message,
            repo=args.repo,
            issue_number=args.issue,
            path=args.records,
            operator=args.operator,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "notify-jenny-now":
        payload = notify_jenny_now(
            request_id=args.request_id,
            project_id=args.project_id,
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            status=args.status,
            message=args.message,
            repo=args.repo,
            issue_number=args.issue,
            ssh_target=args.ssh_target,
            remote_runtime=args.remote_runtime,
            ssh_known_hosts=args.ssh_known_hosts,
            path=args.records,
            operator=args.operator,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "respond":
        if args.dry_run:
            index, record, status_record = append_response(
                request_id=args.request_id,
                project_id=args.project_id,
                message=args.message,
                repo=args.repo,
                issue_number=args.issue,
                path=args.records,
                operator=args.operator,
            )
            payload = {
                "record_index": index,
                "record_type": record.record_type if record else "GitHubBridgeMailboxStatusRecord",
                "response": record.to_dict() if record else None,
                "status": status_record.to_dict(),
            }
        else:
            payload = post_github_response(
                request_id=args.request_id,
                project_id=args.project_id,
                message=args.message,
                repo=args.repo,
                issue_number=args.issue,
                path=args.records,
                operator=args.operator,
            )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "answer-pending-with-hermes":
        payload = answer_pending_with_hermes(
            repo=args.repo,
            issue_number=args.issue,
            project_id=args.project_id,
            request_id=args.request_id,
            not_before=args.not_before,
            path=args.records,
            operator=args.operator,
            hermes_bin=args.hermes_bin,
            profile_home=args.profile_home,
            cwd=args.cwd,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "watch":
        fetch_comments = None
        sleep_fn = time.sleep
        if args.comments_json_dir:
            iteration = {"value": 0}

            def fetch_comments() -> list[dict[str, Any]]:
                iteration["value"] += 1
                return _load_watch_comments_batch(args.comments_json_dir, iteration["value"])

            sleep_fn = lambda _seconds: None
        payload = watch_github_issue(
            repo=args.repo,
            issue_number=args.issue,
            interval_seconds=args.interval_seconds,
            to_agent=args.to_agent,
            max_iterations=args.max_iterations,
            path=args.records,
            operator=args.operator,
            fetch_comments=fetch_comments,
            sleep_fn=sleep_fn,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
