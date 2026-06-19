"""PR merge approval binding record tests."""

from __future__ import annotations

from mission_control.pr_merge_packet_hash import compute_pr_merge_packet_hash
from mission_control.records import JsonlRecordStore, PrMergeApprovalRecord
from mission_control.records.models import approval_matches_pr_merge_packet


VALID_IDENTITY = {
    "repo": "https://github.com/Travisaggie04/Hermes-Agent.git",
    "pr_number": "#42",
    "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
    "head_commit": "ABCDEF1234567890ABCDEF1234567890ABCDEF12",
    "expected_base_head": "1234567890ABCDEF1234567890ABCDEF12345678",
    "merge_method": "SQUASH",
}


def valid_packet(record_id: str = "approval-42") -> dict[str, str]:
    return {
        **VALID_IDENTITY,
        "verifier_evidence_record_id": record_id,
    }


def valid_hash(record_id: str = "approval-42") -> str:
    return compute_pr_merge_packet_hash(valid_packet(record_id))


def make_record(**overrides):
    data = {
        "approval_id": "approval-42",
        "created_at": "2026-06-08T16:00:00Z",
        "expires_at": "2026-06-09T16:00:00Z",
        "action_class": "pr_merge",
        "packet_hash": valid_hash(),
        "packet_version": "pr_merge_packet_v1",
        "operator_id": " Travis  ",
        "approved_scope": "merge_pr_only",
        **VALID_IDENTITY,
        "consumed": True,
        "dry_run_only": False,
        "enforces_runtime": True,
        "raw_log": "do not store",
        "transcript": "do not store",
        "comments": "do not store",
        "pr_body": "do not store",
        "local_path": "/home/jenny/private",
        "token": "secret-token",
        "api_key": "secret-key",
        "canonical_packet_json": "{}",
        "github_response": {"raw": "do not store"},
        "service_status": {"gateway": "active"},
        "full_observed_state": {"too": "much"},
        "would_execute": True,
    }
    data.update(overrides)
    return PrMergeApprovalRecord.from_dict(data)


def test_pr_merge_approval_record_stores_bounded_packet_binding_fields_only():
    payload = make_record().to_dict()

    assert payload == {
        "approval_id": "approval-42",
        "created_at": "2026-06-08T16:00:00Z",
        "expires_at": "2026-06-09T16:00:00Z",
        "action_class": "pr_merge",
        "packet_hash": valid_hash(),
        "packet_version": "pr_merge_packet_v1",
        "repo": "travisaggie04/hermes-agent",
        "pr_number": "42",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "abcdef1234567890abcdef1234567890abcdef12",
        "expected_base_head": "1234567890abcdef1234567890abcdef12345678",
        "merge_method": "squash",
        "operator_id": "Travis",
        "approved_scope": "merge_pr_only",
        "consumed": False,
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }
    for forbidden in (
        "raw_log",
        "transcript",
        "comments",
        "pr_body",
        "local_path",
        "token",
        "api_key",
        "canonical_packet_json",
        "github_response",
        "service_status",
        "full_observed_state",
        "metadata",
    ):
        assert forbidden not in payload


def test_pr_merge_approval_record_omits_invalid_hash_version_action_sha_method_scope():
    payload = make_record(
        action_class="deploy_runtime",
        packet_hash="sha256:not-valid",
        packet_version="bad-version",
        repo="not-a-valid-repo-name",
        pr_number="not-decimal",
        head_commit="short",
        expected_base_head="also-short",
        merge_method="octopus",
        approved_scope="all_actions",
    ).to_dict()

    assert payload == {
        "approval_id": "approval-42",
        "created_at": "2026-06-08T16:00:00Z",
        "expires_at": "2026-06-09T16:00:00Z",
        "operator_id": "Travis",
        "consumed": False,
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }


def test_pr_merge_approval_record_round_trips_through_append_only_jsonl_store(tmp_path):
    store = JsonlRecordStore(tmp_path / "records.jsonl")
    first = make_record(approval_id="approval-42")
    second = make_record(approval_id="approval-43", pr_number=43)

    assert store.append(first) == 1
    assert store.append(second) == 2

    records = store.read_all(PrMergeApprovalRecord)
    assert [record.approval_id for record in records] == ["approval-42", "approval-43"]
    assert records[0].to_dict()["packet_hash"] == valid_hash()
    assert records[1].to_dict()["pr_number"] == "43"
    assert records[0].to_dict()["consumed"] is False
    assert records[1].to_dict()["consumed"] is False


def test_approval_matches_pr_merge_packet_requires_exact_hash_identity_and_action_class():
    approval = make_record().to_dict()
    packet = {
        **valid_packet(),
        "packet_hash": valid_hash(),
        "packet_version": "pr_merge_packet_v1",
        "action_class": "pr_merge",
    }

    result = approval_matches_pr_merge_packet(approval, packet)

    assert result == {
        "valid": True,
        "matches_packet": True,
        "reasons": [],
        "missing_fields": [],
        "invalid_fields": [],
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }

    mismatch = approval_matches_pr_merge_packet(approval, {**packet, "packet_hash": "sha256:" + "0" * 64})
    assert mismatch["valid"] is False
    assert mismatch["matches_packet"] is False
    assert "packet_hash mismatch" in mismatch["reasons"]

    wrong_action = approval_matches_pr_merge_packet(approval, {**packet, "action_class": "deploy_runtime"})
    assert wrong_action["valid"] is False
    assert wrong_action["matches_packet"] is False
    assert "action_class mismatch" in wrong_action["reasons"]


def test_approval_expiry_uses_caller_supplied_now_only():
    approval = make_record(expires_at="2026-06-09T16:00:00Z").to_dict()
    packet = {
        **valid_packet(),
        "packet_hash": valid_hash(),
        "packet_version": "pr_merge_packet_v1",
        "action_class": "pr_merge",
    }

    before_expiry = approval_matches_pr_merge_packet(approval, packet, now="2026-06-09T15:59:59Z")
    after_expiry = approval_matches_pr_merge_packet(approval, packet, now="2026-06-09T16:00:01Z")

    assert before_expiry["valid"] is True
    assert after_expiry["valid"] is False
    assert "approval expired" in after_expiry["reasons"]
