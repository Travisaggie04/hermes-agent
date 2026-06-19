"""Default-off Start Gate policy evaluation for Mission Control envelopes.

This module is intentionally inert: it evaluates compact envelope-like input
and returns a descriptive StartGateCheck value object. It does not read runtime
state, call tools, inspect files, invoke subprocesses, or enforce decisions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mission_control.action_policy import evaluate_action_policy
from mission_control.records import StartGateCheck, TaskControlEnvelope


DEFAULT_OFF = True
INERT = True
WOULD_EXECUTE = False
ENFORCES_RUNTIME = False

_REQUIRED_FIELDS = (
    ("active_lane", "missing active lane"),
    ("mode", "missing mode"),
    ("allowed_actions", "missing allowed actions"),
    ("forbidden_actions", "missing forbidden actions"),
    ("stop_condition", "missing stop condition"),
    ("report_requirements", "missing report requirements"),
)

_AMBIGUOUS_REMOTE_TERMS = (
    "ambiguous",
    "origin and travis",
    "travis and origin",
    "multiple remotes",
)

_TRAVIS_REPO = "Travisaggie04/hermes-agent"
_NOUS_REPO = "NousResearch/hermes-agent"


def evaluate_start_gate(envelope: TaskControlEnvelope | Mapping[str, Any]) -> StartGateCheck:
    """Evaluate an envelope-like request without enforcing runtime behavior."""

    data = _envelope_data(envelope)
    metadata = _mapping(data.get("metadata"))
    envelope_id = str(data.get("envelope_id") or "")

    reasons: list[str] = []
    blocked_actions: list[str] = []
    required_approvals: list[str] = []

    for field_name, reason in _REQUIRED_FIELDS:
        if not _has_value(data.get(field_name)):
            reasons.append(reason)

    requested_actions = _strings(data.get("allowed_actions"))
    approval_ids = _strings(data.get("approval_slice_ids"))
    has_explicit_approval = bool(data.get("approval_required")) and bool(approval_ids)
    action_policy = evaluate_action_policy(
        requested_actions,
        approval_required=bool(data.get("approval_required")),
        approval_slice_ids=approval_ids,
    )

    for decision in action_policy.decisions:
        if decision.decision == "deny":
            reasons.append(f"blocked unsafe request: {decision.action}")
            blocked_actions.append(decision.action)
        elif decision.decision == "ask":
            if has_explicit_approval:
                required_approvals.extend(approval_ids)
            else:
                reasons.append("privileged action requires explicit approval")
                blocked_actions.append(decision.action)
                required_approvals.append("explicit approval for privileged action")

    dirty_worktree_state = _dirty_worktree_state(metadata)
    if dirty_worktree_state != "clean":
        reasons.append(f"unsafe worktree state: {dirty_worktree_state}")

    branch_safety_state = _branch_safety_state(data, metadata)
    if branch_safety_state in {"wrong_repo_or_remote", "repo_remote_ambiguous"}:
        reasons.append(branch_safety_state.replace("_", " "))

    secret_safety_state = _secret_safety_state(requested_actions)
    token_context_state = _token_context_state(data, requested_actions)
    if token_context_state == "unbounded":
        reasons.append("unbounded token/context retrieval requested")

    blocked_actions = _dedupe(blocked_actions)
    required_approvals = _dedupe(required_approvals)

    if _has_blocking_issue(reasons, blocked_actions, dirty_worktree_state, branch_safety_state, token_context_state):
        decision_state = "blocked"
    elif required_approvals and not has_explicit_approval:
        decision_state = "needs_approval"
    elif required_approvals:
        decision_state = "informational"
    else:
        decision_state = "pass"

    if decision_state == "needs_approval":
        # Needs-approval actions are held for humans but are not runtime-enforced here.
        reasons = [reason for reason in reasons if not reason.startswith("blocked unsafe request:")]

    return StartGateCheck(
        start_gate_id=_start_gate_id(envelope_id),
        envelope_id=envelope_id,
        decision_state=decision_state,
        reasons=tuple(_dedupe(reasons)),
        blocked_actions=tuple(blocked_actions),
        required_approvals=tuple(required_approvals),
        dirty_worktree_state=dirty_worktree_state,
        branch_safety_state=branch_safety_state,
        secret_safety_state=secret_safety_state,
        token_context_state=token_context_state,
        created_at=str(data.get("created_at") or ""),
        metadata={
            "default_off": DEFAULT_OFF,
            "inert": INERT,
            "would_execute": WOULD_EXECUTE,
            "enforces_runtime": ENFORCES_RUNTIME,
            "policy": "mission_control.start_gate.default_off.v1",
            "action_policy": action_policy.policy_id,
        },
    )


def _envelope_data(envelope: TaskControlEnvelope | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(envelope, TaskControlEnvelope):
        return envelope.to_dict()
    return dict(envelope)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if str(item).strip())
    return (str(value),)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence):
        return bool(value)
    return True


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _dirty_worktree_state(metadata: Mapping[str, Any]) -> str:
    state = str(metadata.get("worktree_state") or "clean").strip().lower()
    if "quarantined" in state:
        return "quarantined" if state == "quarantined" else state
    if "dirty" in state:
        return "dirty" if state == "dirty" else state
    return "clean"


def _branch_safety_state(data: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    candidates = (
        str(data.get("current_repo") or ""),
        str(metadata.get("target_remote") or ""),
        str(metadata.get("repo_remote") or ""),
        str(metadata.get("authoritative_remote") or ""),
    )
    lowered = " ".join(candidate.lower() for candidate in candidates if candidate)
    if not str(data.get("current_repo") or "").strip():
        return "wrong_repo_or_remote"
    if _NOUS_REPO.lower() in lowered:
        return "wrong_repo_or_remote"
    if _contains_any(lowered, _AMBIGUOUS_REMOTE_TERMS):
        return "repo_remote_ambiguous"
    if _TRAVIS_REPO.lower() not in lowered:
        return "repo_remote_ambiguous"
    return "bounded"


def _secret_safety_state(requested_actions: tuple[str, ...]) -> str:
    if any("secret" in action.lower() for action in requested_actions):
        return "secret_access_requested"
    return "no_secret_access_requested"


def _token_context_state(data: Mapping[str, Any], requested_actions: tuple[str, ...]) -> str:
    text = " ".join((str(data.get("token_context_policy") or ""), *requested_actions)).lower()
    if _contains_any(text, ("unbounded", "dump all context", "full transcript", "without bounds")):
        return "unbounded"
    return "bounded"


def _has_blocking_issue(
    reasons: list[str],
    blocked_actions: list[str],
    dirty_worktree_state: str,
    branch_safety_state: str,
    token_context_state: str,
) -> bool:
    structural_reasons = [reason for reason in reasons if not reason.startswith("privileged action requires")]
    return bool(
        blocked_actions
        and any("blocked unsafe request" in reason for reason in structural_reasons)
        or any(reason.startswith("missing ") for reason in structural_reasons)
        or dirty_worktree_state != "clean"
        or branch_safety_state in {"wrong_repo_or_remote", "repo_remote_ambiguous"}
        or token_context_state == "unbounded"
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _start_gate_id(envelope_id: str) -> str:
    if envelope_id:
        return f"start-gate:{envelope_id}"
    return "start-gate:unidentified-envelope"
