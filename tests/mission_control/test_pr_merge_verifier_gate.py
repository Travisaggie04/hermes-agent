"""Inert PR merge verifier gate v1 policy tests."""

from mission_control.pr_merge_verifier_gate import (
    PR_MERGE_VERIFIER_GATE_POLICY,
    evaluate_pr_merge_verifier_gate,
    get_pr_merge_verifier_gate_policy,
)


def _valid_state():
    return {
        "repo": "Travisaggie04/hermes-agent",
        "pr_number": "36",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "abc123",
        "packet_hash": "sha256:packet",
        "implementer_id": "jenny-implementer",
        "verifier_id": "jenny-verifier",
        "verifier_evidence_record_id": "evidence-1",
        "verifier_evidence": {
            "record_id": "evidence-1",
            "guard_type": "verifier_workflow",
            "action_class": "pr_merge",
            "repo": "Travisaggie04/hermes-agent",
            "pr_number": "36",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
            "head_commit": "abc123",
            "packet_hash": "sha256:packet",
            "implementer_id": "jenny-implementer",
            "verifier_id": "jenny-verifier",
            "would_block": False,
            "blocked_actions": [],
            "dry_run_only": True,
            "enforces_runtime": False,
        },
    }


def test_pr_merge_verifier_gate_policy_loads_as_inert_display_only_record():
    policy = get_pr_merge_verifier_gate_policy()

    assert policy == PR_MERGE_VERIFIER_GATE_POLICY
    assert policy is not PR_MERGE_VERIFIER_GATE_POLICY
    assert policy["gate_id"] == "pr_merge_verifier_gate_v1"
    assert policy["trusted_for_execution"] is False
    assert policy["inert_context_only"] is True
    assert policy["enforcement_enabled"] is False
    assert policy["dry_run_only"] is True
    assert policy["display_only"] is True
    assert "repo" in policy["required_fields"]
    assert "verifier_evidence_record_id" in policy["required_fields"]
    assert policy["future_enforcement_boundary"]["does_not_call_github"] is True
    assert policy["future_enforcement_boundary"]["does_not_merge_prs"] is True


def test_pr_merge_verifier_gate_policy_returns_display_copy_only():
    policy = get_pr_merge_verifier_gate_policy()
    policy["enforcement_enabled"] = True
    policy["future_enforcement_boundary"]["does_not_merge_prs"] = False

    assert PR_MERGE_VERIFIER_GATE_POLICY["enforcement_enabled"] is False
    assert PR_MERGE_VERIFIER_GATE_POLICY["future_enforcement_boundary"]["does_not_merge_prs"] is True


def test_valid_matching_verifier_evidence_allows_but_remains_dry_run_warning():
    result = evaluate_pr_merge_verifier_gate(_valid_state())

    assert result["decision_state"] == "warn"
    assert result["would_block"] is False
    assert result["blocked_actions"] == []
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_missing_verifier_evidence_would_block_pr_merge_packet_progression():
    state = _valid_state()
    state.pop("verifier_evidence")

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["decision_state"] == "would_block"
    assert result["would_block"] is True
    assert "missing verifier evidence" in result["reasons"]
    assert "proceed with PR merge packet" in result["blocked_actions"]
    assert "matching verifier evidence record" in result["required_approvals"]


def test_missing_packet_hash_would_block():
    state = _valid_state()
    state["packet_hash"] = ""

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "missing PR merge packet field: packet_hash" in result["reasons"]
    assert "verifier evidence packet_hash mismatch" in result["reasons"]


def test_packet_hash_mismatch_would_block():
    state = _valid_state()
    state["verifier_evidence"]["packet_hash"] = "sha256:different"

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier evidence packet_hash mismatch" in result["reasons"]


def test_pr_base_and_head_mismatch_would_block():
    state = _valid_state()
    state["verifier_evidence"]["pr_number"] = "35"
    state["verifier_evidence"]["base_branch"] = "main"
    state["verifier_evidence"]["head_commit"] = "def456"

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier evidence pr_number mismatch" in result["reasons"]
    assert "verifier evidence base_branch mismatch" in result["reasons"]
    assert "verifier evidence head_commit mismatch" in result["reasons"]


def test_self_verification_would_block():
    state = _valid_state()
    state["verifier_id"] = "Jenny-Implementer"
    state["verifier_evidence"]["verifier_id"] = "Jenny-Implementer"

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier_id cannot equal implementer_id" in result["reasons"]
    assert "accept self-verification for PR merge" in result["blocked_actions"]


def test_evidence_would_block_true_would_block():
    state = _valid_state()
    state["verifier_evidence"]["would_block"] = True

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier evidence would_block is true" in result["reasons"]


def test_merge_related_blocked_actions_would_block():
    state = _valid_state()
    state["verifier_evidence"]["blocked_actions"] = ["merge PR"]

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier evidence contains merge-related blocked action" in result["reasons"]


def test_evidence_runtime_flags_must_remain_dry_run_only():
    state = _valid_state()
    state["verifier_evidence"]["dry_run_only"] = False
    state["verifier_evidence"]["enforces_runtime"] = True

    result = evaluate_pr_merge_verifier_gate(state)

    assert result["would_block"] is True
    assert "verifier evidence dry_run_only is not true" in result["reasons"]
    assert "verifier evidence enforces_runtime is not false" in result["reasons"]
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_pr_merge_gate_uses_caller_supplied_state_only(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live inspection or mutation is forbidden")

    monkeypatch.setattr("builtins.open", fail_if_called)

    result = evaluate_pr_merge_verifier_gate(_valid_state())

    assert result["would_block"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_pr_merge_gate_unknown_without_observed_state():
    result = evaluate_pr_merge_verifier_gate({})

    assert result["decision_state"] == "unknown"
    assert result["would_block"] is False
    assert "caller-supplied PR merge packet state is incomplete" in result["reasons"]
