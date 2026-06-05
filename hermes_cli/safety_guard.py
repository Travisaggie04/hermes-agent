"""Safety Start Gate and Tool Guard helpers.

These helpers only evaluate local state and proposed tool use. They do not fix,
approve, clean, deploy, restart, or execute user work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import shlex
import subprocess
from typing import Any, Mapping, Sequence


EXPECTED_HERMES_REMOTE = "https://github.com/Travisaggie04/hermes-agent.git"
EXPECTED_SAFETY_BRANCH = "pr-safety-start-gate-tool-guard"
DEFAULT_MAX_STAGED_ENTRIES = 20

_READ_ONLY_LANE_MARKERS = (
    "read-only",
    "documentation-only",
    "docs-only",
    "stop-state",
    "cleanup-only",
)
_CLEANUP_LANE_MARKERS = ("cleanup", "revert")
_WRITE_TOOL_NAMES = {
    "write_file",
    "patch",
    "apply_patch",
    "edit_file",
    "replace_file",
    "create_file",
}
_SCAN_COMMANDS = {"rg", "grep", "find", "ls", "fd"}
_BROAD_TEST_COMMANDS = {"pytest", "python -m pytest", "scripts/run_tests.sh"}
_CLEANUP_COMMAND_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:rm\b|git\s+clean\b|git\s+reset\b|git\s+checkout\s+--\b|mv\b|trash\b)",
    re.IGNORECASE,
)
_EDIT_COMMAND_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:sudo\s+)?(?:cat\s*>|tee\b|sed\s+-i\b|perl\s+-i\b|python\b.*\bwrite_text\b|rm\b|mv\b|cp\b|git\s+(?:clean|reset|checkout\s+--))",
    re.IGNORECASE | re.DOTALL,
)
_SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)=([^\s]+)")


@dataclass(frozen=True)
class WorktreeCounts:
    staged: int = 0
    unstaged: int = 0
    untracked: int = 0


@dataclass(frozen=True)
class SafetyGuardConfig:
    expected_remote: str = EXPECTED_HERMES_REMOTE
    expected_branch: str = EXPECTED_SAFETY_BRANCH
    max_staged_entries: int = DEFAULT_MAX_STAGED_ENTRIES
    allow_wrong_branch: bool = False
    allow_detached_head: bool = False
    require_clean_worktree: bool = True
    active_lane: str = ""
    focused_tests_required: bool = False
    cleanup_target: str | None = None
    block_parent_directory_scans: bool = True
    quarantined_paths: Sequence[str] = field(default_factory=tuple)
    secret_values: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    summary: str
    details: tuple[str, ...] = ()
    counts: WorktreeCounts = WorktreeCounts()


def config_from_env() -> SafetyGuardConfig:
    """Build Tool Guard config from environment without reading secret values."""
    return SafetyGuardConfig(
        expected_remote=os.getenv("HERMES_EXPECTED_REMOTE", EXPECTED_HERMES_REMOTE),
        expected_branch=os.getenv("HERMES_EXPECTED_BRANCH", EXPECTED_SAFETY_BRANCH),
        max_staged_entries=_env_int("HERMES_MAX_STAGED_ENTRIES", DEFAULT_MAX_STAGED_ENTRIES),
        allow_wrong_branch=_env_bool("HERMES_ALLOW_WRONG_BRANCH"),
        allow_detached_head=_env_bool("HERMES_ALLOW_DETACHED_HEAD"),
        active_lane=os.getenv("HERMES_ACTIVE_LANE", ""),
        focused_tests_required=_env_bool("HERMES_FOCUSED_TESTS_REQUIRED"),
        cleanup_target=os.getenv("HERMES_CLEANUP_TARGET") or None,
        block_parent_directory_scans=not _env_bool("HERMES_ALLOW_PARENT_DIRECTORY_SCANS"),
        quarantined_paths=tuple(_split_env_list(os.getenv("HERMES_QUARANTINED_PATHS", ""))),
    )


def evaluate_start_gate(repo_path: str | Path, config: SafetyGuardConfig) -> SafetyDecision:
    """Evaluate whether implementation can start in *repo_path*."""
    repo = Path(repo_path).resolve()
    details: list[str] = []

    remote = _git(repo, "remote", "get-url", "origin")
    if remote != config.expected_remote:
        details.append(f"remote mismatch: origin is {remote!r}; expected {config.expected_remote!r}")

    branch = _git(repo, "branch", "--show-current")
    detached = branch == ""
    if detached:
        if not config.allow_detached_head:
            head = _git(repo, "rev-parse", "--short", "HEAD")
            details.append(f"detached HEAD: current commit {head}")
    elif branch != config.expected_branch and not config.allow_wrong_branch:
        details.append(f"branch mismatch: current branch {branch!r}; expected {config.expected_branch!r}")

    status_lines = _git(repo, "status", "--porcelain=v1").splitlines()
    counts = _count_status_entries(status_lines)
    has_conflicts = _has_unmerged_status(status_lines)
    if counts.staged > config.max_staged_entries:
        details.append(
            "staged-file explosion: "
            f"staged={counts.staged}, max={config.max_staged_entries}"
        )
    if config.require_clean_worktree and (counts.staged or counts.unstaged or counts.untracked):
        details.append(
            "dirty worktree: "
            f"staged={counts.staged}, unstaged={counts.unstaged}, untracked={counts.untracked}"
        )
    if _is_merge_or_rebase_state(repo) or has_conflicts:
        details.append("merge/rebase/conflict state detected")

    if details:
        return SafetyDecision(True, _summary_for_details(details), tuple(_redact_details(details, config)), counts)
    return SafetyDecision(False, "Safety Start Gate passed", counts=counts)


def evaluate_tool_guard(
    tool_name: str,
    args: Mapping[str, Any] | None,
    config: SafetyGuardConfig | None = None,
) -> SafetyDecision:
    """Evaluate whether a proposed tool call should be blocked."""
    cfg = config or config_from_env()
    tool_args = dict(args or {})
    lane = cfg.active_lane.lower().strip()
    command = _extract_command(tool_args)
    haystack = " ".join(_flatten_values(tool_args))
    details: list[str] = []

    if _is_read_only_lane(lane) and _is_write_or_edit_tool(tool_name, command):
        details.append(f"write/edit behavior blocked in lane {cfg.active_lane!r}")

    if cfg.focused_tests_required and command and _is_broad_test_command(command):
        details.append("broad test command blocked while focused tests are required")

    if command and _is_cleanup_command(command):
        if not _is_cleanup_lane(lane):
            details.append("cleanup command blocked outside cleanup/revert lane")
        elif not cfg.cleanup_target:
            details.append("cleanup command blocked because no exact cleanup target was named")
        elif cfg.cleanup_target not in command:
            details.append(f"cleanup command does not name required target {cfg.cleanup_target!r}")

    if cfg.block_parent_directory_scans and _is_parent_directory_scan(tool_name, command, tool_args):
        details.append("parent-directory scan blocked by default")

    if command and _is_parent_directory_write(command):
        details.append("edit tools must prove target-root containment before writing")

    quarantine_hit = _find_quarantined_path(haystack, cfg.quarantined_paths)
    if quarantine_hit:
        details.append(f"quarantined path access blocked: {quarantine_hit}")

    if details:
        return SafetyDecision(True, _summary_for_details(details), tuple(_redact_details(details, cfg)))
    return SafetyDecision(False, "Tool Guard passed")


def stop_report_for_tool(tool_name: str, args: Mapping[str, Any] | None) -> str | None:
    """Return a concise stop report for a tool call, or None when allowed."""
    decision = evaluate_tool_guard(tool_name, args, config_from_env())
    if not decision.blocked:
        return None
    return format_stop_report(decision)


def format_stop_report(decision: SafetyDecision) -> str:
    lines = [f"STOP: {decision.summary}"]
    if decision.counts != WorktreeCounts():
        lines.append(
            "Counts: "
            f"staged={decision.counts.staged}, "
            f"unstaged={decision.counts.unstaged}, "
            f"untracked={decision.counts.untracked}"
        )
    for detail in decision.details[:6]:
        lines.append(f"- {detail}")
    if len(decision.details) > 6:
        lines.append(f"- ... {len(decision.details) - 6} more detail(s)")
    return "\n".join(lines)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _count_status_entries(lines: Sequence[str]) -> WorktreeCounts:
    staged = unstaged = untracked = 0
    for line in lines:
        if not line:
            continue
        if line.startswith("??"):
            untracked += 1
            continue
        x = line[0]
        y = line[1] if len(line) > 1 else " "
        if x != " ":
            staged += 1
        if y != " ":
            unstaged += 1
    return WorktreeCounts(staged=staged, unstaged=unstaged, untracked=untracked)


def _has_unmerged_status(lines: Sequence[str]) -> bool:
    unmerged_pairs = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
    return any(line[:2] in unmerged_pairs for line in lines if len(line) >= 2)


def _is_merge_or_rebase_state(repo: Path) -> bool:
    git_dir_text = _git(repo, "rev-parse", "--git-dir")
    if not git_dir_text:
        return False
    git_dir = Path(git_dir_text)
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    return any(
        (git_dir / marker).exists()
        for marker in ("MERGE_HEAD", "REBASE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD")
    )


def _summary_for_details(details: Sequence[str]) -> str:
    first = details[0]
    return first.split(":", 1)[0]


def _is_read_only_lane(lane: str) -> bool:
    return any(marker in lane for marker in _READ_ONLY_LANE_MARKERS)


def _is_cleanup_lane(lane: str) -> bool:
    return any(marker in lane for marker in _CLEANUP_LANE_MARKERS)


def _is_write_or_edit_tool(tool_name: str, command: str) -> bool:
    if tool_name in _WRITE_TOOL_NAMES:
        return True
    if tool_name == "terminal" and command:
        return bool(_EDIT_COMMAND_RE.search(command) or ">" in command or "<<" in command)
    return False


def _extract_command(args: Mapping[str, Any]) -> str:
    value = args.get("command") or args.get("cmd") or args.get("input") or ""
    return str(value) if value is not None else ""


def _is_broad_test_command(command: str) -> bool:
    normalized = " ".join(command.strip().split())
    if normalized in _BROAD_TEST_COMMANDS:
        return True
    if normalized.startswith("pytest "):
        tokens = shlex.split(normalized)
        positional = [t for t in tokens[1:] if not t.startswith("-")]
        return not positional
    if normalized.startswith("python -m pytest"):
        tokens = shlex.split(normalized)
        positional = [t for t in tokens[3:] if not t.startswith("-")]
        return not positional
    return False


def _is_cleanup_command(command: str) -> bool:
    return bool(_CLEANUP_COMMAND_RE.search(command))


def _is_parent_directory_write(command: str) -> bool:
    if ">" not in command and "<<" not in command:
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return any(_is_parent_ref(token) for token in tokens)


def _is_parent_directory_scan(tool_name: str, command: str, args: Mapping[str, Any]) -> bool:
    values = _flatten_values(args)
    if tool_name == "search_files" and any(_is_parent_ref(value) for value in values):
        return True
    if not command:
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return False
    if tokens[0] not in _SCAN_COMMANDS:
        return False
    return any(_is_parent_ref(token) for token in tokens[1:])


def _is_parent_ref(value: str) -> bool:
    return value == ".." or value.startswith("../") or "/../" in value


def _find_quarantined_path(text: str, quarantined_paths: Sequence[str]) -> str | None:
    for raw in quarantined_paths:
        if not raw:
            continue
        path = str(raw)
        if path and path in text:
            return path
    return None


def _flatten_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        out: list[str] = []
        for item in value.values():
            out.extend(_flatten_values(item))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_flatten_values(item))
        return out
    return [str(value)]


def _redact_details(details: Sequence[str], config: SafetyGuardConfig) -> list[str]:
    redacted = []
    for detail in details:
        text = _SECRET_KEY_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", detail)
        for secret in config.secret_values:
            if secret:
                text = text.replace(secret, "[REDACTED]")
        redacted.append(text)
    return redacted


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except ValueError:
        return default


def _split_env_list(value: str) -> list[str]:
    if not value:
        return []
    return [item for item in (part.strip() for part in value.split(os.pathsep)) if item]
