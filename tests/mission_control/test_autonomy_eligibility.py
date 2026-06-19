from __future__ import annotations

from mission_control.autonomy_eligibility import (
    build_execution_packet_preview,
    classify_bridge_permissions,
    classify_control_path_permissions,
    evaluate_read_only_autonomy_eligibility,
    evaluate_runtime_provenance,
    evaluate_scoped_pr_lane_eligibility,
)
from mission_control.workspace_status import build_workspace_status


HEAD = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
OLD_HEAD = "fe18ce20d6044dd91d115286e949366477a8706b"


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
        "capabilities": {},
        "now": "2026-06-19T00:00:00Z",
    }
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


def test_clean_aligned_runtime_provenance_allows_preview_inputs():
    result = evaluate_runtime_provenance(_clean_runtime_state())

    assert result["status"] == "CLEAN_AND_ALIGNED"
    assert result["primary_status"] == "CLEAN_AND_ALIGNED"
    assert result["autonomy_blocked"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False


def test_stale_accepted_baseline_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(accepted_baseline=_runtime("/runtime/accepted", OLD_HEAD))
    )

    assert result["status"] == "BLOCKED_UNSAFE_FOR_AUTONOMY"
    assert "SOURCE_CURRENT_BUT_BASELINE_STALE" in result["statuses"]
    assert "accepted baseline HEAD does not match source HEAD" in result["autonomy_blocked_reasons"]


def test_dirty_runtime_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(dashboard_runtime=_runtime("/runtime/dashboard", dirty_files=[" M package-lock.json"]))
    )

    assert "DIRTY_RUNTIME" in result["statuses"]
    assert "dashboard runtime has dirty or untracked files" in result["autonomy_blocked_reasons"]


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


def test_rollback_stale_is_surfaced_and_blocks_autonomy():
    result = evaluate_runtime_provenance(
        _clean_runtime_state(rollback_runtime=_runtime("/runtime/rollback", OLD_HEAD))
    )

    assert "ROLLBACK_STALE" in result["statuses"]
    assert "rollback runtime is stale relative to source HEAD" in result["autonomy_blocked_reasons"]


def test_approved_read_only_lane_preview_is_inert_and_eligible():
    result = evaluate_read_only_autonomy_eligibility(_eligible_preview_payload())

    assert result["eligible"] is True
    assert result["would_execute"] is False
    assert result["stored"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False


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

    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]


def test_worker_dispatch_bridge_path_is_not_read_only_safe():
    bridge = classify_bridge_permissions({"worker_dispatch_enabled": True})
    result = evaluate_read_only_autonomy_eligibility(
        _eligible_preview_payload(bridge={"worker_dispatch_enabled": True})
    )

    assert bridge["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert bridge["worker_dispatch_enabled"] is False
    assert result["eligible"] is False
    assert "bridge path is not read-only safe" in result["blocked_reasons"]


def test_control_path_permission_catalog_covers_required_paths_and_blocks_write_capable_paths():
    result = classify_control_path_permissions()

    assert result["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert result["read_only_safe"] is False
    assert result["stored"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False
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
    assert classifications["delegate_tool"] == "unknown_blocked"
    assert classifications["file_write_shell_patch"] == "write_capable_not_safe_for_autonomy"
    assert classifications["laptop_codex_worker_node"] == "write_capable_not_safe_for_autonomy"
    assert classifications["child_agent_capability_inheritance"] == "unknown_blocked"


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

    assert result["eligible"] is False
    assert "tool permission paths are not read-only safe" in result["blocked_reasons"]
    assert any("file_patch" in reason for reason in result["blocked_reasons"])
    assert result["tool_permissions"]["permission_classification"] == "write_capable_not_safe_for_autonomy"


def test_scoped_pr_lane_preview_is_inert_and_eligible_with_exact_scope():
    result = evaluate_scoped_pr_lane_eligibility(_eligible_pr_preview_payload())

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


def test_execution_packet_preview_is_never_an_execution_path():
    result = build_execution_packet_preview(_eligible_pr_preview_payload(mode="scoped_pr"))

    assert result["eligible"] is True
    assert result["packet"]["mode"] == "scoped_pr"
    assert result["packet"]["run_id"] == "run-pr-1"
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


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
            },
        )
    )

    assert result["eligible"] is True
    assert result["packet"]["mode"] == "worker_node"
    assert result["packet"]["worker_node_contract"]["worker_identity"] == "codex"
    assert result["packet"]["worker_node_contract"]["worker_host_label"] == "laptop-codex"
    assert result["packet"]["worker_node_contract"]["parent_run_id"] == "run-pr-1"
    assert result["packet"]["worker_node_contract"]["manual_handoff_only"] is True
    assert result["packet"]["worker_node_contract"]["worker_dispatch_enabled"] is False
    assert result["would_execute"] is False
    assert result["would_dispatch"] is False
    assert result["would_session_send"] is False
    assert result["execution_enabled"] is False
    assert result["dispatch_enabled"] is False
    assert result["session_send_enabled"] is False
    assert result["worker_dispatch_enabled"] is False


def test_worker_node_execution_packet_blocks_dispatch_and_missing_report_review():
    result = build_execution_packet_preview(
        _eligible_pr_preview_payload(
            mode="worker_node",
            report_contract={"required": True, "tests_required": True, "review_required": False},
            worker_node={
                "parent_run_id": "run-pr-1",
                "objective": "Prepare a bounded scoped PR.",
                "worker_dispatch_enabled": True,
                "execution_enabled": True,
            },
        )
    )

    assert result["eligible"] is False
    assert "worker dispatch must stay disabled" in result["blocked_reasons"]
    assert "worker execution must stay disabled" in result["blocked_reasons"]
    assert "worker-node report review is required" in result["blocked_reasons"]
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
