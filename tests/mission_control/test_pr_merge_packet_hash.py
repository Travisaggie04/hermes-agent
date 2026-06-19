"""Deterministic PR merge packet hash tests."""

from __future__ import annotations

import json
import re

import pytest

from mission_control.pr_merge_packet_hash import (
    canonical_pr_merge_packet_json,
    canonicalize_pr_merge_packet,
    compute_pr_merge_packet_hash,
    validate_pr_merge_packet_hash,
)


FULL_HEAD = "abcdef1234567890abcdef1234567890abcdef12"
FULL_BASE = "1234567890abcdef1234567890abcdef12345678"


def valid_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "repo": "Travisaggie04/hermes-agent",
        "pr_number": "#39",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": FULL_HEAD.upper(),
        "merge_method": "MERGE",
        "expected_base_head": FULL_BASE.upper(),
        "verifier_evidence_record_id": "evidence-39",
        "title": "  Add   deterministic   packet hashing  ",
        "operator_id": "  Jenny   Hermes  ",
    }
    packet.update(overrides)
    return packet


def test_canonicalization_normalizes_required_and_optional_fields():
    canonical = canonicalize_pr_merge_packet(
        valid_packet(
            repo="https://github.com/Travisaggie04/hermes-agent.git",
            pr_number=39,
            packet_version="",
            created_at=" 2026-06-08T07:30:00Z ",
        )
    )

    assert canonical == {
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "created_at": "2026-06-08T07:30:00Z",
        "expected_base_head": FULL_BASE,
        "head_commit": FULL_HEAD,
        "merge_method": "merge",
        "operator_id": "Jenny Hermes",
        "packet_version": "pr_merge_packet_v1",
        "pr_number": "39",
        "repo": "travisaggie04/hermes-agent",
        "title": "Add deterministic packet hashing",
        "verifier_evidence_record_id": "evidence-39",
    }


def test_canonical_json_is_stable_sorted_and_hash_format_is_sha256():
    first = valid_packet(repo="https://github.com/Travisaggie04/hermes-agent.git", pr_number=39)
    second = {
        "verifier_evidence_record_id": "evidence-39",
        "expected_base_head": FULL_BASE,
        "merge_method": "merge",
        "head_commit": FULL_HEAD,
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "pr_number": "#39",
        "repo": "travisaggie04/hermes-agent",
        "operator_id": "Jenny Hermes",
        "title": "Add deterministic packet hashing",
    }

    first_json = canonical_pr_merge_packet_json(first)
    second_json = canonical_pr_merge_packet_json(second)
    first_hash = compute_pr_merge_packet_hash(first)
    second_hash = compute_pr_merge_packet_hash(second)

    assert first_json == second_json
    assert json.loads(first_json)["packet_version"] == "pr_merge_packet_v1"
    assert first_json == json.dumps(json.loads(first_json), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert first_hash == second_hash
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", first_hash)


def test_allowlist_excludes_logs_paths_secrets_pr_body_comments_and_evidence_body():
    canonical_json = canonical_pr_merge_packet_json(
        valid_packet(
            raw_logs="token=secret-value and traceback text",
            transcript="secret transcript",
            pr_body="long pull request body",
            comments=["review comment"],
            service_status={"gateway": "active"},
            local_path="/home/jenny/.hermes/private/worktree",
            api_key="sk-test-secret",
            verifier_evidence={"raw": "must not be included"},
        )
    )
    lowered = canonical_json.lower()

    assert "raw_logs" not in canonical_json
    assert "transcript" not in canonical_json
    assert "pr_body" not in canonical_json
    assert "comments" not in canonical_json
    assert "service_status" not in canonical_json
    assert "local_path" not in canonical_json
    assert "api_key" not in canonical_json
    assert "verifier_evidence\":" not in canonical_json
    assert "verifier_evidence_record_id" in canonical_json
    assert "secret" not in lowered
    assert "/home/jenny" not in lowered
    assert "must not be included" not in lowered


@pytest.mark.parametrize(
    "field",
    [
        "repo",
        "pr_number",
        "base_branch",
        "head_commit",
        "merge_method",
        "expected_base_head",
        "verifier_evidence_record_id",
    ],
)
def test_validate_reports_missing_required_fields(field: str):
    packet = valid_packet()
    packet.pop(field)

    result = validate_pr_merge_packet_hash(packet, "sha256:" + "0" * 64)

    assert result["valid"] is False
    assert field in result["missing_fields"]
    assert result["computed_hash"] == ""
    assert result["canonical_json"] == ""
    assert result["would_execute"] is False
    assert result["dry_run_only"] is True
    assert result["enforces_runtime"] is False


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("head_commit", "abc123", "head_commit must be a full 40-character hex SHA"),
        ("expected_base_head", "xyz", "expected_base_head must be a full 40-character hex SHA"),
        ("merge_method", "octopus", "merge_method must be one of merge, squash, rebase"),
        ("pr_number", "abc", "pr_number must be a positive decimal integer"),
        ("repo", "not-a-repo", "repo must be owner/repo"),
    ],
)
def test_validate_reports_invalid_fields(field: str, value: str, reason: str):
    result = validate_pr_merge_packet_hash(
        valid_packet(**{field: value}),
        "sha256:" + "0" * 64,
    )

    assert result["valid"] is False
    assert field in result["invalid_fields"]
    assert reason in result["reasons"]
    assert result["computed_hash"] == ""


def test_validate_matching_hash_passes_and_mismatch_fails():
    packet = valid_packet()
    packet_hash = compute_pr_merge_packet_hash(packet)

    matching = validate_pr_merge_packet_hash(packet, packet_hash)
    mismatched = validate_pr_merge_packet_hash(packet, "sha256:" + "0" * 64)
    malformed = validate_pr_merge_packet_hash(packet, packet_hash.removeprefix("sha256:"))

    assert matching["valid"] is True
    assert matching["computed_hash"] == packet_hash
    assert matching["expected_hash"] == packet_hash
    assert matching["canonical_json"]
    assert matching["reasons"] == []
    assert matching["would_execute"] is False
    assert matching["dry_run_only"] is True
    assert matching["enforces_runtime"] is False

    assert mismatched["valid"] is False
    assert mismatched["computed_hash"] == packet_hash
    assert "packet_hash mismatch" in mismatched["reasons"]

    assert malformed["valid"] is False
    assert malformed["computed_hash"] == packet_hash
    assert "expected_hash must use sha256:<64 lowercase hex> format" in malformed["reasons"]


def test_bad_input_returns_invalid_not_exception():
    for value in (None, [], "not a packet", 123):
        result = validate_pr_merge_packet_hash(value, "sha256:" + "0" * 64)  # type: ignore[arg-type]
        assert result["valid"] is False
        assert result["computed_hash"] == ""
        assert result["canonical_json"] == ""
        assert result["would_execute"] is False
        assert result["reasons"]
