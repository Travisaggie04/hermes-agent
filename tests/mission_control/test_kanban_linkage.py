from __future__ import annotations

from mission_control.kanban_linkage import (
    KanbanLink,
    ObservedKanbanTaskState,
    extract_kanban_link,
    linked_kanban_task_payload,
    validate_kanban_linkage,
)
from mission_control.records.models import GoalContract, TaskControlEnvelope


def test_kanban_linkage_round_trips_through_existing_metadata_fields():
    goal = GoalContract(
        goal_id="goal-link",
        statement="Show linked Kanban state.",
        metadata={
            "kanban_board_id": "mission-control",
            "kanban_task_id": "task-123",
        },
    )
    envelope = TaskControlEnvelope(
        envelope_id="tce-link",
        active_lane="Mission Control / Kanban task-linkage v1",
        mode="bounded implementation",
        metadata={
            "kanban": {
                "board_id": "mission-control",
                "task_id": "task-123",
            },
            "goal_contract_id": "goal-link",
        },
    )

    restored_goal = GoalContract.from_dict(goal.to_dict())
    restored_envelope = TaskControlEnvelope.from_dict(envelope.to_dict())

    assert extract_kanban_link(restored_goal, record_id="goal-link") == KanbanLink(
        board_id="mission-control",
        task_id="task-123",
        goal_contract_id="goal-link",
    )
    assert extract_kanban_link(restored_envelope, record_id="tce-link") == KanbanLink(
        board_id="mission-control",
        task_id="task-123",
        goal_contract_id="goal-link",
        task_control_envelope_id="tce-link",
    )


def test_kanban_linkage_validator_reports_missing_stale_linked_and_unknown():
    assert validate_kanban_linkage(None, None).state == "missing_link"

    link = KanbanLink(board_id="default", task_id="task-123")
    assert validate_kanban_linkage(link, None).state == "stale_link"

    observed = ObservedKanbanTaskState(
        board_id="default",
        task_id="task-123",
        title="Do the work",
        status="ready",
    )
    assert validate_kanban_linkage(link, observed).state == "linked"

    assert validate_kanban_linkage(link, observed, read_error="db unavailable").state == "unknown"


def test_linked_kanban_payload_can_report_missing_link_for_display_only_callers():
    record = TaskControlEnvelope(
        envelope_id="tce-missing-link",
        active_lane="Lane preflight visibility",
        mode="display only",
    )

    assert linked_kanban_task_payload(record, record_id=record.envelope_id) is None
    assert linked_kanban_task_payload(
        record,
        record_id=record.envelope_id,
        include_missing=True,
    ) == {
        "link_state": "missing_link",
        "board_id": "",
        "board_name": "",
        "task_id": "",
        "task_title": "",
        "task_status": "",
        "task_workspace": "",
        "task_branch": "",
        "linked_goal_contract_id": "",
        "linked_task_control_envelope_id": "",
        "reasons": [],
    }


def test_kanban_linkage_validator_reports_scope_mismatch_for_repo_path_and_branch():
    link = KanbanLink(board_id="default", task_id="task-123")
    observed = ObservedKanbanTaskState(
        board_id="default",
        task_id="task-123",
        title="Do the work",
        status="ready",
        workspace_path="/work/hermes-agent",
        branch_name="actual-branch",
    )
    envelope = TaskControlEnvelope(
        active_lane="linked lane",
        mode="bounded implementation",
        current_repo="/work/other-repo",
        metadata={"expected_branch": "expected-branch"},
    )

    result = validate_kanban_linkage(link, observed, envelope=envelope)

    assert result.state == "scope_mismatch"
    assert "current_repo does not match Kanban workspace" in result.reasons
    assert "expected_branch does not match Kanban branch" in result.reasons


def test_linked_kanban_payload_sanitizes_malicious_metadata_and_observed_task(monkeypatch):
    malicious = "\x1b[31mSECRET_TOKEN=sk-test-fake\nline-two\rhidden"
    long_value = malicious + ("x" * 500)
    observed = ObservedKanbanTaskState(
        board_id=long_value,
        task_id=long_value,
        title="Task title " + long_value,
        status="ready\nqueued",
        workspace_path="/home/jenny/.hidden/workspace/" + long_value,
        branch_name="feature/" + long_value,
    )
    record = TaskControlEnvelope(
        envelope_id="tce-" + long_value,
        active_lane="linked lane",
        mode="display only",
        current_repo="/different/workspace",
        metadata={
            "kanban": {
                "board_id": long_value,
                "task_id": long_value,
                "goal_contract_id": "goal-" + long_value,
                "task_control_envelope_id": "nested-" + long_value,
            },
            "expected_branch": "expected-branch",
            "raw_metadata": {"must_not_leak": "secret raw object"},
        },
    )

    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_observed_kanban_task",
        lambda link: (observed, ""),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_kanban_board_name",
        lambda board_id: "Board " + long_value,
    )

    payload = linked_kanban_task_payload(record, record_id=record.envelope_id)

    assert payload is not None
    assert set(payload) == {
        "link_state",
        "board_id",
        "board_name",
        "task_id",
        "task_title",
        "task_status",
        "task_workspace",
        "task_branch",
        "linked_goal_contract_id",
        "linked_task_control_envelope_id",
        "reasons",
    }
    flattened = str(payload)
    assert "\x1b" not in flattened
    assert "\n" not in flattened
    assert "\r" not in flattened
    assert "sk-test-fake" not in flattened
    assert "SECRET_TOKEN" not in flattened
    assert "raw_metadata" not in flattened
    assert "secret raw object" not in flattened
    assert "/home/jenny/.hidden/workspace" not in flattened
    for key, value in payload.items():
        if key == "reasons":
            assert len(value) <= 5
            assert all(len(reason) <= 120 for reason in value)
        else:
            assert len(value) <= 120


def test_linked_kanban_payload_suppresses_absolute_hidden_workspace_path(monkeypatch):
    record = GoalContract(
        goal_id="goal-hidden-path",
        statement="Display linked task safely.",
        metadata={
            "kanban_board_id": "default",
            "kanban_task_id": "task-hidden-path",
        },
    )
    observed = ObservedKanbanTaskState(
        board_id="default",
        task_id="task-hidden-path",
        title="Hidden path task",
        status="ready",
        workspace_path="/home/jenny/.secrets",
        branch_name="main",
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_observed_kanban_task",
        lambda link: (observed, ""),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_kanban_board_name",
        lambda board_id: "Default",
    )

    payload = linked_kanban_task_payload(record, record_id="goal-hidden-path")

    assert payload is not None
    assert payload["task_workspace"] == "[workspace path hidden]"
    assert "/home/jenny/.secrets" not in str(payload)


def test_linked_kanban_payload_uses_bounded_reason_code_for_read_errors(monkeypatch):
    record = GoalContract(
        goal_id="goal-read-error",
        statement="Display linked task safely.",
        metadata={
            "kanban_board_id": "default",
            "kanban_task_id": "task-read-error",
        },
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_observed_kanban_task",
        lambda link: (None, "sqlite error\nSECRET_TOKEN=sk-test-fake " + ("x" * 500)),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_kanban_board_name",
        lambda board_id: "Default",
    )

    payload = linked_kanban_task_payload(record, record_id="goal-read-error")

    assert payload is not None
    assert payload["link_state"] == "unknown"
    assert payload["reasons"] == ["read_error"]
    assert "sk-test-fake" not in str(payload)
