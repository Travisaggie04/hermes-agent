"""Inert Verifier Workflow v1 policy records and dry-run evaluator.

This module is intentionally display-only and dry-run only. It defines future
implementer -> verifier -> decision policy and evaluates caller-supplied
observed workflow state without inspecting live PRs, GitHub, files, processes,
services, models, providers, credentials, queues, databases, or runtime state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INERT_VERIFIER_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "display_only": True,
}

VERIFIER_WORKFLOW_POLICY: dict[str, Any] = {
    "workflow_id": "verifier_workflow_v1",
    **_INERT_VERIFIER_FLAGS,
    "required_workflow": {
        "implementation_step_required": True,
        "independent_verification_required": True,
        "decision_step_required": True,
        "implementer_cannot_self_verify": True,
    },
    "pr_workflow": {
        "pr_ready_requires_verification": True,
        "pr_merge_requires_approved_verification": True,
        "post_merge_verification_required": True,
        "deployment_readiness_required_before_deployment": True,
    },
    "deployment_workflow": {
        "deployment_readiness_packet_required": True,
        "blue_green_required_for_runtime_deployment": True,
        "rollback_plan_required": True,
        "post_deploy_acceptance_required": True,
    },
    "waha_workflow": {
        "waha_technical_verifier_required": True,
        "waha_hard_wall_policy_required": True,
        "waha_approved_model_policy_required_before_model_assisted_work": True,
        "waha_external_upload_archive_requires_explicit_approval": True,
    },
    "model_workflow": {
        "model_router_requires_dry_run_policy_pass": True,
        "verifier_model_must_be_qualified_before_verifier_role": True,
        "unknown_free_cloud_models_blocked_for_protected_domain_verification": True,
    },
    "storage_workflow": {
        "artifact_manifest_verification_required": True,
        "storage_delta_verification_required": True,
        "archive_verification_required_before_delete": True,
        "cleanup_delete_requires_explicit_delete_lane": True,
    },
    "evidence_requirements": (
        "implementation_summary",
        "files_changed",
        "tests_run",
        "safety_scan",
        "verifier_verdict",
        "unresolved_risks",
        "next_recommended_action",
    ),
    "unresolved_policy_fields": (
        "verifier_identity_registry",
        "qualified_verifier_model_registry",
        "protected_domain_verifier_roster",
        "future_runtime_enforcement_wiring",
        "operator_decision_authority",
        "post_merge_verification_record_schema",
        "post_deploy_acceptance_record_schema",
    ),
}

_OBSERVED_WORKFLOW_FIELDS = {
    "implementation_step_present",
    "independent_verification_present",
    "decision_step_present",
    "implementer_id",
    "verifier_id",
    "verifier_same_as_implementer",
    "verification_approved",
    "pr_ready_requested",
    "pr_merge_requested",
    "post_merge_verification_present",
    "deployment_requested",
    "deployment_readiness_packet_present",
    "blue_green_plan_present",
    "rollback_plan_present",
    "post_deploy_acceptance_present",
    "waha_work_requested",
    "waha_technical_verifier_present",
    "waha_hard_wall_policy_present",
    "waha_model_assisted_work_requested",
    "waha_approved_model_policy_present",
    "waha_external_upload_archive_requested",
    "waha_external_upload_archive_approved",
    "model_router_execution_requested",
    "model_router_dry_run_policy_passed",
    "verifier_model_role_requested",
    "verifier_model_qualified",
    "unknown_or_free_cloud_model_for_protected_verification",
    "storage_cleanup_requested",
    "delete_requested",
    "artifact_manifest_verified",
    "storage_delta_verified",
    "archive_verification_present",
    "explicit_delete_lane",
    "implementation_summary_present",
    "files_changed_present",
    "tests_run_present",
    "safety_scan_present",
    "verifier_verdict_present",
    "unresolved_risks_present",
    "next_recommended_action_present",
}


def get_verifier_workflow_policy() -> dict[str, Any]:
    """Return a display copy of the inert Verifier Workflow v1 policy."""

    return deepcopy(VERIFIER_WORKFLOW_POLICY)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _as_bool(value: Any) -> bool:
    return value is True


def _same_identity(implementer_id: Any, verifier_id: Any) -> bool:
    implementer = str(implementer_id or "").strip().lower()
    verifier = str(verifier_id or "").strip().lower()
    return bool(implementer and verifier and implementer == verifier)


def _evidence_missing(state: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    evidence_field_by_requirement = {
        "implementation_summary": "implementation_summary_present",
        "files_changed": "files_changed_present",
        "tests_run": "tests_run_present",
        "safety_scan": "safety_scan_present",
        "verifier_verdict": "verifier_verdict_present",
        "unresolved_risks": "unresolved_risks_present",
        "next_recommended_action": "next_recommended_action_present",
    }
    for requirement, field in evidence_field_by_requirement.items():
        if field in state and not _as_bool(state.get(field)):
            missing.append(requirement)
    return missing


def evaluate_verifier_workflow(observed_state: dict[str, Any] | None) -> dict[str, Any]:
    """Dry-run evaluate caller-supplied workflow state against verifier policy.

    This function is deliberately pure. It only reads the supplied dictionary and
    returns a dry-run decision. It performs no live PR, GitHub, file, process,
    service, model, provider, credential, queue, database, or runtime inspection.
    """

    policy = VERIFIER_WORKFLOW_POLICY
    state = dict(observed_state or {})
    reasons: list[str] = []
    blocked_actions: list[str] = []
    required_approvals: list[str] = []

    observed_keys = set(state) & _OBSERVED_WORKFLOW_FIELDS
    if not observed_keys:
        reasons.append("caller-supplied observed workflow state is incomplete")
        decision_state = "unknown"
    else:
        decision_state = "pass"

    verification_present = _as_bool(state.get("independent_verification_present"))
    verification_approved = _as_bool(state.get("verification_approved"))
    verifier_conflict = _as_bool(state.get("verifier_same_as_implementer")) or _same_identity(
        state.get("implementer_id"),
        state.get("verifier_id"),
    )

    if _as_bool(state.get("pr_ready_requested")) and not verification_present:
        _add_unique(reasons, "PR ready status requested without independent verification")
        _add_unique(blocked_actions, "mark PR ready")
        _add_unique(required_approvals, "independent verifier approval")

    if _as_bool(state.get("pr_merge_requested")):
        if not verification_present:
            _add_unique(reasons, "PR merge requested without independent verification")
        if not verification_approved:
            _add_unique(reasons, "PR merge requested without approved verification")
        if not verification_present or not verification_approved:
            _add_unique(blocked_actions, "merge PR")
            _add_unique(required_approvals, "approved independent verification")

    if verifier_conflict:
        _add_unique(reasons, "implementer cannot self-verify")
        _add_unique(blocked_actions, "accept self-verification")
        _add_unique(required_approvals, "independent verifier assignment")

    if _as_bool(state.get("post_merge_verification_present")) is False and "post_merge_verification_present" in state:
        _add_unique(reasons, "post-merge verification is missing")
        _add_unique(blocked_actions, "mark post-merge workflow complete")

    if _as_bool(state.get("deployment_requested")):
        if not _as_bool(state.get("deployment_readiness_packet_present")):
            _add_unique(reasons, "deployment requested without deployment-readiness packet")
            _add_unique(blocked_actions, "deploy runtime")
            _add_unique(required_approvals, "deployment-readiness approval")
        if not _as_bool(state.get("rollback_plan_present")):
            _add_unique(reasons, "deployment requested without rollback plan")
            _add_unique(blocked_actions, "deploy runtime")
            _add_unique(required_approvals, "rollback plan approval")
        if not _as_bool(state.get("blue_green_plan_present")):
            _add_unique(reasons, "runtime deployment lacks blue/green plan")
            _add_unique(blocked_actions, "deploy runtime")
        if "post_deploy_acceptance_present" in state and not _as_bool(state.get("post_deploy_acceptance_present")):
            _add_unique(reasons, "post-deploy acceptance is missing")
            _add_unique(blocked_actions, "accept deployed runtime")

    if _as_bool(state.get("waha_work_requested")):
        if not _as_bool(state.get("waha_technical_verifier_present")):
            _add_unique(reasons, "Waha work requested without technical verifier")
            _add_unique(blocked_actions, "mark Waha work ready")
            _add_unique(required_approvals, "Waha technical verifier approval")
        if not _as_bool(state.get("waha_hard_wall_policy_present")):
            _add_unique(reasons, "Waha work requested without hard-wall policy")
            _add_unique(blocked_actions, "mark Waha work ready")
            _add_unique(required_approvals, "Waha hard-wall policy approval")

    if _as_bool(state.get("waha_model_assisted_work_requested")) and not _as_bool(
        state.get("waha_approved_model_policy_present")
    ):
        _add_unique(reasons, "Waha model-assisted work requested without approved model policy")
        _add_unique(blocked_actions, "start Waha model-assisted work")
        _add_unique(required_approvals, "Waha approved model policy approval")

    if _as_bool(state.get("waha_external_upload_archive_requested")) and not _as_bool(
        state.get("waha_external_upload_archive_approved")
    ):
        _add_unique(reasons, "Waha external upload/archive lacks explicit approval")
        _add_unique(blocked_actions, "external Waha upload/archive")
        _add_unique(required_approvals, "explicit Waha upload/archive approval")

    if _as_bool(state.get("model_router_execution_requested")) and not _as_bool(
        state.get("model_router_dry_run_policy_passed")
    ):
        _add_unique(reasons, "model router execution requested without dry-run policy pass")
        _add_unique(blocked_actions, "execute model router")
        _add_unique(required_approvals, "model router dry-run policy approval")

    if _as_bool(state.get("verifier_model_role_requested")) and not _as_bool(
        state.get("verifier_model_qualified")
    ):
        _add_unique(reasons, "verifier model role requested with unqualified model")
        _add_unique(blocked_actions, "assign model verifier role")
        _add_unique(required_approvals, "qualified verifier model approval")

    if _as_bool(state.get("unknown_or_free_cloud_model_for_protected_verification")):
        _add_unique(reasons, "unknown/free-cloud model is blocked for protected-domain verification")
        _add_unique(blocked_actions, "use unknown/free-cloud model for protected-domain verification")

    storage_action_requested = _as_bool(state.get("storage_cleanup_requested")) or _as_bool(
        state.get("delete_requested")
    )
    if storage_action_requested:
        if not _as_bool(state.get("artifact_manifest_verified")):
            _add_unique(reasons, "storage cleanup/delete requested without artifact manifest verification")
            _add_unique(blocked_actions, "cleanup/delete storage artifacts")
        if not _as_bool(state.get("storage_delta_verified")):
            _add_unique(reasons, "storage cleanup/delete requested without storage delta verification")
            _add_unique(blocked_actions, "cleanup/delete storage artifacts")
        if _as_bool(state.get("delete_requested")) and not _as_bool(state.get("archive_verification_present")):
            _add_unique(reasons, "delete requested without archive verification")
            _add_unique(blocked_actions, "delete storage artifacts")
        if _as_bool(state.get("delete_requested")) and not _as_bool(state.get("explicit_delete_lane")):
            _add_unique(reasons, "delete requested without explicit delete lane")
            _add_unique(blocked_actions, "delete storage artifacts")
            _add_unique(required_approvals, "explicit delete lane approval")

    missing_evidence = _evidence_missing(state)
    if missing_evidence:
        reasons.append("evidence requirements incomplete: " + ", ".join(missing_evidence))
        if decision_state == "pass":
            decision_state = "warn"

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
