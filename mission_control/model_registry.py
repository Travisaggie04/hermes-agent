"""Display-only Mission Control model registry policy records.

The registry is intentionally inert. It describes future model-picker/router
policy shape without reading credentials, calling providers, routing tasks, or
executing models.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INERT_MODEL_FLAGS = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "routing_enabled": False,
    "display_only": True,
}

MODEL_REGISTRY_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "model_id": "local-model-placeholder",
        "display_name": "Local model placeholder",
        "provider_type": "local",
        "execution_mode": "future_supported",
        "cost_class": "free",
        "privacy_class": "local_private",
        "allowed_lanes": ("drafting", "summarization", "offline_research"),
        "forbidden_lanes": ("deployment_review", "protected_domain_verification"),
        "allowed_domains": ("general",),
        "forbidden_domains": ("waha", "protected_domains"),
        "allowed_for_waha": False,
        "suitable_roles": ("summarizer", "planner"),
        "verifier_allowed": False,
        "fallback_allowed": False,
        "max_context_class": "unknown",
        "notes": "Placeholder for future local/private models; not approved for protected domains or verifier roles.",
        "unresolved_before_routing": (
            "approved_model_identity",
            "runtime_availability_probe",
            "quality_benchmark",
            "explicit_waha_model_approval",
        ),
        **_INERT_MODEL_FLAGS,
    },
    {
        "model_id": "free-cloud-placeholder",
        "display_name": "Free cloud model placeholder",
        "provider_type": "free_cloud",
        "execution_mode": "display_only",
        "cost_class": "free",
        "privacy_class": "cloud_standard",
        "allowed_lanes": ("brainstorming", "low_risk_summary"),
        "forbidden_lanes": ("deployment_review", "protected_domain_verification", "customer_delivery"),
        "allowed_domains": ("general",),
        "forbidden_domains": ("waha", "protected_domains", "customer_data"),
        "allowed_for_waha": False,
        "suitable_roles": ("summarizer", "researcher"),
        "verifier_allowed": False,
        "fallback_allowed": False,
        "max_context_class": "unknown",
        "notes": "Generic free-cloud models are forbidden for Waha until explicitly approved.",
        "unresolved_before_routing": (
            "approved_model_identity",
            "provider_privacy_review",
            "explicit_waha_model_approval",
            "cost_limit_policy",
        ),
        **_INERT_MODEL_FLAGS,
    },
    {
        "model_id": "premium-cloud-placeholder",
        "display_name": "Premium cloud model placeholder",
        "provider_type": "premium_cloud",
        "execution_mode": "display_only",
        "cost_class": "high",
        "privacy_class": "cloud_restricted",
        "allowed_lanes": ("planning", "code_review", "research"),
        "forbidden_lanes": ("deployment_review", "protected_domain_verification"),
        "allowed_domains": ("general",),
        "forbidden_domains": ("waha", "protected_domains"),
        "allowed_for_waha": False,
        "suitable_roles": ("planner", "coder", "researcher", "verifier"),
        "verifier_allowed": False,
        "fallback_allowed": False,
        "max_context_class": "unknown",
        "notes": "Premium cloud candidates need explicit approval, budget policy, and verifier qualification before routing.",
        "unresolved_before_routing": (
            "approved_model_identity",
            "budget_cap",
            "privacy_review",
            "verifier_qualification",
            "explicit_waha_model_approval",
        ),
        **_INERT_MODEL_FLAGS,
    },
    {
        "model_id": "unknown-unapproved-model",
        "display_name": "Unknown / unapproved model",
        "provider_type": "unknown",
        "execution_mode": "unavailable",
        "cost_class": "unknown",
        "privacy_class": "unknown",
        "allowed_lanes": (),
        "forbidden_lanes": (
            "deployment_review",
            "protected_domain_verification",
            "customer_delivery",
            "public_action",
        ),
        "allowed_domains": (),
        "forbidden_domains": ("waha", "protected_domains", "customer_data", "business", "personal"),
        "allowed_for_waha": False,
        "suitable_roles": ("unknown",),
        "verifier_allowed": False,
        "fallback_allowed": False,
        "max_context_class": "unknown",
        "notes": "Unknown models are not allowed for Waha, verifier roles, deployment review, or protected-domain work.",
        "unresolved_before_routing": (
            "approved_model_identity",
            "provider_type",
            "privacy_class",
            "cost_class",
            "quality_benchmark",
        ),
        **_INERT_MODEL_FLAGS,
    },
)


def get_model_registry_records() -> tuple[dict[str, Any], ...]:
    """Return display copies of inert model registry records."""

    return deepcopy(MODEL_REGISTRY_RECORDS)


def model_allowed_for_future_waha_routing(record: dict[str, Any]) -> bool:
    """Report future Waha routing readiness without enabling routing."""

    return bool(
        record.get("allowed_for_waha") is True
        and record.get("routing_enabled") is True
        and "waha" in tuple(record.get("allowed_domains") or ())
        and "waha" not in tuple(record.get("forbidden_domains") or ())
        and not record.get("unresolved_before_routing")
    )


def model_allowed_for_future_protected_verifier(record: dict[str, Any]) -> bool:
    """Report future verifier readiness without enabling execution."""

    return bool(
        record.get("verifier_allowed") is True
        and record.get("routing_enabled") is True
        and "verifier" in tuple(record.get("suitable_roles") or ())
        and "protected_domain_verification" not in tuple(record.get("forbidden_lanes") or ())
        and not record.get("unresolved_before_routing")
    )
