"""Durable active task/workspace state for gateway resume recovery."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from hermes_constants import get_hermes_home
from utils import atomic_json_write


DEFAULT_ACTIVE_TASK_TTL_SECONDS = 48 * 60 * 60
FOREGROUND_SESSION_TTL_SECONDS = 6 * 60 * 60
ACTIVE_TASK_STATUSES = {
    "active",
    "running",
    "interrupted",
    "detached",
    "succeeded",
    "failed",
    "lost",
    "recovered",
    "unknown",
}
FINAL_REPORT_STATUSES = {"pending", "sent", "recovered", "failed"}
FOREGROUND_SESSION_FIELDS = (
    "session_key_hash",
    "repo_path",
    "branch",
    "head",
    "mode",
    "status",
    "task_summary_safe",
    "task_contract",
    "updated_at",
)
TASK_CONTRACT_ACTIVE_STATUSES = {"active", "paused"}
TASK_CONTRACT_MAX_SUMMARY_CHARS = 500
logger = logging.getLogger(__name__)

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9._-]{8,}\b"),
    re.compile(r"\b[A-Za-z0-9_]*(?:token|secret|password|api[_-]?key)[A-Za-z0-9_]*\s*[:=]\s*\S+", re.I),
    re.compile(r"\b(?:session|thread|channel|message|discord)[-_:\s]*(?:id[-_:\s]*)?[A-Za-z0-9:._-]{12,}\b", re.I),
    re.compile(r"\bplatform:[A-Za-z0-9:._-]{8,}\b", re.I),
    re.compile(r"\b\d{17,20}\b"),
    re.compile(r"\b(?=[A-Za-z0-9._-]{32,}\b)(?=[A-Za-z0-9._-]*[A-Za-z])(?=[A-Za-z0-9._-]*\d)[A-Za-z0-9._-]{32,}\b"),
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hash_ref(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]}"


def redact_task_summary(value: Any, *, max_chars: int = TASK_CONTRACT_MAX_SUMMARY_CHARS) -> str:
    """Return a short, secret-scrubbed task summary safe for recovery prompts."""
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 15].rstrip() + " ...[truncated]"
    return text


def _clean_str_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return []
    cleaned: list[str] = []
    for item in values:
        text = redact_task_summary(item, max_chars=160)
        if text:
            cleaned.append(text)
    return cleaned[:20]


def _normalize_contract_status(value: Any) -> str:
    status = str(value or "active").strip().lower()
    if status in {"active", "paused", "completed", "superseded"}:
        return status
    if status in {"done", "succeeded", "success"}:
        return "completed"
    return "active"


def _contract_is_recoverable(contract: Any) -> bool:
    if not isinstance(contract, dict):
        return False
    return str(contract.get("status") or "active") in TASK_CONTRACT_ACTIVE_STATUSES


@dataclass
class ActiveTaskRecord:
    session_key: str
    session_key_hash: Optional[str] = None
    execution_id: Optional[str] = None
    session_id: Optional[str] = None
    platform: Optional[str] = None
    chat_id: Optional[str] = None
    thread_id: Optional[str] = None
    repo_path: Optional[str] = None
    branch: Optional[str] = None
    head: Optional[str] = None
    mode: Optional[str] = None
    command_label: Optional[str] = None
    command: Optional[str] = None
    task_summary: Optional[str] = None
    task_summary_safe: Optional[str] = None
    task_contract: Optional[dict[str, Any]] = None
    status: str = "unknown"
    pid: Optional[int] = None
    process_session_id: Optional[str] = None
    exit_code: Optional[int] = None
    completed_at: Optional[str] = None
    output_tail: Optional[str] = None
    output_path: Optional[str] = None
    latest_log_path: Optional[str] = None
    latest_summary_path: Optional[str] = None
    start_time: Optional[str] = None
    last_heartbeat_time: Optional[str] = None
    last_observed_process_state: Optional[str] = None
    final_report_status: Optional[str] = None
    final_report_path: Optional[str] = None
    final_report_error: Optional[str] = None
    final_report_updated_at: Optional[str] = None
    expected_commit: Optional[str] = None
    expected_files: Optional[str] = None
    updated_at: str = ""
    resume_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveTaskRecord":
        fields = {name for name in cls.__dataclass_fields__}
        if data.get("mode") == "foreground_session":
            fields = fields & set(FOREGROUND_SESSION_FIELDS)
        payload = {key: data.get(key) for key in fields if key in data}
        if "session_key" in data:
            payload["session_key"] = data.get("session_key")
        if not payload.get("updated_at"):
            payload["updated_at"] = _utc_now_iso()
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        if self.mode == "foreground_session":
            raw = asdict(self)
            return {
                key: raw.get(key)
                for key in FOREGROUND_SESSION_FIELDS
                if raw.get(key) not in (None, "", [], {})
            }
        return asdict(self)

    def is_fresh(self, ttl_seconds: int = DEFAULT_ACTIVE_TASK_TTL_SECONDS) -> bool:
        updated = _parse_iso_timestamp(self.updated_at)
        if updated is None:
            return False
        age = datetime.now(timezone.utc) - updated
        return age.total_seconds() <= ttl_seconds

    def freshness_ttl_seconds(self) -> int:
        if self.mode == "foreground_session":
            return FOREGROUND_SESSION_TTL_SECONDS
        return DEFAULT_ACTIVE_TASK_TTL_SECONDS

    def has_usable_workspace(self) -> bool:
        if self.status not in ACTIVE_TASK_STATUSES:
            return False
        if not self.repo_path:
            return False
        try:
            path = Path(self.repo_path).expanduser()
            if not path.exists():
                return False
            if self.mode != "foreground_session":
                return True
            if resolve_git_toplevel(path) is None:
                return False
            return bool(self.head or resolve_git_head(path))
        except OSError:
            return False


class ActiveTaskStore:
    """Small JSON store keyed by gateway session_key."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else get_hermes_home() / "session_active_tasks.json"
        self._lock = threading.Lock()

    def _read_unlocked(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.debug("active-task store file is absent: %s", self.path)
            return {}
        except json.JSONDecodeError as exc:
            logger.warning("failed to parse active-task store %s: %s", self.path, exc)
            return {}
        except OSError as exc:
            logger.warning("failed to read active-task store %s: %s", self.path, exc)
            return {}
        return data if isinstance(data, dict) else {}

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        atomic_json_write(self.path, data, indent=2)

    def inspect_metadata(self) -> dict[str, Any]:
        """Return safe store metadata for recovery diagnostics."""
        exists = self.path.exists()
        metadata: dict[str, Any] = {
            "exists": exists,
            "parsed": False,
            "record_count": 0,
            "foreground_count": 0,
        }
        if not exists:
            return metadata
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("failed to parse active-task store %s: %s", self.path, exc)
            return metadata
        except OSError as exc:
            logger.warning("failed to read active-task store %s: %s", self.path, exc)
            return metadata
        if not isinstance(data, dict):
            return metadata
        metadata["parsed"] = True
        metadata["record_count"] = len(data)
        metadata["foreground_count"] = sum(
            1
            for record in data.values()
            if isinstance(record, dict) and record.get("mode") == "foreground_session"
        )
        return metadata

    def get(self, session_key: str) -> Optional[ActiveTaskRecord]:
        if not session_key:
            return None
        with self._lock:
            raw = self._read_unlocked().get(session_key)
        if not isinstance(raw, dict):
            return None
        raw = dict(raw)
        raw.setdefault("session_key", session_key)
        try:
            return ActiveTaskRecord.from_dict(raw)
        except TypeError:
            return None

    def upsert(self, *, session_key: str, **fields: Any) -> ActiveTaskRecord:
        if not session_key:
            raise ValueError("session_key is required")

        with self._lock:
            data = self._read_unlocked()
            existing = data.get(session_key) if isinstance(data.get(session_key), dict) else {}
            payload = dict(existing)
            payload["session_key"] = session_key
            for key, value in fields.items():
                if key not in ActiveTaskRecord.__dataclass_fields__:
                    continue
                if key in {"pid", "exit_code"}:
                    payload[key] = int(value) if value is not None else None
                elif key == "status":
                    payload[key] = _clean_optional_str(value) or "unknown"
                elif key == "final_report_status":
                    status = _clean_optional_str(value)
                    payload[key] = status if status in FINAL_REPORT_STATUSES else None
                elif key == "task_contract":
                    payload[key] = value if isinstance(value, dict) else None
                elif key == "task_summary_safe":
                    payload[key] = redact_task_summary(value)
                else:
                    payload[key] = _clean_optional_str(value)
            payload["updated_at"] = _utc_now_iso()
            record = ActiveTaskRecord.from_dict(payload)
            data[session_key] = record.to_dict()
            self._write_unlocked(data)
            return record

    def persist_final_report(
        self,
        *,
        session_key: str,
        content: str,
        status: str = "pending",
        error: Optional[str] = None,
    ) -> ActiveTaskRecord:
        """Persist a final report before attempting platform delivery."""
        if not session_key:
            raise ValueError("session_key is required")
        if status not in FINAL_REPORT_STATUSES:
            raise ValueError(f"invalid final report status: {status}")

        reports_dir = self.path.parent / "final_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        safe_key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in session_key)
        report_path = reports_dir / f"{safe_key}_{int(time.time() * 1000)}.txt"
        tmp_path = report_path.with_suffix(report_path.suffix + ".tmp")
        tmp_path.write_text(content or "", encoding="utf-8")
        tmp_path.replace(report_path)
        return self.upsert(
            session_key=session_key,
            final_report_status=status,
            final_report_path=str(report_path),
            final_report_error=error,
            final_report_updated_at=_utc_now_iso(),
        )

    def mark_final_report(
        self,
        *,
        session_key: str,
        status: str,
        error: Optional[str] = None,
    ) -> Optional[ActiveTaskRecord]:
        if not session_key:
            return None
        if status not in FINAL_REPORT_STATUSES:
            raise ValueError(f"invalid final report status: {status}")
        return self.upsert(
            session_key=session_key,
            final_report_status=status,
            final_report_error=error,
            final_report_updated_at=_utc_now_iso(),
        )

    def replace_foreground_session(
        self,
        *,
        session_key: str,
        repo_path: str,
        branch: Optional[str] = None,
        head: Optional[str] = None,
        task_summary: Optional[str] = None,
        task_type: Optional[str] = None,
        expected_paths: Any = None,
        risk_level: Optional[str] = None,
        allowed_operations: Any = None,
        forbidden_operations: Any = None,
        restart_policy: Optional[str] = None,
        validation_required: bool | None = None,
        source: str = "foreground_turn",
        status: str = "active",
    ) -> ActiveTaskRecord:
        if not session_key:
            raise ValueError("session_key is required")

        with self._lock:
            data = self._read_unlocked()
            existing = data.get(session_key) if isinstance(data.get(session_key), dict) else {}
        existing_contract = (
            existing.get("task_contract")
            if isinstance(existing, dict) and isinstance(existing.get("task_contract"), dict)
            else None
        )
        now = _utc_now_iso()
        safe_summary = redact_task_summary(task_summary) or (
            redact_task_summary(existing.get("task_summary_safe"))
            if isinstance(existing, dict)
            else ""
        )
        contract = None
        if safe_summary:
            created_at = (
                existing_contract.get("created_at")
                if isinstance(existing_contract, dict)
                else None
            )
            contract = {
                "session_key_hash": _hash_ref(session_key),
                "task_summary_safe": safe_summary,
                "task_type": redact_task_summary(
                    task_type
                    or (existing_contract or {}).get("task_type")
                    or "foreground_turn",
                    max_chars=80,
                ),
                "intended_repo": _clean_optional_str(repo_path),
                "intended_branch": redact_task_summary(branch, max_chars=120),
                "expected_paths": _clean_str_list(
                    expected_paths if expected_paths is not None else (existing_contract or {}).get("expected_paths")
                ),
                "risk_level": redact_task_summary(
                    risk_level or (existing_contract or {}).get("risk_level") or "unknown",
                    max_chars=80,
                ),
                "allowed_operations": _clean_str_list(
                    allowed_operations if allowed_operations is not None else (existing_contract or {}).get("allowed_operations")
                ),
                "forbidden_operations": _clean_str_list(
                    forbidden_operations if forbidden_operations is not None else (existing_contract or {}).get("forbidden_operations")
                ),
                "restart_policy": redact_task_summary(
                    restart_policy
                    or (existing_contract or {}).get("restart_policy")
                    or "resume_with_safe_summary",
                    max_chars=120,
                ),
                "validation_required": bool(
                    validation_required
                    if validation_required is not None
                    else (existing_contract or {}).get("validation_required", False)
                ),
                "created_at": created_at or now,
                "updated_at": now,
                "source": redact_task_summary(
                    source or (existing_contract or {}).get("source"),
                    max_chars=80,
                ) or "foreground_turn",
                "status": _normalize_contract_status(
                    status or (existing_contract or {}).get("status")
                ),
            }
        payload = {
            "session_key": session_key,
            "session_key_hash": _hash_ref(session_key),
            "repo_path": _clean_optional_str(repo_path),
            "branch": _clean_optional_str(branch),
            "head": _clean_optional_str(head),
            "mode": "foreground_session",
            "status": "active",
            "task_summary_safe": safe_summary or None,
            "task_contract": contract,
            "updated_at": now,
        }
        record = ActiveTaskRecord.from_dict(payload)
        with self._lock:
            data[session_key] = record.to_dict()
            self._write_unlocked(data)
        return record

    def update_task_contract(
        self,
        *,
        session_key: str,
        task_summary: str,
        source: str = "foreground_turn",
        status: str = "active",
        task_type: Optional[str] = None,
        intended_repo: Optional[str] = None,
        intended_branch: Optional[str] = None,
        expected_paths: Any = None,
        risk_level: Optional[str] = None,
        allowed_operations: Any = None,
        forbidden_operations: Any = None,
        restart_policy: Optional[str] = None,
        validation_required: bool | None = None,
    ) -> ActiveTaskRecord:
        if not session_key:
            raise ValueError("session_key is required")
        safe_summary = redact_task_summary(task_summary)
        if not safe_summary:
            raise ValueError("task_summary is required")

        now = _utc_now_iso()
        with self._lock:
            data = self._read_unlocked()
            existing = data.get(session_key) if isinstance(data.get(session_key), dict) else {}
            contract = existing.get("task_contract") if isinstance(existing.get("task_contract"), dict) else {}
            created_at = contract.get("created_at") if isinstance(contract, dict) else None
            repo = _clean_optional_str(intended_repo) or _clean_optional_str(existing.get("repo_path"))
            branch = (
                redact_task_summary(intended_branch, max_chars=120)
                or redact_task_summary(existing.get("branch"), max_chars=120)
            )
            updated_contract = {
                "session_key_hash": _hash_ref(session_key),
                "task_summary_safe": safe_summary,
                "task_type": redact_task_summary(task_type or contract.get("task_type") or "foreground_turn", max_chars=80),
                "intended_repo": repo,
                "intended_branch": branch,
                "expected_paths": _clean_str_list(expected_paths or contract.get("expected_paths")),
                "risk_level": redact_task_summary(risk_level or contract.get("risk_level") or "unknown", max_chars=80),
                "allowed_operations": _clean_str_list(allowed_operations or contract.get("allowed_operations")),
                "forbidden_operations": _clean_str_list(forbidden_operations or contract.get("forbidden_operations")),
                "restart_policy": redact_task_summary(
                    restart_policy or contract.get("restart_policy") or "resume_with_safe_summary",
                    max_chars=120,
                ),
                "validation_required": bool(
                    validation_required
                    if validation_required is not None
                    else contract.get("validation_required", False)
                ),
                "created_at": created_at or now,
                "updated_at": now,
                "source": redact_task_summary(source, max_chars=80) or "foreground_turn",
                "status": _normalize_contract_status(status),
            }
            payload = dict(existing)
            payload["session_key"] = session_key
            payload["session_key_hash"] = _hash_ref(session_key)
            payload["task_summary_safe"] = safe_summary
            payload["task_contract"] = updated_contract
            payload["updated_at"] = now
            if not payload.get("mode"):
                payload["mode"] = "foreground_session"
            if not payload.get("status"):
                payload["status"] = "active"
            record = ActiveTaskRecord.from_dict(payload)
            data[session_key] = record.to_dict()
            self._write_unlocked(data)
            return record


def resolve_git_branch(repo_path: str | os.PathLike[str] | None) -> Optional[str]:
    if not repo_path:
        return None
    path = Path(repo_path).expanduser()
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    branch = (result.stdout or "").strip()
    return branch or None


def resolve_git_toplevel(repo_path: str | os.PathLike[str] | None) -> Optional[str]:
    if not repo_path:
        return None
    path = Path(repo_path).expanduser()
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    toplevel = (result.stdout or "").strip()
    return toplevel or None


def resolve_git_head(repo_path: str | os.PathLike[str] | None) -> Optional[str]:
    if not repo_path:
        return None
    path = Path(repo_path).expanduser()
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    head = (result.stdout or "").strip()
    return head or None


def build_active_task_recovery_note(
    record: ActiveTaskRecord | None,
    resume_reason: str | None = None,
) -> str:
    reason = resume_reason or (record.resume_reason if record else None) or "restart_timeout"
    reason_phrase = (
        "a gateway restart"
        if reason == "restart_timeout"
        else "a gateway shutdown"
        if reason == "shutdown_timeout"
        else "a gateway interruption"
    )
    base = (
        "[System note: Your previous turn in this session was interrupted by "
        f"{reason_phrase}. The conversation history below is intact."
    )

    if record is None:
        return (
            base
            + " Active workspace/process state: unknown. Do not silently default "
            "to the gateway working directory as the active project. Report that "
            "the previous repo, branch, command, and process status are unknown "
            "before continuing. Next safe recovery check: inspect durable active "
            "task/process records for this session_key, then ask before running "
            "project commands.]"
        )

    safe_contract = record.task_contract if isinstance(record.task_contract, dict) else None
    safe_contract_recoverable = _contract_is_recoverable(safe_contract)
    safe_summary = (
        record.task_summary_safe
        if record.task_summary_safe and (safe_contract is None or safe_contract_recoverable)
        else None
    )
    task_known = bool(safe_summary or record.task_summary or record.command)
    task = safe_summary or record.task_summary or record.command or "unknown"
    lines = [
        base,
        f" Previous active task: {task}",
        f"Previous repo path: {record.repo_path or 'unknown'}",
        f"Previous branch: {record.branch or 'unknown'}",
        f"Previous HEAD: {record.head or 'unknown'}",
        f"Previous command: {record.command or 'unknown'}",
        f"Process status: {record.status or 'unknown'}",
    ]
    if safe_summary:
        lines.append(f"Recovered safe task summary: {safe_summary}")
        if safe_contract:
            lines.append(
                "Safe task contract: "
                f"source={safe_contract.get('source') or 'unknown'}, "
                f"status={safe_contract.get('status') or 'active'}, "
                f"risk_level={safe_contract.get('risk_level') or 'unknown'}, "
                f"restart_policy={safe_contract.get('restart_policy') or 'unknown'}, "
                f"validation_required={bool(safe_contract.get('validation_required'))}"
            )
            intended_repo = safe_contract.get("intended_repo")
            if intended_repo:
                lines.append(f"Intended repo from safe contract: {intended_repo}")
            expected_paths = safe_contract.get("expected_paths")
            if isinstance(expected_paths, list) and expected_paths:
                lines.append(f"Expected paths from safe contract: {', '.join(map(str, expected_paths[:10]))}")
    if record.mode == "foreground_session" and not task_known:
        lines.append("Exact interrupted session record: found")
        lines.append(
            "Recovery task body: unknown; this is a workspace-only foreground "
            "record, not a persisted task record."
        )
    if record.mode == "foreground_session":
        lines.append(
            "Do not infer the task from unrelated logs, dirty checkout files, "
            "or broad history searches; ask the user before continuing."
        )
    if record.process_session_id or record.pid is not None:
        process_ref = record.process_session_id or f"pid:{record.pid}"
        lines.append(f"Process/session id: {process_ref}")
    if record.latest_log_path:
        lines.append(f"Latest log path: {record.latest_log_path}")
    if record.latest_summary_path:
        lines.append(f"Latest summary path: {record.latest_summary_path}")
    lines.append(
        "Next safe recovery check: verify the process/session status and latest "
        "log or summary path before running continuation commands.]"
    )
    return "\n".join(lines)


def render_safe_task_contract_for_prompt(record: ActiveTaskRecord | None) -> str:
    """Render safe active-task contract metadata for prompt-cache-aware context."""
    if record is None:
        return ""
    contract = record.task_contract if isinstance(record.task_contract, dict) else None
    if contract is not None and not _contract_is_recoverable(contract):
        return ""
    summary = record.task_summary_safe or (contract or {}).get("task_summary_safe")
    if not summary:
        return ""
    lines = [
        "## Safe Active Task Contract",
        "",
        f"Recovered safe task summary: {summary}",
        f"Task type: {(contract or {}).get('task_type') or record.mode or 'unknown'}",
        f"Intended repo: {(contract or {}).get('intended_repo') or record.repo_path or 'unknown'}",
        f"Intended branch: {(contract or {}).get('intended_branch') or record.branch or 'unknown'}",
        f"Risk level: {(contract or {}).get('risk_level') or 'unknown'}",
        f"Restart policy: {(contract or {}).get('restart_policy') or 'unknown'}",
        f"Validation required: {bool((contract or {}).get('validation_required'))}",
        f"Contract updated at: {(contract or {}).get('updated_at') or record.updated_at}",
        "",
        "Use this summary only as safe recovery context. Do not infer from logs, dirty files, or unrelated history.",
    ]
    expected_paths = (contract or {}).get("expected_paths")
    if isinstance(expected_paths, list) and expected_paths:
        lines.insert(5, f"Expected paths: {', '.join(map(str, expected_paths[:10]))}")
    return "\n".join(lines)
