import json

import pytest

from mission_control.records.errors import RecordDecodeError, UnknownRecordTypeError
from mission_control.records.models import (
    AcceptedBaselineRecord,
    ApprovalSlice,
    ArtifactRef,
    GoalContract,
    JennyReportRecord,
    LaneRequestRecord,
    ProjectRecord,
)
from mission_control.records.store import JsonlRecordStore


def test_jsonl_store_appends_and_reads_typed_records(tmp_path):
    path = tmp_path / "nested" / "records.jsonl"
    store = JsonlRecordStore(path)
    goal = GoalContract(
        goal_id="goal-001",
        statement="Keep Mission Control records inert.",
        success_criteria=("no runtime wiring",),
    )
    artifact = ArtifactRef(
        ref_id="artifact-001",
        kind="file",
        location=str(tmp_path / "missing-artifact.txt"),
        description="Reference only; store must not open it.",
    )

    assert store.append(goal) == 1
    assert store.append(artifact) == 2

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "record_type": "GoalContract",
        "record": {
            "goal_id": "goal-001",
            "statement": "Keep Mission Control records inert.",
            "success_criteria": ["no runtime wiring"],
            "constraints": [],
            "metadata": {},
        },
    }
    assert store.read_all() == (goal, artifact)
    assert store.read_all(GoalContract) == (goal,)


def test_jsonl_store_appends_and_reads_workspace_records(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    project = ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control")
    lane = LaneRequestRecord(
        lane_request_id="lane-request-1",
        project_id="project-hermes",
        title="Read-only status refresh",
        draft_prompt="Manual transport only",
    )

    assert store.append(project) == 1
    assert store.append(lane) == 2

    assert store.read_all(ProjectRecord) == (project,)
    assert store.read_all(LaneRequestRecord) == (lane,)
    assert store.read_latest(record_class=LaneRequestRecord, limit=1) == ((1, lane),)

    report = JennyReportRecord(
        report_id="report-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        summary="Manual report",
    )
    assert store.append(report) == 3
    assert store.read_all(JennyReportRecord) == (report,)
    assert store.read_latest(record_class=JennyReportRecord, limit=1) == ((2, report),)


def test_jsonl_store_reads_legacy_top_level_records(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        json.dumps(
            {
                "record_type": "AcceptedBaselineRecord",
                "baseline_id": "accepted-pr91-active-lanes-479762d",
                "head": "479762d7afe76ceda71f69253b157094b6ad61da",
                "runtime_path": "/home/jenny/.hermes/hermes-runtime-active-lanes-479762d",
                "rollback_head": "7bbaa8314880a29bc1acef3c2b34cea4b1eb6c63",
                "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-github-bridge-gh245-7bbaa83",
                "dispatch_in_gateway": False,
                "active_kanban": 0,
                "max_active_lane": 1,
                "issue": "PR #91 active lanes runtime switch",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    store = JsonlRecordStore(path)

    records = store.read_all(AcceptedBaselineRecord)

    assert len(records) == 1
    assert records[0].baseline_id == "accepted-pr91-active-lanes-479762d"
    assert records[0].head == "479762d7afe76ceda71f69253b157094b6ad61da"
    assert records[0].runtime_path == "/home/jenny/.hermes/hermes-runtime-active-lanes-479762d"


def test_jsonl_store_missing_file_reads_empty_tuple(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")

    assert store.read_all() == ()


def test_jsonl_store_rejects_unknown_record_type(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"record_type": "GatewayHook", "record": {}}\n', encoding="utf-8")
    store = JsonlRecordStore(path)

    with pytest.raises(UnknownRecordTypeError):
        store.read_all()


def test_jsonl_store_wraps_invalid_json_with_line_number(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        (
            '{"record_type": "GoalContract", '
            '"record": {"goal_id": "goal-001", "statement": "valid"}}\n'
            "not-json\n"
        ),
        encoding="utf-8",
    )
    store = JsonlRecordStore(path)

    with pytest.raises(RecordDecodeError) as excinfo:
        store.read_all()

    assert excinfo.value.line_number == 2


def test_jsonl_store_read_latest_returns_latest_n_with_original_indexes(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    records = tuple(
        GoalContract(goal_id=f"goal-{index}", statement=f"Goal {index}")
        for index in range(5)
    )
    for record in records:
        store.append(record)

    assert store.read_latest(limit=2) == (
        (3, records[3]),
        (4, records[4]),
    )


def test_jsonl_store_read_latest_filters_record_class_with_original_indexes(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    goal = GoalContract(goal_id="goal-1", statement="Unrelated goal")
    approvals = tuple(
        ApprovalSlice(approval_id=f"approval-{index}", lane="lane", mode="mode")
        for index in range(3)
    )
    store.append(approvals[0])
    store.append(goal)
    store.append(approvals[1])
    store.append(approvals[2])

    assert store.read_latest(record_class=ApprovalSlice, limit=2) == (
        (2, approvals[1]),
        (3, approvals[2]),
    )


def test_jsonl_store_read_latest_missing_file_reads_empty_tuple(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")

    assert store.read_latest() == ()


def test_jsonl_store_read_latest_zero_or_invalid_limit_reads_empty_tuple(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")
    store.append(GoalContract(goal_id="goal-1", statement="Present but not requested"))

    assert store.read_latest(limit=0) == ()
    assert store.read_latest(limit=-1) == ()


def test_jsonl_store_read_latest_preserves_malformed_record_errors(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        (
            '{"record_type": "GoalContract", '
            '"record": {"goal_id": "goal-001", "statement": "valid"}}\n'
            "not-json\n"
        ),
        encoding="utf-8",
    )
    store = JsonlRecordStore(path)

    with pytest.raises(RecordDecodeError) as excinfo:
        store.read_latest()

    assert excinfo.value.line_number == 2


def test_jsonl_store_read_latest_preserves_unknown_record_errors(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"record_type": "GatewayHook", "record": {}}\n', encoding="utf-8")
    store = JsonlRecordStore(path)

    with pytest.raises(UnknownRecordTypeError):
        store.read_latest()
