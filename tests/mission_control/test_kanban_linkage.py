from __future__ import annotations

from mission_control.kanban_linkage import (
    KanbanLink,
    ObservedKanbanTaskState,
    extract_kanban_link,
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
