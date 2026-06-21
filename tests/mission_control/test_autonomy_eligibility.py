from __future__ import annotations

from mission_control.autonomy_eligibility import (
    build_execution_packet_preview,
    classify_bridge_permissions,
    classify_control_path_permissions,
    classify_execution_mode,
    evaluate_read_only_autonomy_eligibility,
    evaluate_runtime_provenance,
    evaluate_scoped_pr_execution_eligibility,
    evaluate_scoped_pr_lane_eligibility,
)
from mission_control.workspace_status import build_workspace_status


HEAD = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
OLD_HEAD = "fe18ce20d6044dd91d115286e949366477a8706b"


def _assert_inert_preview(payload):
    assert payload["display_only"] is True
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["would_execute"] is False
    assert payload["would_dispatch"] is False
    assert payload["would_session_send"] is False
    assert payload["execution_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["dispatch_in_gateway"] is False
    assert payload["dispatch_state"] is False
    assert payload["execution_ready"] is False
    assert payload["live_operations_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["workers_enabled"] is False
    assert payload["worker_dispatch_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["daemon_enabled"] is False
    assert payload["waha_enabled"] is False
    assert payload["social_enabled"] is False
    assert payload["payment_enabled"] is False
    assert payload["queue_mutation_enabled"] is False
    assert payload["model_routing_enabled"] is False
    assert payload["stored"] is False
    assert payload["dry_run_only"] is True


def _runtime(path: str, head: str = HEAD, **overrides):
    payload = {
        "path": path,
        "exists": True,
        "git_healthy": True,
        "head": head,
        "status_short": ["## HEAD (no branch)"],
        "dirty_files": [],
        "untracked_files": [],
        "error": "",
    }
    payload.update(overrides)
    return payload


def _clean_runtime_state(**overrides):
    payload = {
        "source": {"head": HEAD},
        "accepted_baseline": _runtime("/runtime/accepted", HEAD),
        "dashboard_runtime": _runtime("/runtime/dashboard", HEAD),
        "gateway_runtime": _runtime("/runtime/gateway", HEAD),
        "rollback_runtime": _runtime("/runtime/rollback", HEAD),
        "dispatch_in_gateway": False,
        "active_lane_count": 0,
        "max_active_lane": 1,
    }
    payload.update(overrides)
    return payload


def _forbidden_actions():
    return [
        "file write",
        "commit",
        "PR creation",
        "merge",
        "deploy",
        "restart",
        "runtime switch",
        "Waha",
        "social",
        "payment",
        "model routing",
        "queue mutation",
        "worker",
        "timer",
        "daemon",
        "dispatch",
        "session-send",
    ]


def _read_only_packet_tool_profile():
    return {
        "paths": [
            {
                "path_id": "supervised_read_only_preview_packet",
                "label": "Supervised read-only preview packet",
                "read_only_safe": True,
                "tools": [
                    "read_workspace_status",
                    "read_record_summary",
                    "render_preview_packet",
                ],
            }
        ]
    }


def _eligible_preview_payload(**overrides):
    payload = {
        "runtime_provenance": evaluate_runtime_provenance(_clean_runtime_state()),
        "approval": {
            "approval_id": "approval-read-only-1",
            "status": "approved",
            "approval_mode": "one_time",
            "approval_scope": "project-hermes-mission-control:read-only-inspection",
            "action_class": "read_only_inspection",
            "expires_at": "2099-01-01T00:00:00Z",
            "consumed_at": "",
        },
        "run": {
            "run_id": "run-read-only-1",
            "project_id": "project-hermes-mission-control",
            "approval_id": "approval-read-only-1",
            "lane_type": "read_only_inspection",
            "status": "requested",
            "dispatch_state": False,
            "forbidden_actions": _forbidden_actions(),
        },
        "lane": {
            "lane_type": "read_only_inspection",
            "forbidden_actions": _forbidden_actions(),
        },
        "report_inbox_ready": True,
        "active_mutation_lane_count": 0,
        "bridge": {"manual_start_only": True, "dispatch_enabled": False, "session_send_enabled": False},
        "tool_permissions": _read_only_packet_tool_profile(),
        "capabilities": {},
        "now": "2026-06-19T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _eligible_one_run_status_report_payload(**overrides):
    approval_id = "approval-read-only-status-1"
    run_id = "run-read-only-status-1"
    report_id = "report-read-only-status-contract-1"
    payload = _eligible_preview_payload(
        mode="read_only",
        approval={
            "approval_id": approval_id,
            "run_id": run_id,
            "status": "approved",
            "approval_mode": "one_time",
            "approval_scope": "project-hermes-mission-control:supervised_read_only_status_report",
            "action_class": "supervised_read_only_status_report",
            "approved_actions": ("run exactly one supervised read-only Mission Control status report",),
            "forbidden_actions": _forbidden_actions(),
            "expires_at": "2099-01-01T00:00:00Z",
            "consumed_at": "",
        },
        run={
            "run_id": run_id,
            "project_id": "project-hermes-mission-control",
            "approval_id": approval_id,
            "lane_type": "supervised_read_only_status_report",
            "status": "requested",
            "execution_mode": "one_run_read_only",
            "dispatch_state": False,
            "forbidden_actions": _forbidden_actions(),
            "metadata": {
                "one_run_only": True,
                "execution_enabled": False,
                "dispatch_enabled": False,
                "session_send_enabled": False,
                "worker_dispatch_enabled": False,
            },
        },
        lane={
            "lane_type": "supervised_read_only_status_report",
            "forbidden_actions": _forbidden_actions(),
        },
        report={
            "report_id": report_id,
            "run_id": run_id,
            "approval_id": approval_id,
            "project_id": "project-hermes-mission-control",
            "status": "reviewed",
            "report_kind": "supervised_read_only_status_report_contract",
            "summary": "One-run read-only status-report contract.",
            "result": "Contract only; no Jenny execution occurred.",
            "risks": ("Execution remains limited to one read-only status report.",),
            "tests": ("trusted one-run packet gate",),
            "next_recommended_lane": "Run the guarded backend status-report path once.",
            "evidence_refs": ("accepted runtime head",),
            "metadata": {"no_jenny_execution": True, "jenny_executed": False},
        },
        report_inbox_ready=True,
        report_record_ready=True,
    )
    payload.update(overrides)
    return payload


def _eligible_pr_preview_payload(**overrides):
    payload = {
        "runtime_provenance": evaluate_runtime_provenance(_clean_runtime_state()),
        "approval": {
            "approval_id": "approval-pr-1",
            "status": "approved",
            "approval_mode": "one_time",
            "approval_scope": "project-hermes-mission-control:scoped-pr:mission_control/",
            "action_class": "pr_creation",
            "expires_at": "2099-01-01T00:00:00Z",
            "consumed_at": "",
            "approved_files": ["mission_control/autonomy_eligibility.py"],
        },
        "run": {
            "run_id": "run-pr-1",
            "project_id": "project-hermes-mission-control",
            "approval_id": "approval-pr-1",
            "lane_type": "pr_creation",
            "status": "requested",
            "dispatch_state": False,
            "forbidden_actions": _forbidden_actions(),
        },
        "lane": {
            "lane_type": "pr_creation",
            "allowed_files": ["mission_control/autonomy_eligibility.py"],
            "forbidden_actions": _forbidden_actions(),
            "tests_required": True,
            "review_required": True,
        },
        "report_contract": {"required": True, "tests_required": True, "review_required": True},
        "active_mutation_lane_count": 1,
        "bridge": {"manual_start_only": True},
        "capabilities": {},
        "now": "2026-06-19T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _eligible_scoped_pr_execution_payload(**overrides):
    forbidden = _forbidden_actions() + ["secrets access", "files outside exact scope"]
    file_path = "docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md"
    payload = _eligible_pr_preview_payload(
        mode="scoped_pr",
        approval={
            "approval_id": "approval-scoped-pr-exec-1",
            "run_id": "run-scoped-pr-exec-1",
            "status": "approved",
            "approval_mode": "one_time",
            "approval_scope": "project-hermes-mission-control:scoped-pr-draft:exact-docs-file",
            "action_class": "pr_creation",
            "approved_actions": ("create exactly one docs-only draft PR",),
            "forbidden_actions": forbidden,
            "expires_at": "2099-01-01T00:00:00Z",
            "consumed_at": "",
            "approved_files": [file_path],
            "metadata": {
                "approved_files": [file_path],
                "max_files": 1,
                "max_commits": 1,
                "max_prs": 1,
            },
        },
        run={
            "run_id": "run-scoped-pr-exec-1",
            "project_id": "project-hermes-mission-control",
            "approval_id": "approval-scoped-pr-exec-1",
            "lane_type": "pr_creation",
            "status": "requested",
            "execution_mode": "scoped_pr_draft",
            "dispatch_state": False,
            "allowed_actions": ("create exactly one docs-only draft PR",),
            "forbidden_actions": forbidden,
            "metadata": {
                "scoped_pr_execution": True,
                "draft_pr": True,
                "runner_id": "mission_control_scoped_pr_draft_runner",
                "branch_name": "codex/scoped-pr-docs-smoke-test",
                "base_branch": "accepted-live/approval-safety-5ad8906",
                "draft_pr_title": "docs: record scoped PR creation smoke test",
                "edit_instruction": "Append a bounded scoped PR smoke-test note.",
                "allowed_files": [file_path],
                "max_files": 1,
                "max_commits": 1,
                "max_prs": 1,
            },
        },
        lane={
            "lane_type": "pr_creation",
            "execution_mode": "scoped_pr_draft",
            "allowed_actions": ("create exactly one docs-only draft PR",),
            "allowed_files": [file_path],
            "forbidden_actions": forbidden,
            "runner_id": "mission_control_scoped_pr_draft_runner",
            "branch_name": "codex/scoped-pr-docs-smoke-test",
            "base_branch": "accepted-live/approval-safety-5ad8906",
            "draft_pr_title": "docs: record scoped PR creation smoke test",
            "edit_instruction": "Append a bounded scoped PR smoke-test note.",
            "max_files": 1,
            "max_commits": 1,
            "max_prs": 1,
            "tests_required": True,
            "review_required": True,
        },
        report_contract={
            "required": True,
            "tests_required": True,
            "review_required": True,
            "result_summary_required": True,
            "report_kind": "scoped_pr_draft_execution_contract",
        },
        active_read_only_lane_count=0,
        active_mutation_lane_count=1,
        active_unknown_lane_count=0,
    )
    payload.update(overrides)
    return payload


def test_clean_aligned_runtime_provenance_allows_preview_inputs():
    result = evaluate_runtime_provenance(_clean_runtime_state())

    _assert_inert_preview(result)
    assert result["status"] == "CLEAN_AND_ALIGNED"
    assert result["primary_status"] == "CLEAN_AND_ALIGNED"
    assert result["autonomy_blocked"] is False
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_stale_accepted_baseline_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(accepted_baseline=_runtime("/runtime/accepted", OLD_HEAD))
    )

    _assert_inert_preview(result)
    assert result["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert "SOURCE_CURRENT_BUT_BASELINE_STALE" in result["statuses"]
    assert "accepted baseline HEAD does not match source HEAD" in result["autonomy_blocked_reasons"]


def test_source_default_branch_drift_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(source={"head": HEAD, "default_branch_head": OLD_HEAD})
    )

    assert result["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert result["primary_status"] == "SOURCE_DEFAULT_DRIFT"
    assert "SOURCE_DEFAULT_DRIFT" in result["statuses"]
    assert result["default_branch_head"] == OLD_HEAD
    assert "source HEAD does not match default branch HEAD" in result["autonomy_blocked_reasons"]


def test_merged_prs_after_accepted_baseline_are_explicit_provenance_blockers():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(
            source={
                "head": HEAD,
                "latest_merged_pr": "396",
                "merged_prs_after_accepted_baseline": ["395", "#396"],
            },
            accepted_baseline=_runtime("/runtime/accepted", OLD_HEAD),
        )
    )

    assert result["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert result["primary_status"] == "SOURCE_CURRENT_BUT_BASELINE_STALE"
    assert "SOURCE_CURRENT_BUT_BASELINE_STALE" in result["statuses"]
    assert result["latest_merged_pr"] == "396"
    assert result["merged_prs_after_accepted_baseline"] == ["395", "#396"]
    assert "latest merged PR #396 is after the accepted baseline" in result["autonomy_blocked_reasons"]
    assert "merged PRs after accepted baseline: PR #395, PR #396" in result["autonomy_blocked_reasons"]


def test_dirty_runtime_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(dashboard_runtime=_runtime("/runtime/dashboard", dirty_files=[" M package-lock.json"]))
    )

    assert "DIRTY_RUNTIME" in result["statuses"]
    assert "dashboard runtime has dirty or untracked files" in result["autonomy_blocked_reasons"]


def test_runtime_provenance_blocks_stringy_dispatch_flags():
    result = evaluate_runtime_provenance(_clean_runtime_state(dispatch_in_gateway="true"))

    assert result["autonomy_blocked"] is True
    assert "dispatch is enabled" in result["autonomy_blocked_reasons"]
    assert result["would_execute"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_broken_gateway_git_metadata_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(
            gateway_runtime=_runtime(
                "/runtime/gateway",
                git_healthy=False,
                error="fatal: not a git repository: /runtime/gateway",
            )
        )
    )

    assert "BROKEN_GIT_METADATA" in result["statuses"]
    assert "GATEWAY_UNTRUSTED" in result["statuses"]
    assert "gateway git metadata is broken" in result["autonomy_blocked_reasons"]


def test_dashboard_gateway_mismatch_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(gateway_runtime=_runtime("/runtime/gateway", OLD_HEAD))
    )

    assert "DASHBOARD_GATEWAY_DRIFT" in result["statuses"]
    assert "dashboard and gateway runtime HEADs do not match" in result["autonomy_blocked_reasons"]


def test_missing_runtime_path_blocks_autonomy():
    result = evaluate_runtime_provenance(_clean_runtime_state(gateway_runtime={"exists": False}))

    assert "MISSING_RUNTIME_PATH" in result["statuses"]
    assert "gateway runtime path is missing or absent" in result["autonomy_blocked_reasons"]


def test_unrecorded_runtime_blocks_without_missing_path_status():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(gateway_runtime={"recorded": False, "state": "unrecorded"})
    )

    assert "UNRECORDED_RUNTIME" in result["statuses"]
    assert "MISSING_RUNTIME_PATH" not in result["statuses"]
    assert "gateway runtime facts are unrecorded" in result["autonomy_blocked_reasons"]
    assert result["runtimes"]["gateway"]["state"] == "unrecorded"
    assert result["runtimes"]["gateway"]["unrecorded"] is True


def test_clean_previous_version_rollback_is_informational_not_blocking():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(rollback_runtime=_runtime("/runtime/rollback", OLD_HEAD))
    )

    assert result["status"] == "CLEAN_AND_ALIGNED"
    assert result["primary_status"] == "CLEAN_AND_ALIGNED"
    assert result["autonomy_blocked"] is False
    assert result["statuses"] == ["CLEAN_AND_ALIGNED"]
    assert "ROLLBACK_STALE" not in result["statuses"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" in result["informational_statuses"]
    assert "rollback runtime is a clean previous version" in result["warnings"]
    assert result["runtimes"]["rollback"]["availability"] == "previous_version"
    assert result["would_execute"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_missing_rollback_runtime_path_blocks_autonomy():
    result = evaluate_runtime_provenance(_clean_runtime_state(rollback_runtime={"exists": False}))

    assert "MISSING_RUNTIME_PATH" in result["statuses"]
    assert "rollback runtime path is missing or absent" in result["autonomy_blocked_reasons"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" not in result["informational_statuses"]


def test_broken_rollback_git_metadata_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(
            rollback_runtime=_runtime(
                "/runtime/rollback",
                OLD_HEAD,
                git_healthy=False,
                error="fatal: not a git repository: /runtime/rollback",
            )
        )
    )

    assert "BROKEN_GIT_METADATA" in result["statuses"]
    assert "rollback git metadata is broken" in result["autonomy_blocked_reasons"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" not in result["informational_statuses"]


def test_dirty_rollback_runtime_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(
            rollback_runtime=_runtime(
                "/runtime/rollback",
                OLD_HEAD,
                status_short=["## HEAD (no branch)", " M mission_control/autonomy_eligibility.py"],
            )
        )
    )

    assert "DIRTY_RUNTIME" in result["statuses"]
    assert "rollback runtime has dirty or untracked files" in result["autonomy_blocked_reasons"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" not in result["informational_statuses"]


def test_unknown_rollback_head_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(rollback_runtime=_runtime("/runtime/rollback", ""))
    )

    assert "ROLLBACK_HEAD_UNKNOWN" in result["statuses"]
    assert "rollback runtime HEAD is missing or invalid" in result["autonomy_blocked_reasons"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" not in result["informational_statuses"]


def test_malformed_rollback_head_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(rollback_runtime=_runtime("/runtime/rollback", "not-a-sha"))
    )

    assert "ROLLBACK_HEAD_UNKNOWN" in result["statuses"]
    assert "rollback runtime HEAD is missing or invalid" in result["autonomy_blocked_reasons"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" not in result["informational_statuses"]


def test_read_only_preview_with_previous_rollback_remains_inert_and_eligible():
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            runtime_provenance=evaluate_runtime_provenance(
                _clean_runtime_state(rollback_runtime=_runtime("/runtime/rollback", OLD_HEAD))
            )
        )
    )

    assert result["eligible"] is True
    assert result["runtime_provenance"]["primary_status"] == "CLEAN_AND_ALIGNED"
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" in result["runtime_provenance"]["informational_statuses"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_approved_read_only_lane_preview_is_inert_and_eligible():
    result = evaluate_read_only_autonomy_eligibility(_eligible_preview_payload())

    _assert_inert_preview(result)
    assert result["eligible"] is True
    assert result["would_execute"] is False
    assert result["stored"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False


def test_split_policy_allows_two_read_only_lanes_without_global_lane_block():
    provenance = evaluate_runtime_provenance(
        _clean_runtime_state(
            active_lane_count=2,
            max_active_lane=1,
            split_lane_policy_present=True,
            active_read_only_lane_count=2,
            max_read_only_lanes=2,
            active_mutation_lane_count=0,
            max_mutation_lanes=1,
            active_unknown_lane_count=0,
        )
    )
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            runtime_provenance=provenance,
            active_read_only_lane_count=2,
            max_read_only_lanes=2,
            active_mutation_lane_count=0,
        )
    )

    assert provenance["primary_status"] == "CLEAN_AND_ALIGNED"
    assert provenance["autonomy_blocked"] is False
    assert provenance["active_read_only_lane_count"] == 2
    assert provenance["max_read_only_lanes"] == 2
    assert result["eligible"] is True
    assert result["read_only_concurrency_supported"] is True
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_split_policy_blocks_third_read_only_lane():
    provenance = evaluate_runtime_provenance(
        _clean_runtime_state(
            active_lane_count=3,
            max_active_lane=1,
            split_lane_policy_present=True,
            active_read_only_lane_count=3,
            max_read_only_lanes=2,
            active_mutation_lane_count=0,
            max_mutation_lanes=1,
            active_unknown_lane_count=0,
        )
    )
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            runtime_provenance=provenance,
            active_read_only_lane_count=3,
            max_read_only_lanes=2,
        )
    )

    assert provenance["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert "active read-only lane count exceeds configured maximum" in provenance["autonomy_blocked_reasons"]
    assert result["eligible"] is False
    assert "active read-only lane count exceeds configured maximum" in result["blocked_reasons"]


def test_split_policy_blocks_unknown_lane_classification():
    provenance = evaluate_runtime_provenance(
        _clean_runtime_state(
            active_lane_count=1,
            max_active_lane=1,
            split_lane_policy_present=True,
            active_read_only_lane_count=0,
            active_mutation_lane_count=0,
            active_unknown_lane_count=1,
        )
    )
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            runtime_provenance=provenance,
            active_unknown_lane_count=1,
        )
    )

    assert provenance["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert "active lane classification is unknown" in provenance["autonomy_blocked_reasons"]
    assert result["eligible"] is False
    assert "active lane classification is unknown" in result["blocked_reasons"]


def test_approval_expiry_consumption_and_broad_scope_block_eligibility():
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            approval={
                "approval_id": "approval-read-only-1",
                "status": "consumed",
                "approval_mode": "one_time",
                "approval_scope": "*",
                "action_class": "read_only_inspection",
                "expires_at": "2020-01-01T00:00:00Z",
                "consumed_at": "2026-06-19T00:00:00Z",
            }
        )
    )

    _assert_inert_preview(result)
    assert result["eligible"] is False
    assert "approval is consumed" in result["blocked_reasons"]
    assert "approval is expired" in result["blocked_reasons"]
    assert "approval scope must be exact and bounded" in result["blocked_reasons"]


def test_active_mutation_lane_and_non_read_only_lane_block_eligibility():
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            active_mutation_lane_count=1,
            run={
                "run_id": "run-impl",
                "project_id": "project-hermes-mission-control",
                "approval_id": "approval-read-only-1",
                "lane_type": "implementation",
                "status": "requested",
                "dispatch_state": False,
                "forbidden_actions": _forbidden_actions(),
            },
        )
    )

    assert result["eligible"] is False
    assert "active mutation lane count must be 0" in result["blocked_reasons"]
    assert "lane type must be read-only" in result["blocked_reasons"]


def test_write_capable_bridge_is_not_read_only_safe():
    bridge = classify_bridge_permissions({"manual_hermes_answer_enabled": True})
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(bridge={"manual_hermes_answer_enabled": True})
    )

    _assert_inert_preview(bridge)
    _assert_inert_preview(result)
    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]


def test_worker_dispatch_bridge_path_is_not_read_only_safe():
    bridge = classify_bridge_permissions({"worker_dispatch_enabled": True})
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(bridge={"worker_dispatch_enabled": True})
    )

    _assert_inert_preview(bridge)
    _assert_inert_preview(result)
    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert bridge["worker_dispatch_enabled"] is False
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]


def test_live_bridge_flags_override_read_only_safe_claim():
    bridge_state = {
        "read_only_safe": True,
        "would_execute": True,
        "model_routing_enabled": True,
        "discord_automation_enabled": True,
        "waha_enabled": True,
        "social_enabled": True,
        "payment_enabled": True,
        "queue_mutation_enabled": True,
        "workers_enabled": True,
    }
    bridge = classify_bridge_permissions(bridge_state)
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(bridge=bridge_state)
    )

    _assert_inert_preview(bridge)
    _assert_inert_preview(result)
    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert bridge["read_only_safe"] is False
    assert bridge["would_execute"] is False
    assert bridge["model_routing_enabled"] is False
    assert bridge["discord_automation_enabled"] is False
    assert bridge["waha_enabled"] is False
    assert bridge["social_enabled"] is False
    assert bridge["payment_enabled"] is False
    assert bridge["queue_mutation_enabled"] is False
    assert bridge["workers_enabled"] is False
    assert any("would_execute must remain false in previews" in reason for reason in bridge["reasons"])
    assert any("model_routing_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("discord_automation_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("waha_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("social_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("payment_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("queue_mutation_enabled must remain false" in reason for reason in bridge["reasons"])
    assert any("workers_enabled must remain false" in reason for reason in bridge["reasons"])
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]
    assert any(reason.startswith("bridge: bridge live execution flags must be disabled") for reason in result["blocked_reasons"])


def test_send_to_jenny_bridge_path_is_not_read_only_safe():
    bridge = classify_bridge_permissions({"send_to_jenny_enabled": True})
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(bridge={"send_to_jenny_enabled": True})
    )

    _assert_inert_preview(bridge)
    _assert_inert_preview(result)
    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert bridge["send_to_jenny_enabled"] is False
    assert any("send_to_jenny_enabled must remain false" in reason for reason in bridge["reasons"])
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]
    assert "bridge: bridge live execution flags must be disabled: send_to_jenny_enabled must remain false" in result["blocked_reasons"]


def test_control_path_permission_catalog_covers_required_paths_and_blocks_write_capable_paths():
    result = classify_control_path_permissions()

    _assert_inert_preview(result)
    assert result["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert result["read_only_safe"] is False
    assert result["stored"] is False
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
    assert all(path["would_execute"] is False for path in result["paths"])
    assert all(path["would_dispatch"] is False for path in result["paths"])
    assert all(path["would_session_send"] is False for path in result["paths"])
    for path in result["paths"]:
        _assert_inert_preview(path)
    path_ids = {path["path_id"] for path in result["paths"]}
    assert {
        "github_bridge_outbox",
        "github_bridge_answer_once",
        "jenny_bridge_relay",
        "hermes_responder_toolsets",
        "delegate_tool",
        "async_delegation",
        "process_registry",
        "file_write_shell_patch",
        "laptop_codex_worker_node",
        "child_agent_capability_inheritance",
    }.issubset(path_ids)
    classifications = {path["path_id"]: path["permission_classification"] for path in result["paths"]}
    assert classifications["github_bridge_outbox"] == "write_capable_not_safe_for_autonomy"
    assert classifications["github_bridge_answer_once"] == "write_capable_not_safe_for_autonomy"
    assert classifications["jenny_bridge_relay"] == "manual_only"
    assert classifications["hermes_responder_toolsets"] == "write_capable_not_safe_for_autonomy"
    assert classifications["delegate_tool"] == "unknown_blocked"
    assert classifications["file_write_shell_patch"] == "write_capable_not_safe_for_autonomy"
    assert classifications["laptop_codex_worker_node"] == "write_capable_not_safe_for_autonomy"
    assert classifications["child_agent_capability_inheritance"] == "unknown_blocked"


def test_control_path_detector_blocks_dangerous_named_tools_even_when_marked_read_only():
    result = classify_control_path_permissions(
        {
            "paths": [
                {"path_id": "delegator", "read_only_safe": True, "allowed_tools": ["delegate_task"]},
                {"path_id": "async_agent", "read_only_safe": True, "tools": ["async_delegation"]},
                {"path_id": "processes", "read_only_safe": True, "tool_names": ["process_registry"]},
                {"path_id": "messenger", "read_only_safe": True, "tools": ["send_message"]},
                {"path_id": "file_ops", "read_only_safe": True, "tools": ["file_operations"]},
                {"path_id": "responder_file_toolset", "read_only_safe": True, "enabled_toolsets": "file,skills"},
            ]
        }
    )

    _assert_inert_preview(result)
    for path in result["paths"]:
        _assert_inert_preview(path)
    classifications = {path["path_id"]: path["permission_classification"] for path in result["paths"]}
    assert result["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert classifications == {
        "delegator": "write_capable_not_safe_for_autonomy",
        "async_agent": "write_capable_not_safe_for_autonomy",
        "processes": "write_capable_not_safe_for_autonomy",
        "messenger": "write_capable_not_safe_for_autonomy",
        "file_ops": "write_capable_not_safe_for_autonomy",
        "responder_file_toolset": "write_capable_not_safe_for_autonomy",
    }
    assert set(result["write_capable_path_ids"]) == set(classifications)


def test_control_path_permission_detector_separates_read_only_manual_and_write_tools():
    result = classify_control_path_permissions(
        {
            "paths": [
                {"path_id": "audit_read", "read_only_safe": True, "tools": ["read_file", "list_records"]},
                {"path_id": "manual_report", "manual_copy_only": True, "append_records": True},
                {"path_id": "shell_patch", "tools": ["shell", "apply_patch"]},
            ]
        }
    )

    _assert_inert_preview(result)
    for path in result["paths"]:
        _assert_inert_preview(path)
    classifications = {path["path_id"]: path["permission_classification"] for path in result["paths"]}
    assert result["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert classifications["audit_read"] == "read_only_safe"
    assert classifications["manual_report"] == "manual_only"
    assert classifications["shell_patch"] == "write_capable_not_safe_for_autonomy"
    assert "shell_patch" in result["write_capable_path_ids"]


def test_read_only_eligibility_blocks_write_capable_tool_permissions():
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            tool_permissions={
                "paths": [
                    {"path_id": "audit_read", "read_only_safe": True, "tools": ["read_file"]},
                    {"path_id": "file_patch", "patch": True},
                ]
            }
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["tool_permissions"])
    assert result["eligible"] is False
    assert "tool permission paths are not read-only safe" in result["blocked_reasons"]
    assert any("file_patch" in reason for reason in result["blocked_reasons"])
    assert result["tool_permissions"]["permission_classification"] == "write_capable_not_safe_for_autonomy"


def test_read_only_eligibility_accepts_inert_preview_packet_tool_permissions():
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            bridge={"manual_copy_only": True},
            tool_permissions={
                "paths": [
                    {
                        "path_id": "supervised_read_only_preview_packet",
                        "label": "Supervised read-only preview packet",
                        "read_only_safe": True,
                        "tools": [
                            "read_workspace_status",
                            "read_record_summary",
                            "render_preview_packet",
                        ],
                    }
                ]
            },
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["tool_permissions"])
    assert result["eligible"] is True
    assert result["execution_ready"] is False
    assert result["bridge_permissions"]["permission_classification"] == "manual_only"
    assert result["tool_permissions"]["permission_classification"] == "read_only_safe"
    assert result["tool_permissions"]["read_only_safe"] is True
    assert result["blocked_reasons"] == []


def test_eligibility_blocks_protected_capability_aliases():
    read_only = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(
            capabilities={
                "daemon_enabled": True,
                "model_routing_enabled": True,
                "queue_mutation_enabled": True,
                "worker_dispatch_enabled": True,
                "workers_enabled": True,
            }
        )
    )
    scoped_pr = evaluate_scoped_pr_lane_eligibility(
        _eligible_pr_preview_payload(
            capabilities={
                "daemon": True,
                "payment_enabled": True,
                "social_enabled": True,
                "timer_enabled": True,
                "waha_enabled": True,
            }
        )
    )

    _assert_inert_preview(read_only)
    _assert_inert_preview(scoped_pr)
    assert read_only["eligible"] is False
    assert scoped_pr["eligible"] is False
    for reason in (
        "capability daemon_enabled must be disabled",
        "capability model_routing_enabled must be disabled",
        "capability queue_mutation_enabled must be disabled",
        "capability worker_dispatch_enabled must be disabled",
        "capability workers_enabled must be disabled",
    ):
        assert reason in read_only["blocked_reasons"]
    for reason in (
        "capability daemon must be disabled",
        "capability payment_enabled must be disabled",
        "capability social_enabled must be disabled",
        "capability timer_enabled must be disabled",
        "capability waha_enabled must be disabled",
    ):
        assert reason in scoped_pr["blocked_reasons"]


def test_scoped_pr_lane_preview_is_inert_and_eligible_with_exact_scope():
    result = evaluate_scoped_pr_lane_eligibility(_eligible_pr_preview_payload())

    _assert_inert_preview(result)
    assert result["eligible"] is True
    assert result["would_execute"] is False
    assert result["would_create_pr"] is False
    assert result["would_commit"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
    assert result["scope"]["files"] == ["mission_control/autonomy_eligibility.py"]


def test_scoped_pr_lane_blocks_wildcard_scope_and_missing_report_contract():
    result = evaluate_scoped_pr_lane_eligibility(
        _eligible_pr_preview_payload(
            approval={
                "approval_id": "approval-pr-1",
                "status": "approved",
                "approval_mode": "one_time",
                "approval_scope": "project-hermes-mission-control:scoped-pr:*",
                "action_class": "pr_creation",
                "approved_files": ["*"],
            },
            lane={"lane_type": "pr_creation", "allowed_files": ["*"], "forbidden_actions": _forbidden_actions()},
            report_contract={},
        )
    )

    _assert_inert_preview(result)
    assert result["eligible"] is False
    assert "approval scope must be exact and bounded" in result["blocked_reasons"]
    assert "scoped PR lane cannot use wildcard paths" in result["blocked_reasons"]
    assert "report/result contract is required" in result["blocked_reasons"]


def test_scoped_pr_lane_blocks_merge_deploy_and_runtime_switch():
    result = evaluate_scoped_pr_lane_eligibility(
        _eligible_pr_preview_payload(
            lane={
                "lane_type": "pr_creation",
                "allowed_files": ["mission_control/autonomy_eligibility.py"],
                "forbidden_actions": _forbidden_actions(),
                "merge_allowed": True,
                "deploy_allowed": True,
                "runtime_switch_allowed": True,
                "tests_required": True,
                "review_required": True,
            },
            capabilities={"merge": True, "deploy": True, "runtime_switch": True},
        )
    )

    assert result["eligible"] is False
    assert "merge is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "deploy is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "runtime switch is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "capability merge must be disabled" in result["blocked_reasons"]
    assert "capability deploy must be disabled" in result["blocked_reasons"]
    assert "capability runtime_switch must be disabled" in result["blocked_reasons"]


def test_scoped_pr_execution_gate_authorizes_exact_docs_draft_pr_lane():
    result = evaluate_scoped_pr_execution_eligibility(_eligible_scoped_pr_execution_payload())

    assert result["source"] == "mission_control_scoped_pr_execution_eligibility_v1"
    assert result["eligible"] is True
    assert result["trusted_for_execution"] is True
    assert result["one_run_authorized"] is True
    assert result["would_execute"] is True
    assert result["would_create_pr"] is True
    assert result["would_write_files"] is True
    assert result["would_commit"] is True
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
    assert result["merge_enabled"] is False
    assert result["deploy_enabled"] is False
    assert result["runtime_switch_enabled"] is False
    packet = result["packet"]
    assert packet["runner_id"] == "mission_control_scoped_pr_draft_runner"
    assert packet["mode"] == "scoped_pr_draft"
    assert packet["draft_pr_required"] is True
    assert packet["max_files"] == 1
    assert packet["max_commits"] == 1
    assert packet["max_prs"] == 1
    assert packet["allowed_file"] == "docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md"


def test_scoped_pr_execution_gate_blocks_code_paths_and_non_draft_metadata():
    payload = _eligible_scoped_pr_execution_payload()
    payload["approval"] = {
        **payload["approval"],
        "approved_files": ["mission_control/autonomy_eligibility.py"],
    }
    payload["lane"] = {
        **payload["lane"],
        "allowed_files": ["mission_control/autonomy_eligibility.py"],
    }
    payload["run"] = {
        **payload["run"],
        "metadata": {
            **payload["run"]["metadata"],
            "allowed_files": ["mission_control/autonomy_eligibility.py"],
            "draft_pr": False,
        },
    }

    result = evaluate_scoped_pr_execution_eligibility(payload)

    assert result["eligible"] is False
    assert result["trusted_for_execution"] is False
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert "RunRecord metadata must require draft_pr=true" in result["blocked_reasons"]
    assert "scoped PR execution is limited to safe docs file paths" in result["blocked_reasons"]


def test_scoped_pr_execution_gate_blocks_missing_runner_limits_and_live_flags():
    payload = _eligible_scoped_pr_execution_payload(
        lane={
            "lane_type": "pr_creation",
            "execution_mode": "scoped_pr_draft",
            "allowed_actions": ("create exactly one docs-only draft PR",),
            "allowed_files": ["docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md"],
            "forbidden_actions": _forbidden_actions() + ["secrets access", "files outside exact scope"],
            "runner_id": "other_runner",
            "branch_name": "main",
            "draft_pr_title": "docs: unsafe",
            "edit_instruction": "Append note.",
            "max_files": 2,
            "max_commits": 1,
            "max_prs": 1,
            "dispatch_enabled": True,
            "tests_required": True,
            "review_required": True,
        }
    )

    result = evaluate_scoped_pr_execution_eligibility(payload)

    assert result["eligible"] is False
    assert "dispatch_enabled must remain false for scoped PR execution" in result["blocked_reasons"]
    assert "scoped PR execution requires the approved draft PR runner" in result["blocked_reasons"]
    assert "scoped PR execution requires a safe codex/* branch name" in result["blocked_reasons"]
    assert "max_files must be exactly 1" in result["blocked_reasons"]


def test_execution_mode_classification_allows_preview_families_without_execution():
    cases = [
        (_eligible_preview_payload(), "read_only_preview", "read_only_preview_allowed"),
        (_eligible_pr_preview_payload(mode="scoped_pr"), "scoped_pr_preview", "scoped_pr_preview_allowed"),
        (
            _eligible_pr_preview_payload(
                mode="worker_node",
                worker_node={
                    "parent_run_id": "run-pr-1",
                    "worker_identity": "codex",
                    "worker_host_label": "laptop-codex",
                    "presence_status": "online",
                },
            ),
            "worker_node_preview",
            "worker_node_preview_allowed",
        ),
    ]

    for payload, mode_family, allowed_key in cases:
        result = classify_execution_mode(payload)

        _assert_inert_preview(result)
        assert result["source"] == "mission_control_execution_mode_classification_v1"
        assert result["mode_family"] == mode_family
        assert result["preview_ready"] is True
        assert result[allowed_key] is True
        assert result["blocked"] is False
        assert result["display_only"] is True
        assert result["trusted_for_execution"] is False
        assert result["would_execute"] is False
        assert result["execution_enabled"] is False
        assert result["dispatch_enabled"] is False
        assert result["session_send_enabled"] is False
        assert result["worker_dispatch_enabled"] is False
        assert result["stored"] is False
        assert result["dry_run_only"] is True


def test_execution_mode_classification_blocks_protected_modes_and_enabled_flags():
    cases = [
        {"mode": "deploy", "action_class": "deploy"},
        {"mode": "restart gateway", "lane_type": "restart"},
        {"mode": "runtime switch", "action_class": "runtime_switch"},
        {"mode": "read_only", "capabilities": {"payment": True}},
        {"mode": "scoped_pr", "capabilities": {"waha": True}},
        {"mode": "worker_node", "worker_node": {"worker_dispatch_enabled": True}},
        {"mode": "read_only", "action_class": "model_routing"},
        {"mode": "implementation", "action_class": "implementation"},
        {"mode": "read_only", "execution_enabled": "yes", "dispatch_enabled": "1"},
    ]

    for payload in cases:
        result = classify_execution_mode(payload)

        _assert_inert_preview(result)
        assert result["preview_ready"] is False
        assert result["blocked"] is True
        assert result["blocked_reasons"]
        assert result["would_execute"] is False
        assert result["execution_enabled"] is False
        assert result["dispatch_enabled"] is False
        assert result["session_send_enabled"] is False
        assert result["worker_dispatch_enabled"] is False
        assert result["trusted_for_execution"] is False


def test_implementation_lane_cannot_smuggle_deploy_or_live_ops():
    result = classify_execution_mode(
        {
            "mode": "implementation",
            "action_class": "implementation",
            "lane": {
                "lane_type": "implementation",
                "allowed_actions": [
                    "deploy gateway",
                    "restart runtime",
                    "runtime switch",
                    "Waha send",
                    "payment checkout",
                    "model routing",
                    "queue enqueue",
                    "cron timer",
                    "session-send",
                ],
            },
            "capabilities": {
                "deploy": True,
                "restart": True,
                "runtime_switch": True,
                "waha": True,
                "payment": True,
                "model_routing": True,
                "queue_mutation": True,
                "dispatch": True,
                "session_send": True,
                "worker_dispatch_enabled": True,
            },
        }
    )

    _assert_inert_preview(result)
    assert result["mode_family"] == "higher_risk_blocked"
    assert result["preview_ready"] is False
    assert result["blocked"] is True
    assert result["separate_approval_required"] is True
    assert "action_class implementation is not eligible for autonomous execution" in result["blocked_reasons"]
    assert set(result["protected_action_markers"]) >= {
        "deploy",
        "restart",
        "runtime_switch",
        "waha",
        "payment",
        "model_routing",
        "queue_mutation",
        "dispatch",
        "session_send",
        "worker dispatch enabled",
        "worker_timer_enablement",
    }
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
    assert result["trusted_for_execution"] is False


def test_execution_packet_preview_is_never_an_execution_path():
    result = build_execution_packet_preview(_eligible_pr_preview_payload(mode="scoped_pr"))

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    _assert_inert_preview(result["packet"]["worker_node_contract"])
    assert result["eligible"] is True
    assert result["source"] == "mission_control_execution_packet_preview_v1"
    assert result["display_only"] is True
    assert result["trusted_for_execution"] is False
    assert result["packet"]["mode"] == "scoped_pr"
    assert result["packet"]["run_id"] == "run-pr-1"
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_read_only_execution_packet_allows_manual_bridge_with_read_only_safe_packet_path():
    result = build_execution_packet_preview(_eligible_preview_payload(mode="read_only"))

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    assert result["eligible"] is True
    assert result["packet"]["mode"] == "read_only"
    assert result["packet"]["run_id"] == "run-read-only-1"
    assert result["packet"]["approval_id"] == "approval-read-only-1"
    assert result["packet"]["would_execute"] is False
    assert result["packet"]["execution_enabled"] is False
    assert result["blocked_reasons"] == []
    assert "bridge path is manual-only; preview must not execute" in result["warnings"]
    assert result["trusted_for_execution"] is False
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_trusted_read_only_one_run_status_packet_stays_narrow_and_non_dispatching():
    result = build_execution_packet_preview(_eligible_one_run_status_report_payload())

    assert result["eligible"] is True
    assert result["blocked_reasons"] == []
    assert result["display_only"] is True
    assert result["trusted_for_execution"] is True
    assert result["one_run_authorized"] is True
    assert result["one_run_authorization_scope"] == "supervised_read_only_status_report"
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
    packet = result["packet"]
    assert packet["mode"] == "read_only"
    assert packet["one_run_authorized"] is True
    assert packet["status_report_only"] is True
    assert packet["uses_bridge"] is False
    assert packet["uses_dispatch"] is False
    assert packet["uses_session_send"] is False
    assert packet["uses_worker_dispatch"] is False
    assert packet["uses_write_tools"] is False
    assert packet["would_execute"] is False
    assert packet["execution_enabled"] is False
    assert packet["dispatch_enabled"] is False
    assert packet["session_send_enabled"] is False
    assert packet["worker_dispatch_enabled"] is False


def test_trusted_read_only_one_run_status_packet_blocks_duplicate_approval_id():
    result = build_execution_packet_preview(
        _eligible_one_run_status_report_payload(
            approval_record_count_for_id=2,
            approval_id_duplicated=True,
            duplicate_approval_ids=["approval-read-only-status-1"],
        )
    )

    assert result["eligible"] is False
    assert result["trusted_for_execution"] is False
    assert result["one_run_authorized"] is False
    assert "approval_id approval-read-only-status-1 is duplicated and ambiguous" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False


def test_trusted_read_only_one_run_status_packet_requires_exact_report_link():
    result = build_execution_packet_preview(
        _eligible_one_run_status_report_payload(
            report={
                "report_id": "report-read-only-status-contract-1",
                "run_id": "run-other",
                "approval_id": "approval-read-only-status-1",
                "project_id": "project-hermes-mission-control",
                "status": "reviewed",
                "report_kind": "supervised_read_only_status_report_contract",
                "metadata": {"no_jenny_execution": True, "jenny_executed": False},
            }
        )
    )

    assert result["eligible"] is False
    assert result["trusted_for_execution"] is False
    assert "read-only status report contract must link to the exact RunRecord" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False


def test_trusted_read_only_one_run_status_packet_requires_fresh_bound_run():
    result = build_execution_packet_preview(
        _eligible_one_run_status_report_payload(
            approval={
                "approval_id": "approval-read-only-status-1",
                "run_id": "run-other",
                "status": "approved",
                "approval_mode": "one_time",
                "approval_scope": "project-hermes-mission-control:supervised_read_only_status_report",
                "action_class": "supervised_read_only_status_report",
                "approved_actions": ("run exactly one supervised read-only Mission Control status report",),
                "forbidden_actions": _forbidden_actions(),
                "expires_at": "2099-01-01T00:00:00Z",
                "consumed_at": "",
            },
            run_record_count_for_id=2,
        )
    )

    assert result["eligible"] is False
    assert result["trusted_for_execution"] is False
    assert "one-run approval must be bound to the exact RunRecord" in result["blocked_reasons"]
    assert "one-run RunRecord id has prior append-only updates; create a fresh run_id" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False


def test_read_only_execution_packet_requires_explicit_read_only_safe_tool_profile():
    payload = _eligible_preview_payload(mode="read_only")
    payload.pop("tool_permissions")

    result = build_execution_packet_preview(payload)

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    assert result["eligible"] is False
    assert "read-only execution packet requires a read-only-safe tool profile" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False


def test_read_only_execution_packet_blocks_unsafe_bridge_even_with_safe_packet_path():
    result = build_execution_packet_preview(
        _eligible_preview_payload(
            mode="read_only",
            bridge={"manual_hermes_answer_enabled": True},
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]
    assert "bridge: bridge can execute or write an external/response record" in result["blocked_reasons"]


def test_read_only_execution_packet_blocks_unknown_tool_profile():
    result = build_execution_packet_preview(
        _eligible_preview_payload(
            mode="read_only",
            tool_permissions={"paths": [{"path_id": "unknown-preview-path", "capability_inheritance": "unknown"}]},
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    assert result["eligible"] is False
    assert "tool permission paths are not read-only safe" in result["blocked_reasons"]
    assert "read-only execution packet requires a read-only-safe tool profile" in result["blocked_reasons"]
    assert "unknown-preview-path: path capability inheritance is unknown" in result["blocked_reasons"]


def test_read_only_execution_packet_preserves_core_safety_blockers():
    cases = [
        (
            {"approval": {}},
            "exact approved ApprovalRecord is required",
        ),
        (
            {"run": {}},
            "valid RunRecord is required",
        ),
        (
            {"report_inbox_ready": False, "report": {}},
            "report inbox must be ready",
        ),
        (
            {
                "run": {
                    "run_id": "run-read-only-1",
                    "project_id": "project-hermes-mission-control",
                    "approval_id": "approval-read-only-1",
                    "lane_type": "read_only_inspection",
                    "status": "requested",
                    "dispatch_state": False,
                    "forbidden_actions": ["merge"],
                },
                "lane": {"lane_type": "read_only_inspection", "forbidden_actions": ["merge"]},
            },
            "forbidden actions missing mutation classes",
        ),
        (
            {
                "runtime_provenance": evaluate_runtime_provenance(
                    _clean_runtime_state(
                        dashboard_runtime=_runtime(
                            "/runtime/dashboard",
                            HEAD,
                            status_short=["## HEAD (no branch)", " M mission_control/autonomy_eligibility.py"],
                        )
                    )
                )
            },
            "runtime provenance is not clean",
        ),
        (
            {"dispatch_enabled": True, "session_send_enabled": True, "worker_dispatch_enabled": True},
            "dispatch_enabled must remain false",
        ),
    ]

    for overrides, expected_reason in cases:
        result = build_execution_packet_preview(_eligible_preview_payload(mode="read_only", **overrides))

        _assert_inert_preview(result)
        _assert_inert_preview(result["packet"])
        assert result["eligible"] is False
        assert any(expected_reason in reason for reason in result["blocked_reasons"])
        assert result["would_execute"] is False
        assert result["dispatch_enabled"] is False
        assert result["session_send_enabled"] is False
        assert result["worker_dispatch_enabled"] is False


def test_execution_packet_preview_rejects_requested_live_action_flags():
    cases = [
        _eligible_preview_payload(
            mode="read_only",
            dispatch_enabled=True,
            execution_enabled=True,
            session_send_enabled=True,
            worker_dispatch_enabled=True,
            would_dispatch=True,
            would_execute=True,
            would_session_send=True,
        ),
        _eligible_pr_preview_payload(
            mode="scoped_pr",
            dispatch_enabled=True,
            execution_enabled=True,
            session_send_enabled=True,
            worker_dispatch_enabled=True,
            would_dispatch=True,
            would_execute=True,
            would_session_send=True,
        ),
        {
            "mode": "deploy",
            "dispatch_enabled": True,
            "execution_enabled": True,
            "session_send_enabled": True,
            "worker_dispatch_enabled": True,
            "would_dispatch": True,
            "would_execute": True,
            "would_session_send": True,
        },
    ]

    for payload in cases:
        result = build_execution_packet_preview(payload)

        _assert_inert_preview(result)
        _assert_inert_preview(result["packet"])
        _assert_inert_preview(result["packet"]["worker_node_contract"])
        assert result["eligible"] is False
        assert "would_execute must remain false in previews" in result["blocked_reasons"]
        assert "would_dispatch must remain false in previews" in result["blocked_reasons"]
        assert "would_session_send must remain false in previews" in result["blocked_reasons"]
        assert "execution_enabled must remain false" in result["blocked_reasons"]
        assert "dispatch_enabled must remain false" in result["blocked_reasons"]
        assert "session_send_enabled must remain false" in result["blocked_reasons"]
        assert "worker_dispatch_enabled must remain false" in result["blocked_reasons"]
        assert result["would_execute"] is False
        assert result["would_dispatch"] is False
        assert result["would_session_send"] is False
        assert result["execution_enabled"] is False
        assert result["dispatch_enabled"] is False
        assert result["session_send_enabled"] is False
        assert result["worker_dispatch_enabled"] is False


def test_execution_packet_preview_rejects_stringy_live_action_flags():
    result = build_execution_packet_preview(
        _eligible_pr_preview_payload(
            mode="scoped_pr",
            dispatch_enabled="true",
            execution_enabled="yes",
            send_to_jenny_enabled="enabled",
            session_send_enabled="on",
            worker_dispatch_enabled=1,
            would_dispatch="1",
            would_execute="enabled",
            would_session_send="y",
            merge_allowed="true",
            deploy_allowed="yes",
            runtime_switch_allowed="on",
            capabilities={"merge": "true", "worker_dispatch_enabled": "enabled"},
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    assert result["eligible"] is False
    assert "would_execute must remain false in previews" in result["blocked_reasons"]
    assert "would_dispatch must remain false in previews" in result["blocked_reasons"]
    assert "would_session_send must remain false in previews" in result["blocked_reasons"]
    assert "execution_enabled must remain false" in result["blocked_reasons"]
    assert "dispatch_enabled must remain false" in result["blocked_reasons"]
    assert "send_to_jenny_enabled must remain false" in result["blocked_reasons"]
    assert "session_send_enabled must remain false" in result["blocked_reasons"]
    assert "worker_dispatch_enabled must remain false" in result["blocked_reasons"]
    assert "merge is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "deploy is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "runtime switch is not allowed in scoped PR lanes" in result["blocked_reasons"]
    assert "capability merge must be disabled" in result["blocked_reasons"]
    assert "capability worker_dispatch_enabled must be disabled" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_execution_packet_preview_rejects_top_level_platform_live_flags():
    result = build_execution_packet_preview(
        _eligible_pr_preview_payload(
            mode="scoped_pr",
            dispatch_in_gateway="true",
            dispatch_state="enabled",
            execution_ready=True,
            live_operations_enabled="yes",
            worker_enabled=True,
            workers_enabled=1,
            timer_enabled="on",
            daemon_enabled="enabled",
            waha_enabled="yes",
            social_enabled=True,
            payment_enabled=True,
            queue_mutation_enabled="on",
            model_routing_enabled="true",
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    _assert_inert_preview(result["packet"]["worker_node_contract"])
    assert result["eligible"] is False
    for reason in (
        "dispatch_in_gateway must remain false",
        "dispatch_state must remain false",
        "execution_ready must remain false",
        "live_operations_enabled must remain false",
        "worker_enabled must remain false",
        "workers_enabled must remain false",
        "timer_enabled must remain false",
        "daemon_enabled must remain false",
        "waha_enabled must remain false",
        "social_enabled must remain false",
        "payment_enabled must remain false",
        "queue_mutation_enabled must remain false",
        "model_routing_enabled must remain false",
    ):
        assert reason in result["blocked_reasons"]


def test_permission_classifiers_treat_stringy_live_flags_as_unsafe():
    bridge = classify_bridge_permissions({"read_only_safe": True, "would_execute": "true"})
    permissions = classify_control_path_permissions(
        {
            "path_id": "shell-path",
            "read_only_safe": True,
            "capabilities": {"shell": "yes"},
        }
    )

    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert any("would_execute must remain false" in reason for reason in bridge["reasons"])
    assert permissions["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert permissions["write_capable_path_ids"] == ["shell-path"]
    assert "shell-path: path exposes write or execution capabilities: shell" in permissions["blocked_reasons"]
    assert permissions["would_execute"] is False
    assert permissions["dispatch_enabled"] is False
    assert permissions["session_send_enabled"] is False
    assert permissions["worker_dispatch_enabled"] is False


def test_control_path_blocks_top_level_platform_live_flag_aliases():
    permissions = classify_control_path_permissions(
        {
            "path_id": "platform-live-path",
            "read_only_safe": True,
            "waha_enabled": "yes",
            "social_enabled": True,
            "payment_enabled": True,
            "queue_mutation_enabled": "on",
            "workers_enabled": 1,
        }
    )

    _assert_inert_preview(permissions)
    assert permissions["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert permissions["read_only_safe"] is False
    assert permissions["write_capable_path_ids"] == ["platform-live-path"]
    assert "platform-live-path" in permissions["blocked_reasons"][0]
    for marker in ("waha enabled", "social enabled", "payment enabled", "queue mutation enabled", "workers enabled"):
        assert marker in permissions["paths"][0]["write_capability_markers"]


def test_worker_node_execution_packet_preview_wraps_scoped_pr_without_dispatch():
    result = build_execution_packet_preview(
        _eligible_pr_preview_payload(
            mode="worker_node",
            run={
                "run_id": "run-pr-1",
                "project_id": "project-hermes-mission-control",
                "approval_id": "approval-pr-1",
                "lane_type": "pr_creation",
                "status": "requested",
                "dispatch_state": False,
                "objective": "Prepare a bounded scoped PR.",
                "forbidden_actions": _forbidden_actions(),
            },
            worker_node={
                "parent_run_id": "run-pr-1",
                "worker_identity": "codex",
                "worker_host_label": "laptop-codex",
                "worker_kind": "laptop_codex",
                "presence_status": "online",
            },
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    _assert_inert_preview(result["packet"]["worker_node_contract"])
    assert result["eligible"] is True
    assert result["packet"]["mode"] == "worker_node"
    assert result["packet"]["worker_node_contract"]["worker_identity"] == "codex"
    assert result["packet"]["worker_node_contract"]["worker_host_label"] == "laptop-codex"
    assert result["packet"]["worker_node_contract"]["parent_run_id"] == "run-pr-1"
    assert result["packet"]["worker_node_contract"]["manual_handoff_only"] is True
    assert result["packet"]["worker_node_contract"]["codex_safety_hardness_required"] is True
    assert result["packet"]["worker_node_contract"]["would_execute"] is False
    assert result["packet"]["worker_node_contract"]["would_dispatch"] is False
    assert result["packet"]["worker_node_contract"]["would_session_send"] is False
    assert result["packet"]["worker_node_contract"]["worker_safety_hardness"] == [
        "Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.",
        "A Jenny packet is not permission to bypass Codex safety checks.",
    ]
    assert result["packet"]["worker_node_contract"]["worker_dispatch_enabled"] is False
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_worker_node_execution_packet_requires_tests_contract():
    result = build_execution_packet_preview(
        _eligible_preview_payload(
            mode="worker_node",
            report_contract={"required": True, "tests_required": False, "review_required": True},
            worker_node={
                "parent_run_id": "run-read-only-1",
                "worker_identity": "codex",
                "worker_host_label": "laptop-codex",
                "worker_kind": "laptop_codex",
                "lane_mode": "read_only_inspection",
                "objective": "Inspect bounded evidence.",
                "presence_status": "online",
            },
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    _assert_inert_preview(result["packet"]["worker_node_contract"])
    assert result["eligible"] is False
    assert "worker-node tests/checks are required" in result["blocked_reasons"]
    assert result["would_execute"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_worker_node_execution_packet_blocks_dispatch_and_missing_report_review():
    result = build_execution_packet_preview(
        _eligible_pr_preview_payload(
            mode="worker_node",
            report_contract={"required": True, "tests_required": True, "review_required": False},
            dispatch_enabled=True,
            would_dispatch=True,
            would_execute=True,
            would_session_send=True,
            worker_node={
                "parent_run_id": "run-pr-1",
                "objective": "Prepare a bounded scoped PR.",
                "worker_dispatch_enabled": True,
                "execution_enabled": True,
            },
        )
    )

    _assert_inert_preview(result)
    _assert_inert_preview(result["packet"])
    _assert_inert_preview(result["packet"]["worker_node_contract"])
    assert result["eligible"] is False
    assert "worker dispatch must stay disabled" in result["blocked_reasons"]
    assert "worker execution must stay disabled" in result["blocked_reasons"]
    assert "dispatch_enabled must remain false" in result["blocked_reasons"]
    assert "would_execute must remain false in previews" in result["blocked_reasons"]
    assert "would_dispatch must remain false in previews" in result["blocked_reasons"]
    assert "would_session_send must remain false in previews" in result["blocked_reasons"]
    assert "worker-node report review is required" in result["blocked_reasons"]
    assert "worker-node presence is not confirmed online" in result["blocked_reasons"]
    assert result["worker_dispatch_enabled"] is False


def test_workspace_status_surfaces_provenance_and_blocks_when_gateway_untrusted():
    status = build_workspace_status(
        {
            "accepted_baseline_record": {
                "baseline_id": "accepted-current",
                "runtime_path": "/runtime/accepted",
                "head": HEAD,
                "rollback_runtime_path": "/runtime/rollback",
                "rollback_head": HEAD,
                "dispatch_in_gateway": False,
            },
            "source_control": {"accepted_live_head": HEAD},
            "dashboard_runtime": _runtime("/runtime/dashboard", HEAD),
            "gateway_runtime": _runtime("/runtime/gateway", git_healthy=False, error="fatal: not a git repository"),
            "rollback_runtime": _runtime("/runtime/rollback", HEAD),
        }
    )

    assert status["runtime_provenance"]["autonomy_blocked"] is True
    assert "GATEWAY_UNTRUSTED" in status["runtime_provenance"]["statuses"]
    assert status["read_only_autonomy_eligibility"]["eligible"] is False
    assert "GATEWAY_UNTRUSTED" in status["stale_context"]["warnings"]
