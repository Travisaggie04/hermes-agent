"""Display-only Mission Control operating workspace status tests."""

from __future__ import annotations

from mission_control.workspace_status import build_workspace_status, default_workspace_status_input


def _baseline_payload(**overrides):
    payload = {
        "accepted_baseline": {
            "runtime_path": "/home/jenny/.hermes/hermes-runtime-approvalhash-775f493",
            "head": "775f49352189fdec3169f59e3378b6744da2bdda",
        },
        "rollback_baseline": {
            "runtime_path": "/home/jenny/.hermes/hermes-runtime-evidencehash-cb42bbc",
            "head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
            "clean": True,
        },
        "lane": {
            "active_lane": "Mission Control OS workspace status slice",
            "mode": "bounded display-only PR",
            "declared_baseline_head": "775f49352189fdec3169f59e3378b6744da2bdda",
            "max_active_lane": 1,
            "active_lane_count": 1,
        },
        "safety": {
            "dispatch_in_gateway": False,
            "workers_enabled": False,
            "queue_mutation_enabled": False,
            "model_routing_enabled": False,
            "enforcement_enabled": False,
        },
        "activity": {
            "active_workers": 0,
            "active_tasks": 0,
            "active_runs": 0,
            "appserver_pairs": 1,
        },
        "pr_gate": {
            "latest_pr": 42,
            "packet_hash": "sha256:" + "1" * 64,
            "verifier_evidence_record_id": "evidence-42",
            "verifier_evidence_match": True,
            "approval_record_id": "approval-42",
            "approval_record_match": True,
        },
        "deployment": {
            "status": "accepted",
            "target_runtime": "/home/jenny/.hermes/hermes-runtime-approvalhash-775f493",
            "target_head": "775f49352189fdec3169f59e3378b6744da2bdda",
            "rollback_used": False,
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}
        else:
            payload[key] = value
    return payload


def test_workspace_status_returns_inert_display_only_flags_and_baselines():
    status = build_workspace_status(_baseline_payload())

    assert status["display_only"] is True
    assert status["trusted_for_execution"] is False
    assert status["inert_context_only"] is True
    assert status["execution_enabled"] is False
    assert status["enforcement_enabled"] is False
    assert status["dry_run_only"] is True
    assert status["enforces_runtime"] is False
    assert status["accepted_baseline"]["head"] == "775f49352189fdec3169f59e3378b6744da2bdda"
    assert status["rollback_baseline"]["clean"] is True
    assert status["lane"]["active_lane_count"] == 1
    assert status["lane"]["max_active_lane"] == 1
    assert status["lane"]["lane_status"] == "within_limit"
    assert status["safety"]["dispatch_in_gateway"] is False
    assert status["activity"]["active_workers"] == 0
    assert status["pr_gate"]["packet_hash_valid"] is True
    assert status["deployment"]["status"] == "accepted"
    warnings = set(status["stale_context"]["warnings"])
    assert "accepted_baseline_source_missing" in warnings
    assert "MISSING_RUNTIME_PATH" in warnings
    assert status["runtime_provenance"]["autonomy_blocked"] is True
    assert status["read_only_autonomy_eligibility"]["eligible"] is False


def test_workspace_status_surfaces_scoped_pr_lane_eligibility_as_inert_preview():
    status = build_workspace_status(
        _baseline_payload(
            scoped_pr_eligibility={
                "approval": {
                    "approval_id": "approval-pr-1",
                    "status": "approved",
                    "approval_mode": "one_time",
                    "approval_scope": "project-hermes-mission-control:scoped-pr:mission_control/",
                    "action_class": "pr_creation",
                    "approved_files": ["mission_control/workspace_status.py"],
                    "expires_at": "2099-01-01T00:00:00Z",
                },
                "run": {
                    "run_id": "run-pr-1",
                    "project_id": "project-hermes-mission-control",
                    "approval_id": "approval-pr-1",
                    "lane_type": "pr_creation",
                    "status": "requested",
                    "forbidden_actions": ["merge", "deploy", "restart", "runtime switch"],
                },
                "lane": {
                    "lane_type": "pr_creation",
                    "allowed_files": ["mission_control/workspace_status.py"],
                    "forbidden_actions": ["merge", "deploy", "restart", "runtime switch"],
                    "tests_required": True,
                    "review_required": True,
                },
                "report_contract": {"required": True, "tests_required": True, "review_required": True},
            }
        )
    )

    scoped_pr = status["scoped_pr_lane_eligibility"]
    assert scoped_pr["stored"] is False
    assert scoped_pr["dry_run_only"] is True
    assert scoped_pr["would_execute"] is False
    assert scoped_pr["would_create_pr"] is False
    assert scoped_pr["would_commit"] is False
    assert scoped_pr["execution_enabled"] is False
    assert scoped_pr["dispatch_enabled"] is False
    assert scoped_pr["session_send_enabled"] is False
    assert scoped_pr["worker_dispatch_enabled"] is False
    assert scoped_pr["eligible"] is False
    assert "runtime provenance is not clean" in scoped_pr["blocked_reasons"]


def test_workspace_status_warns_on_stale_baseline_dispatch_lane_and_workers():
    status = build_workspace_status(
        _baseline_payload(
            lane={
                "declared_baseline_head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
                "active_lane_count": 2,
            },
            safety={"dispatch_in_gateway": True},
            activity={"active_workers": 1, "active_tasks": 2, "active_runs": 3},
        )
    )

    warnings = set(status["stale_context"]["warnings"])
    assert "baseline_mismatch" in warnings
    assert "dispatch_not_false" in warnings
    assert "active_lane_count_exceeds_max" in warnings
    assert "active_workers_tasks_or_runs_present" in warnings
    assert status["stale_context"]["baseline_mismatch"] is True
    assert status["lane"]["lane_status"] == "exceeds_limit"


def test_workspace_status_exposes_runtime_worktree_guard_blockers_display_only():
    runtime = "/home/jenny/.hermes/hermes-runtime-approvalhash-775f493"
    status = build_workspace_status(
        _baseline_payload(
            runtime_worktree_guard={
                "candidate_worktree_path": runtime,
                "candidate_git_top_level": runtime,
                "requested_action_class": "pr_create",
                "accepted_runtime_disk_head": "wrong-head",
                "accepted_runtime_branch": "feature/accidental-runtime-branch",
                "requested_dev_worktree_exists": False,
            }
        )
    )

    guard = status["runtime_worktree_guard"]
    assert guard["dry_run_only"] is True
    assert guard["enforces_runtime"] is False
    assert guard["would_block"] is True
    assert guard["decision_state"] == "blocked"
    assert "dev_worktree_is_live_runtime" in guard["blockers"]
    assert "runtime_disk_head_mismatch" in guard["blockers"]
    assert "runtime_on_feature_branch" in guard["blockers"]
    assert "requested_dev_worktree_missing" in guard["blockers"]
    warnings = set(status["stale_context"]["warnings"])
    assert "dev_worktree_is_live_runtime" in warnings
    assert "runtime_disk_head_mismatch" in warnings


def test_workspace_status_warns_when_pr_lane_lacks_packet_evidence_or_approval():
    status = build_workspace_status(
        _baseline_payload(
            lane={"active_lane": "PR #43 read-only verify"},
            pr_gate={
                "packet_hash": "",
                "verifier_evidence_record_id": "",
                "approval_record_id": "",
                "verifier_evidence_match": None,
                "approval_record_match": None,
            },
        )
    )

    warnings = set(status["stale_context"]["warnings"])
    assert "missing_pr_packet_hash" in warnings
    assert "missing_verifier_evidence" in warnings
    assert "missing_approval_record" in warnings


def test_workspace_status_omits_raw_transcript_logs_tokens_api_responses_and_paths():
    status = build_workspace_status(
        _baseline_payload(
            raw_log="secret log",
            transcript="full discord transcript",
            discord_messages=["message one"],
            comments="PR comments",
            pr_body="PR body",
            token="secret-token",
            api_key="secret-key",
            github_response={"raw": "api"},
            local_path="/home/jenny/private/path",
            full_observed_state={"raw": "state"},
            lane={"active_lane": "x" * 2000},
        )
    )

    rendered = str(status).lower()
    for forbidden in (
        "secret log",
        "full discord transcript",
        "message one",
        "pr comments",
        "pr body",
        "secret-token",
        "secret-key",
        "github_response",
        "/home/jenny/private/path",
        "full_observed_state",
    ):
        assert forbidden not in rendered
    assert len(status["lane"]["active_lane"]) <= 160


def test_workspace_status_flags_stale_discord_context_marker():
    status = build_workspace_status(_baseline_payload(stale_discord_context=True))

    assert "stale_discord_context" in status["stale_context"]["warnings"]
    assert status["stale_context"]["thread_mismatch"] is True



def test_workspace_status_latest_handoff_absent_is_explicitly_not_present():
    status = build_workspace_status(_baseline_payload())

    assert status["latest_handoff"] == {"present": False}


def test_workspace_status_exposes_latest_handoff_as_inert_display_context():
    status = build_workspace_status(
        _baseline_payload(
            latest_handoff={
                "handoff_id": "handoff-001",
                "created_at": "2026-06-09T00:00:00Z",
                "source": "operator_supplied_handoff",
                "active_lane": "PR #45 Operating Workspace handoff records",
                "lane_mode": "bounded display-only PR",
                "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
                "accepted_head": "775f49352189fdec3169f59e3378b6744da2bdda",
                "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-evidencehash-cb42bbc",
                "rollback_head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
                "dispatch_in_gateway": False,
                "max_active_lane": 1,
                "active_lane_count": 1,
                "target_type": "pr",
                "target_id": "45",
                "target_head": "775f49352189fdec3169f59e3378b6744da2bdda",
                "status": "active",
                "last_result": "PR #44 accepted",
                "next_action": "Implement PR #45",
                "warnings": ["display-only"],
                "dry_run_only": False,
                "enforces_runtime": True,
                "display_only": False,
                "raw_log": "forbidden",
                "discord_messages": ["forbidden"],
                "token": "secret-token",
                "github_response": {"raw": "forbidden"},
            }
        )
    )

    handoff = status["latest_handoff"]
    assert handoff["present"] is True
    assert handoff["handoff_id"] == "handoff-001"
    assert handoff["active_lane"] == "PR #45 Operating Workspace handoff records"
    assert handoff["accepted_head"] == "775f49352189fdec3169f59e3378b6744da2bdda"
    assert handoff["target_head"] == "775f49352189fdec3169f59e3378b6744da2bdda"
    assert handoff["dry_run_only"] is True
    assert handoff["enforces_runtime"] is False
    assert handoff["display_only"] is True
    rendered = str(status).lower()
    assert "raw_log" not in rendered
    assert "discord_messages" not in rendered
    assert "secret-token" not in rendered
    assert "github_response" not in rendered


def test_workspace_status_warns_on_handoff_baseline_dispatch_lane_and_missing_target():
    status = build_workspace_status(
        _baseline_payload(
            latest_handoff={
                "handoff_id": "handoff-002",
                "created_at": "2026-06-09T00:00:00Z",
                "accepted_head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
                "dispatch_in_gateway": True,
                "max_active_lane": 1,
                "active_lane_count": 2,
                "target_type": "pr",
                "target_id": "45",
                "target_head": "",
                "dry_run_only": True,
                "enforces_runtime": False,
                "display_only": True,
            }
        )
    )

    warnings = set(status["stale_context"]["warnings"])
    assert "handoff_baseline_mismatch" in warnings
    assert "handoff_dispatch_not_false" in warnings
    assert "handoff_active_lane_count_exceeds_max" in warnings
    assert "handoff_missing_target_head" in warnings



def _accepted_baseline_record_payload(**overrides):
    payload = {
        "baseline_id": "baseline-001",
        "recorded_at": "2026-06-09T00:00:00Z",
        "source": "operator_accepted_baseline",
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        "head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "rollback_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "dispatch_in_gateway": False,
        "active_kanban": 0,
        "max_active_lane": 1,
        "issue": "none",
        "display_only": True,
        "dry_run_only": True,
        "enforces_runtime": False,
    }
    payload.update(overrides)
    return payload


def test_workspace_status_uses_accepted_baseline_record_source_when_present():
    status = build_workspace_status(_baseline_payload(accepted_baseline_record=_accepted_baseline_record_payload()))

    assert status["accepted_baseline_source"] == "record"
    assert status["accepted_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7"
    assert status["accepted_baseline"]["head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    assert status["rollback_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f"
    assert status["rollback_baseline"]["head"] == "d11681f81c7cd16a99c53649f157040b2d10a89f"
    assert "accepted_baseline_source_missing" not in status["stale_context"]["warnings"]




def test_workspace_status_record_source_defaults_lane_to_idle_and_matching_baseline():
    payload = default_workspace_status_input()
    payload["accepted_baseline_record"] = _accepted_baseline_record_payload()
    status = build_workspace_status(payload)

    assert status["accepted_baseline_source"] == "record"
    assert status["lane"]["declared_baseline_head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    assert status["lane"]["active_lane"] == ""
    assert status["lane"]["active_lane_count"] == 0
    assert status["lane"]["max_active_lane"] == 1
    assert status["lane"]["lane_status"] == "within_limit"
    assert "baseline_mismatch" not in status["stale_context"]["warnings"]
    assert status["stale_context"]["baseline_mismatch"] is False
    assert status["safety"]["dispatch_in_gateway"] is False
    assert status["safety"]["workers_enabled"] is False
    assert status["safety"]["queue_mutation_enabled"] is False
    assert status["safety"]["model_routing_enabled"] is False
    assert status["safety"]["enforcement_enabled"] is False
    assert status["execution_enabled"] is False
    assert status["display_only"] is True
    assert status["dry_run_only"] is True
    assert status["enforces_runtime"] is False


def test_workspace_status_record_source_preserves_caller_supplied_active_lane():
    status = build_workspace_status(
        _baseline_payload(
            accepted_baseline_record=_accepted_baseline_record_payload(),
            lane={
                "active_lane": "PR #47 Mission Control handoff draft",
                "mode": "discovery only",
                "declared_baseline_head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
                "active_lane_count": 1,
            },
        )
    )

    assert status["accepted_baseline_source"] == "record"
    assert status["lane"]["active_lane"] == "PR #47 Mission Control handoff draft"
    assert status["lane"]["mode"] == "discovery only"
    assert status["lane"]["active_lane_count"] == 1
    assert status["lane"]["declared_baseline_head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    assert "baseline_mismatch" not in status["stale_context"]["warnings"]


def test_workspace_status_record_source_still_warns_on_real_caller_baseline_mismatch():
    status = build_workspace_status(
        _baseline_payload(
            accepted_baseline_record=_accepted_baseline_record_payload(),
            lane={"declared_baseline_head": "d11681f81c7cd16a99c53649f157040b2d10a89f"},
        )
    )

    assert status["accepted_baseline_source"] == "record"
    assert status["lane"]["declared_baseline_head"] == "d11681f81c7cd16a99c53649f157040b2d10a89f"
    assert "baseline_mismatch" in status["stale_context"]["warnings"]

def test_workspace_status_uses_handoff_source_when_no_accepted_record_exists():
    status = build_workspace_status(_baseline_payload(latest_handoff={
        "handoff_id": "handoff-001",
        "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        "accepted_head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "rollback_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "dispatch_in_gateway": False,
        "active_lane_count": 1,
        "max_active_lane": 1,
        "display_only": True,
        "dry_run_only": True,
        "enforces_runtime": False,
    }))

    assert status["accepted_baseline_source"] == "handoff"
    assert status["accepted_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7"
    assert status["accepted_baseline"]["head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    assert status["rollback_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f"
    assert status["rollback_baseline"]["head"] == "d11681f81c7cd16a99c53649f157040b2d10a89f"


def test_workspace_status_static_fallback_warns_when_no_record_or_handoff_source():
    status = build_workspace_status(default_workspace_status_input())

    assert status["accepted_baseline_source"] == "static_fallback"
    assert status["lane"]["active_lane"] == ""
    assert status["lane"]["active_lane_count"] == 0
    assert "accepted_baseline_source_missing" in status["stale_context"]["warnings"]


def test_workspace_status_warns_when_handoff_conflicts_with_accepted_record():
    status = build_workspace_status(_baseline_payload(
        accepted_baseline_record=_accepted_baseline_record_payload(),
        latest_handoff={
            "handoff_id": "handoff-002",
            "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-old",
            "accepted_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
            "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
            "rollback_head": "f20aa2da2a2e978d72f837007d8ab1b14301795b",
            "dispatch_in_gateway": False,
            "active_lane_count": 1,
            "max_active_lane": 1,
        },
    ))

    warnings = set(status["stale_context"]["warnings"])
    assert "handoff_baseline_mismatch" in warnings
    assert "handoff_rollback_baseline_mismatch" in warnings
