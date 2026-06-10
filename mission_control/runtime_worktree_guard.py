"""Pure Runtime Worktree Guard for Mission Control.

This evaluator is intentionally inert. It accepts caller-supplied observed
state and reports whether a proposed development worktree/action would touch an
accepted or rollback runtime checkout. It does not inspect local resources,
call Git, persist records, or enforce anything at runtime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

GUARD_ID = "runtime_worktree_guard_v1"
DEFAULT_OFF = True
DRY_RUN_ONLY = True
ENFORCES_RUNTIME = False

BLOCKING_ACTION_CLASSES = frozenset(
    {
        "edit",
        "commit",
        "push",
        "pr_create",
        "build",
        "feature_checkout",
    }
)

RUNTIME_ALLOWED_ACTION_CLASSES = frozenset(
    {
        "controlled_deploy",
        "runtime_recovery",
        "read_only_smoke",
        "read_only_status",
    }
)

_BLOCKER_LABELS = {
    "dev_worktree_is_live_runtime": "development worktree is the accepted live runtime",
    "dev_worktree_is_rollback_runtime": "development worktree is the rollback runtime",
    "runtime_disk_head_mismatch": "accepted runtime disk HEAD does not match accepted record",
    "runtime_on_feature_branch": "accepted runtime is on a feature branch",
    "rollback_disk_head_mismatch": "rollback runtime disk HEAD does not match rollback record",
    "requested_dev_worktree_missing": "requested development worktree does not exist",
}


def evaluate_runtime_worktree_guard(observed_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate caller-supplied runtime/worktree state without side effects."""

    state = dict(observed_state or {})
    action_class = _safe_text(state.get("requested_action_class")).lower()
    action_blocks = action_class in BLOCKING_ACTION_CLASSES
    runtime_allowed = action_class in RUNTIME_ALLOWED_ACTION_CLASSES

    candidate_top = _normalized_path(state.get("candidate_git_top_level")) or _normalized_path(
        state.get("candidate_worktree_path")
    )
    accepted_runtime = _normalized_path(state.get("accepted_runtime_path"))
    rollback_runtime = _normalized_path(state.get("rollback_runtime_path"))

    observed_risks: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    def add_risk(name: str, *, blocks_for_dev: bool = True) -> None:
        _add_unique(observed_risks, name)
        if action_blocks and blocks_for_dev and not runtime_allowed:
            _add_unique(blockers, name)
        elif not action_blocks:
            _add_unique(warnings, name)

    if _safe_bool(state.get("requested_dev_worktree_exists"), default=True) is False:
        add_risk("requested_dev_worktree_missing")

    if candidate_top and accepted_runtime and candidate_top == accepted_runtime:
        add_risk("dev_worktree_is_live_runtime")

    if candidate_top and rollback_runtime and candidate_top == rollback_runtime:
        add_risk("dev_worktree_is_rollback_runtime")

    accepted_head = _safe_text(state.get("accepted_head"))
    accepted_disk_head = _safe_text(state.get("accepted_runtime_disk_head"))
    if accepted_head and accepted_disk_head and accepted_head != accepted_disk_head:
        add_risk("runtime_disk_head_mismatch")

    accepted_branch = _safe_text(state.get("accepted_runtime_branch"))
    if _is_feature_branch(accepted_branch):
        add_risk("runtime_on_feature_branch")

    rollback_head = _safe_text(state.get("rollback_head"))
    rollback_disk_head = _safe_text(state.get("rollback_runtime_disk_head"))
    if rollback_head and rollback_disk_head and rollback_head != rollback_disk_head:
        add_risk("rollback_disk_head_mismatch")

    if _safe_bool(state.get("candidate_status_clean"), default=True) is False and action_blocks:
        _add_unique(blockers, "candidate_worktree_not_clean")
    if _safe_bool(state.get("accepted_runtime_status_clean"), default=True) is False and action_blocks:
        _add_unique(blockers, "accepted_runtime_not_clean")
    if _safe_bool(state.get("rollback_runtime_status_clean"), default=True) is False and action_blocks:
        _add_unique(blockers, "rollback_runtime_not_clean")

    if blockers:
        decision_state = "blocked"
    elif observed_risks:
        decision_state = "informational"
    else:
        decision_state = "pass"

    return {
        "guard_id": GUARD_ID,
        "default_off": DEFAULT_OFF,
        "dry_run_only": DRY_RUN_ONLY,
        "enforces_runtime": ENFORCES_RUNTIME,
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "requested_action_class": action_class,
        "runtime_paths_allowed_for_action": runtime_allowed,
        "decision_state": decision_state,
        "would_block": bool(blockers),
        "blockers": blockers,
        "blocked_actions": [_BLOCKER_LABELS.get(name, name) for name in blockers],
        "observed_risks": observed_risks,
        "warnings": warnings,
        "required_approvals": [],
    }


def _normalized_path(value: Any) -> str:
    text = _safe_text(value, max_chars=500)
    if not text:
        return ""
    return os.path.normpath(text.rstrip("/"))


def _safe_text(value: Any, *, max_chars: int = 240) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\x00", "")
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _safe_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _is_feature_branch(branch: str) -> bool:
    if not branch:
        return False
    lowered = branch.lower()
    if lowered in {"head", "detached", "main", "master"}:
        return False
    return lowered.startswith(("feature/", "fix/", "bugfix/", "chore/", "pr-"))


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
