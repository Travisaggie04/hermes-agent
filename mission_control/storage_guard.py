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
    "would_execute": False,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

STORAGE_GUARD_POLICY: dict[str, Any] = {
    "guard_id": "storage_guard_v1",
    **_INERT_STORAGE_FLAGS,
    "disk_thresholds": {
        "lean_target_percent": 50,
        "disk_warning_threshold_percent": 65,
        "disk_block_threshold_percent": 80,
        "disk_critical_threshold_percent": 90,
        "minimum_free_gib": 100,
        "per_project_local_budget_gib": 25,
    },
    "lean_runtime_retention_policy": {
        "keep_current_live_runtime": True,
        "keep_rollback_runtimes": 2,
        "keep_active_review_worktrees": True,
        "keep_accepted_live_repo": True,
        "remove_clean_merged_pr_worktrees": True,
        "remove_clean_stale_review_worktrees": True,
        "remove_clean_stale_dashboard_runtimes": True,
        "remove_build_outputs_after_packaging": True,
        "remove_test_and_package_caches": True,
        "never_remove_dirty_worktrees": True,
        "never_remove_records_state_db_or_secrets": True,
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
        "local_large_artifact_threshold_gib": 5,
        "raw_intermediate_retention_days": 3,
        "review_package_retention_days": 14,
        "codex_log_retention_days": 14,
        "cache_cleanup_policy": "safe caches may be removed after reproducible validation",
    },
    "project_specific_posture": {
        "signal_room_video_requires_artifact_manifest_and_archive_plan": True,
        "waha_external_archive_upload_requires_explicit_approval": True,
        "tool_tally_production_evidence_must_preserve_audit_artifacts": True,
        "generic_coding_prs_report_storage_delta_when_artifacts_generated": True,
    },
    "unresolved_policy_fields": (
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
    "disk_critical_threshold_percent",
    "lean_target_percent",
    "minimum_free_gib",
    "free_gib",
    "project_domain",
    "external_archive_or_upload_requested",
    "waha_external_upload_approved",
    "archive_plan_present",
    "production_evidence_delete_requested",
    "audit_artifact_preservation_confirmed",
    "cleanup_dry_run_manifest_present",
    "current_live_runtime_protected",
    "rollback_runtimes_protected",
    "accepted_live_repo_protected",
    "records_state_db_secrets_protected",
    "dirty_worktree_cleanup_requested",
    "stale_clean_runtime_count",
    "stale_clean_worktree_count",
    "build_output_cleanup_requested",
    "cache_cleanup_requested",
}


def get_storage_guard_policy() -> dict[str, Any]:
    """Return a display copy of the inert Storage Guard policy."""

    return deepcopy(STORAGE_GUARD_POLICY)


def _bounded_text(value: Any, *, max_chars: int = 500) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:max_chars]


def _bounded_kind(value: Any) -> str:
    return _bounded_text(value, max_chars=80).lower().replace(" ", "_")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _path_matches(path: str, protected_paths: set[str]) -> bool:
    normalized = path.rstrip("/\\")
    return bool(normalized) and normalized in protected_paths


def build_storage_cleanup_manifest(observed_state: dict[str, Any] | None) -> dict[str, Any]:
    """Build a dry-run cleanup manifest from caller-supplied inventory.

    The manifest builder is intentionally pure. It does not inspect disks,
    filesystems, cloud remotes, services, credentials, records, or environment
    variables. Callers must supply candidate paths and protection metadata from
    a separate read-only inventory step.
    """

    state = dict(observed_state or {})
    current_live_runtime = _bounded_text(state.get("current_live_runtime"), max_chars=500)
    accepted_live_repo = _bounded_text(state.get("accepted_live_repo"), max_chars=500)
    rollback_runtimes = [
        _bounded_text(item, max_chars=500)
        for item in _as_list(state.get("rollback_runtimes"))
        if _bounded_text(item, max_chars=500)
    ]
    protected_paths = {path.rstrip("/\\") for path in [current_live_runtime, accepted_live_repo, *rollback_runtimes] if path}

    protected: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []
    reasons: list[str] = []

    if not current_live_runtime:
        _add_unique(reasons, "current live runtime path was not supplied")
    if not accepted_live_repo:
        _add_unique(reasons, "accepted-live repo path was not supplied")
    if not rollback_runtimes:
        _add_unique(reasons, "rollback runtime paths were not supplied")

    total_eligible_gib = 0.0
    total_blocked_gib = 0.0
    total_review_gib = 0.0
    candidates = _as_list(state.get("candidates"))

    for index, raw in enumerate(candidates):
        item = raw if isinstance(raw, dict) else {}
        path = _bounded_text(item.get("path"), max_chars=500)
        kind = _bounded_kind(item.get("kind") or item.get("category") or "unknown")
        size_gib = _as_float(item.get("size_gib")) or 0.0
        clean = _as_bool(item.get("clean"))
        dirty = _as_bool(item.get("dirty")) or not clean if kind.endswith("worktree") else _as_bool(item.get("dirty"))
        active = _as_bool(item.get("active"))
        merged = _as_bool(item.get("merged"))
        current = _as_bool(item.get("current")) or _path_matches(path, protected_paths)
        contains_records = _as_bool(item.get("contains_records")) or "records" in kind or path.endswith("records.jsonl")
        contains_state_db = _as_bool(item.get("contains_state_db")) or path.endswith("state.db")
        contains_secrets = _as_bool(item.get("contains_secrets")) or any(token in path.lower() for token in ("secret", ".env", "token"))

        entry = {
            "index": index,
            "path": path,
            "kind": kind,
            "size_gib": size_gib,
            "clean": clean,
            "dirty": dirty,
            "active": active,
            "merged": merged,
            "current": current,
        }

        if not path:
            blocked.append({**entry, "reason": "candidate path is missing"})
            total_blocked_gib += size_gib
            continue
        if current:
            protected.append({**entry, "reason": "current, rollback, or accepted-live path is protected"})
            continue
        if contains_records or contains_state_db or contains_secrets:
            blocked.append({**entry, "reason": "records, state.db, or secrets are never cleanup candidates"})
            total_blocked_gib += size_gib
            continue
        if dirty:
            blocked.append({**entry, "reason": "dirty worktrees are never cleanup candidates"})
            total_blocked_gib += size_gib
            continue
        if active:
            protected.append({**entry, "reason": "active runtime or review worktree is protected"})
            continue

        if kind in {"stale_runtime", "dashboard_runtime", "review_worktree", "pr_worktree"}:
            if clean and (merged or kind in {"stale_runtime", "dashboard_runtime"}):
                eligible.append({**entry, "reason": "clean stale runtime/worktree can be removed in an approved cleanup lane"})
                total_eligible_gib += size_gib
            else:
                needs_review.append({**entry, "reason": "runtime/worktree needs review before cleanup"})
                total_review_gib += size_gib
            continue

        if kind in {"build_output", "cache", "package_cache", "test_cache", "log", "temp"}:
            eligible.append({**entry, "reason": "reproducible build/cache/log artifact can be removed in an approved cleanup lane"})
            total_eligible_gib += size_gib
            continue

        if kind in {"archive_candidate", "large_artifact", "export", "report_package"}:
            needs_review.append({**entry, "reason": "archive or large artifact needs cloud/archive decision before cleanup"})
            total_review_gib += size_gib
            continue

        needs_review.append({**entry, "reason": "unknown cleanup class needs human review"})
        total_review_gib += size_gib

    before_used_percent = _as_float(state.get("disk_used_percent"))
    target_used_percent = _as_float(state.get("target_used_percent")) or _as_float(
        STORAGE_GUARD_POLICY["disk_thresholds"]["lean_target_percent"]
    )

    return {
        "manifest_id": _bounded_text(state.get("manifest_id") or "storage-cleanup-dry-run", max_chars=120),
        **_INERT_STORAGE_FLAGS,
        "source": "caller_supplied_cleanup_inventory",
        "stored": False,
        "delete_enabled": False,
        "upload_enabled": False,
        "requires_explicit_cleanup_lane": True,
        "current_live_runtime_protected": bool(current_live_runtime),
        "rollback_runtimes_protected": bool(rollback_runtimes),
        "accepted_live_repo_protected": bool(accepted_live_repo),
        "records_state_db_secrets_protected": True,
        "target_used_percent": target_used_percent,
        "before_used_percent": before_used_percent,
        "candidate_count": len(candidates),
        "protected": protected,
        "eligible": eligible,
        "blocked": blocked,
        "needs_review": needs_review,
        "summary": {
            "eligible_count": len(eligible),
            "blocked_count": len(blocked),
            "protected_count": len(protected),
            "needs_review_count": len(needs_review),
            "eligible_gib": round(total_eligible_gib, 3),
            "blocked_gib": round(total_blocked_gib, 3),
            "needs_review_gib": round(total_review_gib, 3),
        },
        "reasons": reasons,
    }


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

    thresholds = policy["disk_thresholds"]
    disk_used = _as_float(state.get("disk_used_percent"))
    block_threshold = _as_float(state.get("disk_block_threshold_percent")) or _as_float(
        thresholds.get("disk_block_threshold_percent")
    )
    warning_threshold = _as_float(state.get("disk_warning_threshold_percent")) or _as_float(
        thresholds.get("disk_warning_threshold_percent")
    )
    critical_threshold = _as_float(state.get("disk_critical_threshold_percent")) or _as_float(
        thresholds.get("disk_critical_threshold_percent")
    )
    lean_target = _as_float(state.get("lean_target_percent")) or _as_float(thresholds.get("lean_target_percent"))
    minimum_free_gib = _as_float(state.get("minimum_free_gib")) or _as_float(thresholds.get("minimum_free_gib"))
    free_gib = _as_float(state.get("free_gib"))

    if disk_used is not None and critical_threshold is not None and disk_used >= critical_threshold:
        _add_unique(reasons, "observed disk usage is at or above lean critical threshold")
        _add_unique(blocked_actions, "start non-cleanup work")
    if disk_used is not None and block_threshold is not None and disk_used >= block_threshold:
        _add_unique(reasons, "observed disk usage is at or above supplied block threshold")
        _add_unique(blocked_actions, "start artifact-heavy work")
    elif disk_used is not None and warning_threshold is not None and disk_used >= warning_threshold:
        _add_unique(reasons, "observed disk usage is at or above lean warning threshold")
    if free_gib is not None and minimum_free_gib is not None and free_gib < minimum_free_gib:
        _add_unique(reasons, "observed free disk is below lean minimum free space")
        _add_unique(blocked_actions, "start artifact-heavy work")

    cleanup_requested = _as_bool(state.get("cleanup_requested"))
    if cleanup_requested:
        if not _as_bool(state.get("cleanup_dry_run_manifest_present")):
            _add_unique(reasons, "cleanup requested without dry-run cleanup manifest")
            _add_unique(blocked_actions, "perform storage cleanup")
        for key, reason in (
            ("current_live_runtime_protected", "cleanup did not confirm current live runtime is protected"),
            ("rollback_runtimes_protected", "cleanup did not confirm rollback runtimes are protected"),
            ("accepted_live_repo_protected", "cleanup did not confirm accepted-live repo is protected"),
            ("records_state_db_secrets_protected", "cleanup did not confirm records/state/secrets are protected"),
        ):
            if not _as_bool(state.get(key)):
                _add_unique(reasons, reason)
                _add_unique(blocked_actions, "perform storage cleanup")
    if _as_bool(state.get("dirty_worktree_cleanup_requested")):
        _add_unique(reasons, "dirty worktree cleanup is forbidden by lean-runtime policy")
        _add_unique(blocked_actions, "delete dirty worktrees")
    if disk_used is not None and lean_target is not None and cleanup_requested and disk_used > lean_target:
        _add_unique(reasons, "cleanup target is not yet met")
    if (_as_float(state.get("stale_clean_runtime_count")) or 0) > 0 and not cleanup_requested:
        _add_unique(reasons, "clean stale runtimes are eligible for a cleanup lane")
    if (_as_float(state.get("stale_clean_worktree_count")) or 0) > 0 and not cleanup_requested:
        _add_unique(reasons, "clean stale worktrees are eligible for a cleanup lane")

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
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }
