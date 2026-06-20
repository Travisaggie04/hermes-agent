import builtins
import socket
import subprocess
from pathlib import Path

import pytest

from mission_control.records import StartGateCheck, TaskControlEnvelope
from mission_control.records import store as records_store


def _lane_start_request(**overrides):
    payload = {
        "active_lane": "PR-N default-off preflight integration design",
        "mode": "bounded implementation in a new clean worktree only",
        "allowed_actions": ("add inert preflight adapter", "run targeted tests"),
        "forbidden_actions": ("no live enforcement", "no deploy", "no secrets"),
        "stop_condition": "Stop after draft PR.",
        "report_requirements": ("files changed", "tests run", "safety confirmation"),
        "repo_target": "Travisaggie04/hermes-agent",
        "branch": "pr-n-start-gate-preflight-default-off",
        "worktree_state": "clean",
        "token_context_policy": "bounded records only",
        "requested_actions": ("add inert preflight adapter", "run targeted tests"),
    }
    payload.update(overrides)
    return payload


def test_valid_lane_start_request_passes_as_default_off_dry_run_preflight():
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request())

    assert isinstance(check, StartGateCheck)
    assert check.decision_state == "pass"
    assert check.branch_safety_state == "bounded"
    assert check.dirty_worktree_state == "clean"
    assert check.token_context_state == "bounded"
    assert check.metadata["default_off"] is True
    assert check.metadata["would_execute"] is False
    assert check.metadata["dry_run_only"] is True
    assert check.metadata["enforces_runtime"] is False
    assert check.metadata["adapter"] == "mission_control.preflight.lane_start.v1"


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
def test_missing_lane_control_fields_block(field_name, replacement, reason_fragment):
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request(**{field_name: replacement}))

    assert check.decision_state == "blocked"
    assert any(reason_fragment in reason for reason in check.reasons)


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
def test_dangerous_requested_actions_need_approval_or_block(requested_action):
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request(requested_actions=(requested_action,)))

    assert check.decision_state in {"needs_approval", "blocked"}
    assert requested_action in check.blocked_actions


@pytest.mark.parametrize(
    "repo_target",
    ("NousResearch/hermes-agent", "origin and travis both possible", ""),
)
def test_wrong_repo_or_remote_ambiguity_blocks_or_needs_approval(repo_target):
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request(repo_target=repo_target))

    assert check.decision_state in {"blocked", "needs_approval"}
    assert check.branch_safety_state in {"wrong_repo_or_remote", "repo_remote_ambiguous"}


@pytest.mark.parametrize("worktree_state", ("dirty", "quarantined", "dirty/quarantined"))
def test_dirty_or_quarantined_worktree_state_blocks(worktree_state):
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request(worktree_state=worktree_state))

    assert check.decision_state == "blocked"
    assert check.dirty_worktree_state == worktree_state


@pytest.mark.parametrize(
    "token_context_policy",
    ("unbounded", "dump all context", "full transcript without bounds"),
)
def test_unbounded_context_policy_blocks_or_needs_approval(token_context_policy):
    from mission_control.preflight import evaluate_lane_start_preflight

    check = evaluate_lane_start_preflight(_lane_start_request(token_context_policy=token_context_policy))

    assert check.decision_state in {"blocked", "needs_approval"}
    assert check.token_context_state == "unbounded"


def test_preflight_builds_task_control_envelope_and_calls_evaluator(monkeypatch):
    import mission_control.preflight as preflight

    captured = {}

    def fake_evaluator(envelope):
        captured["envelope"] = envelope
        return StartGateCheck(
            start_gate_id="start-gate:test",
            envelope_id=envelope.envelope_id,
            decision_state="pass",
            metadata={"default_off": True, "would_execute": False, "enforces_runtime": False},
        )

    monkeypatch.setattr(preflight, "evaluate_start_gate", fake_evaluator)

    check = preflight.evaluate_lane_start_preflight(_lane_start_request())

    envelope = captured["envelope"]
    assert isinstance(envelope, TaskControlEnvelope)
    assert envelope.active_lane == "PR-N default-off preflight integration design"
    assert envelope.current_repo == "Travisaggie04/hermes-agent"
    assert envelope.metadata["worktree_state"] == "clean"
    assert envelope.metadata["branch"] == "pr-n-start-gate-preflight-default-off"
    assert envelope.metadata["requested_actions"] == [
        "add inert preflight adapter",
        "run targeted tests",
    ]
    assert check.metadata["dry_run_only"] is True
    assert check.metadata["would_execute"] is False
    assert check.metadata["enforces_runtime"] is False


def test_adapter_does_not_write_records_or_call_runtime_surfaces(monkeypatch):
    from mission_control.preflight import evaluate_lane_start_preflight

    def forbidden(*args, **kwargs):
        raise AssertionError("preflight adapter touched a forbidden runtime surface")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(records_store.JsonlRecordStore, "append", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    check = evaluate_lane_start_preflight(_lane_start_request())

    assert check.decision_state == "pass"
    assert check.metadata["would_execute"] is False
    assert check.metadata["dry_run_only"] is True
