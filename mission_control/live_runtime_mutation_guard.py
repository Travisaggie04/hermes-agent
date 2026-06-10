"""Hard guard for accepted/rollback runtime git mutations.

AcceptedBaselineRecord runtimes are immutable runtime artifacts. General
``hermes update`` and branch-changing git commands must not run from those
paths; controlled deploy/recovery code must opt in explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
from typing import Literal

from hermes_constants import get_hermes_home
from mission_control.records import AcceptedBaselineRecord, JsonlRecordStore

MutationAction = Literal["checkout", "switch", "reset", "pull", "update"]

ALLOWED_EXCEPTION_CONTEXTS = frozenset(
    {"controlled_deploy", "runtime_recovery", "explicit_live_runtime_switch"}
)

_LIVE_BLOCKERS = {
    "checkout": "live_runtime_checkout_blocked",
    "switch": "live_runtime_switch_blocked",
    "reset": "live_runtime_reset_blocked",
    "pull": "live_runtime_pull_blocked",
    "update": "live_runtime_update_blocked",
}

_ROLLBACK_BLOCKERS = {
    "checkout": "rollback_runtime_checkout_blocked",
    "switch": "rollback_runtime_checkout_blocked",
    "reset": "rollback_runtime_checkout_blocked",
    "pull": "rollback_runtime_checkout_blocked",
    "update": "rollback_runtime_update_blocked",
}

_GIT_MUTATION_RE = re.compile(r"(?:^|[;&|]\s*)git\s+(checkout|switch|reset|pull)\b")


@dataclass(frozen=True)
class RuntimeMutationDecision:
    allowed: bool
    action: str
    blocker: str | None = None
    protected_kind: str | None = None
    runtime_path: str | None = None
    cwd: str | None = None
    exception_context: str | None = None
    reason: str | None = None


class LiveRuntimeMutationBlocked(RuntimeError):
    """Raised when a mutating operation targets an accepted/rollback runtime."""

    def __init__(self, decision: RuntimeMutationDecision) -> None:
        self.decision = decision
        super().__init__(decision.reason or decision.blocker or "live_runtime_mutation_blocked")


def _record_store_path() -> Path:
    return get_hermes_home() / "mission-control" / "records.jsonl"


def _latest_accepted_baseline() -> AcceptedBaselineRecord | None:
    path = _record_store_path()
    if not path.exists() or path.stat().st_size == 0:
        return None
    records = JsonlRecordStore(path).read_latest(AcceptedBaselineRecord, limit=1)
    if not records:
        return None
    return records[-1][1]


def _normalize_path(path: str | Path | None) -> Path:
    if path is None:
        path = os.getcwd()
    return Path(path).expanduser().resolve()


def _git_top_level(cwd: Path) -> Path:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return cwd
    top = proc.stdout.strip()
    if proc.returncode == 0 and top:
        try:
            return Path(top).expanduser().resolve()
        except Exception:
            return cwd
    return cwd


def _path_matches(candidate: Path, runtime_path: str) -> bool:
    if not runtime_path:
        return False
    protected = Path(runtime_path).expanduser().resolve()
    return candidate == protected


def _active_exception_context(explicit: str | None = None) -> str | None:
    context = explicit or os.environ.get("HERMES_LIVE_RUNTIME_MUTATION_CONTEXT", "")
    context = context.strip()
    if context in ALLOWED_EXCEPTION_CONTEXTS:
        return context
    return None


def evaluate_runtime_mutation(
    action: str,
    *,
    cwd: str | Path | None = None,
    exception_context: str | None = None,
) -> RuntimeMutationDecision:
    normalized_action = action.strip().lower()
    if normalized_action not in _LIVE_BLOCKERS:
        return RuntimeMutationDecision(allowed=True, action=normalized_action, cwd=str(_normalize_path(cwd)))

    baseline = _latest_accepted_baseline()
    current = _normalize_path(cwd)
    git_top = _git_top_level(current)
    context = _active_exception_context(exception_context)

    if baseline is None:
        return RuntimeMutationDecision(allowed=True, action=normalized_action, cwd=str(current))

    if _path_matches(git_top, baseline.runtime_path):
        if context:
            return RuntimeMutationDecision(
                allowed=True,
                action=normalized_action,
                protected_kind="live",
                runtime_path=baseline.runtime_path,
                cwd=str(current),
                exception_context=context,
            )
        blocker = _LIVE_BLOCKERS[normalized_action]
        return RuntimeMutationDecision(
            allowed=False,
            action=normalized_action,
            blocker=blocker,
            protected_kind="live",
            runtime_path=baseline.runtime_path,
            cwd=str(current),
            reason=f"{blocker}: refusing {normalized_action} inside accepted live runtime {baseline.runtime_path}",
        )

    if _path_matches(git_top, baseline.rollback_runtime_path):
        if context:
            return RuntimeMutationDecision(
                allowed=True,
                action=normalized_action,
                protected_kind="rollback",
                runtime_path=baseline.rollback_runtime_path,
                cwd=str(current),
                exception_context=context,
            )
        blocker = _ROLLBACK_BLOCKERS[normalized_action]
        return RuntimeMutationDecision(
            allowed=False,
            action=normalized_action,
            blocker=blocker,
            protected_kind="rollback",
            runtime_path=baseline.rollback_runtime_path,
            cwd=str(current),
            reason=f"{blocker}: refusing {normalized_action} inside rollback runtime {baseline.rollback_runtime_path}",
        )

    return RuntimeMutationDecision(allowed=True, action=normalized_action, cwd=str(current))


def assert_runtime_mutation_allowed(
    action: str,
    *,
    cwd: str | Path | None = None,
    exception_context: str | None = None,
) -> RuntimeMutationDecision:
    decision = evaluate_runtime_mutation(
        action,
        cwd=cwd,
        exception_context=exception_context,
    )
    if not decision.allowed:
        raise LiveRuntimeMutationBlocked(decision)
    return decision


def detect_git_mutation_action(command: str) -> str | None:
    match = _GIT_MUTATION_RE.search(command)
    if match:
        return match.group(1).lower()
    return None


def block_result(decision: RuntimeMutationDecision) -> dict[str, object]:
    return {
        "approved": False,
        "message": f"BLOCKED: {decision.reason}",
        "pattern_key": decision.blocker,
        "description": decision.reason,
        "outcome": "blocked",
        "user_consent": False,
    }
