"""Default-off lane-start preflight caller for Mission Control.

This module models the future boundary where lane startup asks preflight for a
decision. It is intentionally report-only: it calls the existing in-memory
preflight adapter and returns a compact dry-run result without enforcing,
writing records, inspecting runtime state, or invoking tools.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mission_control.preflight import (
    ADAPTER_POLICY,
    DEFAULT_OFF,
    DRY_RUN_ONLY,
    ENFORCES_RUNTIME,
    evaluate_lane_start_preflight,
)
from mission_control.records import StartGateCheck


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
)


def run_lane_start_preflight(lane_start: Mapping[str, Any]) -> dict[str, Any]:
    """Return a dry-run lane-start preflight decision without runtime enforcement."""

    check = evaluate_lane_start_preflight(lane_start)
    would_block = check.decision_state == "blocked"
    would_require_approval = (
        bool(check.required_approvals)
        or check.decision_state == "needs_approval"
    )

    return {
        "caller": CALLER_POLICY,
        "preflight_adapter": ADAPTER_POLICY,
        "default_off": DEFAULT_OFF,
        "dry_run_only": DRY_RUN_ONLY,
        "enforces_runtime": ENFORCES_RUNTIME,
        "would_block": would_block,
        "would_require_approval": would_require_approval,
        "decision_state": check.decision_state,
        "reasons": list(check.reasons),
        "blocked_actions": list(check.blocked_actions),
        "required_approvals": list(check.required_approvals),
        "supported_input_fields": list(SUPPORTED_INPUT_FIELDS),
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
