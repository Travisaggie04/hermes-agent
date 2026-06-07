"""Inert Global Concurrency / Resource Guard policy tests."""

from mission_control.global_resource_guard import (
    GLOBAL_RESOURCE_GUARD_POLICY,
    evaluate_global_resource_guard,
    get_global_resource_guard_policy,
)


def test_global_resource_guard_policy_is_inert_dry_run_and_display_only():
    policy = get_global_resource_guard_policy()

    assert policy == GLOBAL_RESOURCE_GUARD_POLICY
    assert policy is not GLOBAL_RESOURCE_GUARD_POLICY
    assert policy["guard_id"] == "global_concurrency_resource_v1"
    assert policy["trusted_for_execution"] is False
    assert policy["inert_context_only"] is True
    assert policy["enforcement_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["display_only"] is True
    assert policy["global_lane_limits"] == {
        "max_active_jenny_codex_lanes": 1,
        "parallel_lanes_allowed": False,
        "require_queue_when_busy": True,
    }
    assert policy["process_limits"]["max_codex_app_server_pairs"] == 1
    assert policy["kanban_limits"]["embedded_dispatch_allowed"] is False
    assert policy["kanban_limits"]["max_kanban_workers"] == 0
    assert policy["worktree_repo_limits"]["block_parent_directory_scans"] is True
    assert policy["model_router_limits"]["model_routing_allowed"] is False
    assert policy["model_router_limits"]["model_picker_execution_allowed"] is False
    assert "disk_warning_threshold_percent" in policy["unresolved_policy_fields"]
    assert "storage_delta_required_before_done" in policy["unresolved_policy_fields"]


def test_global_resource_guard_policy_returns_display_copy_only():
    policy = get_global_resource_guard_policy()

    policy["enforcement_enabled"] = True
    policy["kanban_limits"]["embedded_dispatch_allowed"] = True

    assert GLOBAL_RESOURCE_GUARD_POLICY["enforcement_enabled"] is False
    assert GLOBAL_RESOURCE_GUARD_POLICY["kanban_limits"]["embedded_dispatch_allowed"] is False


def test_dry_run_evaluator_passes_safe_single_lane_state():
    result = evaluate_global_resource_guard(
        {
            "active_jenny_codex_lanes": 1,
            "codex_app_server_pairs": 1,
            "embedded_dispatch_enabled": False,
            "kanban_worker_count": 0,
            "worktree_state": "clean",
            "uses_dirty_or_quarantined_worktree": False,
            "parent_directory_scan_requested": False,
            "model_routing_requested": False,
            "model_picker_execution_requested": False,
            "waha_execution_requested": False,
            "recent_resource_errors": [],
            "stale_app_server_pair_detected": False,
        }
    )

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "storage_delta_required_before_done" in result["unresolved_policy_fields"]


def test_dry_run_evaluator_blocks_parallel_lanes_and_embedded_dispatch():
    result = evaluate_global_resource_guard(
        {
            "active_jenny_codex_lanes": 2,
            "embedded_dispatch_enabled": True,
            "kanban_worker_count": 1,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "parallel Jenny/Codex lanes exceed max_active_jenny_codex_lanes=1" in result["reasons"]
    assert "embedded Kanban dispatch is not approved" in result["reasons"]
    assert "start additional Jenny/Codex lane" in result["blocked_actions"]
    assert "run embedded Kanban dispatcher" in result["blocked_actions"]
    assert "explicit dispatch lane approval" in result["required_approvals"]


def test_dry_run_evaluator_blocks_stale_app_server_and_resource_errors():
    result = evaluate_global_resource_guard(
        {
            "codex_app_server_pairs": 2,
            "stale_app_server_pair_detected": True,
            "recent_resource_errors": ["Too many open files", "cannot fork"],
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "codex/app-server pair count exceeds max_codex_app_server_pairs=1" in result["reasons"]
    assert "stale app-server pair detected" in result["reasons"]
    assert "recent resource error matched: Too many open files" in result["reasons"]
    assert "recent resource error matched: cannot fork" in result["reasons"]


def test_dry_run_evaluator_blocks_waha_until_hard_wall_model_and_verifier_ready():
    result = evaluate_global_resource_guard(
        {
            "waha_execution_requested": True,
            "waha_hard_wall_ready": False,
            "waha_approved_model_policy_ready": False,
            "waha_technical_verifier_ready": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "Waha hard-wall policy is unresolved" in result["reasons"]
    assert "Waha approved model policy is unresolved" in result["reasons"]
    assert "Waha technical verifier is unresolved" in result["reasons"]
    assert "execute protected-domain Waha work" in result["blocked_actions"]
    assert "Waha technical verifier approval" in result["required_approvals"]


def test_dry_run_evaluator_blocks_model_routing_and_execution_requests():
    result = evaluate_global_resource_guard(
        {
            "model_routing_requested": True,
            "model_picker_execution_requested": True,
            "free_cloud_model_for_protected_domain": True,
            "unknown_model_for_protected_domain": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "model routing is not approved" in result["reasons"]
    assert "model picker execution is not approved" in result["reasons"]
    assert "free-cloud models are forbidden for Waha/protected-domain work" in result["reasons"]
    assert "unknown models are forbidden for Waha/protected-domain work" in result["reasons"]
    assert "route tasks to models" in result["blocked_actions"]
    assert "execute model picker selection" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_dirty_quarantined_worktree_and_parent_scan():
    result = evaluate_global_resource_guard(
        {
            "worktree_state": "dirty",
            "uses_dirty_or_quarantined_worktree": True,
            "parent_directory_scan_requested": True,
            "travis_fork_pr_work": True,
            "repo_remote_owner": "NousResearch",
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "clean worktree is required" in result["reasons"]
    assert "dirty or quarantined worktree is blocked" in result["reasons"]
    assert "parent-directory scan is blocked" in result["reasons"]
    assert "Travis fork PR work must target Travisaggie04/hermes-agent" in result["reasons"]
    assert "use dirty/quarantined worktree" in result["blocked_actions"]


def test_dry_run_evaluator_unknown_without_observed_state():
    result = evaluate_global_resource_guard({})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "caller-supplied observed state is incomplete" in result["reasons"]
