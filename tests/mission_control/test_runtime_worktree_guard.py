from __future__ import annotations

import builtins
import inspect
import socket
import subprocess
from pathlib import Path

from mission_control.runtime_worktree_guard import evaluate_runtime_worktree_guard


BASE_STATE = {
    "candidate_worktree_path": "/home/jenny/.hermes/worktrees/example",
    "candidate_git_top_level": "/home/jenny/.hermes/worktrees/example",
    "candidate_head": "9b3b21b0c24cce67243e8c654fce0893930359d1",
    "candidate_branch": "feature/example",
    "candidate_status_clean": True,
    "requested_action_class": "pr_create",
    "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-handoffbuilder-13a19cf",
    "accepted_head": "13a19cfedc7783ca2f141d9149b4c382f841c36f",
    "accepted_runtime_disk_head": "13a19cfedc7783ca2f141d9149b4c382f841c36f",
    "accepted_runtime_branch": "",
    "accepted_runtime_status_clean": True,
    "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-missioncontrolnav-247fab8",
    "rollback_head": "247fab80ef964390e4741e6dbd430514e17f1c24",
    "rollback_runtime_disk_head": "247fab80ef964390e4741e6dbd430514e17f1c24",
    "rollback_runtime_branch": "",
    "rollback_runtime_status_clean": True,
    "requested_dev_worktree_exists": True,
}


def _state(**overrides):
    value = dict(BASE_STATE)
    value.update(overrides)
    return value


def test_clean_non_runtime_worktree_passes_for_pr_create():
    result = evaluate_runtime_worktree_guard(_state())

    assert result["default_off"] is True
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert result["decision_state"] == "pass"
    assert result["would_block"] is False
    assert result["blockers"] == []


def test_candidate_worktree_equal_to_accepted_runtime_blocks_dev_action():
    runtime = BASE_STATE["accepted_runtime_path"]

    result = evaluate_runtime_worktree_guard(
        _state(candidate_worktree_path=runtime, candidate_git_top_level=runtime)
    )

    assert result["decision_state"] == "blocked"
    assert result["would_block"] is True
    assert "dev_worktree_is_live_runtime" in result["blockers"]


def test_candidate_worktree_equal_to_rollback_runtime_blocks_dev_action():
    runtime = BASE_STATE["rollback_runtime_path"]

    result = evaluate_runtime_worktree_guard(
        _state(candidate_worktree_path=runtime, candidate_git_top_level=runtime)
    )

    assert result["decision_state"] == "blocked"
    assert "dev_worktree_is_rollback_runtime" in result["blockers"]


def test_accepted_runtime_disk_head_mismatch_blocks_dev_action():
    result = evaluate_runtime_worktree_guard(
        _state(accepted_runtime_disk_head="9b3b21b0c24cce67243e8c654fce0893930359d1")
    )

    assert result["decision_state"] == "blocked"
    assert "runtime_disk_head_mismatch" in result["blockers"]


def test_accepted_runtime_on_feature_branch_blocks_dev_action():
    result = evaluate_runtime_worktree_guard(
        _state(accepted_runtime_branch="feature/mission-control-project-workspace-v1")
    )

    assert result["decision_state"] == "blocked"
    assert "runtime_on_feature_branch" in result["blockers"]


def test_rollback_runtime_disk_head_mismatch_blocks_dev_action():
    result = evaluate_runtime_worktree_guard(
        _state(rollback_runtime_disk_head="9b3b21b0c24cce67243e8c654fce0893930359d1")
    )

    assert result["decision_state"] == "blocked"
    assert "rollback_disk_head_mismatch" in result["blockers"]


def test_missing_requested_dev_worktree_blocks_dev_action():
    result = evaluate_runtime_worktree_guard(_state(requested_dev_worktree_exists=False))

    assert result["decision_state"] == "blocked"
    assert "requested_dev_worktree_missing" in result["blockers"]


def test_read_only_status_lane_reports_but_does_not_block_runtime_path():
    runtime = BASE_STATE["accepted_runtime_path"]

    result = evaluate_runtime_worktree_guard(
        _state(
            requested_action_class="read_only_status",
            candidate_worktree_path=runtime,
            candidate_git_top_level=runtime,
            accepted_runtime_branch="feature/accidental-runtime-branch",
        )
    )

    assert result["decision_state"] == "informational"
    assert result["would_block"] is False
    assert result["blockers"] == []
    assert "dev_worktree_is_live_runtime" in result["observed_risks"]
    assert "runtime_on_feature_branch" in result["observed_risks"]
    assert result["runtime_paths_allowed_for_action"] is True


def test_controlled_deploy_and_recovery_can_use_runtime_path_but_still_report_risks():
    runtime = BASE_STATE["accepted_runtime_path"]

    for action_class in ("controlled_deploy", "runtime_recovery"):
        result = evaluate_runtime_worktree_guard(
            _state(
                requested_action_class=action_class,
                candidate_worktree_path=runtime,
                candidate_git_top_level=runtime,
            )
        )

        assert result["decision_state"] == "informational"
        assert result["would_block"] is False
        assert "dev_worktree_is_live_runtime" in result["observed_risks"]
        assert result["runtime_paths_allowed_for_action"] is True


def test_evaluator_uses_no_runtime_surfaces(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime worktree guard touched a forbidden runtime surface")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    result = evaluate_runtime_worktree_guard(_state())

    assert result["decision_state"] == "pass"


def test_evaluator_source_has_no_filesystem_network_subprocess_or_record_store_calls():
    import mission_control.runtime_worktree_guard as guard

    source = inspect.getsource(guard)
    for forbidden in (
        "subprocess",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "JsonlRecordStore",
        "record_store_path",
        ".write(",
        "read_text",
        "write_text",
        "open(",
    ):
        assert forbidden not in source
