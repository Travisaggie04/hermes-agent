import pytest

from mission_control.action_policy import POLICY_ID
from mission_control.records import StartGateCheck, TaskControlEnvelope
from mission_control.start_gate import evaluate_start_gate


def _bounded_envelope(**overrides):
    payload = {
        "envelope_id": "envelope-pr-k",
        "active_lane": "PR-K default-off Start Gate enforcement design spike",
        "mode": "bounded implementation in a new clean worktree only",
        "allowed_actions": ("add inert evaluator", "run targeted tests"),
        "forbidden_actions": ("no live enforcement", "no deploy", "no secrets"),
        "current_repo": "Travisaggie04/hermes-agent",
        "stop_condition": "Stop after draft PR.",
        "report_requirements": ("files changed", "tests run", "safety confirmation"),
        "token_context_policy": "bounded records only",
        "metadata": {
            "target_remote": "Travisaggie04/hermes-agent",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        },
    }
    payload.update(overrides)
    return TaskControlEnvelope(**payload)


def test_valid_bounded_envelope_passes_default_off_and_inert():
    check = evaluate_start_gate(_bounded_envelope())

    assert isinstance(check, StartGateCheck)
    assert check.decision_state == "pass"
    assert check.envelope_id == "envelope-pr-k"
    assert check.blocked_actions == ()
    assert check.required_approvals == ()
    assert check.dirty_worktree_state == "clean"
    assert check.branch_safety_state == "bounded"
    assert check.secret_safety_state == "no_secret_access_requested"
    assert check.token_context_state == "bounded"
    assert check.created_at == ""
    assert check.metadata["default_off"] is True
    assert check.metadata["inert"] is True
    assert check.metadata["would_execute"] is False
    assert check.metadata["enforces_runtime"] is False
    assert check.metadata["action_policy"] == POLICY_ID


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
def test_required_envelope_fields_block(field_name, replacement, reason_fragment):
    check = evaluate_start_gate(_bounded_envelope(**{field_name: replacement}))

    assert check.decision_state == "blocked"
    assert any(reason_fragment in reason for reason in check.reasons)


@pytest.mark.parametrize(
    "requested_action",
    (
        "deploy Mission Control",
        "restart live Hermes",
        "merge the branch",
        "force-push the branch",
        "delete stale worktrees",
        "clean the worktree",
        "reset --hard",
        "stash dirty files",
        "inspect secrets",
    ),
)
def test_dangerous_actions_need_approval_when_requested(requested_action):
    check = evaluate_start_gate(_bounded_envelope(allowed_actions=(requested_action,)))

    assert check.decision_state == "needs_approval"
    assert requested_action in check.blocked_actions
    assert check.required_approvals == ("explicit approval for privileged action",)


@pytest.mark.parametrize(
    "requested_action",
    (
        "scan parent directory /home/jenny",
        "load the full transcript dump",
        "dump all context and records without bounds",
        "retrieve unbounded records context",
    ),
)
def test_context_and_parent_directory_requests_block(requested_action):
    check = evaluate_start_gate(_bounded_envelope(allowed_actions=(requested_action,)))

    assert check.decision_state == "blocked"
    assert requested_action in check.blocked_actions


@pytest.mark.parametrize(
    "overrides",
    (
        {"current_repo": ""},
        {"current_repo": "NousResearch/hermes-agent"},
        {"metadata": {"target_remote": "NousResearch/hermes-agent"}},
        {"metadata": {"repo_remote": "origin and travis both possible"}},
    ),
)
def test_wrong_or_ambiguous_repo_remote_blocks(overrides):
    check = evaluate_start_gate(_bounded_envelope(**overrides))

    assert check.decision_state == "blocked"
    assert check.branch_safety_state in {"wrong_repo_or_remote", "repo_remote_ambiguous"}


@pytest.mark.parametrize("dirty_state", ("dirty", "quarantined", "dirty/quarantined"))
def test_dirty_or_quarantined_worktree_blocks(dirty_state):
    check = evaluate_start_gate(_bounded_envelope(metadata={"worktree_state": dirty_state}))

    assert check.decision_state == "blocked"
    assert check.dirty_worktree_state == dirty_state


def test_explicit_approval_can_pass_privileged_action_as_informational_only():
    check = evaluate_start_gate(
        _bounded_envelope(
            allowed_actions=("push the narrow PR branch",),
            approval_required=True,
            approval_slice_ids=("approval-pr-k-push",),
        )
    )

    assert check.decision_state == "informational"
    assert check.blocked_actions == ()
    assert check.required_approvals == ("approval-pr-k-push",)
    assert check.metadata["would_execute"] is False
    assert check.metadata["enforces_runtime"] is False
