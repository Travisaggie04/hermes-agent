import json

import pytest

from mission_control.records.errors import RecordDecodeError, UnknownRecordTypeError
from mission_control.records.models import ArtifactRef, GoalContract
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
