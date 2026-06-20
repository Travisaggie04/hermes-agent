"""Display-only Mission Control domain governance policy records.

These records are intentionally inert policy data. They make protected-domain
posture visible to Mission Control dashboards before any future autonomous work,
model routing, or parallel orchestration is enabled.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from mission_control.inert_contract import inert_live_operation_flags


WAHA_HARD_WALL_POLICY: dict[str, Any] = {
    "domain_id": "waha",
    "domain_type": "professional_engineering",
    "isolation_level": "hard_wall_required",
    "board_policy": {
        "required_board": "waha",
        "non_waha_boards_forbidden": True,
    },
    "workspace_policy": {
        "allowed_roots": [],
        "deny_cross_project_reads": True,
        "deny_cross_project_writes": True,
    },
    "profile_policy": {
        "allowed_profiles": ("wahainspection",),
        "forbidden_profiles": (
            "default",
            "generic",
            "money-signal-video",
            "no-call-estimateready",
            "family-hub",
            "personal-life",
            "hermes-ops",
        ),
    },
    "memory_policy": {
        "required_namespace": "waha",
        "deny_cross_domain_memory": True,
    },
    "model_policy_placeholder": {
        "approved_models_required": True,
        "generic_free_cloud_forbidden_until_approved": True,
        "verifier_required": True,
    },
    "verifier_policy": {
        "waha_technical_verifier_required": True,
    },
    "enforcement": inert_live_operation_flags(
        enforcement_enabled=False,
        dry_run_only=True,
        display_only=True,
    ),
    "unresolved_required_before_enforcement": (
        "allowed_roots",
        "approved_models",
        "technical_verifier_identity",
    ),
}

DOMAIN_GOVERNANCE_POLICIES: tuple[dict[str, Any], ...] = (WAHA_HARD_WALL_POLICY,)


def get_domain_governance_policies() -> tuple[dict[str, Any], ...]:
    """Return display copies of inert domain governance policy records."""

    return deepcopy(DOMAIN_GOVERNANCE_POLICIES)
