"""Default-off Jenny PR merge lane guard.

This module applies the inert ``pr_merge_verifier_gate_v1`` evaluator to a
caller-supplied PR merge packet and config dictionary. It is intentionally a
pure decision helper: it performs no GitHub inspection, no merge execution, no
process calls, no worker/model/queue activity, and no persistence.
"""

from __future__ import annotations

from typing import Any

from mission_control.pr_merge_verifier_gate import evaluate_pr_merge_verifier_gate

GUARD_ID = "pr_merge_verifier_gate_v1"
CONFIG_SECTION = "mission_control"
CONFIG_ENFORCEMENT_SECTION = "enforcement"
CONFIG_FLAG = "pr_merge_verifier_gate_enabled"


def pr_merge_verifier_gate_enabled(config: dict[str, Any] | None) -> bool:
    """Return the default-off PR merge gate flag from a caller-supplied config."""

    if not isinstance(config, dict):
        return False
    mission_control = config.get(CONFIG_SECTION)
    if not isinstance(mission_control, dict):
        return False
    enforcement = mission_control.get(CONFIG_ENFORCEMENT_SECTION)
    if not isinstance(enforcement, dict):
        return False
    return enforcement.get(CONFIG_FLAG) is True


def evaluate_pr_merge_lane_guard(
    config: dict[str, Any] | None,
    merge_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate whether Jenny's PR merge lane should stop.

    ``merge_packet`` is caller supplied and should include the PR merge packet
    fields plus the matching verifier evidence summary expected by
    ``evaluate_pr_merge_verifier_gate``. When the config flag is absent or
    false, this remains advisory-only and never blocks. When the flag is true,
    it stops Jenny's merge lane only if the dry-run evaluator would block.
    """

    enabled = pr_merge_verifier_gate_enabled(config)
    gate_result = evaluate_pr_merge_verifier_gate(merge_packet)
    would_block = gate_result.get("would_block") is True
    stop_merge_lane = enabled and would_block
    reasons = list(gate_result.get("reasons") or [])
    blocked_actions = list(gate_result.get("blocked_actions") or [])

    if not enabled:
        advisory_reason = "PR merge verifier gate is default-off; advisory only"
        if advisory_reason not in reasons:
            reasons.append(advisory_reason)

    return {
        "guard_id": GUARD_ID,
        "enabled": enabled,
        "advisory_only": not enabled,
        "stop_merge_lane": stop_merge_lane,
        "would_block": would_block,
        "decision_state": gate_result.get("decision_state", "unknown"),
        "reasons": reasons,
        "blocked_actions": blocked_actions,
        "required_approvals": list(gate_result.get("required_approvals") or []),
        "unresolved_policy_fields": list(gate_result.get("unresolved_policy_fields") or []),
        "dry_run_only": True,
        "enforces_runtime": False,
    }
