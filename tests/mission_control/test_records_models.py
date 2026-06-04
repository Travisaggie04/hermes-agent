from dataclasses import FrozenInstanceError

import pytest

from mission_control.records.models import (
    ApprovalSlice,
    ArtifactRef,
    EvidenceCard,
    GoalContract,
    MissionBrief,
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
                "approval_id": "approval-001",
                "lane": "code/test",
                "mode": "code/test only",
                "approved_actions": ["create inert records"],
                "forbidden_actions": ["runtime wiring"],
                "approver": "Travisaggie04",
                "approved_at": "2026-06-04T10:01:00Z",
                "expires_at": None,
                "metadata": {},
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence-001",
                "summary": "Focused tests passed.",
                "artifact_refs": [
                    {
                        "ref_id": "artifact-001",
                        "kind": "test-output",
                        "location": "pytest://tests/mission_control",
                        "description": "pytest output reference",
                        "metadata": {},
                    }
                ],
                "metadata": {},
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
