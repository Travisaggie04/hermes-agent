"""Inert Verifier Workflow v1 policy tests."""

from mission_control.pr_merge_packet_hash import compute_pr_merge_packet_hash
from mission_control.pr_merge_verifier_gate import evaluate_pr_merge_verifier_gate
from mission_control.records import JsonlRecordStore, VerifierWorkflowEvidenceRecord
from mission_control.verifier_workflow import (
    VERIFIER_WORKFLOW_POLICY,
    evaluate_verifier_workflow,
    get_verifier_workflow_policy,
)


def test_verifier_workflow_policy_loads_as_inert_display_only_record():
    policy = get_verifier_workflow_policy()

    assert policy == VERIFIER_WORKFLOW_POLICY
    assert policy is not VERIFIER_WORKFLOW_POLICY
    assert policy["workflow_id"] == "verifier_workflow_v1"
    assert policy["trusted_for_execution"] is False
    assert policy["inert_context_only"] is True
    assert policy["enforcement_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["display_only"] is True
    assert policy["required_workflow"] == {
        "implementation_step_required": True,
        "independent_verification_required": True,
        "decision_step_required": True,
        "implementer_cannot_self_verify": True,
    }
    assert policy["pr_workflow"]["pr_ready_requires_verification"] is True
    assert policy["pr_workflow"]["pr_merge_requires_approved_verification"] is True
    assert policy["deployment_workflow"]["blue_green_required_for_runtime_deployment"] is True
    assert policy["waha_workflow"]["waha_technical_verifier_required"] is True
    assert policy["model_workflow"]["verifier_model_must_be_qualified_before_verifier_role"] is True
    assert policy["storage_workflow"]["artifact_manifest_verification_required"] is True
    assert "verifier_verdict" in policy["evidence_requirements"]
    assert "future_runtime_enforcement_wiring" in policy["unresolved_policy_fields"]


def test_verifier_workflow_policy_returns_display_copy_only():
    policy = get_verifier_workflow_policy()

    policy["enforcement_enabled"] = True
    policy["required_workflow"]["implementer_cannot_self_verify"] = False

    assert VERIFIER_WORKFLOW_POLICY["enforcement_enabled"] is False
    assert VERIFIER_WORKFLOW_POLICY["required_workflow"]["implementer_cannot_self_verify"] is True


def test_dry_run_evaluator_warns_for_complete_safe_state_because_future_fields_unresolved():
    result = evaluate_verifier_workflow(
        {
            "implementation_step_present": True,
            "independent_verification_present": True,
            "decision_step_present": True,
            "implementer_id": "implementer-a",
            "verifier_id": "verifier-b",
            "verification_approved": True,
            "pr_ready_requested": False,
            "pr_merge_requested": False,
            "deployment_requested": False,
            "waha_work_requested": False,
            "model_router_execution_requested": False,
            "storage_cleanup_requested": False,
            "implementation_summary_present": True,
            "files_changed_present": True,
            "tests_run_present": True,
            "safety_scan_present": True,
            "verifier_verdict_present": True,
            "unresolved_risks_present": True,
            "next_recommended_action_present": True,
        }
    )

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "future_runtime_enforcement_wiring" in result["unresolved_policy_fields"]


def test_dry_run_evaluator_blocks_pr_merge_without_verifier():
    result = evaluate_verifier_workflow(
        {
            "pr_merge_requested": True,
            "independent_verification_present": False,
            "verification_approved": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "PR merge requested without independent verification" in result["reasons"]
    assert "PR merge requested without approved verification" in result["reasons"]
    assert "merge PR" in result["blocked_actions"]
    assert "approved independent verification" in result["required_approvals"]


def test_dry_run_evaluator_blocks_pr_ready_without_verification():
    result = evaluate_verifier_workflow(
        {
            "pr_ready_requested": True,
            "independent_verification_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert "PR ready status requested without independent verification" in result["reasons"]
    assert "mark PR ready" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_self_verification():
    result = evaluate_verifier_workflow(
        {
            "implementer_id": "jenny",
            "verifier_id": "Jenny",
            "independent_verification_present": True,
            "verification_approved": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "implementer cannot self-verify" in result["reasons"]
    assert "accept self-verification" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_deployment_without_readiness_and_rollback():
    result = evaluate_verifier_workflow(
        {
            "deployment_requested": True,
            "deployment_readiness_packet_present": False,
            "rollback_plan_present": False,
            "blue_green_plan_present": False,
            "post_deploy_acceptance_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert "deployment requested without deployment-readiness packet" in result["reasons"]
    assert "deployment requested without rollback plan" in result["reasons"]
    assert "runtime deployment lacks blue/green plan" in result["reasons"]
    assert "post-deploy acceptance is missing" in result["reasons"]
    assert "deploy runtime" in result["blocked_actions"]
    assert "accept deployed runtime" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_waha_work_without_technical_verifier():
    result = evaluate_verifier_workflow(
        {
            "waha_work_requested": True,
            "waha_technical_verifier_present": False,
            "waha_hard_wall_policy_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert "Waha work requested without technical verifier" in result["reasons"]
    assert "Waha work requested without hard-wall policy" in result["reasons"]
    assert "mark Waha work ready" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_model_verifier_role_with_unqualified_model():
    result = evaluate_verifier_workflow(
        {
            "verifier_model_role_requested": True,
            "verifier_model_qualified": False,
            "unknown_or_free_cloud_model_for_protected_verification": True,
        }
    )

    assert result["decision_state"] == "would_block"
    assert "verifier model role requested with unqualified model" in result["reasons"]
    assert "unknown/free-cloud model is blocked for protected-domain verification" in result["reasons"]
    assert "assign model verifier role" in result["blocked_actions"]


def test_dry_run_evaluator_blocks_cleanup_without_storage_verification():
    result = evaluate_verifier_workflow(
        {
            "storage_cleanup_requested": True,
            "delete_requested": True,
            "artifact_manifest_verified": False,
            "storage_delta_verified": False,
            "archive_verification_present": False,
            "explicit_delete_lane": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert "storage cleanup/delete requested without artifact manifest verification" in result["reasons"]
    assert "storage cleanup/delete requested without storage delta verification" in result["reasons"]
    assert "delete requested without archive verification" in result["reasons"]
    assert "delete requested without explicit delete lane" in result["reasons"]
    assert "cleanup/delete storage artifacts" in result["blocked_actions"]
    assert "delete storage artifacts" in result["blocked_actions"]


def test_dry_run_evaluator_uses_caller_supplied_state_only(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live inspection is forbidden")

    monkeypatch.setattr("builtins.open", fail_if_called)

    result = evaluate_verifier_workflow(
        {
            "pr_ready_requested": True,
            "independent_verification_present": False,
        }
    )

    assert result["decision_state"] == "would_block"
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_dry_run_evaluator_unknown_without_observed_state():
    result = evaluate_verifier_workflow({})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "caller-supplied observed workflow state is incomplete" in result["reasons"]


def test_verifier_workflow_evidence_record_is_append_only_and_inert(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")
    first = VerifierWorkflowEvidenceRecord(
        record_id="record-1",
        created_at="2026-06-08T00:00:00Z",
        source="unit-test",
        lane_id="lane-a",
        task_id="task-a",
        domain_id="mission-control",
        action_class="pr_merge",
        decision_state="would_block",
        would_block=True,
        reasons=("PR merge requested without approved verification",),
        blocked_actions=("merge PR",),
        required_approvals=("approved independent verification",),
        unresolved_policy_fields=("future_runtime_enforcement_wiring",),
    )
    second = VerifierWorkflowEvidenceRecord(
        record_id="record-2",
        created_at="2026-06-08T00:01:00Z",
        decision_state="warn",
        would_block=False,
    )

    assert store.append(first) == 1
    assert store.append(second) == 2

    records = store.read_all(VerifierWorkflowEvidenceRecord)
    assert [record.record_id for record in records] == ["record-1", "record-2"]
    assert records[0].guard_type == "verifier_workflow"
    assert records[0].dry_run_only is True
    assert records[0].enforces_runtime is False
    assert records[0].to_dict()["dry_run_only"] is True
    assert records[0].to_dict()["enforces_runtime"] is False


def _valid_pr_merge_packet_identity():
    return {
        "repo": "https://github.com/Travisaggie04/Hermes-Agent.git",
        "pr_number": "#41",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "F14333C74219F23F39D0DC6110A16EF7DBA70BE1",
        "expected_base_head": "a167cf137730f2b1cab0c608a23f280ffe2770dd",
        "merge_method": "MERGE",
    }


def test_verifier_evidence_record_stores_pr_merge_packet_hash_identity_only():
    identity = _valid_pr_merge_packet_identity()
    packet = {
        **identity,
        "verifier_evidence_record_id": "record-41",
    }
    packet_hash = compute_pr_merge_packet_hash(packet)

    record = VerifierWorkflowEvidenceRecord(
        record_id="record-41",
        created_at="2026-06-08T01:00:00Z",
        action_class="pr_merge",
        decision_state="warn",
        packet_hash=packet_hash,
        packet_version="pr_merge_packet_v1",
        packet_identity={
            **identity,
            "raw_log": "do not store",
            "transcript": "do not store",
            "comments": "do not store",
            "pr_body": "do not store",
            "local_path": "/home/jenny/secret/path",
            "token": "not-a-real-token-but-still-forbidden",
            "api_key": "not-a-real-api-key-but-still-forbidden",
            "canonical_packet_json": "do not store",
        },
    )

    payload = record.to_dict()

    assert payload["packet_hash"] == packet_hash
    assert payload["packet_version"] == "pr_merge_packet_v1"
    assert payload["packet_identity"] == {
        "repo": "travisaggie04/hermes-agent",
        "pr_number": "41",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "f14333c74219f23f39d0dc6110a16ef7dba70be1",
        "expected_base_head": "a167cf137730f2b1cab0c608a23f280ffe2770dd",
        "merge_method": "merge",
    }
    assert "canonical_packet_json" not in payload
    for forbidden in ("raw_log", "transcript", "comments", "pr_body", "local_path", "token", "api_key"):
        assert forbidden not in payload["packet_identity"]
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False


def test_verifier_evidence_record_omits_invalid_pr_merge_packet_fields():
    record = VerifierWorkflowEvidenceRecord(
        record_id="record-bad-packet",
        created_at="2026-06-08T01:01:00Z",
        action_class="pr_merge",
        packet_hash="sha256:not-valid",
        packet_version="wrong-version",
        packet_identity={
            "repo": "not-a-valid-repo-name",
            "pr_number": "not-decimal",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
            "head_commit": "short-sha",
            "expected_base_head": "also-short",
            "merge_method": "octopus",
        },
    )

    payload = record.to_dict()

    assert "packet_hash" not in payload
    assert "packet_version" not in payload
    assert payload["packet_identity"] == {
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records"
    }
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False


def test_verifier_evidence_packet_fields_round_trip_and_append_only(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")
    identity = _valid_pr_merge_packet_identity()
    packet_hash = compute_pr_merge_packet_hash({**identity, "verifier_evidence_record_id": "record-roundtrip"})
    first = VerifierWorkflowEvidenceRecord(
        record_id="record-roundtrip",
        created_at="2026-06-08T01:02:00Z",
        action_class="pr_merge",
        packet_hash=packet_hash,
        packet_identity=identity,
    )
    second = VerifierWorkflowEvidenceRecord(
        record_id="record-after",
        created_at="2026-06-08T01:03:00Z",
        action_class="pr_ready",
    )

    assert store.append(first) == 1
    assert store.append(second) == 2
    records = store.read_all(VerifierWorkflowEvidenceRecord)

    assert [record.record_id for record in records] == ["record-roundtrip", "record-after"]
    assert records[0].packet_hash == packet_hash
    assert records[0].packet_version == "pr_merge_packet_v1"
    assert records[0].packet_identity["repo"] == "travisaggie04/hermes-agent"
    assert records[0].dry_run_only is True
    assert records[0].enforces_runtime is False


def test_pr_merge_gate_can_consume_stored_packet_evidence_summary():
    identity = _valid_pr_merge_packet_identity()
    record_id = "record-gate-summary"
    packet = {**identity, "verifier_evidence_record_id": record_id}
    packet_hash = compute_pr_merge_packet_hash(packet)
    record = VerifierWorkflowEvidenceRecord(
        record_id=record_id,
        created_at="2026-06-08T01:04:00Z",
        action_class="pr_merge",
        decision_state="warn",
        would_block=False,
        packet_hash=packet_hash,
        packet_identity=identity,
    )
    payload = record.to_dict()
    packet_identity = payload["packet_identity"]
    evidence_summary = {
        "record_id": payload["record_id"],
        "guard_type": payload["guard_type"],
        "action_class": payload["action_class"],
        "repo": packet_identity["repo"],
        "pr_number": packet_identity["pr_number"],
        "base_branch": packet_identity["base_branch"],
        "head_commit": packet_identity["head_commit"],
        "packet_hash": payload["packet_hash"],
        "implementer_id": "jenny-implementer",
        "verifier_id": "jenny-verifier",
        "would_block": payload["would_block"],
        "blocked_actions": payload["blocked_actions"],
        "dry_run_only": payload["dry_run_only"],
        "enforces_runtime": payload["enforces_runtime"],
    }
    state = {
        **packet_identity,
        "packet_hash": packet_hash,
        "merge_packet": packet,
        "implementer_id": "jenny-implementer",
        "verifier_id": "jenny-verifier",
        "verifier_evidence_record_id": record_id,
        "verifier_evidence": evidence_summary,
    }

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is False
    assert result["packet_hash_valid"] is True
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
