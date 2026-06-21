from mission_control.action_policy import POLICY_ID, evaluate_action_policy


def test_action_policy_allows_bounded_work_without_runtime_enforcement():
    report = evaluate_action_policy(("read approved context", "run targeted tests"))

    assert report.policy_id == POLICY_ID
    assert report.default_off is True
    assert report.would_execute is False
    assert report.enforces_runtime is False
    assert report.denied_actions == ()
    assert report.approval_actions == ()
    assert [decision.decision for decision in report.decisions] == ["allow", "allow"]
    assert [decision.lane_state for decision in report.decisions] == ["APPROVED_SAFE_LANE", "APPROVED_SAFE_LANE"]


def test_action_policy_denies_unbounded_context_and_parent_directory_access():
    report = evaluate_action_policy(
        (
            "dump all context and records without bounds",
            "scan parent directory /home/jenny",
        )
    )

    assert report.denied_actions == (
        "dump all context and records without bounds",
        "scan parent directory /home/jenny",
    )
    assert [decision.decision for decision in report.decisions] == ["deny", "deny"]
    assert {decision.lane_state for decision in report.decisions} == {"BLOCKED_DANGEROUS_LANE"}


def test_action_policy_asks_for_protected_actions():
    report = evaluate_action_policy(
        (
            "restart live Hermes gateway",
            "switch runtime",
            "deploy dashboard",
            "resume payment checkout",
            "run outreach",
            "post to Waha and social accounts",
            "start hidden worker timer",
            "inspect secrets and state.db",
            "dispatch session-send",
            "push branch",
        )
    )

    assert report.denied_actions == ()
    assert report.approval_actions == (
        "restart live Hermes gateway",
        "switch runtime",
        "deploy dashboard",
        "resume payment checkout",
        "run outreach",
        "post to Waha and social accounts",
        "start hidden worker timer",
        "inspect secrets and state.db",
        "dispatch session-send",
        "push branch",
    )
    assert {decision.decision for decision in report.decisions} == {"ask"}
    assert {decision.lane_state for decision in report.decisions} == {"APPROVAL_GATED_LANE"}
    assert report.required_approvals == ()
    assert report.approval_satisfied is False


def test_action_policy_preserves_explicit_approval_slices_without_enforcing_runtime():
    report = evaluate_action_policy(
        ("deploy dashboard",),
        approval_required=True,
        approval_slice_ids=("approval-dashboard-deploy",),
    )

    assert report.approval_actions == ("deploy dashboard",)
    assert report.required_approvals == ("approval-dashboard-deploy",)
    assert report.approval_satisfied is True
    assert report.would_execute is False
    assert report.enforces_runtime is False
