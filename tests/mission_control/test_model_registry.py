"""Inert Mission Control model registry policy tests."""

from mission_control.model_registry import (
    MODEL_REGISTRY_RECORDS,
    get_model_registry_records,
    model_allowed_for_future_waha_routing,
    model_allowed_for_future_protected_verifier,
)


def test_model_registry_records_are_inert_and_display_only():
    records = get_model_registry_records()

    assert records == MODEL_REGISTRY_RECORDS
    assert records is not MODEL_REGISTRY_RECORDS
    assert len(records) >= 3
    for record in records:
        assert record["trusted_for_execution"] is False
        assert record["inert_context_only"] is True
        assert record["routing_enabled"] is False
        assert record["display_only"] is True
        assert record["execution_mode"] in {"unavailable", "display_only", "future_supported"}
        assert record["provider_type"] in {"local", "free_cloud", "budget_cloud", "premium_cloud", "unknown"}
        assert record["cost_class"] in {"free", "low", "medium", "high", "unknown"}
        assert record["privacy_class"] in {"local_private", "cloud_standard", "cloud_restricted", "unknown"}
        assert record["allowed_for_waha"] is False
        assert record["fallback_allowed"] is False
        assert "approved_model_identity" in record["unresolved_before_routing"]


def test_unknown_model_is_not_allowed_for_verifier_deployment_or_protected_domains():
    unknown = next(record for record in get_model_registry_records() if record["provider_type"] == "unknown")

    assert unknown["model_id"] == "unknown-unapproved-model"
    assert unknown["allowed_for_waha"] is False
    assert unknown["verifier_allowed"] is False
    assert "deployment_review" in unknown["forbidden_lanes"]
    assert "protected_domains" in unknown["forbidden_domains"]
    assert model_allowed_for_future_waha_routing(unknown) is False
    assert model_allowed_for_future_protected_verifier(unknown) is False


def test_free_cloud_models_are_forbidden_for_waha_until_explicitly_approved():
    free_cloud = next(record for record in get_model_registry_records() if record["provider_type"] == "free_cloud")

    assert free_cloud["cost_class"] == "free"
    assert free_cloud["allowed_for_waha"] is False
    assert "waha" in free_cloud["forbidden_domains"]
    assert "explicit_waha_model_approval" in free_cloud["unresolved_before_routing"]
    assert model_allowed_for_future_waha_routing(free_cloud) is False


def test_registry_returns_display_copies_only():
    records = get_model_registry_records()

    records[0]["routing_enabled"] = True
    records[0]["allowed_for_waha"] = True
    assert MODEL_REGISTRY_RECORDS[0]["routing_enabled"] is False
    assert MODEL_REGISTRY_RECORDS[0]["allowed_for_waha"] is False
