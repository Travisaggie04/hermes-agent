import builtins
import socket
import subprocess
from pathlib import Path

import pytest

from mission_control.records import StartGateCheck
from mission_control.records import store as records_store


def _lane_start_request(**overrides):
    payload = {
        "active_lane": "PR-O default-off lane-start preflight caller",
        "mode": "bounded implementation in a new clean worktree only",
        "allowed_actions": ("add default-off caller", "run targeted tests"),
        "forbidden_actions": ("no live enforcement", "no deploy", "no secrets"),
        "stop_condition": "Stop after draft PR.",
        "report_requirements": ("files changed", "tests run", "safety confirmation"),
        "repo_target": "Travisaggie04/hermes-agent",
        "branch": "pr-o-lane-start-preflight-caller-default-off",
        "worktree_state": "clean",
        "token_context_policy": "bounded records only",
        "requested_actions": ("add default-off caller", "run targeted tests"),
    }
    payload.update(overrides)
    return payload


def test_valid_lane_start_request_returns_dry_run_pass_result():
    from mission_control.lane_preflight import run_lane_start_preflight

    result = run_lane_start_preflight(_lane_start_request())

    assert result["default_off"] is True
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert result["would_block"] is False
    assert result["would_require_approval"] is False
    assert result["decision_state"] == "pass"
    assert result["reasons"] == []
    assert result["start_gate_check"]["decision_state"] == "pass"
    assert result["start_gate_check"]["branch_safety_state"] == "bounded"
    assert "metadata" not in result
    assert "metadata" not in result["start_gate_check"]


@pytest.mark.parametrize(
    ("field_name", "replacement", "reason_fragment"),
    (
        ("active_lane", "", "missing active lane"),
        ("mode", "", "missing mode"),
        ("allowed_actions", (), "missing allowed actions"),
        ("forbidden_actions", (), "missing forbidden actions"),
        ("stop_condition", "", "missing stop condition"),
        ("report_requirements", (), "missing report requirements"),
    ),
)
def test_missing_required_fields_are_reported_without_runtime_enforcement(field_name, replacement, reason_fragment):
    from mission_control.lane_preflight import run_lane_start_preflight

    result = run_lane_start_preflight(_lane_start_request(**{field_name: replacement}))

    assert result["default_off"] is True
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert result["would_block"] is True
    assert result["would_require_approval"] is False
    assert result["decision_state"] == "blocked"
    assert any(reason_fragment in reason for reason in result["reasons"])


@pytest.mark.parametrize(
    "requested_action",
    (
        "deploy Mission Control",
        "restart live Hermes",
        "merge the branch",
        "force-push the branch",
        "inspect secrets",
    ),
)
def test_dangerous_requested_actions_are_reported_as_approval_or_block_decisions(requested_action):
    from mission_control.lane_preflight import run_lane_start_preflight

    result = run_lane_start_preflight(_lane_start_request(requested_actions=(requested_action,)))

    assert result["enforces_runtime"] is False
    assert result["would_block"] or result["would_require_approval"]
    assert requested_action in result["blocked_actions"]


@pytest.mark.parametrize(
    ("repo_target", "expected_state"),
    (
        ("NousResearch/hermes-agent", "wrong_repo_or_remote"),
        ("origin and travis both possible", "repo_remote_ambiguous"),
        ("", "wrong_repo_or_remote"),
    ),
)
def test_wrong_repo_or_remote_states_are_reported(repo_target, expected_state):
    from mission_control.lane_preflight import run_lane_start_preflight

    result = run_lane_start_preflight(_lane_start_request(repo_target=repo_target))

    assert result["would_block"] is True
    assert result["start_gate_check"]["branch_safety_state"] == expected_state


@pytest.mark.parametrize("worktree_state", ("dirty", "quarantined", "dirty/quarantined"))
def test_dirty_or_quarantined_worktree_states_are_reported(worktree_state):
    from mission_control.lane_preflight import run_lane_start_preflight

    result = run_lane_start_preflight(_lane_start_request(worktree_state=worktree_state))

    assert result["would_block"] is True
    assert result["start_gate_check"]["dirty_worktree_state"] == worktree_state


def test_caller_preserves_start_gate_decision_state_and_reasons(monkeypatch):
    import mission_control.lane_preflight as lane_preflight

    def fake_adapter(request):
        assert request["active_lane"] == "PR-O default-off lane-start preflight caller"
        return StartGateCheck(
            start_gate_id="start-gate:test",
            envelope_id="lane-start:test",
            decision_state="needs_approval",
            reasons=("privileged action requires explicit approval",),
            blocked_actions=("push the branch",),
            required_approvals=("explicit approval for privileged action",),
            dirty_worktree_state="clean",
            branch_safety_state="bounded",
            secret_safety_state="no_secret_access_requested",
            token_context_state="bounded",
            metadata={"raw_scan": "do not expose"},
        )

    monkeypatch.setattr(lane_preflight, "evaluate_lane_start_preflight", fake_adapter)

    result = lane_preflight.run_lane_start_preflight(_lane_start_request())

    assert result["decision_state"] == "needs_approval"
    assert result["would_block"] is False
    assert result["would_require_approval"] is True
    assert result["reasons"] == ["privileged action requires explicit approval"]
    assert result["required_approvals"] == ["explicit approval for privileged action"]
    assert "raw_scan" not in str(result)


def test_caller_does_not_write_records_or_call_runtime_surfaces(monkeypatch):
    from mission_control.lane_preflight import run_lane_start_preflight

    def forbidden(*args, **kwargs):
        raise AssertionError("lane preflight caller touched a forbidden runtime surface")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(records_store.JsonlRecordStore, "append", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    result = run_lane_start_preflight(_lane_start_request())

    assert result["decision_state"] == "pass"
    assert result["dry_run_only"] is True
