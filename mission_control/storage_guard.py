"""Inert Storage Guard policy records.

This module is intentionally dry-run only. It defines future storage and
artifact governance policy plus a caller-supplied-state evaluator without
inspecting live disks, filesystems, cloud remotes, databases, services,
credentials, environment variables, or runtime state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INERT_STORAGE_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

STORAGE_GUARD_POLICY: dict[str, Any] = {
    "guard_id": "storage_guard_v1",
    **_INERT_STORAGE_FLAGS,
    "disk_thresholds": {
        "disk_warning_threshold_percent": "placeholder",
        "disk_block_threshold_percent": "placeholder",
        "minimum_free_gib_placeholder": "placeholder",
        "per_project_local_budget_gib_placeholder": "placeholder",
    },
    "artifact_manifest_rules": {
        "artifact_manifest_required_before_done": True,
        "artifact_manifest_required_for_video_work": True,
        "artifact_manifest_required_for_archive_work": True,
        "artifact_manifest_required_for_cleanup_work": True,
    },
    "storage_delta_rules": {
        "storage_delta_required_before_done": True,
        "before_after_disk_usage_required": True,
        "large_file_delta_required": True,
    },
    "archive_delete_rules": {
        "archive_verification_required_before_delete": True,
        "cloud_destination_required_before_large_delete": True,
        "checksum_or_count_verification_required": True,
        "delete_requires_explicit_lane": True,
        "delete_forbidden_without_manifest": True,
    },
    "cloud_archive_policy": {
        "allowed_archive_targets_placeholder": (
            "littleton-google-drive",
            "future-one-drive-primary",
        ),
        "cloud_upload_requires_explicit_approval": True,
        "no_cloud_upload_in_dry_run": True,
    },
    "local_artifact_policy": {
        "local_large_artifact_threshold_placeholder": "placeholder",
        "raw_intermediate_retention_policy_placeholder": "placeholder",
        "review_package_retention_policy_placeholder": "placeholder",
        "codex_log_retention_policy_placeholder": "placeholder",
        "cache_cleanup_policy_placeholder": "placeholder",
    },
    "project_specific_posture": {
        "signal_room_video_requires_artifact_manifest_and_archive_plan": True,
        "waha_external_archive_upload_requires_explicit_approval": True,
        "tool_tally_production_evidence_must_preserve_audit_artifacts": True,
        "generic_coding_prs_report_storage_delta_when_artifacts_generated": True,
    },
    "unresolved_policy_fields": (
        "disk_warning_threshold_percent",
        "disk_block_threshold_percent",
        "minimum_free_gib_placeholder",
        "per_project_local_budget_gib_placeholder",
        "local_large_artifact_threshold_placeholder",
        "raw_intermediate_retention_policy_placeholder",
        "review_package_retention_policy_placeholder",
        "codex_log_retention_policy_placeholder",
        "cache_cleanup_policy_placeholder",
        "future_enforcement_wiring",
        "approved_archive_targets",
    ),
}

_OBSERVED_STORAGE_FIELDS = {
    "task_marked_done",
    "artifact_manifest_required",
    "artifact_manifest_present",
    "artifact_heavy_lane",
    "video_generation_requested",
    "archive_work_requested",
    "cleanup_requested",
    "delete_requested",
    "archive_verification_present",
    "cloud_destination_supplied",
    "checksum_or_count_verification_present",
    "explicit_delete_lane",
    "cloud_upload_requested",
    "cloud_upload_explicitly_approved",
    "large_artifact_created",
    "storage_delta_present",
    "before_after_disk_usage_present",
    "large_file_delta_present",
    "disk_used_percent",
    "disk_warning_threshold_percent",
    "disk_block_threshold_percent",
    "project_domain",
    "external_archive_or_upload_requested",
    "waha_external_upload_approved",
    "archive_plan_present",
    "production_evidence_delete_requested",
    "audit_artifact_preservation_confirmed",
}


def get_storage_guard_policy() -> dict[str, Any]:
    """Return a display copy of the inert Storage Guard policy."""

    return deepcopy(STORAGE_GUARD_POLICY)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _as_bool(value: Any) -> bool:
    return value is True


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_storage_guard(observed_state: dict[str, Any] | None) -> dict[str, Any]:
    """Dry-run evaluate caller-supplied storage/artifact state.

    The evaluator is deliberately pure: it only reads the provided dictionary and
    returns a dry-run decision. It does not inspect live filesystems, disks,
    cloud remotes, DBs, services, providers, credentials, or environment values.
    """

    policy = STORAGE_GUARD_POLICY
    state = dict(observed_state or {})
    reasons: list[str] = []
    blocked_actions: list[str] = []
    required_approvals: list[str] = []

    observed_keys = set(state) & _OBSERVED_STORAGE_FIELDS
    if not observed_keys:
        reasons.append("caller-supplied observed storage state is incomplete")
        decision_state = "unknown"
    else:
        decision_state = "pass"

    artifact_manifest_required = _as_bool(state.get("artifact_manifest_required")) or any(
        _as_bool(state.get(key))
        for key in (
            "task_marked_done",
            "artifact_heavy_lane",
            "video_generation_requested",
            "archive_work_requested",
            "cleanup_requested",
            "delete_requested",
        )
    )
    manifest_present = _as_bool(state.get("artifact_manifest_present"))

    if _as_bool(state.get("task_marked_done")) and artifact_manifest_required and not manifest_present:
        _add_unique(reasons, "task marked done without required artifact manifest")
        _add_unique(blocked_actions, "mark task done")

    if (_as_bool(state.get("cleanup_requested")) or _as_bool(state.get("delete_requested"))) and not manifest_present:
        _add_unique(reasons, "cleanup/delete requested without artifact manifest")
        _add_unique(blocked_actions, "cleanup/delete artifacts")

    if _as_bool(state.get("delete_requested")):
        if not _as_bool(state.get("archive_verification_present")):
            _add_unique(reasons, "delete requested without archive verification")
            _add_unique(blocked_actions, "delete artifacts")
        if not _as_bool(state.get("explicit_delete_lane")):
            _add_unique(reasons, "delete requested without explicit delete lane")
            _add_unique(blocked_actions, "delete artifacts")
        if not _as_bool(state.get("checksum_or_count_verification_present")):
            _add_unique(reasons, "delete requested without checksum/count verification")
            _add_unique(blocked_actions, "delete artifacts")

    if _as_bool(state.get("cloud_upload_requested")):
        _add_unique(reasons, "cloud upload requested during dry-run")
        _add_unique(blocked_actions, "upload artifacts to cloud")
        if not _as_bool(state.get("cloud_upload_explicitly_approved")):
            _add_unique(reasons, "cloud upload lacks explicit approval")
            _add_unique(required_approvals, "explicit cloud upload approval")
        if not _as_bool(state.get("cloud_destination_supplied")):
            _add_unique(reasons, "cloud upload lacks supplied destination")

    if _as_bool(state.get("large_artifact_created")):
        if not _as_bool(state.get("storage_delta_present")):
            _add_unique(reasons, "large artifact created without storage delta")
            _add_unique(blocked_actions, "complete artifact-heavy task")
        if not _as_bool(state.get("before_after_disk_usage_present")):
            _add_unique(reasons, "before/after disk usage is missing")
            _add_unique(blocked_actions, "complete artifact-heavy task")
        if not _as_bool(state.get("large_file_delta_present")):
            _add_unique(reasons, "large file delta is missing")
            _add_unique(blocked_actions, "complete artifact-heavy task")

    disk_used = _as_float(state.get("disk_used_percent"))
    block_threshold = _as_float(state.get("disk_block_threshold_percent"))
    warning_threshold = _as_float(state.get("disk_warning_threshold_percent"))
    if disk_used is not None and block_threshold is not None and disk_used >= block_threshold:
        _add_unique(reasons, "observed disk usage is at or above supplied block threshold")
        _add_unique(blocked_actions, "start artifact-heavy work")
    elif disk_used is not None and warning_threshold is not None and disk_used >= warning_threshold:
        _add_unique(reasons, "observed disk usage is at or above supplied warning threshold")

    project_domain = str(state.get("project_domain") or "").lower()
    if project_domain in {"waha", "wahainspection"} and _as_bool(state.get("external_archive_or_upload_requested")):
        if not _as_bool(state.get("waha_external_upload_approved")):
            _add_unique(reasons, "Waha external archive/upload lacks explicit approval")
            _add_unique(blocked_actions, "external archive/upload for Waha")
            _add_unique(required_approvals, "explicit Waha external archive/upload approval")

    is_signal_video = project_domain in {"signal_room", "signal-room", "video"} or _as_bool(state.get("video_generation_requested"))
    if is_signal_video and _as_bool(state.get("artifact_heavy_lane")):
        if not manifest_present:
            _add_unique(reasons, "Signal Room/video work lacks artifact manifest")
            _add_unique(blocked_actions, "start Signal Room/video artifact-heavy work")
        if not _as_bool(state.get("archive_plan_present")):
            _add_unique(reasons, "Signal Room/video work lacks archive plan")
            _add_unique(blocked_actions, "start Signal Room/video artifact-heavy work")

    if project_domain in {"tool_tally", "tool&tally", "tool-and-tally"} and _as_bool(state.get("production_evidence_delete_requested")):
        if not _as_bool(state.get("audit_artifact_preservation_confirmed")):
            _add_unique(reasons, "Tool & Tally production evidence deletion lacks preservation confirmation")
            _add_unique(blocked_actions, "delete Tool & Tally production evidence")
            _add_unique(required_approvals, "Tool & Tally audit preservation approval")

    if _as_bool(state.get("artifact_heavy_lane")):
        known_storage_state = any(
            key in state
            for key in (
                "artifact_manifest_present",
                "storage_delta_present",
                "before_after_disk_usage_present",
                "disk_used_percent",
                "archive_plan_present",
            )
        )
        if not known_storage_state and not blocked_actions:
            _add_unique(reasons, "artifact-heavy lane has unknown storage state")
            decision_state = "unknown"

    would_block = bool(blocked_actions)
    if would_block:
        decision_state = "would_block"
    elif decision_state != "unknown" and policy.get("unresolved_policy_fields"):
        decision_state = "warn"

    return {
        "decision_state": decision_state,
        "would_block": would_block,
        "reasons": reasons,
        "blocked_actions": blocked_actions,
        "required_approvals": required_approvals,
        "unresolved_policy_fields": list(policy["unresolved_policy_fields"]),
        "dry_run_only": True,
        "enforces_runtime": False,
    }
