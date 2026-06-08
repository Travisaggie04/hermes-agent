"""Default-off PR merge lane guard tests."""

from hermes_cli.config import DEFAULT_CONFIG
from mission_control.pr_merge_lane_guard import (
    CONFIG_FLAG,
    evaluate_pr_merge_lane_guard,
    pr_merge_verifier_gate_enabled,
)


def _enabled_config(enabled: bool = True):
    return {
        "mission_control": {
            "enforcement": {
                "pr_merge_verifier_gate_enabled": enabled,
            },
        },
    }


def _valid_packet():
    return {
        "repo": "Travisaggie04/hermes-agent",
        "pr_number": "37",
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
            "pr_number": "37",
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


def test_config_default_false_is_present():
    assert DEFAULT_CONFIG["mission_control"]["enforcement"][CONFIG_FLAG] is False
    assert pr_merge_verifier_gate_enabled(DEFAULT_CONFIG) is False


def test_missing_or_false_config_is_advisory_only_and_never_stops():
    result = evaluate_pr_merge_lane_guard(None, {"repo": "Travisaggie04/hermes-agent"})

    assert result["enabled"] is False
    assert result["advisory_only"] is True
    assert result["would_block"] is True
    assert result["stop_merge_lane"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
    assert "PR merge verifier gate is default-off; advisory only" in result["reasons"]

    explicit_false = evaluate_pr_merge_lane_guard(_enabled_config(False), {"repo": "Travisaggie04/hermes-agent"})
    assert explicit_false["enabled"] is False
    assert explicit_false["stop_merge_lane"] is False


def test_enabled_valid_packet_allows_merge_lane_but_does_not_execute():
    result = evaluate_pr_merge_lane_guard(_enabled_config(True), _valid_packet())

    assert result["enabled"] is True
    assert result["advisory_only"] is False
    assert result["would_block"] is False
    assert result["stop_merge_lane"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_enabled_missing_evidence_stops_merge_lane():
    packet = _valid_packet()
    packet.pop("verifier_evidence")

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), packet)

    assert result["would_block"] is True
    assert result["stop_merge_lane"] is True
    assert "missing verifier evidence" in result["reasons"]


def test_enabled_hash_mismatch_stops_merge_lane():
    packet = _valid_packet()
    packet["verifier_evidence"]["packet_hash"] = "sha256:different"

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), packet)

    assert result["stop_merge_lane"] is True
    assert "verifier evidence packet_hash mismatch" in result["reasons"]


def test_enabled_repo_pr_base_and_head_mismatch_stop_merge_lane():
    packet = _valid_packet()
    packet["verifier_evidence"]["repo"] = "Other/repo"
    packet["verifier_evidence"]["pr_number"] = "36"
    packet["verifier_evidence"]["base_branch"] = "main"
    packet["verifier_evidence"]["head_commit"] = "def456"

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), packet)

    assert result["stop_merge_lane"] is True
    assert "verifier evidence repo mismatch" in result["reasons"]
    assert "verifier evidence pr_number mismatch" in result["reasons"]
    assert "verifier evidence base_branch mismatch" in result["reasons"]
    assert "verifier evidence head_commit mismatch" in result["reasons"]


def test_enabled_self_verification_stops_merge_lane():
    packet = _valid_packet()
    packet["verifier_id"] = "Jenny-Implementer"
    packet["verifier_evidence"]["verifier_id"] = "Jenny-Implementer"

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), packet)

    assert result["stop_merge_lane"] is True
    assert "verifier_id cannot equal implementer_id" in result["reasons"]


def test_enabled_bad_evidence_state_stops_merge_lane():
    packet = _valid_packet()
    packet["verifier_evidence"].update(
        {
            "would_block": True,
            "blocked_actions": ["merge PR"],
            "dry_run_only": False,
            "enforces_runtime": True,
        }
    )

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), packet)

    assert result["stop_merge_lane"] is True
    assert "verifier evidence would_block is true" in result["reasons"]
    assert "verifier evidence contains merge-related blocked action" in result["reasons"]
    assert "verifier evidence dry_run_only is not true" in result["reasons"]
    assert "verifier evidence enforces_runtime is not false" in result["reasons"]
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


def test_guard_uses_caller_supplied_state_only(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("live inspection or mutation is forbidden")

    monkeypatch.setattr("builtins.open", fail_if_called)

    result = evaluate_pr_merge_lane_guard(_enabled_config(True), _valid_packet())

    assert result["stop_merge_lane"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False
