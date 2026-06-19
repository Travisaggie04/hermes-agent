"""Central ALLOW / ASK / DENY policy classification for Mission Control.

This module is intentionally pure and inert. It classifies requested action
text so other Mission Control surfaces can share one policy vocabulary without
starting workers, reading secrets, mutating records, or enforcing runtime
behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal


PolicyDecisionState = Literal["allow", "ask", "deny"]

POLICY_ID = "mission_control.action_policy.allow_ask_deny.v1"
DEFAULT_OFF = True
WOULD_EXECUTE = False
ENFORCES_RUNTIME = False


@dataclass(frozen=True)
class ActionPolicyDecision:
    action: str
    decision: PolicyDecisionState
    category: str
    reason: str


@dataclass(frozen=True)
class ActionPolicyReport:
    policy_id: str
    decisions: tuple[ActionPolicyDecision, ...]
    denied_actions: tuple[str, ...]
    approval_actions: tuple[str, ...]
    required_approvals: tuple[str, ...]
    approval_satisfied: bool
    default_off: bool = DEFAULT_OFF
    would_execute: bool = WOULD_EXECUTE
    enforces_runtime: bool = ENFORCES_RUNTIME


_DENY_TERMS: tuple[tuple[str, str], ...] = (
    ("parent directory", "parent-directory access"),
    ("../", "parent-directory access"),
    ("full transcript", "unbounded transcript/context"),
    ("transcript dump", "unbounded transcript/context"),
    ("dump all context", "unbounded transcript/context"),
    ("dump all records", "unbounded records/context"),
    ("unbounded records", "unbounded records/context"),
    ("unbounded context", "unbounded records/context"),
    ("without bounds", "unbounded records/context"),
    ("full-text search", "unbounded records/context"),
)

_ASK_TERMS: tuple[tuple[str, str], ...] = (
    ("gateway restart", "gateway restart"),
    ("restart gateway", "gateway restart"),
    ("restart", "restart"),
    ("runtime switch", "runtime switch"),
    ("switch runtime", "runtime switch"),
    ("hermes update", "Hermes update"),
    ("upgrade hermes", "Hermes update"),
    ("deploy", "deployment"),
    ("payment", "payment"),
    ("checkout", "payment"),
    ("outreach", "outreach"),
    ("customer", "customer-facing action"),
    ("waha", "Waha / WhatsApp"),
    ("whatsapp", "Waha / WhatsApp"),
    ("social posting", "social posting"),
    ("social post", "social posting"),
    ("post to", "social posting"),
    ("worker", "worker/timer"),
    ("timer", "worker/timer"),
    ("daemon", "worker/timer"),
    ("cron", "worker/timer"),
    ("model routing", "model routing"),
    ("route model", "model routing"),
    ("session-send", "session-send"),
    ("session send", "session-send"),
    ("dispatch", "dispatch"),
    ("secret", "secrets/state"),
    ("secrets", "secrets/state"),
    ("state.db", "secrets/state"),
    ("state mutation", "secrets/state"),
    ("config/state", "secrets/state"),
    ("merge", "git mutation"),
    ("push", "git mutation"),
    ("force-push", "git mutation"),
    ("force push", "git mutation"),
    ("delete", "filesystem mutation"),
    ("clean", "filesystem mutation"),
    ("reset", "filesystem mutation"),
    ("stash", "filesystem mutation"),
)


def evaluate_action_policy(
    actions: Iterable[str],
    *,
    approval_required: bool = False,
    approval_slice_ids: Sequence[str] = (),
) -> ActionPolicyReport:
    """Classify action strings with a shared ALLOW / ASK / DENY vocabulary."""

    decisions = tuple(_decision_for(action) for action in _dedupe(str(action) for action in actions if str(action).strip()))
    denied_actions = tuple(decision.action for decision in decisions if decision.decision == "deny")
    approval_actions = tuple(decision.action for decision in decisions if decision.decision == "ask")
    approvals = tuple(str(item) for item in approval_slice_ids if str(item).strip())
    approval_satisfied = approval_required and bool(approvals)

    return ActionPolicyReport(
        policy_id=POLICY_ID,
        decisions=decisions,
        denied_actions=denied_actions,
        approval_actions=approval_actions,
        required_approvals=approvals if approval_satisfied else (),
        approval_satisfied=approval_satisfied,
    )


def _decision_for(action: str) -> ActionPolicyDecision:
    normalized = action.strip()
    lowered = normalized.lower()
    deny_category = _matching_category(lowered, _DENY_TERMS)

    if deny_category:
        return ActionPolicyDecision(
            action=normalized,
            category=deny_category,
            decision="deny",
            reason=f"{deny_category} is outside bounded Mission Control context",
        )

    ask_category = _matching_category(lowered, _ASK_TERMS)
    if ask_category:
        return ActionPolicyDecision(
            action=normalized,
            category=ask_category,
            decision="ask",
            reason=f"{ask_category} requires explicit approval",
        )

    return ActionPolicyDecision(
        action=normalized,
        category="bounded",
        decision="allow",
        reason="bounded action",
    )


def _matching_category(value: str, terms: tuple[tuple[str, str], ...]) -> str:
    for term, category in terms:
        if term in value:
            return category
    return ""


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        out.append(item)

    return tuple(out)
