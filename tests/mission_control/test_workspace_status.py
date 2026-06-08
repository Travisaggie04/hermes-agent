"""Display-only Mission Control operating workspace status tests."""

from __future__ import annotations

from mission_control.workspace_status import build_workspace_status


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
    assert status["lane"]["max_active_lane"] == 1
    assert status["lane"]["lane_status"] == "within_limit"
    assert status["safety"]["dispatch_in_gateway"] is False
    assert status["activity"]["active_workers"] == 0
    assert status["pr_gate"]["packet_hash_valid"] is True
    assert status["deployment"]["status"] == "accepted"
    assert status["stale_context"]["warnings"] == []


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
