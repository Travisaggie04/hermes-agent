"""Central Jenny OS ALLOW / ASK / DENY action policy.

This module is deliberately pure and inert. It classifies caller-supplied
request text/actions so UI, bridge, and future orchestration paths can share one
policy vocabulary without enabling runtime enforcement in this PR.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

Decision = Literal["ALLOW", "ASK", "DENY"]

INERT_POLICY_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

ACTION_POLICY_GUARDRAILS: dict[str, Any] = {
    "policy_id": "jenny_os_action_policy_v1",
    **INERT_POLICY_FLAGS,
    "decisions": ("ALLOW", "ASK", "DENY"),
    "default_decision": "ASK",
    "protected_action_categories": (
        "gateway_restart",
        "runtime_switch",
        "deploy",
        "payment",
        "outreach",
        "waha_social_posting",
        "hidden_workers_timers_daemons_cron",
        "secrets_or_state_mutation",
        "local_llm_routing",
        "tool_tally_report_builder",
    ),
    "denied_action_categories": (
        "broad_or_unlimited_approval",
        "disable_guardrails",
        "bypass_review_or_evidence",
    ),
    "allowed_action_examples": (
        "read approved context",
        "inspect status",
        "plan a bounded lane",
        "create a draft PR",
        "run targeted tests",
        "report evidence",
    ),
}

_ASK_RULES: tuple[dict[str, Any], ...] = (
    {
        "category": "gateway_restart",
        "patterns": ("gateway restart", "restart gateway", "hermes-gateway.service", "gateway runtime"),
        "reason": "gateway restarts and gateway runtime changes require separate approval",
        "required_approval": "explicit gateway restart/runtime approval",
        "blocked_action": "restart or switch gateway",
    },
    {
        "category": "runtime_switch",
        "patterns": ("runtime switch", "switch runtime", "accepted runtime", "rollback runtime"),
        "reason": "runtime switching requires a bounded deploy/recovery lane",
        "required_approval": "explicit runtime switch approval",
        "blocked_action": "switch live runtime",
    },
    {
        "category": "deploy",
        "patterns": ("deploy", "deployment", "dashboard deploy", "production deploy", "restart service"),
        "reason": "deployments require an explicit deploy lane and validation evidence",
        "required_approval": "explicit deploy approval",
        "blocked_action": "deploy or restart service",
    },
    {
        "category": "payment",
        "patterns": ("payment", "checkout", "charge", "refund", "stripe", "invoice", "paid order"),
        "reason": "payment and checkout actions require separate approval",
        "required_approval": "explicit payment/checkout approval",
        "blocked_action": "mutate payment or checkout state",
    },
    {
        "category": "outreach",
        "patterns": ("outreach", "email customers", "send email", "contact customer", "customer delivery"),
        "reason": "customer outreach and delivery require separate approval",
        "required_approval": "explicit customer/outreach approval",
        "blocked_action": "contact customers or deliver customer-facing work",
    },
    {
        "category": "waha_social_posting",
        "patterns": (
            "waha",
            "whatsapp",
            "post to youtube",
            "post to facebook",
            "post to instagram",
            "post to tiktok",
            "social posting",
            "publish video",
        ),
        "reason": "Waha, WhatsApp, social posting, and publishing are protected actions",
        "required_approval": "explicit Waha/social/publishing approval",
        "blocked_action": "send Waha/social/publishing action",
    },
    {
        "category": "hidden_workers_timers_daemons_cron",
        "patterns": (
            "hidden worker",
            "background worker",
            "start worker",
            "timer",
            "daemon",
            "cron",
            "scheduler",
            "always-on",
            "auto loop",
        ),
        "reason": "workers, timers, daemons, cron, and always-on loops require separate approval",
        "required_approval": "explicit worker/timer/daemon approval",
        "blocked_action": "enable hidden or scheduled execution",
    },
    {
        "category": "secrets_or_state_mutation",
        "patterns": (
            "secret",
            "token",
            "state.db",
            "delete records",
            "delete record",
            "remove records",
            "mutate records",
            "config mutation",
        ),
        "reason": "secrets, state.db, config, and record mutation require separate approval",
        "required_approval": "explicit secrets/state/config approval",
        "blocked_action": "read or mutate secrets/state/config/records",
    },
    {
        "category": "local_llm_routing",
        "patterns": ("local llm", "lm studio", "qwen", "route to local model", "model routing"),
        "reason": "local LLM routing is lab-only unless separately approved",
        "required_approval": "explicit local model routing approval",
        "blocked_action": "route Jenny work to local model",
    },
    {
        "category": "tool_tally_report_builder",
        "patterns": ("tool & tally report", "toolandtally report", "report builder", "report-engine"),
        "reason": "Tool & Tally report-builder changes are paused and protected",
        "required_approval": "explicit Tool & Tally report-builder approval",
        "blocked_action": "change Tool & Tally report-builder pipeline",
    },
)

_DENY_RULES: tuple[dict[str, Any], ...] = (
    {
        "category": "broad_or_unlimited_approval",
        "patterns": (
            "approve all actions",
            "approval for everything",
            "unlimited approval",
            "global approval",
            "anything you need",
            "do whatever",
        ),
        "reason": "broad or unlimited approvals are not acceptable guardrail inputs",
        "blocked_action": "accept broad approval",
    },
    {
        "category": "disable_guardrails",
        "patterns": (
            "disable guardrails",
            "turn off guardrails",
            "ignore guardrails",
            "bypass guardrails",
            "skip approvals",
        ),
        "reason": "requests to disable or bypass guardrails are denied",
        "blocked_action": "disable guardrails",
    },
    {
        "category": "bypass_review_or_evidence",
        "patterns": (
            "merge without review",
            "skip tests",
            "ignore ci",
            "no evidence needed",
            "mark done without evidence",
        ),
        "reason": "Jenny must require review, tests, and evidence before completion",
        "blocked_action": "bypass review/tests/evidence",
    },
)


def get_action_policy_guardrails() -> dict[str, Any]:
    """Return a display copy of the central Jenny OS action policy."""

    return deepcopy(ACTION_POLICY_GUARDRAILS)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _payload_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("text", "message", "request", "prompt", "objective", "summary"):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    actions = payload.get("requested_actions") or payload.get("actions") or ()
    if isinstance(actions, str):
        parts.append(actions)
    elif isinstance(actions, (list, tuple)):
        parts.extend(str(item) for item in actions if item is not None)
    return "\n".join(parts).strip()


def _matches_rule(text: str, rule: dict[str, Any]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in rule["patterns"])


def evaluate_action_policy(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Classify caller-supplied request text/actions as ALLOW, ASK, or DENY.

    The evaluator never returns the raw request text. It reports matched policy
    categories and reasons only, so callers can display concise status without
    leaking hidden context, secrets, or long prompt packets.
    """

    request = dict(payload or {})
    text = _payload_text(request)
    matched_categories: list[str] = []
    required_approvals: list[str] = []
    blocked_actions: list[str] = []
    reasons: list[str] = []

    if not text:
        return {
            "decision": "ASK",
            "decision_state": "needs_request",
            "matched_categories": [],
            "reasons": ["request text or requested_actions are required"],
            "blocked_actions": [],
            "required_approvals": [],
            "dry_run_only": True,
            "enforces_runtime": False,
        }

    for rule in _DENY_RULES:
        if not _matches_rule(text, rule):
            continue
        _add_unique(matched_categories, rule["category"])
        _add_unique(reasons, rule["reason"])
        _add_unique(blocked_actions, rule["blocked_action"])

    if blocked_actions:
        return {
            "decision": "DENY",
            "decision_state": "denied",
            "matched_categories": matched_categories,
            "reasons": reasons,
            "blocked_actions": blocked_actions,
            "required_approvals": required_approvals,
            "dry_run_only": True,
            "enforces_runtime": False,
        }

    for rule in _ASK_RULES:
        if not _matches_rule(text, rule):
            continue
        _add_unique(matched_categories, rule["category"])
        _add_unique(reasons, rule["reason"])
        _add_unique(blocked_actions, rule["blocked_action"])
        _add_unique(required_approvals, rule["required_approval"])

    if blocked_actions:
        return {
            "decision": "ASK",
            "decision_state": "requires_explicit_approval",
            "matched_categories": matched_categories,
            "reasons": reasons,
            "blocked_actions": blocked_actions,
            "required_approvals": required_approvals,
            "dry_run_only": True,
            "enforces_runtime": False,
        }

    return {
        "decision": "ALLOW",
        "decision_state": "allowed_in_current_guardrails",
        "matched_categories": [],
        "reasons": ["request has no protected action matches"],
        "blocked_actions": [],
        "required_approvals": [],
        "dry_run_only": True,
        "enforces_runtime": False,
    }
