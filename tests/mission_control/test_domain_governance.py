"""Inert domain governance policy record tests."""

from mission_control.domain_governance import (
    DOMAIN_GOVERNANCE_POLICIES,
    WAHA_HARD_WALL_POLICY,
    get_domain_governance_policies,
)


def test_waha_hard_wall_policy_is_explicit_and_inert():
    policy = WAHA_HARD_WALL_POLICY

    assert policy["domain_id"] == "waha"
    assert policy["domain_type"] == "professional_engineering"
    assert policy["isolation_level"] == "hard_wall_required"
    assert policy["board_policy"] == {
        "required_board": "waha",
        "non_waha_boards_forbidden": True,
    }
    assert policy["workspace_policy"]["deny_cross_project_reads"] is True
    assert policy["workspace_policy"]["deny_cross_project_writes"] is True
    assert policy["workspace_policy"]["allowed_roots"] == []
    assert "allowed_roots" in policy["unresolved_required_before_enforcement"]
    assert policy["profile_policy"]["allowed_profiles"] == ("wahainspection",)
    assert "generic" in policy["profile_policy"]["forbidden_profiles"]
    assert policy["memory_policy"] == {
        "required_namespace": "waha",
        "deny_cross_domain_memory": True,
    }
    assert policy["model_policy_placeholder"] == {
        "approved_models_required": True,
        "generic_free_cloud_forbidden_until_approved": True,
        "verifier_required": True,
    }
    assert policy["verifier_policy"]["waha_technical_verifier_required"] is True
    assert policy["enforcement"] == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "enforcement_enabled": False,
        "display_only": True,
    }


def test_domain_governance_policy_registry_returns_display_copies_only():
    policies = get_domain_governance_policies()

    assert policies == DOMAIN_GOVERNANCE_POLICIES
    assert policies is not DOMAIN_GOVERNANCE_POLICIES
    assert policies[0]["domain_id"] == "waha"
    policies[0]["enforcement"]["enforcement_enabled"] = True
    assert WAHA_HARD_WALL_POLICY["enforcement"]["enforcement_enabled"] is False
