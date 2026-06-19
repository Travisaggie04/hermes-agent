"""Default-off lane-start preflight adapter for Mission Control.

This adapter is intentionally inert. It converts compact lane startup input
into an in-memory TaskControlEnvelope and evaluates it with the Start Gate. It
does not read files, inspect secrets, call tools, invoke Git/subprocess/network,
write records, or enforce runtime behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mission_control.records import StartGateCheck, TaskControlEnvelope
from mission_control.start_gate import evaluate_start_gate


DEFAULT_OFF = True
WOULD_EXECUTE = False
DRY_RUN_ONLY = True
ENFORCES_RUNTIME = False
ADAPTER_POLICY = "mission_control.preflight.lane_start.v1"


def evaluate_lane_start_preflight(lane_start: Mapping[str, Any]) -> StartGateCheck:
    """Evaluate a compact lane-start request without runtime enforcement."""

    envelope = build_task_control_envelope(lane_start)
    check = evaluate_start_gate(envelope)
    return _with_preflight_flags(check)


def build_task_control_envelope(lane_start: Mapping[str, Any]) -> TaskControlEnvelope:
    """Build the Task Control Envelope used by the dry-run preflight check."""

    data = dict(lane_start)
    allowed_actions = _strings(data.get("allowed_actions"))
    requested_actions = _strings(data.get("requested_actions"))

    return TaskControlEnvelope(
        envelope_id=_envelope_id(data),
        active_lane=str(data.get("active_lane") or ""),
        mode=str(data.get("mode") or ""),
        allowed_actions=_evaluated_actions(allowed_actions, requested_actions),
        forbidden_actions=_strings(data.get("forbidden_actions")),
        current_repo=str(data.get("repo_target") or ""),
        stop_condition=str(data.get("stop_condition") or ""),
        report_requirements=_strings(data.get("report_requirements")),
        approval_required=bool(data.get("approval_required", False)),
        approval_slice_ids=_strings(data.get("approval_slice_ids")),
        token_context_policy=str(data.get("token_context_policy") or ""),
        metadata={
            "target_remote": str(data.get("repo_target") or ""),
            "branch": str(data.get("branch") or ""),
            "worktree_state": str(data.get("worktree_state") or ""),
            "requested_actions": list(requested_actions),
            "preflight_adapter": ADAPTER_POLICY,
            "default_off": DEFAULT_OFF,
            "would_execute": WOULD_EXECUTE,
            "dry_run_only": DRY_RUN_ONLY,
            "enforces_runtime": ENFORCES_RUNTIME,
        },
    )


def _evaluated_actions(allowed_actions: tuple[str, ...], requested_actions: tuple[str, ...]) -> tuple[str, ...]:
    if not allowed_actions:
        return ()
    return _dedupe((*allowed_actions, *requested_actions))


def _with_preflight_flags(check: StartGateCheck) -> StartGateCheck:
    metadata = dict(check.metadata)
    metadata.update(
        {
            "default_off": DEFAULT_OFF,
            "would_execute": WOULD_EXECUTE,
            "dry_run_only": DRY_RUN_ONLY,
            "enforces_runtime": ENFORCES_RUNTIME,
            "adapter": ADAPTER_POLICY,
        }
    )
    return StartGateCheck(
        start_gate_id=check.start_gate_id,
        envelope_id=check.envelope_id,
        decision_state=check.decision_state,
        reasons=check.reasons,
        blocked_actions=check.blocked_actions,
        required_approvals=check.required_approvals,
        dirty_worktree_state=check.dirty_worktree_state,
        branch_safety_state=check.branch_safety_state,
        secret_safety_state=check.secret_safety_state,
        token_context_state=check.token_context_state,
        created_at=check.created_at,
        metadata=metadata,
    )


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if str(item).strip())
    return (str(value),)


def _dedupe(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return tuple(deduped)


def _envelope_id(data: Mapping[str, Any]) -> str:
    branch = str(data.get("branch") or "").strip()
    if branch:
        return f"lane-start:{branch}"
    active_lane = str(data.get("active_lane") or "").strip()
    if active_lane:
        normalized = "-".join(active_lane.lower().split())
        return f"lane-start:{normalized}"
    return "lane-start:unidentified"
