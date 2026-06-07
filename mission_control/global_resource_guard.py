"""Inert Global Concurrency / Resource Guard policy records.

This module is intentionally dry-run only. It defines future guard policy and a
caller-supplied-state evaluator without inspecting live processes, files,
services, databases, provider config, credentials, or runtime state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INERT_GUARD_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

GLOBAL_RESOURCE_GUARD_POLICY: dict[str, Any] = {
    "guard_id": "global_concurrency_resource_v1",
    **_INERT_GUARD_FLAGS,
    "global_lane_limits": {
        "max_active_jenny_codex_lanes": 1,
        "parallel_lanes_allowed": False,
        "require_queue_when_busy": True,
    },
    "process_limits": {
        "max_codex_app_server_pairs": 1,
        "block_if_stale_app_server_pair": True,
        "block_if_resource_errors_recent": True,
        "app_server_resource_error_patterns": (
            "Too many open files",
            "Resource temporarily unavailable",
            "cannot fork",
            "failed to spawn thread",
        ),
    },
    "kanban_limits": {
        "embedded_dispatch_allowed": False,
        "max_kanban_workers": 0,
        "require_explicit_dispatch_lane": True,
        "block_auto_decompose_until_approved": True,
    },
    "worktree_repo_limits": {
        "require_clean_worktree": True,
        "block_dirty_or_quarantined_worktrees": True,
        "block_parent_directory_scans": True,
        "require_travis_fork_for_travis_pr_work": True,
        "warn_if_origin_points_to_nousresearch_for_travis_pr_work": True,
    },
    "resource_limits": {
        "disk_warning_threshold_percent": "placeholder",
        "disk_block_threshold_percent": "placeholder",
        "memory_warning_threshold": "placeholder",
    },
    "protected_domain_limits": {
        "waha_requires_hard_wall_policy_before_execution": True,
        "waha_requires_approved_model_policy_before_model_use": True,
        "waha_requires_technical_verifier_before_ready_done": True,
    },
    "model_router_limits": {
        "model_routing_allowed": False,
        "model_picker_execution_allowed": False,
        "verifier_model_required_before_protected_domain_work": True,
        "unknown_free_cloud_models_forbidden_for_waha_protected_domain_work": True,
    },
    "storage_artifact_limits": {
        "artifact_manifest_required_before_done": "placeholder",
        "storage_delta_required_before_done": "placeholder",
        "archive_status_required_before_delete": "placeholder",
        "local_large_artifact_threshold": "placeholder",
    },
    "unresolved_policy_fields": (
        "disk_warning_threshold_percent",
        "disk_block_threshold_percent",
        "memory_warning_threshold",
        "artifact_manifest_required_before_done",
        "storage_delta_required_before_done",
        "archive_status_required_before_delete",
        "local_large_artifact_threshold",
        "future_enforcement_wiring",
        "operator_approval_identity",
    ),
}

_OBSERVED_STATE_FIELDS = {
    "active_jenny_codex_lanes",
    "codex_app_server_pairs",
    "embedded_dispatch_enabled",
    "kanban_worker_count",
    "auto_decompose_requested",
    "worktree_state",
    "uses_dirty_or_quarantined_worktree",
    "parent_directory_scan_requested",
    "travis_fork_pr_work",
    "repo_remote_owner",
    "repo_full_name",
    "model_routing_requested",
    "model_picker_execution_requested",
    "free_cloud_model_for_protected_domain",
    "unknown_model_for_protected_domain",
    "waha_execution_requested",
    "waha_model_use_requested",
    "waha_ready_done_requested",
    "waha_hard_wall_ready",
    "waha_approved_model_policy_ready",
    "waha_technical_verifier_ready",
    "recent_resource_errors",
    "stale_app_server_pair_detected",
}


def get_global_resource_guard_policy() -> dict[str, Any]:
    """Return a display copy of the inert global resource guard policy."""

    return deepcopy(GLOBAL_RESOURCE_GUARD_POLICY)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    return value is True


def _matched_resource_errors(observed_state: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    raw_errors = observed_state.get("recent_resource_errors") or ()
    if isinstance(raw_errors, str):
        raw_errors = (raw_errors,)
    patterns = tuple(policy["process_limits"]["app_server_resource_error_patterns"])
    matches: list[str] = []
    for item in raw_errors:
        text = str(item)
        for pattern in patterns:
            if pattern.lower() in text.lower():
                _add_unique(matches, pattern)
    return matches


def evaluate_global_resource_guard(observed_state: dict[str, Any] | None) -> dict[str, Any]:
    """Dry-run evaluate caller-supplied observed state against future guard policy.

    The evaluator is deliberately pure: it only reads the provided dictionary and
    returns a dry-run decision. It does not inspect runtime services, processes,
    DBs, files, queues, models, providers, credentials, or environment variables.
    """

    policy = GLOBAL_RESOURCE_GUARD_POLICY
    state = dict(observed_state or {})
    reasons: list[str] = []
    blocked_actions: list[str] = []
    required_approvals: list[str] = []

    observed_keys = set(state) & _OBSERVED_STATE_FIELDS
    if not observed_keys:
        reasons.append("caller-supplied observed state is incomplete")
        decision_state = "unknown"
    else:
        decision_state = "pass"

    max_lanes = int(policy["global_lane_limits"]["max_active_jenny_codex_lanes"])
    if _as_int(state.get("active_jenny_codex_lanes")) > max_lanes:
        _add_unique(reasons, "parallel Jenny/Codex lanes exceed max_active_jenny_codex_lanes=1")
        _add_unique(blocked_actions, "start additional Jenny/Codex lane")
        _add_unique(required_approvals, "explicit parallel lane approval")

    max_pairs = int(policy["process_limits"]["max_codex_app_server_pairs"])
    if _as_int(state.get("codex_app_server_pairs")) > max_pairs:
        _add_unique(reasons, "codex/app-server pair count exceeds max_codex_app_server_pairs=1")
        _add_unique(blocked_actions, "start additional codex/app-server pair")

    if _as_bool(state.get("stale_app_server_pair_detected")):
        _add_unique(reasons, "stale app-server pair detected")
        _add_unique(blocked_actions, "continue with stale app-server pair")

    for match in _matched_resource_errors(state, policy):
        _add_unique(reasons, f"recent resource error matched: {match}")
        _add_unique(blocked_actions, "start resource-intensive worker")

    if _as_bool(state.get("embedded_dispatch_enabled")):
        _add_unique(reasons, "embedded Kanban dispatch is not approved")
        _add_unique(blocked_actions, "run embedded Kanban dispatcher")
        _add_unique(required_approvals, "explicit dispatch lane approval")

    if _as_int(state.get("kanban_worker_count")) > int(policy["kanban_limits"]["max_kanban_workers"]):
        _add_unique(reasons, "Kanban worker count exceeds max_kanban_workers=0")
        _add_unique(blocked_actions, "spawn Kanban worker")
        _add_unique(required_approvals, "explicit dispatch lane approval")

    if _as_bool(state.get("auto_decompose_requested")):
        _add_unique(reasons, "auto-decompose is blocked until approved")
        _add_unique(blocked_actions, "auto-decompose work into workers")
        _add_unique(required_approvals, "explicit dispatch lane approval")

    worktree_state = str(state.get("worktree_state") or "").lower()
    if worktree_state and worktree_state != "clean":
        _add_unique(reasons, "clean worktree is required")
        _add_unique(blocked_actions, "continue with unclean worktree")

    if _as_bool(state.get("uses_dirty_or_quarantined_worktree")):
        _add_unique(reasons, "dirty or quarantined worktree is blocked")
        _add_unique(blocked_actions, "use dirty/quarantined worktree")

    if _as_bool(state.get("parent_directory_scan_requested")):
        _add_unique(reasons, "parent-directory scan is blocked")
        _add_unique(blocked_actions, "run parent-directory scan")

    repo_owner = str(state.get("repo_remote_owner") or "")
    repo_full_name = str(state.get("repo_full_name") or "")
    if _as_bool(state.get("travis_fork_pr_work")) and repo_owner and repo_owner != "Travisaggie04":
        _add_unique(reasons, "Travis fork PR work must target Travisaggie04/hermes-agent")
        _add_unique(blocked_actions, "open Travis fork PR from non-Travis remote")
    if _as_bool(state.get("travis_fork_pr_work")) and repo_full_name and repo_full_name != "Travisaggie04/hermes-agent":
        _add_unique(reasons, "Travis fork PR work must target Travisaggie04/hermes-agent")
        _add_unique(blocked_actions, "open Travis fork PR from non-Travis remote")

    if _as_bool(state.get("model_routing_requested")):
        _add_unique(reasons, "model routing is not approved")
        _add_unique(blocked_actions, "route tasks to models")
        _add_unique(required_approvals, "model router enforcement approval")

    if _as_bool(state.get("model_picker_execution_requested")):
        _add_unique(reasons, "model picker execution is not approved")
        _add_unique(blocked_actions, "execute model picker selection")
        _add_unique(required_approvals, "model picker execution approval")

    if _as_bool(state.get("free_cloud_model_for_protected_domain")):
        _add_unique(reasons, "free-cloud models are forbidden for Waha/protected-domain work")
        _add_unique(blocked_actions, "use free-cloud model for protected-domain work")

    if _as_bool(state.get("unknown_model_for_protected_domain")):
        _add_unique(reasons, "unknown models are forbidden for Waha/protected-domain work")
        _add_unique(blocked_actions, "use unknown model for protected-domain work")

    waha_requested = any(
        _as_bool(state.get(key))
        for key in (
            "waha_execution_requested",
            "waha_model_use_requested",
            "waha_ready_done_requested",
        )
    )
    if waha_requested:
        _add_unique(blocked_actions, "execute protected-domain Waha work")
        if not _as_bool(state.get("waha_hard_wall_ready")):
            _add_unique(reasons, "Waha hard-wall policy is unresolved")
            _add_unique(required_approvals, "Waha hard-wall approval")
        if not _as_bool(state.get("waha_approved_model_policy_ready")):
            _add_unique(reasons, "Waha approved model policy is unresolved")
            _add_unique(required_approvals, "Waha approved model policy approval")
        if not _as_bool(state.get("waha_technical_verifier_ready")):
            _add_unique(reasons, "Waha technical verifier is unresolved")
            _add_unique(required_approvals, "Waha technical verifier approval")

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
