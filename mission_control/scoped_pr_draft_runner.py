"""Gated scoped draft-PR runner for one approved docs-only lane.

The runner is intentionally narrow: it reads the record-sourced execution gate,
creates one temporary worktree, edits one approved docs file, creates one commit,
pushes one branch, and opens one draft PR. It never merges, deploys, restarts,
switches runtimes, dispatches workers, uses session-send, or reads secrets.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Protocol

from mission_control.workspace_status_records import build_workspace_status_from_records


DEFAULT_REPO = "Travisaggie04/hermes-agent"
DEFAULT_BASE_BRANCH = "accepted-live/approval-safety-5ad8906"
APPROVED_RUNNER_ID = "mission_control_scoped_pr_draft_runner"


class ScopedPrDraftRunnerError(RuntimeError):
    """Raised when the scoped PR runner refuses to continue."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def __call__(self, args: list[str], *, cwd: Path | None = None, check: bool = True) -> CommandResult:
        ...


@dataclass(frozen=True)
class ScopedPrDraftResult:
    run_id: str
    approval_id: str
    branch_name: str
    base_branch: str
    commit_sha: str
    pr_url: str
    changed_files: tuple[str, ...]
    tests: tuple[str, ...]
    draft: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "approval_id": self.approval_id,
            "branch_name": self.branch_name,
            "base_branch": self.base_branch,
            "commit_sha": self.commit_sha,
            "pr_url": self.pr_url,
            "changed_files": list(self.changed_files),
            "tests": list(self.tests),
            "draft": self.draft,
        }


def load_scoped_pr_execution_packet(
    *,
    run_id: str,
    records_path: str | Path | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = build_workspace_status_from_records(payload or {}, records_path=records_path)
    gate = status.get("scoped_pr_execution_eligibility")
    if not isinstance(gate, dict):
        raise ScopedPrDraftRunnerError("scoped PR execution gate is unavailable")
    packet = gate.get("packet")
    if not isinstance(packet, dict):
        raise ScopedPrDraftRunnerError("scoped PR execution packet is unavailable")
    if packet.get("run_id") != run_id:
        raise ScopedPrDraftRunnerError("scoped PR execution packet run_id does not match requested run")
    if gate.get("eligible") is not True or gate.get("one_run_authorized") is not True:
        reasons = gate.get("blocked_reasons") if isinstance(gate.get("blocked_reasons"), list) else []
        reason_text = "; ".join(str(item) for item in reasons[:8]) or "gate is not eligible"
        raise ScopedPrDraftRunnerError(f"scoped PR execution is not authorized: {reason_text}")
    return packet


def run_scoped_pr_draft(
    packet: dict[str, Any],
    *,
    worktree_root: str | Path,
    repo: str = DEFAULT_REPO,
    command_runner: CommandRunner | None = None,
) -> ScopedPrDraftResult:
    runner = command_runner or _run_command
    plan = _validate_packet(packet, repo=repo)
    worktree = Path(worktree_root) / plan["run_id"]
    if worktree.exists():
        raise ScopedPrDraftRunnerError("scoped PR worktree already exists; refusing to reuse or delete it")

    _assert_no_existing_pr(repo=repo, branch_name=plan["branch_name"], runner=runner)
    repo_url = f"https://github.com/{repo}.git"
    _assert_no_existing_remote_branch(repo_url=repo_url, branch_name=plan["branch_name"], runner=runner)

    worktree.parent.mkdir(parents=True, exist_ok=True)
    runner(["git", "clone", "--branch", plan["base_branch"], repo_url, str(worktree)])
    runner(["git", "checkout", "-b", plan["branch_name"]], cwd=worktree)

    target_path = worktree / plan["allowed_file"]
    _append_docs_note(
        target_path,
        run_id=plan["run_id"],
        approval_id=plan["approval_id"],
        edit_instruction=plan["edit_instruction"],
    )
    changed_files = _changed_files(worktree, runner)
    if changed_files != (plan["allowed_file"],):
        raise ScopedPrDraftRunnerError(f"changed files are outside approved scope: {', '.join(changed_files)}")

    runner(["git", "diff", "--check"], cwd=worktree)
    runner(["git", "add", "--", plan["allowed_file"]], cwd=worktree)
    runner(["git", "commit", "-m", plan["draft_pr_title"]], cwd=worktree)
    commit_sha = runner(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()
    committed_files = _committed_files(worktree, runner)
    if committed_files != (plan["allowed_file"],):
        raise ScopedPrDraftRunnerError(f"commit changed files are outside approved scope: {', '.join(committed_files)}")

    runner(["git", "push", "origin", f"HEAD:refs/heads/{plan['branch_name']}"], cwd=worktree)
    pr_create = runner(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            plan["base_branch"],
            "--head",
            plan["branch_name"],
            "--draft",
            "--title",
            plan["draft_pr_title"],
            "--body",
            _draft_pr_body(plan),
        ],
        cwd=worktree,
    )
    pr_url = pr_create.stdout.strip().splitlines()[-1].strip()
    pr_state = _gh_pr_view(repo=repo, branch_name=plan["branch_name"], runner=runner)
    _verify_created_pr(pr_state, plan=plan)

    if not pr_url:
        pr_url = str(pr_state.get("url") or "")
    return ScopedPrDraftResult(
        run_id=plan["run_id"],
        approval_id=plan["approval_id"],
        branch_name=plan["branch_name"],
        base_branch=plan["base_branch"],
        commit_sha=commit_sha,
        pr_url=pr_url,
        changed_files=committed_files,
        tests=("git diff --check",),
        draft=True,
    )


def run_from_records(
    *,
    run_id: str,
    records_path: str | Path | None = None,
    worktree_root: str | Path,
    repo: str = DEFAULT_REPO,
    payload: dict[str, Any] | None = None,
    command_runner: CommandRunner | None = None,
) -> ScopedPrDraftResult:
    packet = load_scoped_pr_execution_packet(run_id=run_id, records_path=records_path, payload=payload)
    return run_scoped_pr_draft(
        packet,
        worktree_root=worktree_root,
        repo=repo,
        command_runner=command_runner,
    )


def _run_command(args: list[str], *, cwd: Path | None = None, check: bool = True) -> CommandResult:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = CommandResult(completed.returncode, completed.stdout, completed.stderr)
    if check and result.returncode != 0:
        raise ScopedPrDraftRunnerError(
            f"command failed ({args[0]}): {_safe_command_output(result.stderr or result.stdout)}"
        )
    return result


def _validate_packet(packet: dict[str, Any], *, repo: str) -> dict[str, str]:
    if packet.get("runner_id") != APPROVED_RUNNER_ID:
        raise ScopedPrDraftRunnerError("packet is not bound to the scoped draft PR runner")
    if packet.get("mode") != "scoped_pr_draft":
        raise ScopedPrDraftRunnerError("packet mode must be scoped_pr_draft")
    if packet.get("draft_pr_required") is not True:
        raise ScopedPrDraftRunnerError("packet must require a draft PR")
    for key in ("dispatch_enabled", "session_send_enabled", "worker_dispatch_enabled", "merge_enabled", "deploy_enabled", "restart_enabled", "runtime_switch_enabled"):
        if packet.get(key) is not False:
            raise ScopedPrDraftRunnerError(f"packet {key} must be false")
    for key, expected in (("max_files", 1), ("max_commits", 1), ("max_prs", 1)):
        if packet.get(key) != expected:
            raise ScopedPrDraftRunnerError(f"packet {key} must be exactly {expected}")

    scope = packet.get("scope") if isinstance(packet.get("scope"), dict) else {}
    files = tuple(str(item).replace("\\", "/").strip() for item in scope.get("files", ()) if str(item).strip())
    if len(files) != 1 or tuple(scope.get("directories", ())):
        raise ScopedPrDraftRunnerError("packet must approve exactly one file and no directories")
    allowed_file = files[0]
    if not _safe_docs_file(allowed_file):
        raise ScopedPrDraftRunnerError("packet file scope must be a safe docs markdown path")

    branch_name = str(packet.get("branch_name") or "").strip()
    if not _safe_branch_name(branch_name):
        raise ScopedPrDraftRunnerError("packet branch name is unsafe")
    base_branch = str(packet.get("base_branch") or DEFAULT_BASE_BRANCH).strip()
    if base_branch != DEFAULT_BASE_BRANCH:
        raise ScopedPrDraftRunnerError("packet base branch is outside the approved scoped PR lane")
    draft_pr_title = str(packet.get("draft_pr_title") or "").strip()
    if not draft_pr_title:
        raise ScopedPrDraftRunnerError("packet draft PR title is required")
    edit_instruction = str(packet.get("edit_instruction") or "").strip()
    if not edit_instruction:
        raise ScopedPrDraftRunnerError("packet edit instruction is required")
    if repo != DEFAULT_REPO:
        raise ScopedPrDraftRunnerError("runner is limited to Travisaggie04/hermes-agent")
    return {
        "run_id": str(packet.get("run_id") or "").strip(),
        "approval_id": str(packet.get("approval_id") or "").strip(),
        "branch_name": branch_name,
        "base_branch": base_branch,
        "draft_pr_title": draft_pr_title,
        "edit_instruction": edit_instruction,
        "allowed_file": allowed_file,
    }


def _append_docs_note(path: Path, *, run_id: str, approval_id: str, edit_instruction: str) -> None:
    if not path.exists() or not path.is_file():
        raise ScopedPrDraftRunnerError("approved docs file does not exist in worktree")
    original = path.read_text(encoding="utf-8")
    marker = f"<!-- scoped-pr-draft-runner:{run_id} -->"
    if marker in original:
        raise ScopedPrDraftRunnerError("approved docs file already contains this run marker")
    note = (
        f"\n\n{marker}\n"
        "### Scoped PR creation smoke test\n\n"
        f"- RunRecord: `{run_id}`\n"
        f"- ApprovalRecord: `{approval_id}`\n"
        f"- Scope: {edit_instruction}\n"
        "- Result target: one docs-only draft PR for human review; no merge, deploy, restart, or runtime switch.\n"
    )
    path.write_text(original.rstrip() + note, encoding="utf-8")


def _changed_files(worktree: Path, runner: CommandRunner) -> tuple[str, ...]:
    status = runner(["git", "status", "--short"], cwd=worktree).stdout
    files: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip().replace("\\", "/"))
    return tuple(files)


def _committed_files(worktree: Path, runner: CommandRunner) -> tuple[str, ...]:
    output = runner(["git", "diff", "--name-only", "HEAD~1..HEAD"], cwd=worktree).stdout
    return tuple(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())


def _assert_no_existing_remote_branch(*, repo_url: str, branch_name: str, runner: CommandRunner) -> None:
    result = runner(["git", "ls-remote", "--heads", repo_url, branch_name], check=False)
    if result.returncode == 0 and result.stdout.strip():
        raise ScopedPrDraftRunnerError("remote branch already exists")
    if result.returncode not in (0, 2):
        raise ScopedPrDraftRunnerError(f"could not verify remote branch absence: {_safe_command_output(result.stderr)}")


def _assert_no_existing_pr(*, repo: str, branch_name: str, runner: CommandRunner) -> None:
    result = runner(
        ["gh", "pr", "list", "--repo", repo, "--head", branch_name, "--state", "all", "--json", "number,url"],
        check=False,
    )
    if result.returncode != 0:
        raise ScopedPrDraftRunnerError(f"could not verify existing PR absence: {_safe_command_output(result.stderr)}")
    try:
        prs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ScopedPrDraftRunnerError("could not parse existing PR check") from exc
    if prs:
        raise ScopedPrDraftRunnerError("PR already exists for scoped PR branch")


def _gh_pr_view(*, repo: str, branch_name: str, runner: CommandRunner) -> dict[str, Any]:
    result = runner(
        [
            "gh",
            "pr",
            "view",
            branch_name,
            "--repo",
            repo,
            "--json",
            "url,isDraft,state,headRefName,baseRefName,files,commits",
        ]
    )
    try:
        value = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ScopedPrDraftRunnerError("could not parse created PR verification") from exc
    return value if isinstance(value, dict) else {}


def _verify_created_pr(pr_state: dict[str, Any], *, plan: dict[str, str]) -> None:
    if pr_state.get("isDraft") is not True:
        raise ScopedPrDraftRunnerError("created PR is not draft")
    if pr_state.get("state") != "OPEN":
        raise ScopedPrDraftRunnerError("created PR is not open")
    if pr_state.get("headRefName") != plan["branch_name"]:
        raise ScopedPrDraftRunnerError("created PR head branch mismatch")
    if pr_state.get("baseRefName") != plan["base_branch"]:
        raise ScopedPrDraftRunnerError("created PR base branch mismatch")
    files = pr_state.get("files") if isinstance(pr_state.get("files"), list) else []
    file_paths = tuple(str(item.get("path") or "").replace("\\", "/") for item in files if isinstance(item, dict))
    if file_paths != (plan["allowed_file"],):
        raise ScopedPrDraftRunnerError("created PR changed files are outside approved scope")
    commits = pr_state.get("commits") if isinstance(pr_state.get("commits"), list) else []
    if len(commits) != 1:
        raise ScopedPrDraftRunnerError("created PR must contain exactly one commit")


def _draft_pr_body(plan: dict[str, str]) -> str:
    return (
        "Scoped PR creation smoke test.\n\n"
        f"- RunRecord: `{plan['run_id']}`\n"
        f"- ApprovalRecord: `{plan['approval_id']}`\n"
        f"- Approved file: `{plan['allowed_file']}`\n"
        "- Draft only: yes\n"
        "- Merge/deploy/restart/runtime switch: forbidden\n"
        "- Human review required before any merge\n"
    )


def _safe_docs_file(path: str) -> bool:
    return (
        bool(path)
        and path.startswith("docs/")
        and path.endswith(".md")
        and not path.startswith("/")
        and not path.startswith(".")
        and ".." not in path.split("/")
        and "\\" not in path
    )


def _safe_branch_name(branch_name: str) -> bool:
    if not branch_name.startswith("codex/") or len(branch_name) > 120:
        return False
    if branch_name.endswith("/") or branch_name.endswith(".") or branch_name.endswith(".lock"):
        return False
    if ".." in branch_name or "//" in branch_name or "\\" in branch_name:
        return False
    disallowed = set(" ~^:?*[")
    return all(char not in disallowed and ord(char) >= 32 for char in branch_name)


def _safe_command_output(value: str) -> str:
    text = str(value or "").strip().replace("\x00", "")
    redacted_lines = []
    for line in text.splitlines()[:4]:
        lowered = line.lower()
        if any(marker in lowered for marker in ("token", "secret", "authorization", "cookie", "api_key")):
            redacted_lines.append("[redacted]")
        else:
            redacted_lines.append(line[:240])
    return "\n".join(redacted_lines) or "no command output"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one gated scoped draft-PR lane.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--records-path")
    parser.add_argument("--worktree-root", required=True)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    args = parser.parse_args(argv)
    result = run_from_records(
        run_id=args.run_id,
        records_path=args.records_path,
        worktree_root=args.worktree_root,
        repo=args.repo,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
