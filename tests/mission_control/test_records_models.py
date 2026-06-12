from dataclasses import FrozenInstanceError

import pytest

from mission_control.records.models import (
    ApprovalSlice,
    ArtifactRef,
    ChallengeReviewRecord,
    EvidenceCard,
    GoalContract,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    AcceptedBaselineRecord,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectBriefRecord,
    ProjectRecord,
    RECORD_TYPES,
    StartGateCheck,
    TaskControlEnvelope,
)


def test_project_record_round_trips_workspace_fields():
    record = ProjectRecord(
        project_id="project-hermes",
        name="Hermes / Mission Control",
        status="live",
        current_goal="Make Mission Control the workspace.",
        next_recommended_lane="Draft the next safe lane.",
        mistakes_guards="No dispatch without approval.",
        source_of_truth="Mission Control",
        profile="default",
        created_at="2026-06-10T10:00:00Z",
        updated_at="2026-06-10T10:01:00Z",
        metadata={"source": "unit-test"},
    )

    data = record.to_dict()

    assert data["project_id"] == "project-hermes"
    assert data["name"] == "Hermes / Mission Control"
    assert data["metadata"] == {"source": "unit-test"}
    assert ProjectRecord.from_dict(data) == record
    assert RECORD_TYPES["ProjectRecord"] is ProjectRecord


def test_project_brief_record_round_trips_project_intake_fields():
    record = ProjectBriefRecord(
        brief_id="brief-1",
        project_id="project-hermes",
        name="Hermes / Mission Control",
        outcome="Make Jenny reliable before autonomy.",
        audience="Travis",
        source_of_truth="Mission Control records",
        success_criteria=("status agrees", "challenge gate exists"),
        constraints=("manual-copy only",),
        forbidden_actions=("dispatch", "session-send"),
        approval_rules=("deploy requires explicit approval",),
        context_pack_path="context-packs/mission-control-current.md",
        status="active",
        created_at="2026-06-12T10:00:00Z",
        updated_at="2026-06-12T10:01:00Z",
        metadata={"challenge_gate_required": True},
    )

    data = record.to_dict()

    assert data["success_criteria"] == ["status agrees", "challenge gate exists"]
    assert data["forbidden_actions"] == ["dispatch", "session-send"]
    assert ProjectBriefRecord.from_dict(data) == record
    assert isinstance(ProjectBriefRecord.from_dict(data).approval_rules, tuple)
    assert RECORD_TYPES["ProjectBriefRecord"] is ProjectBriefRecord


def test_challenge_review_record_round_trips_judgment_fields():
    record = ChallengeReviewRecord(
        review_id="review-1",
        project_id="project-hermes",
        request_summary="Make Jenny post automatically every day.",
        decision_state="wrong_approach_likely",
        recommended_path="Start with scheduled drafts and approval-gated posting.",
        concerns=("automation before observability",),
        questions=("Which platform fails first?",),
        required_spec_updates=("add posting failure policy",),
        required_approvals=("public posting approval",),
        suggested_lane_title="Read-only scheduler readiness audit",
        status="draft",
        created_at="2026-06-12T10:00:00Z",
        reviewed_by="jenny",
        metadata={"manual_copy_only": True},
    )

    data = record.to_dict()

    assert data["decision_state"] == "wrong_approach_likely"
    assert data["concerns"] == ["automation before observability"]
    assert ChallengeReviewRecord.from_dict(data) == record
    assert isinstance(ChallengeReviewRecord.from_dict(data).questions, tuple)
    assert RECORD_TYPES["ChallengeReviewRecord"] is ChallengeReviewRecord


def test_lane_request_record_round_trips_manual_copy_fields():
    record = LaneRequestRecord(
        lane_request_id="lane-request-1",
        project_id="project-hermes",
        title="Read-only status refresh",
        mode="read-only/manual-copy",
        objective="Inspect project state and recommend next lane.",
        allowed_actions=("read context", "report status"),
        forbidden_actions=("dispatch", "execute", "queue mutation"),
        stop_conditions=("workspace-status fails",),
        expected_report_format=("preflight", "no-mutation confirmation"),
        draft_prompt="Active lane:\nRead-only status refresh",
        status="draft",
        created_at="2026-06-10T10:00:00Z",
        updated_at="2026-06-10T10:01:00Z",
        metadata={"manual_copy_only": True},
    )

    data = record.to_dict()

    assert data["allowed_actions"] == ["read context", "report status"]
    assert data["forbidden_actions"] == ["dispatch", "execute", "queue mutation"]
    assert LaneRequestRecord.from_dict(data) == record
    assert isinstance(LaneRequestRecord.from_dict(data).allowed_actions, tuple)
    assert RECORD_TYPES["LaneRequestRecord"] is LaneRequestRecord


def test_jenny_report_record_round_trips_manual_report_fields():
    record = JennyReportRecord(
        report_id="report-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        summary="Report summary",
        result="Completed safely.",
        changed_files=("a.py", "b.py"),
        tests=("pytest -q",),
        risks=("none",),
        next_recommended_lane="Review next lane",
        created_at="2026-06-10T12:00:00Z",
        metadata={"manual": True},
    )

    data = record.to_dict()

    assert data["changed_files"] == ["a.py", "b.py"]
    assert data["tests"] == ["pytest -q"]
    assert data["risks"] == ["none"]
    assert JennyReportRecord.from_dict(data) == record
    assert isinstance(JennyReportRecord.from_dict(data).changed_files, tuple)
    assert RECORD_TYPES["JennyReportRecord"] is JennyReportRecord


def test_mission_brief_round_trips_nested_records_to_plain_dicts():
    brief = MissionBrief(
        mission_id="mission-001",
        title="PR-A records",
        created_at="2026-06-04T10:00:00Z",
        goal=GoalContract(
            goal_id="goal-001",
            statement="Implement inert Mission Control governance records.",
            success_criteria=("models round-trip", "jsonl store round-trips"),
        ),
        control=TaskControlEnvelope(
            active_lane="code/test",
            mode="code/test only",
            allowed_actions=("edit records files", "run focused tests"),
            forbidden_actions=("gateway edits", "dashboard edits", "tool execution"),
            current_repo="/repo",
            expected_systems_files=("mission_control/records/models.py",),
            stop_condition="stop before commit",
            other_threads_excluded=("Mission Control OS development",),
        ),
        approvals=(
            ApprovalSlice(
                approval_id="approval-001",
                lane="code/test",
                mode="code/test only",
                approved_actions=("create inert records",),
                forbidden_actions=("runtime wiring",),
                approver="Travisaggie04",
                approved_at="2026-06-04T10:01:00Z",
            ),
        ),
        evidence=(
            EvidenceCard(
                evidence_id="evidence-001",
                summary="Focused tests passed.",
                artifact_refs=(
                    ArtifactRef(
                        ref_id="artifact-001",
                        kind="test-output",
                        location="pytest://tests/mission_control",
                        description="pytest output reference",
                    ),
                ),
            ),
        ),
        artifacts=(
            ArtifactRef(
                ref_id="artifact-002",
                kind="file",
                location="mission_control/records/models.py",
            ),
        ),
        metadata={"tag": "v2026.5.29.2"},
    )

    data = brief.to_dict()

    assert data == {
        "mission_id": "mission-001",
        "title": "PR-A records",
        "created_at": "2026-06-04T10:00:00Z",
        "goal": {
            "goal_id": "goal-001",
            "statement": "Implement inert Mission Control governance records.",
            "success_criteria": ["models round-trip", "jsonl store round-trips"],
            "constraints": [],
            "metadata": {},
        },
        "control": {
            "envelope_id": "",
            "active_lane": "code/test",
            "mode": "code/test only",
            "allowed_actions": ["edit records files", "run focused tests"],
            "forbidden_actions": ["gateway edits", "dashboard edits", "tool execution"],
            "current_repo": "/repo",
            "expected_systems_files": ["mission_control/records/models.py"],
            "stop_condition": "stop before commit",
            "other_threads_excluded": ["Mission Control OS development"],
            "report_requirements": [],
            "risk_level": "",
            "approval_required": False,
            "approval_slice_ids": [],
            "evidence_ids": [],
            "token_context_policy": "",
            "created_at": "",
            "status": "",
            "metadata": {},
        },
        "approvals": [
            {
                "approval_slice_id": "approval-001",
                "related_action_id": "",
                "approval_type": "",
                "decision_state": "pending",
                "required_by": "Travisaggie04",
                "reason": "",
                "safety_conditions": ["runtime wiring"],
                "evidence_ids": [],
                "created_at": "2026-06-04T10:01:00Z",
                "expires_at": None,
                "metadata": {},
                "lane": "code/test",
                "mode": "code/test only",
                "approved_actions": ["create inert records"],
                "forbidden_actions": ["runtime wiring"],
                "approver": "Travisaggie04",
                "approved_at": "2026-06-04T10:01:00Z",
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence-001",
                "related_lane": "",
                "related_action_id": "",
                "related_record_type": "",
                "summary": "Focused tests passed.",
                "evidence_type": "",
                "source_label": "",
                "created_at": "",
                "risk_notes": [],
                "metadata": {},
                "artifact_refs": [
                    {
                        "ref_id": "artifact-001",
                        "kind": "test-output",
                        "location": "pytest://tests/mission_control",
                        "description": "pytest output reference",
                        "metadata": {},
                    }
                ],
            }
        ],
        "artifacts": [
            {
                "ref_id": "artifact-002",
                "kind": "file",
                "location": "mission_control/records/models.py",
                "description": "",
                "metadata": {},
            }
        ],
        "metadata": {"tag": "v2026.5.29.2"},
    }
    assert MissionBrief.from_dict(data) == brief
    assert isinstance(MissionBrief.from_dict(data).approvals, tuple)
    assert isinstance(MissionBrief.from_dict(data).evidence[0].artifact_refs, tuple)


def test_records_are_frozen_value_objects():
    artifact = ArtifactRef(ref_id="artifact-001", kind="file", location="README.md")

    with pytest.raises(FrozenInstanceError):
        artifact.location = "changed.md"


def test_from_dict_rejects_missing_required_fields():
    with pytest.raises(TypeError):
        GoalContract.from_dict({"goal_id": "goal-001"})


def test_approval_slice_round_trips_pr_h_planning_fields():
    approval = ApprovalSlice(
        approval_slice_id="approval-slice-001",
        related_action_id="action-001",
        approval_type="human",
        decision_state="pending",
        required_by="Travis",
        reason="Approve only after focused tests pass.",
        safety_conditions=("no deploy", "no tool execution"),
        evidence_ids=("evidence-001", "evidence-002"),
        created_at="2026-06-06T00:00:00Z",
        expires_at="2026-06-07T00:00:00Z",
        metadata={"internal_note": "store only"},
    )

    data = approval.to_dict()

    assert data == {
        "approval_slice_id": "approval-slice-001",
        "related_action_id": "action-001",
        "approval_type": "human",
        "decision_state": "pending",
        "required_by": "Travis",
        "reason": "Approve only after focused tests pass.",
        "safety_conditions": ["no deploy", "no tool execution"],
        "evidence_ids": ["evidence-001", "evidence-002"],
        "created_at": "2026-06-06T00:00:00Z",
        "expires_at": "2026-06-07T00:00:00Z",
        "metadata": {"internal_note": "store only"},
    }
    assert ApprovalSlice.from_dict(data) == approval
    assert isinstance(ApprovalSlice.from_dict(data).safety_conditions, tuple)
    assert isinstance(ApprovalSlice.from_dict(data).evidence_ids, tuple)


def test_evidence_card_round_trips_pr_h_planning_fields():
    evidence = EvidenceCard(
        evidence_id="evidence-001",
        related_lane="PR-H Evidence Cards",
        related_action_id="action-001",
        related_record_type="OperatorAction",
        summary="Focused tests show bounded read-only behavior.",
        evidence_type="test",
        source_label="pytest",
        created_at="2026-06-06T00:00:00Z",
        risk_notes=("No execution path added.",),
        metadata={"raw_log": "store only"},
    )

    data = evidence.to_dict()

    assert data == {
        "evidence_id": "evidence-001",
        "related_lane": "PR-H Evidence Cards",
        "related_action_id": "action-001",
        "related_record_type": "OperatorAction",
        "summary": "Focused tests show bounded read-only behavior.",
        "evidence_type": "test",
        "source_label": "pytest",
        "created_at": "2026-06-06T00:00:00Z",
        "risk_notes": ["No execution path added."],
        "metadata": {"raw_log": "store only"},
    }
    assert EvidenceCard.from_dict(data) == evidence
    assert isinstance(EvidenceCard.from_dict(data).risk_notes, tuple)


def test_operator_action_round_trips_to_plain_dicts():
    action = OperatorAction(
        action_id="action-001",
        title="Request bounded implementation slice",
        lane="PR-G Operator Action Queue implementation",
        mode="focused tests only",
        requested_action="Implement inert read-only queue summary.",
        risk_level="low",
        status="requested",
        required_approval="Travis approval before commit",
        approval_id="approval-001",
        evidence_ids=("evidence-001", "evidence-002"),
        stop_condition="Stop after focused tests.",
        created_at="2026-06-05T10:00:00Z",
        expires_at="2026-06-06T10:00:00Z",
        metadata={"source": "planning", "internal_note": "display only"},
    )

    data = action.to_dict()

    assert data == {
        "action_id": "action-001",
        "title": "Request bounded implementation slice",
        "lane": "PR-G Operator Action Queue implementation",
        "mode": "focused tests only",
        "requested_action": "Implement inert read-only queue summary.",
        "risk_level": "low",
        "status": "requested",
        "required_approval": "Travis approval before commit",
        "approval_id": "approval-001",
        "evidence_ids": ["evidence-001", "evidence-002"],
        "stop_condition": "Stop after focused tests.",
        "created_at": "2026-06-05T10:00:00Z",
        "expires_at": "2026-06-06T10:00:00Z",
        "metadata": {"source": "planning", "internal_note": "display only"},
    }
    assert OperatorAction.from_dict(data) == action
    assert isinstance(OperatorAction.from_dict(data).evidence_ids, tuple)


def test_task_control_envelope_round_trips_pr_i_fields():
    envelope = TaskControlEnvelope(
        envelope_id="envelope-001",
        active_lane="PR-I Start Gate",
        mode="bounded implementation",
        allowed_actions=("create inert records",),
        forbidden_actions=("execute tools", "approve actions"),
        stop_condition="Stop after draft PR.",
        report_requirements=("report tests", "report safety posture"),
        risk_level="low",
        approval_required=True,
        approval_slice_ids=("approval-001",),
        evidence_ids=("evidence-001",),
        token_context_policy="summary-first latest-N only",
        created_at="2026-06-06T00:00:00Z",
        status="active",
        metadata={"raw_context": "stored only"},
    )

    data = envelope.to_dict()

    assert data == {
        "envelope_id": "envelope-001",
        "active_lane": "PR-I Start Gate",
        "mode": "bounded implementation",
        "allowed_actions": ["create inert records"],
        "forbidden_actions": ["execute tools", "approve actions"],
        "current_repo": "",
        "expected_systems_files": [],
        "stop_condition": "Stop after draft PR.",
        "other_threads_excluded": [],
        "report_requirements": ["report tests", "report safety posture"],
        "risk_level": "low",
        "approval_required": True,
        "approval_slice_ids": ["approval-001"],
        "evidence_ids": ["evidence-001"],
        "token_context_policy": "summary-first latest-N only",
        "created_at": "2026-06-06T00:00:00Z",
        "status": "active",
        "metadata": {"raw_context": "stored only"},
    }
    assert TaskControlEnvelope.from_dict(data) == envelope
    assert isinstance(TaskControlEnvelope.from_dict(data).approval_slice_ids, tuple)


def test_start_gate_check_round_trips_descriptive_fields_only():
    check = StartGateCheck(
        start_gate_id="start-gate-001",
        envelope_id="envelope-001",
        decision_state="needs_approval",
        reasons=("approval slice required",),
        blocked_actions=("push", "deploy"),
        required_approvals=("approval-001",),
        dirty_worktree_state="clean",
        branch_safety_state="exact base",
        secret_safety_state="not touched",
        token_context_state="bounded",
        created_at="2026-06-06T00:01:00Z",
        metadata={"raw_scan": "stored only"},
    )

    data = check.to_dict()

    assert data == {
        "start_gate_id": "start-gate-001",
        "envelope_id": "envelope-001",
        "decision_state": "needs_approval",
        "reasons": ["approval slice required"],
        "blocked_actions": ["push", "deploy"],
        "required_approvals": ["approval-001"],
        "dirty_worktree_state": "clean",
        "branch_safety_state": "exact base",
        "secret_safety_state": "not touched",
        "token_context_state": "bounded",
        "created_at": "2026-06-06T00:01:00Z",
        "metadata": {"raw_scan": "stored only"},
    }
    assert StartGateCheck.from_dict(data) == check
    assert isinstance(StartGateCheck.from_dict(data).blocked_actions, tuple)


def test_operator_action_is_registered_and_exported():
    from mission_control.records import OperatorAction as ExportedOperatorAction
    from mission_control.records.models import RECORD_TYPES

    assert ExportedOperatorAction is OperatorAction
    assert RECORD_TYPES["OperatorAction"] is OperatorAction


def test_operator_action_metadata_is_optional():
    action = OperatorAction.from_dict({
        "action_id": "action-minimal",
        "title": "Minimal requested action",
        "lane": "read-only lane",
        "mode": "inventory only",
        "requested_action": "Review summary card.",
    })

    assert action.metadata == {}
    assert action.evidence_ids == ()
    assert action.risk_level == ""
    assert action.status == "requested"



def test_operating_workspace_handoff_record_round_trips_display_only_fields():
    record = OperatingWorkspaceHandoffRecord(
        handoff_id="handoff-001",
        created_at="2026-06-09T00:00:00Z",
        source="operator_supplied_handoff",
        active_lane="PR #45 Operating Workspace handoff records",
        lane_mode="bounded display-only PR",
        accepted_runtime_path="/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        accepted_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
        rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
        rollback_head="f20aa2da2a2e978d72f837007d8ab1b14301795b",
        dispatch_in_gateway=False,
        max_active_lane=1,
        active_lane_count=1,
        target_type="pr",
        target_id="45",
        target_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
        status="active",
        last_result="PR #44 accepted",
        next_action="Implement PR #45 tests",
        warnings=("display-only",),
        dry_run_only=False,
        enforces_runtime=True,
        display_only=False,
    )

    data = record.to_dict()

    assert data == {
        "handoff_id": "handoff-001",
        "created_at": "2026-06-09T00:00:00Z",
        "source": "operator_supplied_handoff",
        "active_lane": "PR #45 Operating Workspace handoff records",
        "lane_mode": "bounded display-only PR",
        "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "accepted_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
        "rollback_head": "f20aa2da2a2e978d72f837007d8ab1b14301795b",
        "dispatch_in_gateway": False,
        "max_active_lane": 1,
        "active_lane_count": 1,
        "target_type": "pr",
        "target_id": "45",
        "target_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "status": "active",
        "last_result": "PR #44 accepted",
        "next_action": "Implement PR #45 tests",
        "warnings": ["display-only"],
        "dry_run_only": True,
        "enforces_runtime": False,
        "display_only": True,
    }
    assert OperatingWorkspaceHandoffRecord.from_dict(data) == record
    assert isinstance(OperatingWorkspaceHandoffRecord.from_dict(data).warnings, tuple)
    assert RECORD_TYPES["OperatingWorkspaceHandoffRecord"] is OperatingWorkspaceHandoffRecord


def test_operating_workspace_handoff_record_sanitizes_allowlist_bounds_and_shas():
    record = OperatingWorkspaceHandoffRecord.from_dict(
        {
            "handoff_id": "h" * 500,
            "created_at": "2026-06-09T00:00:00Z",
            "source": "operator",
            "active_lane": "x" * 500,
            "lane_mode": "mode",
            "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
            "accepted_head": "not-a-sha",
            "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
            "rollback_head": "f20aa2da2a2e978d72f837007d8ab1b14301795b",
            "dispatch_in_gateway": True,
            "max_active_lane": 5000,
            "active_lane_count": 5001,
            "target_type": "pr",
            "target_id": "45",
            "target_head": "also-not-a-sha",
            "status": "active",
            "last_result": "raw log must not appear",
            "next_action": "next",
            "warnings": [str(i) for i in range(25)],
            "raw_log": "forbidden",
            "discord_messages": ["forbidden"],
            "token": "secret-token",
            "github_response": {"raw": "forbidden"},
        }
    )

    data = record.to_dict()

    assert len(data["handoff_id"]) <= 160
    assert len(data["active_lane"]) <= 160
    assert data["accepted_head"] == ""
    assert data["target_head"] == ""
    assert len(data["warnings"]) == 20
    rendered = str(data).lower()
    assert "raw_log" not in rendered
    assert "discord_messages" not in rendered
    assert "secret-token" not in rendered
    assert "github_response" not in rendered



def test_accepted_baseline_record_round_trips_and_forces_inert_flags():
    record = AcceptedBaselineRecord(
        baseline_id="baseline-001",
        recorded_at="2026-06-09T00:00:00Z",
        source="operator_accepted_baseline",
        runtime_path="/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        head="8c560c739606564aeeb4db464fe1989cb67a40b6",
        rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        rollback_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
        dispatch_in_gateway=False,
        active_kanban=0,
        max_active_lane=1,
        issue="none",
        display_only=False,
        dry_run_only=False,
        enforces_runtime=True,
    )

    data = record.to_dict()

    assert data == {
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
    assert AcceptedBaselineRecord.from_dict(data) == record
    assert RECORD_TYPES["AcceptedBaselineRecord"] is AcceptedBaselineRecord


def test_accepted_baseline_record_sanitizes_bounds_shas_and_forbidden_fields():
    record = AcceptedBaselineRecord.from_dict({
        "baseline_id": "b" * 500,
        "recorded_at": "2026-06-09T00:00:00Z",
        "source": "operator",
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        "head": "not-a-sha",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "rollback_head": "also-not-a-sha",
        "dispatch_in_gateway": True,
        "active_kanban": 5000,
        "max_active_lane": 5001,
        "issue": "x" * 500,
        "raw_log": "forbidden",
        "transcript": "forbidden",
        "discord_messages": ["forbidden"],
        "pr_body": "forbidden",
        "github_response": {"raw": "forbidden"},
        "token": "placeholder-token",
        "canonical_packet_json": {"raw": "forbidden"},
    })

    data = record.to_dict()

    assert len(data["baseline_id"]) <= 160
    assert len(data["issue"]) <= 160
    assert data["head"] == ""
    assert data["rollback_head"] == ""
    assert data["active_kanban"] == 999
    assert data["max_active_lane"] == 999
    rendered = str(data).lower()
    for forbidden in ("raw_log", "transcript", "discord_messages", "pr_body", "github_response", "placeholder-token", "canonical_packet_json"):
        assert forbidden not in rendered
