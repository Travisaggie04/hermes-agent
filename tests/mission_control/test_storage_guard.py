"""Inert Storage Guard policy tests."""

from mission_control.storage_guard import (
    STORAGE_GUARD_POLICY,
    build_storage_cleanup_manifest,
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
    assert policy["would_execute"] is False
    assert policy["enforcement_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["display_only"] is True
    assert policy["disk_thresholds"]["lean_target_percent"] == 50
    assert policy["disk_thresholds"]["disk_warning_threshold_percent"] == 65
    assert policy["disk_thresholds"]["disk_block_threshold_percent"] == 80
    assert policy["disk_thresholds"]["disk_critical_threshold_percent"] == 90
    assert policy["lean_runtime_retention_policy"]["keep_current_live_runtime"] is True
    assert policy["lean_runtime_retention_policy"]["keep_rollback_runtimes"] == 2
    assert policy["lean_runtime_retention_policy"]["remove_clean_stale_dashboard_runtimes"] is True
    assert policy["lean_runtime_retention_policy"]["never_remove_dirty_worktrees"] is True
    assert policy["artifact_manifest_rules"]["artifact_manifest_required_before_done"] is True
    assert policy["storage_delta_rules"]["storage_delta_required_before_done"] is True
    assert policy["archive_delete_rules"]["archive_verification_required_before_delete"] is True
    assert policy["archive_delete_rules"]["delete_forbidden_without_manifest"] is True
    assert policy["cloud_archive_policy"]["no_cloud_upload_in_dry_run"] is True
    assert "littleton-google-drive" in policy["cloud_archive_policy"]["allowed_archive_targets_placeholder"]
    assert policy["project_specific_posture"]["signal_room_video_requires_artifact_manifest_and_archive_plan"] is True
    assert policy["project_specific_posture"]["waha_external_archive_upload_requires_explicit_approval"] is True
    assert "future_enforcement_wiring" in policy["unresolved_policy_fields"]
    assert "approved_archive_targets" in policy["unresolved_policy_fields"]


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
    assert result["would_execute"] is False
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


def test_storage_guard_blocks_non_cleanup_work_above_critical_threshold():
    result = evaluate_storage_guard(
        {
            "disk_used_percent": 91,
            "free_gib": 80,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "observed disk usage is at or above lean critical threshold" in result["reasons"]
    assert "observed free disk is below lean minimum free space" in result["reasons"]
    assert "start non-cleanup work" in result["blocked_actions"]
    assert "start artifact-heavy work" in result["blocked_actions"]


def test_storage_guard_blocks_cleanup_without_manifest_and_runtime_protection():
    result = evaluate_storage_guard(
        {
            "cleanup_requested": True,
            "artifact_manifest_present": True,
            "cleanup_dry_run_manifest_present": False,
            "current_live_runtime_protected": False,
            "rollback_runtimes_protected": False,
            "accepted_live_repo_protected": True,
            "records_state_db_secrets_protected": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "cleanup requested without dry-run cleanup manifest" in result["reasons"]
    assert "cleanup did not confirm current live runtime is protected" in result["reasons"]
    assert "cleanup did not confirm rollback runtimes are protected" in result["reasons"]
    assert "perform storage cleanup" in result["blocked_actions"]


def test_storage_guard_blocks_dirty_worktree_deletion():
    result = evaluate_storage_guard(
        {
            "cleanup_requested": True,
            "artifact_manifest_present": True,
            "cleanup_dry_run_manifest_present": True,
            "current_live_runtime_protected": True,
            "rollback_runtimes_protected": True,
            "accepted_live_repo_protected": True,
            "records_state_db_secrets_protected": True,
            "dirty_worktree_cleanup_requested": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "dirty worktree cleanup is forbidden by lean-runtime policy" in result["reasons"]
    assert "delete dirty worktrees" in result["blocked_actions"]


def test_storage_guard_warns_when_cleanup_target_is_not_met():
    result = evaluate_storage_guard(
        {
            "cleanup_requested": True,
            "artifact_manifest_present": True,
            "cleanup_dry_run_manifest_present": True,
            "current_live_runtime_protected": True,
            "rollback_runtimes_protected": True,
            "accepted_live_repo_protected": True,
            "records_state_db_secrets_protected": True,
            "disk_used_percent": 75,
        }
    )

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert "observed disk usage is at or above lean warning threshold" in result["reasons"]
    assert "cleanup target is not yet met" in result["reasons"]


def test_storage_guard_warns_when_stale_clean_artifacts_are_eligible():
    result = evaluate_storage_guard(
        {
            "artifact_heavy_lane": False,
            "stale_clean_runtime_count": 3,
            "stale_clean_worktree_count": 4,
        }
    )

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert "clean stale runtimes are eligible for a cleanup lane" in result["reasons"]
    assert "clean stale worktrees are eligible for a cleanup lane" in result["reasons"]


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


def test_storage_guard_warns_on_safe_state_with_unresolved_enforcement_fields():
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
    assert "future_enforcement_wiring" in result["unresolved_policy_fields"]
    assert "approved_archive_targets" in result["unresolved_policy_fields"]


def test_storage_guard_unknown_for_artifact_heavy_lane_without_storage_state():
    result = evaluate_storage_guard({"artifact_heavy_lane": True})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert "artifact-heavy lane has unknown storage state" in result["reasons"]


def test_storage_guard_unknown_without_observed_state():
    result = evaluate_storage_guard({})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert result["would_execute"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "caller-supplied observed storage state is incomplete" in result["reasons"]


def test_cleanup_manifest_is_dry_run_and_protects_live_paths():
    manifest = build_storage_cleanup_manifest(
        {
            "current_live_runtime": "/home/jenny/.hermes/hermes-runtime-live",
            "accepted_live_repo": "/home/jenny/.hermes/hermes-agent",
            "rollback_runtimes": ["/home/jenny/.hermes/hermes-runtime-rollback"],
            "candidates": [
                {
                    "path": "/home/jenny/.hermes/hermes-runtime-live",
                    "kind": "dashboard_runtime",
                    "clean": True,
                    "size_gib": 9,
                },
                {
                    "path": "/home/jenny/.hermes/hermes-runtime-old",
                    "kind": "stale_runtime",
                    "clean": True,
                    "merged": True,
                    "size_gib": 12,
                },
            ],
        }
    )

    assert manifest["dry_run_only"] is True
    assert manifest["would_execute"] is False
    assert manifest["delete_enabled"] is False
    assert manifest["upload_enabled"] is False
    assert manifest["current_live_runtime_protected"] is True
    assert manifest["rollback_runtimes_protected"] is True
    assert manifest["accepted_live_repo_protected"] is True
    assert manifest["records_state_db_secrets_protected"] is True
    assert manifest["summary"]["protected_count"] == 1
    assert manifest["summary"]["eligible_count"] == 1
    assert manifest["eligible"][0]["path"] == "/home/jenny/.hermes/hermes-runtime-old"
    assert manifest["summary"]["eligible_gib"] == 12


def test_cleanup_manifest_blocks_dirty_worktrees_and_state_or_secret_paths():
    manifest = build_storage_cleanup_manifest(
        {
            "current_live_runtime": "/runtime/live",
            "accepted_live_repo": "/repo/accepted-live",
            "rollback_runtimes": ["/runtime/rollback"],
            "candidates": [
                {
                    "path": "/home/jenny/.hermes/worktrees/review-pr99",
                    "kind": "review_worktree",
                    "clean": False,
                    "dirty": True,
                    "size_gib": 4,
                },
                {
                    "path": "/home/jenny/.hermes/mission-control/records.jsonl",
                    "kind": "records",
                    "clean": True,
                    "size_gib": 0.1,
                },
                {
                    "path": "/home/jenny/.hermes/.env",
                    "kind": "config",
                    "clean": True,
                    "size_gib": 0.01,
                },
            ],
        }
    )

    assert manifest["summary"]["blocked_count"] == 3
    reasons = {item["reason"] for item in manifest["blocked"]}
    assert "dirty worktrees are never cleanup candidates" in reasons
    assert "records, state.db, or secrets are never cleanup candidates" in reasons


def test_cleanup_manifest_routes_archives_and_unknowns_to_review():
    manifest = build_storage_cleanup_manifest(
        {
            "current_live_runtime": "/runtime/live",
            "accepted_live_repo": "/repo/accepted-live",
            "rollback_runtimes": ["/runtime/rollback"],
            "candidates": [
                {
                    "path": "/home/jenny/reports/tool-tally-report-bundle.zip",
                    "kind": "report_package",
                    "clean": True,
                    "size_gib": 8,
                },
                {
                    "path": "/home/jenny/mystery",
                    "kind": "unknown",
                    "clean": True,
                    "size_gib": 3,
                },
            ],
        }
    )

    assert manifest["summary"]["needs_review_count"] == 2
    assert manifest["summary"]["needs_review_gib"] == 11
    assert "archive or large artifact needs cloud/archive decision before cleanup" in {
        item["reason"] for item in manifest["needs_review"]
    }
