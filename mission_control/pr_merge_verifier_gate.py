"""Inert PR merge verifier gate v1 policy and dry-run evaluator.

This module is intentionally display-only and dry-run only. It evaluates only
caller-supplied PR merge packet state and verifier evidence summaries. It does
not inspect live PRs, GitHub, files, processes, services, models, providers,
queues, databases, or runtime state, and it never performs a merge.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INERT_GATE_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

PR_MERGE_VERIFIER_GATE_POLICY: dict[str, Any] = {
    "gate_id": "pr_merge_verifier_gate_v1",
    **_INERT_GATE_FLAGS,
    "scope": "future Jenny PR merge packet self-blocking guard; not global GitHub enforcement",
    "required_fields": (
        "repo",
        "pr_number",
        "base_branch",
        "head_commit",
        "packet_hash",
        "implementer_id",
        "verifier_id",
        "verifier_evidence_record_id",
    ),
    "required_evidence_fields": (
        "record_id",
        "guard_type",
        "action_class",
        "repo",
        "pr_number",
        "base_branch",
        "head_commit",
        "packet_hash",
        "implementer_id",
        "verifier_id",
        "would_block",
        "blocked_actions",
        "dry_run_only",
        "enforces_runtime",
    ),
    "future_enforcement_boundary": {
        "blocks_only_jenny_pr_merge_lane_progression": True,
        "does_not_call_github": True,
        "does_not_merge_prs": True,
        "does_not_enable_runtime_enforcement": True,
        "does_not_spawn_workers": True,
        "does_not_route_models": True,
        "does_not_mutate_queues": True,
    },
    "unresolved_policy_fields": (
        "operator_identity_registry",
        "packet_hash_canonicalization_schema",
        "evidence_freshness_window",
        "future_default_off_config_flag",
        "future_jenny_merge_lane_wiring",
    ),
}

_PACKET_FIELDS = {
    "repo",
    "pr_number",
    "base_branch",
    "head_commit",
    "packet_hash",
    "implementer_id",
    "verifier_id",
    "verifier_evidence_record_id",
}
_EVIDENCE_FIELDS = {
    "record_id",
    "guard_type",
    "action_class",
    "repo",
    "pr_number",
    "base_branch",
    "head_commit",
    "packet_hash",
    "implementer_id",
    "verifier_id",
    "would_block",
    "blocked_actions",
    "dry_run_only",
    "enforces_runtime",
}
_MERGE_BLOCKED_ACTION_TERMS = ("merge pr", "pr merge", "merge pull request")


def get_pr_merge_verifier_gate_policy() -> dict[str, Any]:
    """Return a display copy of the inert PR merge verifier gate policy."""

    return deepcopy(PR_MERGE_VERIFIER_GATE_POLICY)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _casefold(value: Any) -> str:
    return _text(value).casefold()


def _same_text(left: Any, right: Any) -> bool:
    return _text(left) == _text(right)


def _same_identity(left: Any, right: Any) -> bool:
    left_text = _casefold(left)
    right_text = _casefold(right)
    return bool(left_text and right_text and left_text == right_text)


def _as_bool(value: Any) -> bool:
    return value is True


def _blocked_actions(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    return [_text(item) for item in items if _text(item)]


def _has_merge_blocked_action(actions: list[str]) -> bool:
    for action in actions:
        folded = action.casefold()
        if any(term in folded for term in _MERGE_BLOCKED_ACTION_TERMS):
            return True
    return False


def evaluate_pr_merge_verifier_gate(state: dict[str, Any] | None) -> dict[str, Any]:
    """Dry-run evaluate caller-supplied PR merge packet/evidence state.

    The supplied dictionary may contain packet fields directly and an evidence
    summary under ``verifier_evidence``. This function performs no live PR,
    GitHub, file, process, service, model, provider, queue, database, or runtime
    inspection and never mutates state.
    """

    observed = dict(state or {})
    evidence = observed.get("verifier_evidence")
    evidence = dict(evidence or {}) if isinstance(evidence, dict) else {}
    reasons: list[str] = []
    blocked_actions: list[str] = []
    required_approvals: list[str] = []

    if not observed:
        decision_state = "unknown"
        reasons.append("caller-supplied PR merge packet state is incomplete")
    else:
        decision_state = "pass"

        for field in PR_MERGE_VERIFIER_GATE_POLICY["required_fields"]:
            if not _text(observed.get(field)):
                _add_unique(reasons, f"missing PR merge packet field: {field}")
                _add_unique(blocked_actions, "proceed with PR merge packet")

    if observed and not evidence:
        _add_unique(reasons, "missing verifier evidence")
        _add_unique(blocked_actions, "proceed with PR merge packet")
        _add_unique(required_approvals, "matching verifier evidence record")
    elif evidence:
        if not _same_text(evidence.get("record_id"), observed.get("verifier_evidence_record_id")):
            _add_unique(reasons, "verifier evidence record id mismatch")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if evidence.get("guard_type") != "verifier_workflow":
            _add_unique(reasons, "verifier evidence guard_type is not verifier_workflow")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if evidence.get("action_class") != "pr_merge":
            _add_unique(reasons, "verifier evidence action_class is not pr_merge")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        for field in ("repo", "pr_number", "base_branch", "head_commit", "packet_hash"):
            if not _same_text(evidence.get(field), observed.get(field)):
                _add_unique(reasons, f"verifier evidence {field} mismatch")
                _add_unique(blocked_actions, "proceed with PR merge packet")
        if not _same_identity(evidence.get("implementer_id"), observed.get("implementer_id")):
            _add_unique(reasons, "verifier evidence implementer_id mismatch")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if not _same_identity(evidence.get("verifier_id"), observed.get("verifier_id")):
            _add_unique(reasons, "verifier evidence verifier_id mismatch")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if _as_bool(evidence.get("would_block")):
            _add_unique(reasons, "verifier evidence would_block is true")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        evidence_blocked_actions = _blocked_actions(evidence.get("blocked_actions"))
        if _has_merge_blocked_action(evidence_blocked_actions):
            _add_unique(reasons, "verifier evidence contains merge-related blocked action")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if evidence.get("dry_run_only") is not True:
            _add_unique(reasons, "verifier evidence dry_run_only is not true")
            _add_unique(blocked_actions, "proceed with PR merge packet")
        if evidence.get("enforces_runtime") is not False:
            _add_unique(reasons, "verifier evidence enforces_runtime is not false")
            _add_unique(blocked_actions, "proceed with PR merge packet")

    if _same_identity(observed.get("implementer_id"), observed.get("verifier_id")):
        _add_unique(reasons, "verifier_id cannot equal implementer_id")
        _add_unique(blocked_actions, "accept self-verification for PR merge")
        _add_unique(required_approvals, "independent verifier assignment")

    would_block = bool(blocked_actions)
    if would_block:
        decision_state = "would_block"
    elif decision_state != "unknown" and PR_MERGE_VERIFIER_GATE_POLICY.get("unresolved_policy_fields"):
        decision_state = "warn"

    return {
        "decision_state": decision_state,
        "would_block": would_block,
        "reasons": reasons,
        "blocked_actions": blocked_actions,
        "required_approvals": required_approvals,
        "unresolved_policy_fields": list(PR_MERGE_VERIFIER_GATE_POLICY["unresolved_policy_fields"]),
        "dry_run_only": True,
        "enforces_runtime": False,
    }
