from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from mission_control.records import AcceptedBaselineRecord, JsonlRecordStore


ACCEPTED_HEAD = "0" * 40
ROLLBACK_HEAD = "1" * 40


def _write_baseline(home: Path, accepted: Path, rollback: Path) -> None:
    store = JsonlRecordStore(home / "mission-control" / "records.jsonl")
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted-test",
            recorded_at="2026-06-11T00:00:00Z",
            source="test",
            runtime_path=str(accepted),
            head=ACCEPTED_HEAD,
            rollback_runtime_path=str(rollback),
            rollback_head=ROLLBACK_HEAD,
        )
    )


@pytest.fixture
def live_runtime_layout(tmp_path):
    home = tmp_path / "hermes-home"
    accepted = tmp_path / "accepted-runtime"
    rollback = tmp_path / "rollback-runtime"
    dev = tmp_path / "dev-worktree"
    for path in (accepted, rollback, dev):
        path.mkdir(parents=True)
    _write_baseline(home, accepted, rollback)
    token = set_hermes_home_override(home)
    try:
        yield SimpleNamespace(home=home, accepted=accepted, rollback=rollback, dev=dev)
    finally:
        reset_hermes_home_override(token)


@pytest.mark.parametrize(
    ("action", "blocker"),
    [
        ("checkout", "live_runtime_checkout_blocked"),
        ("switch", "live_runtime_switch_blocked"),
        ("reset", "live_runtime_reset_blocked"),
        ("pull", "live_runtime_pull_blocked"),
        ("update", "live_runtime_update_blocked"),
    ],
)
def test_blocks_live_runtime_mutations(live_runtime_layout, action, blocker):
    from mission_control.live_runtime_mutation_guard import assert_runtime_mutation_allowed

    with pytest.raises(RuntimeError) as excinfo:
        assert_runtime_mutation_allowed(action, cwd=live_runtime_layout.accepted)

    assert blocker in str(excinfo.value)


@pytest.mark.parametrize(
    ("action", "blocker"),
    [
        ("checkout", "rollback_runtime_checkout_blocked"),
        ("update", "rollback_runtime_update_blocked"),
    ],
)
def test_blocks_rollback_runtime_mutations(live_runtime_layout, action, blocker):
    from mission_control.live_runtime_mutation_guard import assert_runtime_mutation_allowed

    with pytest.raises(RuntimeError) as excinfo:
        assert_runtime_mutation_allowed(action, cwd=live_runtime_layout.rollback)

    assert blocker in str(excinfo.value)


def test_allows_normal_dev_worktree(live_runtime_layout):
    from mission_control.live_runtime_mutation_guard import assert_runtime_mutation_allowed

    decision = assert_runtime_mutation_allowed("update", cwd=live_runtime_layout.dev)

    assert decision.allowed is True


@pytest.mark.parametrize("context", ["controlled_deploy", "runtime_recovery", "explicit_live_runtime_switch"])
def test_allows_explicit_exception_contexts(live_runtime_layout, context):
    from mission_control.live_runtime_mutation_guard import assert_runtime_mutation_allowed

    decision = assert_runtime_mutation_allowed(
        "update",
        cwd=live_runtime_layout.accepted,
        exception_context=context,
    )

    assert decision.allowed is True
    assert decision.exception_context == context


@pytest.mark.parametrize(
    ("command", "blocker"),
    [
        ("git checkout main", "live_runtime_checkout_blocked"),
        ("git switch main", "live_runtime_switch_blocked"),
        ("git reset --hard origin/main", "live_runtime_reset_blocked"),
        ("git pull --ff-only origin main", "live_runtime_pull_blocked"),
    ],
)
def test_terminal_command_guard_blocks_git_mutations_in_accepted_runtime(
    live_runtime_layout,
    command,
    blocker,
):
    from tools.approval import check_all_command_guards

    result = check_all_command_guards(command, "local", cwd=live_runtime_layout.accepted)

    assert result["approved"] is False
    assert result["pattern_key"] == blocker


def test_terminal_command_guard_allows_git_mutations_in_normal_dev_worktree(live_runtime_layout):
    from tools.approval import check_all_command_guards

    result = check_all_command_guards("git checkout main", "local", cwd=live_runtime_layout.dev)

    assert result["approved"] is True


def test_terminal_command_guard_blocks_rollback_git_checkout(live_runtime_layout):
    from tools.approval import check_all_command_guards

    result = check_all_command_guards("git checkout main", "local", cwd=live_runtime_layout.rollback)

    assert result["approved"] is False
    assert result["pattern_key"] == "rollback_runtime_checkout_blocked"
