"""Default-off lane-start preflight caller for Mission Control.

This module models the future boundary where lane startup asks preflight for a
decision. It is intentionally report-only: it calls the existing in-memory
preflight adapter and returns a compact dry-run result without enforcing,
writing records, inspecting runtime state, or invoking tools.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mission_control.inert_contract import inert_live_operation_flags
from mission_control.preflight import (
    ADAPTER_POLICY,
    DEFAULT_OFF,
    DRY_RUN_ONLY,
    ENFORCES_RUNTIME,
    evaluate_lane_start_preflight,
)
from mission_control.records import StartGateCheck
from mission_control.runtime_worktree_guard import evaluate_runtime_worktree_guard


CALLER_POLICY = "mission_control.lane_preflight.caller.v1"
SUPPORTED_INPUT_FIELDS = (
    "active_lane",
    "mode",
    "allowed_actions",
    "forbidden_actions",
    "stop_condition",
    "report_requirements",
    "repo_target",
    "branch",
    "worktree_state",
    "token_context_policy",
    "requested_actions",
    "approval_required",
    "approval_slice_ids",
    "candidate_worktree_path",
    "candidate_git_top_level",
    "candidate_head",
    "candidate_branch",
    "candidate_status_clean",
    "requested_action_class",
    "accepted_runtime_path",
    "accepted_head",
    "accepted_runtime_disk_head",
    "accepted_runtime_branch",
    "accepted_runtime_status_clean",
    "rollback_runtime_path",
    "rollback_head",
    "rollback_runtime_disk_head",
    "rollback_runtime_branch",
    "rollback_runtime_status_clean",
    "requested_dev_worktree_exists",
)


def run_lane_start_preflight(lane_start: Mapping[str, Any]) -> dict[str, Any]:
    """Return a dry-run lane-start preflight decision without runtime enforcement."""

    check = evaluate_lane_start_preflight(lane_start)
    runtime_guard = evaluate_runtime_worktree_guard(lane_start)
    would_block = check.decision_state == "blocked" or runtime_guard["would_block"] is True
    would_require_approval = (
        bool(check.required_approvals)
        or check.decision_state == "needs_approval"
    )
    decision_state = "blocked" if runtime_guard["would_block"] is True else check.decision_state

    return {
        "caller": CALLER_POLICY,
        "preflight_adapter": ADAPTER_POLICY,
        "default_off": DEFAULT_OFF,
        **inert_live_operation_flags(),
        "dry_run_only": DRY_RUN_ONLY,
        "enforces_runtime": ENFORCES_RUNTIME,
        "would_block": would_block,
        "would_require_approval": would_require_approval,
        "decision_state": decision_state,
        "reasons": [*list(check.reasons), *runtime_guard["blockers"]],
        "blocked_actions": [*list(check.blocked_actions), *runtime_guard["blocked_actions"]],
        "required_approvals": list(check.required_approvals),
        "supported_input_fields": list(SUPPORTED_INPUT_FIELDS),
        "runtime_worktree_guard": runtime_guard,
        "start_gate_check": _start_gate_check_report(check),
    }


def _start_gate_check_report(check: StartGateCheck) -> dict[str, Any]:
    return {
        "start_gate_id": check.start_gate_id,
        "envelope_id": check.envelope_id,
        "decision_state": check.decision_state,
        "reasons": list(check.reasons),
        "blocked_actions": list(check.blocked_actions),
        "required_approvals": list(check.required_approvals),
        "dirty_worktree_state": check.dirty_worktree_state,
        "branch_safety_state": check.branch_safety_state,
        "secret_safety_state": check.secret_safety_state,
        "token_context_state": check.token_context_state,
        "created_at": check.created_at,
    }
