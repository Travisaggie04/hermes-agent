"""Inert Verifier Workflow v1 policy tests."""

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
