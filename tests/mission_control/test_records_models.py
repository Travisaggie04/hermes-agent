from dataclasses import FrozenInstanceError

import pytest

from mission_control.records.models import (
    ApprovalSlice,
    ArtifactRef,
    EvidenceCard,
    GoalContract,
    MissionBrief,
    OperatorAction,
    TaskControlEnvelope,
)


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
            "active_lane": "code/test",
            "mode": "code/test only",
            "allowed_actions": ["edit records files", "run focused tests"],
            "forbidden_actions": ["gateway edits", "dashboard edits", "tool execution"],
            "current_repo": "/repo",
            "expected_systems_files": ["mission_control/records/models.py"],
            "stop_condition": "stop before commit",
            "other_threads_excluded": ["Mission Control OS development"],
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
