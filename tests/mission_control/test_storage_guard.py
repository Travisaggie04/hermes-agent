"""Inert Storage Guard policy tests."""

from mission_control.storage_guard import (
    STORAGE_GUARD_POLICY,
    evaluate_storage_guard,
    get_storage_guard_policy,
)


def test_storage_guard_policy_is_inert_dry_run_and_display_only():
    policy = get_storage_guard_policy()

    assert policy == STORAGE_GUARD_POLICY
    assert policy is not STORAGE_GUARD_POLICY
    assert policy["guard_id"] == "storage_guard_v1"
    assert policy["trusted_for_execution"] is False
    assert policy["inert_context_only"] is True
    assert policy["enforcement_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["display_only"] is True
    assert policy["disk_thresholds"]["disk_warning_threshold_percent"] == "placeholder"
    assert policy["disk_thresholds"]["disk_block_threshold_percent"] == "placeholder"
    assert policy["artifact_manifest_rules"]["artifact_manifest_required_before_done"] is True
    assert policy["storage_delta_rules"]["storage_delta_required_before_done"] is True
    assert policy["archive_delete_rules"]["archive_verification_required_before_delete"] is True
    assert policy["archive_delete_rules"]["delete_forbidden_without_manifest"] is True
    assert policy["cloud_archive_policy"]["no_cloud_upload_in_dry_run"] is True
    assert "littleton-google-drive" in policy["cloud_archive_policy"]["allowed_archive_targets_placeholder"]
    assert policy["project_specific_posture"]["signal_room_video_requires_artifact_manifest_and_archive_plan"] is True
    assert policy["project_specific_posture"]["waha_external_archive_upload_requires_explicit_approval"] is True
    assert "disk_warning_threshold_percent" in policy["unresolved_policy_fields"]
    assert "local_large_artifact_threshold_placeholder" in policy["unresolved_policy_fields"]


def test_storage_guard_policy_returns_display_copy_only():
    policy = get_storage_guard_policy()

    policy["enforcement_enabled"] = True
    policy["cloud_archive_policy"]["no_cloud_upload_in_dry_run"] = False

    assert STORAGE_GUARD_POLICY["enforcement_enabled"] is False
    assert STORAGE_GUARD_POLICY["cloud_archive_policy"]["no_cloud_upload_in_dry_run"] is True


def test_storage_guard_blocks_done_without_required_artifact_manifest():
    result = evaluate_storage_guard(
        {
            "task_marked_done": True,
            "artifact_manifest_present": False,
            "artifact_manifest_required": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "task marked done without required artifact manifest" in result["reasons"]
    assert "mark task done" in result["blocked_actions"]


def test_storage_guard_blocks_delete_without_manifest_and_archive_verification():
    result = evaluate_storage_guard(
        {
            "cleanup_requested": True,
            "delete_requested": True,
            "artifact_manifest_present": False,
            "archive_verification_present": False,
            "explicit_delete_lane": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "cleanup/delete requested without artifact manifest" in result["reasons"]
    assert "delete requested without archive verification" in result["reasons"]
    assert "delete requested without explicit delete lane" in result["reasons"]
    assert "cleanup/delete artifacts" in result["blocked_actions"]
    assert "delete artifacts" in result["blocked_actions"]


def test_storage_guard_blocks_cloud_upload_in_dry_run():
    result = evaluate_storage_guard(
        {
            "cloud_upload_requested": True,
            "cloud_destination_supplied": True,
            "cloud_upload_explicitly_approved": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "cloud upload requested during dry-run" in result["reasons"]
    assert "cloud upload lacks explicit approval" in result["reasons"]
    assert "upload artifacts to cloud" in result["blocked_actions"]
    assert "explicit cloud upload approval" in result["required_approvals"]


def test_storage_guard_blocks_large_artifact_without_storage_delta():
    result = evaluate_storage_guard(
        {
            "large_artifact_created": True,
            "storage_delta_present": False,
            "before_after_disk_usage_present": False,
            "large_file_delta_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "large artifact created without storage delta" in result["reasons"]
    assert "before/after disk usage is missing" in result["reasons"]
    assert "large file delta is missing" in result["reasons"]
    assert "complete artifact-heavy task" in result["blocked_actions"]


def test_storage_guard_blocks_supplied_disk_percent_above_block_threshold():
    result = evaluate_storage_guard(
        {
            "disk_used_percent": 96,
            "disk_block_threshold_percent": 95,
            "disk_warning_threshold_percent": 85,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "observed disk usage is at or above supplied block threshold" in result["reasons"]
    assert "start artifact-heavy work" in result["blocked_actions"]


def test_storage_guard_blocks_waha_external_upload_without_approval():
    result = evaluate_storage_guard(
        {
            "project_domain": "waha",
            "external_archive_or_upload_requested": True,
            "waha_external_upload_approved": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "Waha external archive/upload lacks explicit approval" in result["reasons"]
    assert "external archive/upload for Waha" in result["blocked_actions"]


def test_storage_guard_blocks_signal_room_video_without_manifest_or_archive_plan():
    result = evaluate_storage_guard(
        {
            "project_domain": "signal_room",
            "artifact_heavy_lane": True,
            "video_generation_requested": True,
            "artifact_manifest_present": False,
            "archive_plan_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "Signal Room/video work lacks artifact manifest" in result["reasons"]
    assert "Signal Room/video work lacks archive plan" in result["reasons"]
    assert "start Signal Room/video artifact-heavy work" in result["blocked_actions"]


def test_storage_guard_blocks_tool_tally_evidence_deletion_without_preservation():
    result = evaluate_storage_guard(
        {
            "project_domain": "tool_tally",
            "production_evidence_delete_requested": True,
            "audit_artifact_preservation_confirmed": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "Tool & Tally production evidence deletion lacks preservation confirmation" in result["reasons"]
    assert "delete Tool & Tally production evidence" in result["blocked_actions"]


def test_storage_guard_warns_on_safe_state_with_unresolved_threshold_placeholders():
    result = evaluate_storage_guard(
        {
            "task_marked_done": False,
            "artifact_heavy_lane": False,
            "cleanup_requested": False,
            "delete_requested": False,
            "cloud_upload_requested": False,
            "large_artifact_created": False,
        }
    )

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert "disk_warning_threshold_percent" in result["unresolved_policy_fields"]
    assert "local_large_artifact_threshold_placeholder" in result["unresolved_policy_fields"]


def test_storage_guard_unknown_for_artifact_heavy_lane_without_storage_state():
    result = evaluate_storage_guard({"artifact_heavy_lane": True})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert "artifact-heavy lane has unknown storage state" in result["reasons"]


def test_storage_guard_unknown_without_observed_state():
    result = evaluate_storage_guard({})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "caller-supplied observed storage state is incomplete" in result["reasons"]
