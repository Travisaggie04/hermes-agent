"""Deterministic PR merge packet hashing helpers.

This module is intentionally pure and caller-supplied-state only. It does not
inspect GitHub, local git state, files, processes, services, queues, databases,
or runtime state, and it never performs or automates a merge.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from mission_control.inert_contract import inert_live_operation_flags

PACKET_VERSION = "pr_merge_packet_v1"
HASH_PREFIX = "sha256:"
ALLOWED_MERGE_METHODS = {"merge", "squash", "rebase"}
REQUIRED_FIELDS = (
    "repo",
    "pr_number",
    "base_branch",
    "head_commit",
    "merge_method",
    "expected_base_head",
    "verifier_evidence_record_id",
)
OPTIONAL_FIELDS = (
    "title",
    "packet_version",
    "created_at",
    "operator_id",
)
_HEX_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_WHITESPACE_RE = re.compile(r"\s+")
_INERT_PACKET_HASH_FLAGS = inert_live_operation_flags(
    dry_run_only=True,
    enforces_runtime=False,
)


def _empty_validation(expected_hash: Any) -> dict[str, Any]:
    return {
        **_INERT_PACKET_HASH_FLAGS,
        "valid": False,
        "computed_hash": "",
        "expected_hash": str(expected_hash or "").strip(),
        "canonical_json": "",
        "reasons": [],
        "missing_fields": [],
        "invalid_fields": [],
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _collapse_text(value: Any) -> str:
    return _WHITESPACE_RE.sub(" ", _text(value))


def _normalize_repo(value: Any) -> str:
    text = _text(value)
    if text.startswith("https://github.com/"):
        text = text.removeprefix("https://github.com/")
    elif text.startswith("http://github.com/"):
        text = text.removeprefix("http://github.com/")
    if text.endswith(".git"):
        text = text.removesuffix(".git")
    return text.strip("/").lower()


def _normalize_pr_number(value: Any) -> str:
    text = _text(value)
    if text.startswith("#"):
        text = text[1:]
    if not text.isdecimal():
        return text
    return str(int(text))


def _normalize_sha(value: Any) -> str:
    return _text(value).lower()


def _normalize_merge_method(value: Any) -> str:
    return _text(value).lower()


def _canonical_fields(packet: dict[str, Any]) -> dict[str, str]:
    canonical = {
        "repo": _normalize_repo(packet.get("repo")),
        "pr_number": _normalize_pr_number(packet.get("pr_number")),
        "base_branch": _text(packet.get("base_branch")),
        "head_commit": _normalize_sha(packet.get("head_commit")),
        "merge_method": _normalize_merge_method(packet.get("merge_method")),
        "expected_base_head": _normalize_sha(packet.get("expected_base_head")),
        "verifier_evidence_record_id": _text(packet.get("verifier_evidence_record_id")),
        "packet_version": _text(packet.get("packet_version")) or PACKET_VERSION,
    }
    title = _collapse_text(packet.get("title"))
    if title:
        canonical["title"] = title
    created_at = _text(packet.get("created_at"))
    if created_at:
        canonical["created_at"] = created_at
    operator_id = _collapse_text(packet.get("operator_id"))
    if operator_id:
        canonical["operator_id"] = operator_id
    return canonical


def _validation_errors(packet: Any) -> tuple[list[str], list[str], list[str], dict[str, str]]:
    reasons: list[str] = []
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    if not isinstance(packet, dict):
        return ["packet must be an object"], list(REQUIRED_FIELDS), [], {}

    canonical = _canonical_fields(packet)
    for field in REQUIRED_FIELDS:
        if not _text(packet.get(field)):
            missing_fields.append(field)
            reasons.append(f"missing required field: {field}")

    repo = canonical.get("repo", "")
    if repo and (repo.count("/") != 1 or any(not part for part in repo.split("/"))):
        invalid_fields.append("repo")
        reasons.append("repo must be owner/repo")

    pr_number = canonical.get("pr_number", "")
    if pr_number and (not pr_number.isdecimal() or int(pr_number) <= 0):
        invalid_fields.append("pr_number")
        reasons.append("pr_number must be a positive decimal integer")

    merge_method = canonical.get("merge_method", "")
    if merge_method and merge_method not in ALLOWED_MERGE_METHODS:
        invalid_fields.append("merge_method")
        reasons.append("merge_method must be one of merge, squash, rebase")

    for field in ("head_commit", "expected_base_head"):
        value = canonical.get(field, "")
        if value and not _HEX_SHA_RE.fullmatch(value):
            invalid_fields.append(field)
            reasons.append(f"{field} must be a full 40-character hex SHA")

    return reasons, missing_fields, invalid_fields, canonical


def canonicalize_pr_merge_packet(packet: dict[str, Any]) -> dict[str, str]:
    """Return the allowlisted, normalized PR merge packet for hashing."""

    reasons, missing_fields, invalid_fields, canonical = _validation_errors(packet)
    if reasons or missing_fields or invalid_fields:
        message = "; ".join(reasons or ["invalid PR merge packet"])
        raise ValueError(message)
    return dict(sorted(canonical.items()))


def canonical_pr_merge_packet_json(packet: dict[str, Any]) -> str:
    """Return stable canonical JSON for a valid PR merge packet."""

    canonical = canonicalize_pr_merge_packet(packet)
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_pr_merge_packet_hash(packet: dict[str, Any]) -> str:
    """Return ``sha256:<hex>`` over the packet's canonical JSON."""

    canonical_json = canonical_pr_merge_packet_json(packet)
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"{HASH_PREFIX}{digest}"


def validate_pr_merge_packet_hash(packet: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    """Validate a caller-supplied packet against an expected canonical hash.

    Ordinary bad input returns ``valid=False`` with compact reasons instead of
    raising. The helper remains dry-run only and never inspects or mutates live
    state.
    """

    result = _empty_validation(expected_hash)
    reasons, missing_fields, invalid_fields, canonical = _validation_errors(packet)
    result["reasons"] = reasons
    result["missing_fields"] = missing_fields
    result["invalid_fields"] = invalid_fields

    if reasons or missing_fields or invalid_fields:
        return result

    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    computed_hash = f"{HASH_PREFIX}{hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()}"
    result["computed_hash"] = computed_hash
    result["canonical_json"] = canonical_json

    expected = _text(expected_hash)
    result["expected_hash"] = expected
    if not _HASH_RE.fullmatch(expected):
        result["reasons"] = ["expected_hash must use sha256:<64 lowercase hex> format"]
        return result

    if computed_hash != expected:
        result["reasons"] = ["packet_hash mismatch"]
        return result

    result["valid"] = True
    result["reasons"] = []
    return result
