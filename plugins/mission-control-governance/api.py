"""Read-only Mission Control governance dashboard API."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from json import JSONDecodeError
from collections import Counter
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from hermes_constants import get_hermes_home
from mission_control.domain_governance import get_domain_governance_policies
from mission_control.global_resource_guard import (
    evaluate_global_resource_guard,
    get_global_resource_guard_policy,
)
from mission_control.model_registry import get_model_registry_records
from mission_control.pr_merge_lane_guard import evaluate_pr_merge_lane_guard
from mission_control.pr_merge_verifier_gate import (
    evaluate_pr_merge_verifier_gate,
    get_pr_merge_verifier_gate_policy,
)
from mission_control.storage_guard import (
    build_storage_cleanup_manifest,
    evaluate_storage_guard,
    get_storage_guard_policy,
)
from mission_control.verifier_workflow import (
    evaluate_verifier_workflow,
    get_verifier_workflow_policy,
)
from mission_control.workspace_status import build_workspace_status
from mission_control.workspace_status_records import build_workspace_status_from_records
from mission_control.lane_preflight import run_lane_start_preflight
from mission_control.github_bridge_mailbox import answer_pending_with_hermes, post_github_message
from mission_control.records.errors import RecordStoreError
from mission_control.records.models import RECORD_TYPES
from mission_control.kanban_linkage import linked_kanban_task_payload
from mission_control.start_gate import evaluate_start_gate
from mission_control.records import (
    AcceptedBaselineRecord,
    ApprovalRecord,
    ApprovalSlice,
    ChallengeReviewRecord,
    EvidenceCard,
    GoalContract,
    GitHubBridgeMailboxStatusRecord,
    GitHubBridgeMessageRecord,
    JennyBridgeMessageRequestRecord,
    JennyBridgeMessageResponseRecord,
    JennyBridgePollerStatusRecord,
    JennyReplyReviewRecord,
    JsonlRecordStore,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectBriefRecord,
    ProjectRecord,
    ReportRecord,
    RunRecord,
    SessionProjectLinkRecord,
    StartGateCheck,
    TaskControlEnvelope,
    VerifierWorkflowEvidenceRecord,
)


PLUGIN_NAME = "mission-control-governance"
DEFAULT_RECORDS_LIMIT = 25
MAX_RECORDS_LIMIT = 50
MAX_EVALUATION_BODY_BYTES = 8192
MAX_EVALUATION_STRING_CHARS = 500
MAX_EVALUATION_LIST_ITEMS = 20
MAX_EVALUATION_METADATA_ITEMS = 8
MAX_VERIFIER_EVIDENCE_RECORDS = 10
MAX_WORKSPACE_BODY_BYTES = 12000
MAX_WORKSPACE_TEXT_CHARS = 1200
MAX_WORKSPACE_PROMPT_CHARS = 4000
MAX_JENNY_BRIDGE_RELAY_PACKET_CHARS = 8000
MAX_WORKSPACE_LIST_ITEMS = 12
_PR_MERGE_GATE_FIELDS = {
    "repo",
    "pr_number",
    "base_branch",
    "head_commit",
    "packet_hash",
    "implementer_id",
    "verifier_id",
    "verifier_evidence_record_id",
    "verifier_evidence",
}
_PR_MERGE_GATE_EVIDENCE_FIELDS = {
    "record_id",
    "guard_type",
    "action_class",
    "repo",
    "pr_number",
    "base_branch",
    "head_commit",
    "packet_hash",
    "implementer_id",
    "verifier_id",
    "would_block",
    "blocked_actions",
    "dry_run_only",
    "enforces_runtime",
}
_PR_MERGE_GATE_BOOL_FIELDS = {"would_block", "dry_run_only", "enforces_runtime"}
_PR_MERGE_GATE_LIST_FIELDS = {"blocked_actions"}
_VERIFIER_EVIDENCE_FIELDS = {"source", "lane_id", "task_id", "domain_id", "action_class"}
_SECRET_LIKE_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_]{8,}|"
    r"(?:api[_-]?key|token|secret|password|bearer)\s*[:=]\s*[^\s,;]+)"
)
_PATH_LIKE_RE = re.compile(r"(?<!\w)(?:/[A-Za-z0-9._@%+\-]+){2,}|[A-Za-z]:\\[^\s,;]+")
INERT_FLAGS = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "execution_enabled": False,
}
CONTROL_PLANE_INERT_FLAGS = {
    **INERT_FLAGS,
    "display_only": True,
    "manual_copy_only": True,
    "send_to_jenny_enabled": False,
    "dispatch_enabled": False,
}
APPROVAL_STATUSES = {"proposed", "approved", "rejected", "expired", "consumed", "cancelled"}
RUN_STATUSES = {"requested", "preflight_passed", "running", "stopping", "stopped", "completed", "failed", "cancelled", "blocked"}
REPORT_STATUSES = {"received", "needs_review", "accepted", "rejected", "superseded"}
PROJECT_BRIEF_STATUSES = {"draft", "active", "superseded", "archived"}
CHALLENGE_REVIEW_STATUSES = {"draft", "accepted", "superseded"}
CHALLENGE_DECISION_STATES = {
    "clear_and_safe",
    "clarify_first",
    "needs_spec_first",
    "split_into_lanes",
    "wrong_approach_likely",
    "unsafe",
    "needs_approval",
}
CHALLENGE_REVIEW_CATEGORIES = {
    "wrong_approach",
    "missing_context",
    "protected_surface",
    "scope_split_required",
    "questions_required",
    "approval_required",
    "evidence_missing",
    "stale_state",
    "report_contract_missing",
}
CHALLENGE_BLOCKING_VERDICTS = {
    "blocks_lane_draft",
    "requires_spec_update",
    "requires_travis_approval",
    "split_lane",
    "read_only_only",
    "stop_live_action",
    "needs_report_contract",
    "needs_fresh_evidence",
}
SAFE_APPROVAL_ACTION_CLASSES = {"read_only_lane", "read_only_design", "read_only_inspection", "pr_creation"}
DANGEROUS_APPROVAL_ACTION_CLASSES = {
    "merge",
    "deploy",
    "runtime_switch",
    "payment",
    "waha",
    "social_post",
    "model_routing",
    "queue_mutation",
    "worker_timer_enablement",
}
APPROVAL_ACTION_CLASSES = SAFE_APPROVAL_ACTION_CLASSES | DANGEROUS_APPROVAL_ACTION_CLASSES
RUN_LANE_TYPES = {
    "read_only_design",
    "read_only_inspection",
    "implementation",
    "pr_creation",
    "deploy",
    "runtime_switch",
    "payment",
    "waha",
    "social_post",
    "model_routing",
    "queue_mutation",
    "worker_timer_enablement",
}
BROAD_APPROVAL_VALUES = {"*", "all", "any", "global", "everything", "unlimited"}
JENNY_BRIDGE_PENDING_STATUSES = {"queued", "retry_requested"}
PROFILE_STORAGE_CACHE_SECONDS = 60
FOREGROUND_WATCH_RUNNING_SECONDS = 15
_PROFILE_STORAGE_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}

PROJECT_ONBOARDING_TEMPLATES = (
    {
        "project_id": "project-hermes-mission-control",
        "slug": "hermes-mission-control",
        "name": "Hermes / Mission Control",
        "status": "Jenny OS native chat workspace; execution remains gated.",
        "source_of_truth": "Mission Control records + accepted-live baseline",
        "current_goal": "Make Jenny OS native chat the obvious operating surface before enabling any execution path.",
        "next_recommended_lane": "Read-only project status refresh or bounded Jenny OS workspace improvement PR.",
        "default_guards": "No deploy, restart, runtime switch, dispatch, queue mutation, model routing, enforcement, or secrets without explicit approval.",
        "profile": "default",
    },
    {
        "project_id": "project-long-form-video",
        "slug": "long-form-video",
        "name": "Long-form Video",
        "status": "Toolchain/proof lane; no publishing from Mission Control.",
        "source_of_truth": "money-signal-video profile + approved review packages",
        "current_goal": "Choose the best adult animated/character toolchain before long content production.",
        "next_recommended_lane": "Manual-copy toolchain proof/status packet for one bounded video question.",
        "default_guards": "No avatar-first fallback, static-card regression, paid render, or public posting without explicit approval.",
        "profile": "money-signal-video",
    },
    {
        "project_id": "project-shorts-video",
        "slug": "shorts-video",
        "name": "Shorts Video",
        "status": "Production strategy exists; publishing remains gated.",
        "source_of_truth": "money-signal-video profile + visible review packages",
        "current_goal": "Produce source-backed short-form concepts with strong hooks and reviewable proofs.",
        "next_recommended_lane": "Manual-copy research/review packet for one specific short concept.",
        "default_guards": "No generic AI clips, weak hooks, skipped source checks, paid API drift, or public posting without approval.",
        "profile": "money-signal-video",
    },
    {
        "project_id": "project-tool-tally",
        "slug": "tool-tally",
        "name": "Tool & Tally",
        "status": "Pre-launch gated; customer/public actions require explicit approval.",
        "source_of_truth": "Tool & Tally OS notes + no-call-estimateready profile",
        "current_goal": "Keep owner-facing evidence-first pages and paid-order monitoring stable without accidental launch actions.",
        "next_recommended_lane": "Read-only status check or critical hardening packet only.",
        "default_guards": "No payment changes, public intake drift, outreach sends, customer delivery, or private asset leaks without approval.",
        "profile": "no-call-estimateready",
    },
    {
        "project_id": "project-waha-work",
        "slug": "waha-work",
        "name": "Waha Work",
        "status": "Owner-side engineering workspace; isolated profile required.",
        "source_of_truth": "wahainspection profile",
        "current_goal": "Support Waha inspection/reporting with exact review-only engineering packets.",
        "next_recommended_lane": "Manual-copy Waha profile handoff for one bounded document, tracker, or review task.",
        "default_guards": "Keep Waha context isolated; no unapproved figures or management-ready claims without review.",
        "profile": "wahainspection",
    },
)
_EVALUATION_FIELDS = {
    "envelope_id",
    "active_lane",
    "mode",
    "allowed_actions",
    "forbidden_actions",
    "current_repo",
    "expected_systems_files",
    "stop_condition",
    "other_threads_excluded",
    "report_requirements",
    "risk_level",
    "approval_required",
    "approval_slice_ids",
    "evidence_ids",
    "token_context_policy",
    "created_at",
    "status",
    "metadata",
}
_EVALUATION_LIST_FIELDS = {
    "allowed_actions",
    "forbidden_actions",
    "expected_systems_files",
    "other_threads_excluded",
    "report_requirements",
    "approval_slice_ids",
    "evidence_ids",
}
_EVALUATION_METADATA_FIELDS = {
    "target_remote",
    "repo_remote",
    "authoritative_remote",
    "worktree_state",
}
_GUARD_OBSERVED_FIELDS = {
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
_GUARD_BOOL_FIELDS = {
    "embedded_dispatch_enabled",
    "auto_decompose_requested",
    "uses_dirty_or_quarantined_worktree",
    "parent_directory_scan_requested",
    "travis_fork_pr_work",
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
    "stale_app_server_pair_detected",
}
_GUARD_INT_FIELDS = {
    "active_jenny_codex_lanes",
    "codex_app_server_pairs",
    "kanban_worker_count",
}
_GUARD_LIST_FIELDS = {"recent_resource_errors"}
_STORAGE_OBSERVED_FIELDS = {
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
_STORAGE_BOOL_FIELDS = {
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
    "external_archive_or_upload_requested",
    "waha_external_upload_approved",
    "archive_plan_present",
    "production_evidence_delete_requested",
    "audit_artifact_preservation_confirmed",
}
_STORAGE_NUMBER_FIELDS = {
    "disk_used_percent",
    "disk_warning_threshold_percent",
    "disk_block_threshold_percent",
}
_VERIFIER_OBSERVED_FIELDS = {
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
_VERIFIER_BOOL_FIELDS = _VERIFIER_OBSERVED_FIELDS - {"implementer_id", "verifier_id"}

router = APIRouter()


def record_store_path() -> Path:
    return get_hermes_home() / "mission-control" / "records.jsonl"


def _record_store_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.stat().st_size == 0:
        return "empty"
    return "ok"


def _load_records_with_state() -> tuple[tuple[Any, ...], str, str | None]:
    path = record_store_path()
    state = _record_store_state(path)
    if state != "ok":
        return (), state, None
    try:
        records = JsonlRecordStore(path).read_all()
    except RecordStoreError as exc:
        return (), "malformed", str(exc)
    if not records:
        return (), "empty", None
    return records, "ok", None


def _load_latest_records_with_state(
    record_class: type[Any] | None = None,
    limit: int = 10,
) -> tuple[tuple[tuple[int, Any], ...], str, str | None]:
    path = record_store_path()
    state = _record_store_state(path)
    if state != "ok":
        return (), state, None
    try:
        records = JsonlRecordStore(path).read_latest(record_class=record_class, limit=limit)
    except RecordStoreError as exc:
        return (), "malformed", str(exc)
    if not records:
        return (), "empty", None
    return records, "ok", None


def _latest_accepted_baseline_payload() -> dict[str, Any]:
    records, _store_status, _error = _load_latest_records_with_state(
        AcceptedBaselineRecord,
        limit=1,
    )
    if not records:
        return {}
    _index, record = records[-1]
    return record.to_dict()


def _latest_handoff_payload() -> dict[str, Any]:
    records, _store_status, _error = _load_latest_records_with_state(
        OperatingWorkspaceHandoffRecord,
        limit=1,
    )
    if not records:
        return {}
    _index, record = records[-1]
    return record.to_dict()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _workspace_text(value: Any, *, max_chars: int = MAX_WORKSPACE_TEXT_CHARS) -> str:
    text = _SECRET_LIKE_RE.sub("[redacted]", str(value or "").strip())
    text = _PATH_LIKE_RE.sub("[path]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        raise HTTPException(status_code=422, detail="workspace field is too large")
    return text


def _workspace_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        raise HTTPException(status_code=422, detail="workspace list field must be a list")
    if len(values) > MAX_WORKSPACE_LIST_ITEMS:
        raise HTTPException(status_code=422, detail="workspace list field has too many items")
    return tuple(_workspace_text(item, max_chars=240) for item in values if str(item).strip())


def _workspace_enum_list(value: Any, allowed: set[str], field_name: str) -> tuple[str, ...]:
    values = _workspace_list(value)
    invalid = [item for item in values if item not in allowed]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must contain only: {', '.join(sorted(allowed))}",
        )
    return values


def _workspace_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise HTTPException(status_code=422, detail="workspace integer field must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="workspace integer field must be an integer") from exc
    if parsed < 0 or parsed > 999:
        raise HTTPException(status_code=422, detail="workspace integer field out of range")
    return parsed


async def _read_workspace_json_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_WORKSPACE_BODY_BYTES:
        raise HTTPException(status_code=413, detail="workspace payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return payload


def _project_payload(record: ProjectRecord) -> dict[str, Any]:
    return record.to_dict()


def _lane_request_payload(record: LaneRequestRecord) -> dict[str, Any]:
    return record.to_dict()


def _jenny_report_payload(record: JennyReportRecord) -> dict[str, Any]:
    return record.to_dict()


def _jenny_bridge_request_payload(record: JennyBridgeMessageRequestRecord) -> dict[str, Any]:
    return record.to_dict()


def _jenny_bridge_response_payload(record: JennyBridgeMessageResponseRecord) -> dict[str, Any]:
    return record.to_dict()


def _jenny_bridge_poller_status_payload(record: JennyBridgePollerStatusRecord) -> dict[str, Any]:
    return record.to_dict()


def _jenny_reply_review_payload(record: JennyReplyReviewRecord) -> dict[str, Any]:
    return record.to_dict()


def _session_project_link_payload(record: SessionProjectLinkRecord) -> dict[str, Any]:
    payload = record.to_dict()
    payload["durable_session_id"] = record.durable_session_id
    return payload


def _workspace_record_payload(record: Any) -> dict[str, Any]:
    if isinstance(record, ProjectRecord):
        return _project_payload(record)
    if isinstance(record, LaneRequestRecord):
        return _lane_request_payload(record)
    if isinstance(record, JennyReportRecord):
        return _jenny_report_payload(record)
    if isinstance(record, JennyBridgeMessageRequestRecord):
        return _jenny_bridge_request_payload(record)
    if isinstance(record, JennyBridgeMessageResponseRecord):
        return _jenny_bridge_response_payload(record)
    if isinstance(record, JennyBridgePollerStatusRecord):
        return _jenny_bridge_poller_status_payload(record)
    if isinstance(record, JennyReplyReviewRecord):
        return _jenny_reply_review_payload(record)
    if isinstance(record, (ApprovalRecord, ReportRecord, RunRecord)):
        return record.to_dict()
    if isinstance(record, SessionProjectLinkRecord):
        return _session_project_link_payload(record)
    return _record_payload(record)


def _latest_workspace_records(record_class: type[Any], limit: int) -> list[dict[str, Any]]:
    records, _store_status, _error = _load_latest_records_with_state(record_class=record_class, limit=limit)
    return [
        {
            "record_index": index,
            "record_type": _record_type(record),
            "record": _workspace_record_payload(record),
        }
        for index, record in records
    ]


def _jenny_bridge_response_request_ids(limit: int = MAX_RECORDS_LIMIT) -> set[str]:
    responses = _latest_workspace_records(JennyBridgeMessageResponseRecord, limit)
    return {
        str(item.get("record", {}).get("request_id") or "").strip()
        for item in responses
        if str(item.get("record", {}).get("request_id") or "").strip()
    }


def _annotate_jenny_bridge_request(item: dict[str, Any], response_request_ids: set[str]) -> dict[str, Any]:
    record = dict(item.get("record", {}))
    request_id = str(record.get("request_id") or "").strip()
    raw_status = str(record.get("status") or "queued").strip() or "queued"
    bridge_state = "replied" if request_id and request_id in response_request_ids else raw_status
    record["bridge_state"] = bridge_state
    record["has_response"] = bridge_state == "replied"
    return {**item, "record": record, "bridge_state": bridge_state, "has_response": bridge_state == "replied"}


def _pending_jenny_bridge_requests(
    *,
    project_id: str = "",
    limit: int = DEFAULT_RECORDS_LIMIT,
) -> list[dict[str, Any]]:
    response_request_ids = _jenny_bridge_response_request_ids()
    latest_by_request_id: dict[str, dict[str, Any]] = {}
    for item in _latest_workspace_records(JennyBridgeMessageRequestRecord, MAX_RECORDS_LIMIT):
        annotated = _annotate_jenny_bridge_request(item, response_request_ids)
        record = annotated.get("record", {})
        request_id = str(record.get("request_id") or "").strip()
        if not request_id:
            continue
        latest_by_request_id[request_id] = annotated

    pending = [
        item
        for item in sorted(latest_by_request_id.values(), key=lambda item: int(item.get("record_index", 0)))
        if item.get("bridge_state") in JENNY_BRIDGE_PENDING_STATUSES
    ]
    if project_id:
        pending = [item for item in pending if item.get("record", {}).get("project_id") == project_id]
    return pending[-limit:]


def _jenny_bridge_relay_packet(requests: list[dict[str, Any]]) -> str:
    lines = [
        "Mission Control Jenny bridge relay packet",
        "",
        "Use these queued bridge requests as inert project-room context.",
        "Do not deploy, restart, switch runtimes, dispatch, use Waha, mutate queues, route models, post socially, spend money, or inspect secrets unless a separate approved lane explicitly allows it.",
        "For each request you handle, append one JennyBridgeMessageResponseRecord through POST /workspace/jenny-bridge/inbox/create.",
        "",
    ]
    if not requests:
        lines.append("No pending bridge requests.")
    for offset, item in enumerate(requests, start=1):
        record = item.get("record", {})
        lines.extend(
            [
                f"Request {offset}",
                f"request_id: {record.get('request_id', '')}",
                f"project_id: {record.get('project_id', '')}",
                f"lane_request_id: {record.get('lane_request_id', '')}",
                f"sender: {record.get('sender', '')}",
                "message:",
                str(record.get("message", "")).strip(),
                "",
                "Expected response payload shape:",
                '{"request_id":"<same request_id>","project_id":"<same project_id>","message":"<your bounded response>","responder":"jenny"}',
                "",
            ]
        )
    packet = "\n".join(lines).strip()
    if len(packet) <= MAX_JENNY_BRIDGE_RELAY_PACKET_CHARS:
        return packet
    return f"{packet[: MAX_JENNY_BRIDGE_RELAY_PACKET_CHARS - 16].rstrip()}\n...[truncated]"


def _iso_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _recent_watch_status_is_running(status: str, created_at: str, *, now: datetime | None = None) -> bool:
    if not status.startswith("watch_") or status == "watch_stopped":
        return False

    created = _iso_datetime(created_at)
    if created is None:
        return False

    current = now or datetime.now(timezone.utc)
    return 0 <= (current - created).total_seconds() <= FOREGROUND_WATCH_RUNNING_SECONDS


def _jenny_bridge_poller_status_projection(limit: int = DEFAULT_RECORDS_LIMIT) -> dict[str, Any]:
    pending = _pending_jenny_bridge_requests(limit=limit)
    statuses = _latest_workspace_records(JennyBridgePollerStatusRecord, limit)
    responses = _latest_workspace_records(JennyBridgeMessageResponseRecord, limit)
    latest_status = statuses[-1]["record"] if statuses else {}
    latest_response = responses[-1]["record"] if responses else {}
    return {
        "manual_start_only": True,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "count": len(statuses),
        "pending_count": len(pending),
        "last_poll_at": latest_status.get("created_at", ""),
        "last_status": latest_status.get("status", "idle"),
        "last_response_at": latest_response.get("created_at", ""),
        "last_response_request_id": latest_response.get("request_id", ""),
        "last_error": latest_status.get("last_error", ""),
        "status_records": statuses,
    }


def _is_operator_github_bridge_record(record: dict[str, Any]) -> bool:
    from_agent = str(record.get("from_agent") or "").lower()
    request_id = str(record.get("request_id") or "").lower()
    text = str(record.get("message") or "").lower()
    return (
        from_agent == "codex"
        or request_id.startswith("codex-")
        or "bounded dashboard-only deploy check" in text
        or "review pr #" in text
        or "codex app-server startup failed" in text
        or "mission control two process" in text
        or "desktop phone bridge" in text
        or "bridge works" in text
        or "success smoke reached" in text
        or "failure guarded" in text
    )


def _operator_github_bridge_group_key(record: dict[str, Any]) -> str:
    if not _is_operator_github_bridge_record(record):
        return ""
    project_id = str(record.get("project_id") or "unknown")
    request_id = str(record.get("request_id") or "").lower()
    text = str(record.get("message") or "").lower()
    if request_id.startswith("codex-deploy-") or "dashboard-only deploy request" in text:
        return f"{project_id}:codex-dashboard-deploy"
    if request_id.startswith("codex-"):
        return f"{project_id}:codex-operator"
    return ""


def _collapse_superseded_operator_pending(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    current: list[dict[str, Any]] = []
    latest_by_group: dict[str, int] = {}
    superseded_count = 0

    for item in items:
        group_key = _operator_github_bridge_group_key(item.get("record", {}))
        if not group_key:
            current.append(item)
            continue

        previous_index = latest_by_group.get(group_key)
        if previous_index is not None:
            current[previous_index] = item
            superseded_count += 1
        else:
            latest_by_group[group_key] = len(current)
            current.append(item)

    return current, superseded_count


def _github_bridge_mailbox_status_projection(limit: int = DEFAULT_RECORDS_LIMIT, project_id: str = "") -> dict[str, Any]:
    messages = _latest_workspace_records(GitHubBridgeMessageRecord, limit)
    statuses = _latest_workspace_records(GitHubBridgeMailboxStatusRecord, limit)
    request_project_by_id = {
        str(item.get("record", {}).get("request_id") or ""): str(item.get("record", {}).get("project_id") or "")
        for item in messages
    }
    response_project_by_id = {
        str(item.get("record", {}).get("request_id") or ""): str(item.get("record", {}).get("project_id") or "")
        for item in messages
        if item.get("record", {}).get("status") in {"replied", "closed"}
        or item.get("record", {}).get("from_agent") == "jenny"
    }
    if project_id:
        messages = [
            item
            for item in messages
            if str(item.get("record", {}).get("project_id") or "") == project_id
        ]
        statuses = [
            item
            for item in statuses
            if request_project_by_id.get(str(item.get("record", {}).get("handled_request_id") or ""))
            == project_id
            or response_project_by_id.get(str(item.get("record", {}).get("handled_response_id") or ""))
            == project_id
        ]
    response_request_ids = {
        item.get("record", {}).get("request_id", "")
        for item in messages
        if item.get("record", {}).get("status") in {"replied", "closed"}
        or item.get("record", {}).get("from_agent") == "jenny"
    }
    raw_pending = [
        item
        for item in messages
        if item.get("record", {}).get("status") in {"queued", "retry_requested"}
        and item.get("record", {}).get("to_agent") == "jenny"
        and item.get("record", {}).get("request_id") not in response_request_ids
    ]
    pending, superseded_background_pending_count = _collapse_superseded_operator_pending(raw_pending)
    visible_pending = [
        item
        for item in pending
        if not _is_operator_github_bridge_record(item.get("record", {}))
    ]
    background_pending_count = max(len(pending) - len(visible_pending), 0)
    responses = [
        item
        for item in messages
        if item.get("record", {}).get("status") in {"replied", "closed"}
        or item.get("record", {}).get("from_agent") == "jenny"
    ]
    latest_status = statuses[-1]["record"] if statuses else {}
    latest_response = responses[-1]["record"] if responses else {}
    return {
        "manual_start_only": True,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "discord_automation_enabled": False,
        "model_routing_enabled": False,
        "stored": False,
        "project_id": project_id,
        "count": len(statuses),
        "pending_count": len(pending),
        "visible_pending_count": len(visible_pending),
        "background_pending_count": background_pending_count,
        "superseded_background_pending_count": superseded_background_pending_count,
        "mode": latest_status.get("mode", "manual"),
        "foreground_watch_supported": True,
        "foreground_watch_running": _recent_watch_status_is_running(latest_status.get("status", ""), latest_status.get("created_at", "")),
        "last_poll_at": latest_status.get("created_at", ""),
        "last_status": latest_status.get("status", "idle"),
        "last_response_at": latest_response.get("created_at", ""),
        "last_response_request_id": latest_response.get("request_id", ""),
        "last_error": latest_status.get("last_error", ""),
        "pending_messages": pending,
        "visible_pending_messages": visible_pending,
        "response_messages": responses[-limit:],
        "recent_messages": messages[-limit:],
        "status_records": statuses,
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_read_repo_text(*relative_parts: str) -> str:
    path = _repo_root().joinpath(*relative_parts)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _async_agent_capability_projection() -> dict[str, Any]:
    delegate_source = _safe_read_repo_text("tools", "delegate_tool.py")
    toolsets_source = _safe_read_repo_text("toolsets.py")
    readme_source = _safe_read_repo_text("README.md")
    combined = "\n".join((delegate_source, toolsets_source, readme_source)).lower()
    sync_delegate_available = "delegate_task" in combined and "delegation" in combined
    async_control_tokens = (
        "async_delegation",
        "async_subagent",
        "spawn_async",
        "async agent",
        "async_agents",
    )
    async_controls_available = any(token in combined for token in async_control_tokens)
    current_mode = (
        "native_async_agents_available"
        if async_controls_available
        else "sync_delegate_task_only"
        if sync_delegate_available
        else "no_delegation_detected"
    )
    recommended_next_lane = (
        "Wire native chat status to Hermes async task lifecycle with approval gates before enabling task starts."
        if async_controls_available
        else "Keep Jenny OS status-only until the Hermes async-agent update is installed in this runtime."
    )

    return {
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "execution_enabled": False,
        "trusted_for_execution": False,
        "inert_context_only": True,
        "stored": False,
        "manual_start_only": True,
        "session_send_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "model_routing_enabled": False,
        "current_mode": current_mode,
        "sync_delegate_task_available": sync_delegate_available,
        "sync_delegate_task_durable": False,
        "async_agent_controls_available": async_controls_available,
        "async_agent_controls_enabled": False,
        "async_agent_controls_expected": ["spawn", "check", "steer", "collect", "cancel", "list"],
        "policy_summary": "Native chat may show async task status, but starting or steering tasks remains approval-gated.",
        "recommended_next_lane": recommended_next_lane,
    }


def _project_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _project_template_payload(template: dict[str, str], existing_projects: tuple[ProjectRecord, ...] = ()) -> dict[str, Any]:
    slug = template["slug"]
    names = {_project_slug(project.name) for project in existing_projects}
    ids = {project.project_id for project in existing_projects}
    exists = slug in names or template["project_id"] in ids
    return {
        **template,
        "canonical_slug": slug,
        "exists": exists,
        "default_guards": template["default_guards"],
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "manual_copy_only": True,
    }


def _project_record_from_template(template: dict[str, str]) -> ProjectRecord:
    now = _utc_now()
    return ProjectRecord(
        project_id=template["project_id"],
        name=template["name"],
        status=template["status"],
        current_goal=template["current_goal"],
        next_recommended_lane=template["next_recommended_lane"],
        mistakes_guards=template["default_guards"],
        source_of_truth=template["source_of_truth"],
        profile=template["profile"],
        created_at=now,
        updated_at=now,
        metadata={
            "source": "mission_control_real_project_onboarding_v1",
            "canonical_slug": template["slug"],
            "default_guards": template["default_guards"],
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
        },
    )


def _seed_project_templates() -> dict[str, Any]:
    store = JsonlRecordStore(record_store_path())
    existing_projects = store.read_all(ProjectRecord)
    existing_slugs = {_project_slug(project.name) for project in existing_projects}
    existing_ids = {project.project_id for project in existing_projects}
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for template in PROJECT_ONBOARDING_TEMPLATES:
        duplicate = template["slug"] in existing_slugs or template["project_id"] in existing_ids
        if duplicate:
            skipped.append({"project_id": template["project_id"], "name": template["name"], "reason": "already_exists"})
            continue
        record = _project_record_from_template(template)
        index = store.append(record)
        created.append({"record_index": index, "record_type": record.record_type, "project": _project_payload(record)})
        existing_slugs.add(template["slug"])
        existing_ids.add(template["project_id"])
    return {"created": created, "skipped": skipped}


def _project_state_artifact_links(report: dict[str, Any]) -> list[str]:
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    raw_links = metadata.get("artifact_links") or metadata.get("artifacts") or []
    if isinstance(raw_links, str):
        raw_links = [raw_links]
    links = [str(item).strip() for item in raw_links if str(item).strip()] if isinstance(raw_links, list) else []
    if links:
        return links

    # Until artifact links are first-class on JennyReportRecord, expose useful
    # report evidence as inert display-only link text. These are not dereferenced
    # and do not grant execution capability.
    return [str(item).strip() for item in report.get("changed_files", []) if str(item).strip()]


def _project_report_contract(report: dict[str, Any], artifact_links: list[str]) -> dict[str, Any]:
    if not report:
        missing = ["report"]
        state = "missing_report"
    else:
        missing = []
        if not report.get("summary"):
            missing.append("summary")
        if not report.get("result"):
            missing.append("result")
        if not (report.get("risks") or report.get("blockers")):
            missing.append("risks/blockers")
        if not artifact_links:
            missing.append("evidence")
        if not report.get("tests"):
            missing.append("tests")
        if not report.get("next_recommended_lane"):
            missing.append("next lane")
        state = "complete" if not missing else "incomplete"

    return {
        "state": state,
        "complete": not missing,
        "missing_fields": missing,
        "required_fields": ["summary", "result", "risks/blockers", "evidence", "tests", "next lane"],
        "display_only": True,
        "trusted_for_execution": False,
    }


def _project_state_missing_fields(
    *,
    lane: dict[str, Any],
    report: dict[str, Any],
    report_contract: dict[str, Any],
    risks: list[str],
    artifact_links: list[str],
) -> list[str]:
    missing: list[str] = []
    if not lane:
        missing.append("latest_lane")
    if not report.get("summary"):
        missing.append("latest_jenny_report")
    if not report.get("result"):
        missing.append("latest_result")
    if not risks:
        missing.append("risks_blockers")
    if not artifact_links:
        missing.append("artifact_links")
    if report_contract.get("complete") is not True:
        missing.append("report_contract")
    return missing


def _project_state_projection(limit: int) -> list[dict[str, Any]]:
    projects = _latest_workspace_records(ProjectRecord, limit)
    lanes = _latest_workspace_records(LaneRequestRecord, limit)
    reports = _latest_workspace_records(JennyReportRecord, limit)
    project_session_summary = _project_sessions_projection(limit)
    session_group_by_project = {
        group.get("project_id", ""): group
        for group in project_session_summary.get("groups", [])
    }

    latest_lane_by_project: dict[str, dict[str, Any]] = {}
    for item in lanes:
        record = item.get("record", {})
        project_id = record.get("project_id", "")
        if project_id:
            latest_lane_by_project[project_id] = item

    latest_report_by_project: dict[str, dict[str, Any]] = {}
    for item in reports:
        record = item.get("record", {})
        project_id = record.get("project_id", "")
        if project_id:
            latest_report_by_project[project_id] = item

    states: list[dict[str, Any]] = []
    for item in projects:
        project = item.get("record", {})
        project_id = project.get("project_id") or project.get("name", "")
        lane_item = latest_lane_by_project.get(project_id)
        report_item = latest_report_by_project.get(project_id)
        lane = lane_item.get("record", {}) if lane_item else {}
        report = report_item.get("record", {}) if report_item else {}
        risks = report.get("risks") or []
        artifact_links = _project_state_artifact_links(report)
        report_contract = _project_report_contract(report, artifact_links)
        has_real_report = bool(report.get("summary") or report.get("result"))
        latest_activity_source = "report" if has_real_report else "lane" if lane else "project"
        latest_activity_at = (
            report.get("created_at")
            or lane.get("updated_at")
            or lane.get("created_at")
            or project.get("updated_at")
            or project.get("created_at")
            or ""
        )
        session_group = session_group_by_project.get(project_id, {})
        recent_sessions = session_group.get("sessions", [])[:3]
        states.append({
            "project_id": project_id,
            "name": project.get("name", project_id),
            "status": project.get("status", ""),
            "current_goal": project.get("current_goal", ""),
            "latest_lane_request": lane,
            "latest_lane_title": lane.get("title", ""),
            "latest_lane_objective": lane.get("objective", ""),
            "latest_jenny_report": report,
            "latest_report_summary": report.get("summary") or project.get("last_report_summary", ""),
            "latest_result": report.get("result", ""),
            "risks_blockers": risks,
            "next_recommended_lane": report.get("next_recommended_lane") or project.get("next_recommended_lane", ""),
            "last_updated": latest_activity_at,
            "latest_activity_at": latest_activity_at,
            "latest_activity_source": latest_activity_source,
            "has_real_report": has_real_report,
            "missing_state_fields": _project_state_missing_fields(
                lane=lane,
                report=report,
                report_contract=report_contract,
                risks=risks,
                artifact_links=artifact_links,
            ),
            "report_contract": report_contract,
            "artifact_links": artifact_links,
            "linked_session_count": session_group.get("linked_session_count", 0),
            "recent_sessions": recent_sessions,
            "unassigned_suggestion_count": session_group.get("unassigned_suggestion_count", 0),
            "source_record_indexes": {
                "project": item.get("record_index"),
                "lane_request": lane_item.get("record_index") if lane_item else None,
                "jenny_report": report_item.get("record_index") if report_item else None,
            },
        })
    return states


def _session_durable_id(session: dict[str, Any]) -> str:
    return str(session.get("_lineage_root_id") or session.get("lineage_root_id") or session.get("id") or "")


def _session_title(session: dict[str, Any]) -> str:
    return str(session.get("title") or session.get("preview") or session.get("id") or "").strip()


def _build_session_project_link_record(payload: dict[str, Any]) -> SessionProjectLinkRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    session_id = _workspace_text(payload.get("session_id"), max_chars=160)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    status = _workspace_text(payload.get("status"), max_chars=40) or "active"
    if status not in {"active", "removed", "superseded"}:
        raise HTTPException(status_code=422, detail="status must be active, removed, or superseded")
    link_method = _workspace_text(payload.get("link_method"), max_chars=40) or "manual"
    if link_method not in {"manual", "suggested", "seeded"}:
        raise HTTPException(status_code=422, detail="link_method must be manual, suggested, or seeded")
    now = _utc_now()
    return SessionProjectLinkRecord(
        link_id=_workspace_text(payload.get("link_id"), max_chars=120) or f"session-project-link-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        session_id=session_id,
        lineage_root_id=_workspace_text(payload.get("lineage_root_id") or payload.get("_lineage_root_id"), max_chars=160),
        profile=_workspace_text(payload.get("profile"), max_chars=80),
        source=_workspace_text(payload.get("source"), max_chars=80),
        title_snapshot=_workspace_text(payload.get("title_snapshot") or payload.get("title"), max_chars=240),
        cwd_snapshot=_workspace_text(payload.get("cwd_snapshot") or payload.get("cwd"), max_chars=240),
        linked_at=_workspace_text(payload.get("linked_at"), max_chars=80) or now,
        linked_by=_workspace_text(payload.get("linked_by"), max_chars=120) or "manual-operator",
        link_method=link_method,
        confidence=_workspace_text(payload.get("confidence"), max_chars=80) or "manual",
        status=status,
        metadata={
            "source": "mission_control_session_project_link_backend_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "auto_inferred": False,
        },
    )


def _active_session_project_links(limit: int) -> dict[str, dict[str, Any]]:
    latest_by_durable: dict[str, dict[str, Any]] = {}
    links = _latest_workspace_records(SessionProjectLinkRecord, limit)
    for item in reversed(links):
        record = item.get("record", {})
        durable = str(record.get("durable_session_id") or record.get("lineage_root_id") or record.get("session_id") or "")
        if not durable or durable in latest_by_durable:
            continue
        latest_by_durable[durable] = item
    return {
        durable: item
        for durable, item in latest_by_durable.items()
        if item.get("record", {}).get("status", "active") == "active"
    }


def _session_projection_payload(session: dict[str, Any], *, link: dict[str, Any] | None = None, suggested_project_id: str = "") -> dict[str, Any]:
    return {
        "session_id": session.get("id", ""),
        "durable_session_id": _session_durable_id(session),
        "lineage_root_id": session.get("_lineage_root_id") or session.get("lineage_root_id") or "",
        "profile": session.get("profile") or "default",
        "is_default_profile": bool(session.get("is_default_profile")),
        "source": session.get("source") or "",
        "title": session.get("title") or "",
        "preview": session.get("preview") or "",
        "cwd": session.get("cwd") or "",
        "started_at": session.get("started_at"),
        "last_active": session.get("last_active") or session.get("started_at"),
        "message_count": session.get("message_count") or 0,
        "tool_call_count": session.get("tool_call_count") or 0,
        "linked_project_id": (link or {}).get("project_id", ""),
        "link_record": link or {},
        "suggested_project_id": suggested_project_id,
    }


def _suggest_project_id_for_session(session: dict[str, Any]) -> str:
    profile = str(session.get("profile") or "").lower()
    cwd = str(session.get("cwd") or "").lower()
    title = str(session.get("title") or "").lower()
    preview = str(session.get("preview") or "").lower()
    haystack = " ".join([profile, cwd, title, preview])
    if profile == "wahainspection" or "waha" in haystack or "es sider" in haystack:
        return "project-waha-work"
    if profile == "no-call-estimateready" or "tool & tally" in haystack or "tool-tally" in haystack or "estimateready" in haystack:
        return "project-tool-tally"
    if "shorts" in haystack or "reels" in haystack or "queue" in haystack:
        return "project-shorts-video"
    if "long-form" in haystack or "longform" in haystack or "moho" in haystack or "hyperframes" in haystack:
        return "project-long-form-video"
    if profile in {"default", "hermes-ops"} and ("mission control" in haystack or "hermes" in haystack or ".hermes" in cwd):
        return "project-hermes-mission-control"
    return ""


def _read_profile_sessions_for_project_links(limit: int) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    sessions: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    try:
        from hermes_state import SessionDB
        from hermes_cli import profiles as profiles_mod
    except Exception as exc:
        return [], [{"profile": "all", "error": str(exc)}]
    try:
        targets = [(info.name, info.path) for info in profiles_mod.list_profiles()]
    except Exception as exc:
        errors.append({"profile": "all", "error": str(exc)})
        targets = [("default", profiles_mod.get_profile_dir("default"))]
    if not targets:
        targets = [("default", profiles_mod.get_profile_dir("default"))]
    per_profile = min(max(limit, 1), 100)
    for profile_name, home in targets:
        db_path = Path(home) / "state.db"
        if not db_path.exists():
            continue
        try:
            db = SessionDB(db_path=db_path, read_only=True)
        except Exception as exc:
            errors.append({"profile": profile_name, "error": str(exc)})
            continue
        try:
            rows = db.list_sessions_rich(
                limit=per_profile,
                offset=0,
                min_message_count=1,
                include_archived=False,
                archived_only=False,
                order_by_last_active=True,
            )
        except Exception as exc:
            # Older profile DBs may not have newer session columns such as
            # archived. Treat those as non-fatal for Mission Control grouping:
            # default/current profile sessions should still render.
            errors.append({"profile": profile_name, "error": str(exc)})
            continue
        finally:
            db.close()
        for row in rows:
            row["profile"] = profile_name
            row["is_default_profile"] = profile_name == "default"
            sessions.append(row)
    sessions.sort(key=lambda item: item.get("last_active") or item.get("started_at") or 0, reverse=True)
    return sessions[:limit], errors


def _project_sessions_projection(limit: int) -> dict[str, Any]:
    projects = _latest_workspace_records(ProjectRecord, limit)
    project_ids = [item.get("record", {}).get("project_id", "") for item in projects]
    active_links = _active_session_project_links(limit)
    sessions, errors = _read_profile_sessions_for_project_links(limit)
    groups = [
        {
            "project_id": item.get("record", {}).get("project_id", ""),
            "name": item.get("record", {}).get("name", ""),
            "sessions": [],
            "linked_session_count": 0,
            "unassigned_suggestion_count": 0,
        }
        for item in projects
    ]
    by_project = {group["project_id"]: group for group in groups}
    unassigned = {
        "project_id": "unassigned-general",
        "name": "Unassigned / General",
        "sessions": [],
        "linked_session_count": 0,
        "unassigned_suggestion_count": 0,
    }
    for session in sessions:
        durable = _session_durable_id(session)
        link_item = active_links.get(durable)
        link = link_item.get("record", {}) if link_item else None
        if link and link.get("project_id") in by_project:
            payload = _session_projection_payload(session, link=link)
            by_project[link["project_id"]]["sessions"].append(payload)
            continue
        suggested = _suggest_project_id_for_session(session)
        payload = _session_projection_payload(session, suggested_project_id=suggested if suggested in project_ids else "")
        unassigned["sessions"].append(payload)
        if payload["suggested_project_id"]:
            unassigned["unassigned_suggestion_count"] += 1
    for group in groups:
        group["linked_session_count"] = len(group["sessions"])
        group["sessions"] = group["sessions"][:5]
    unassigned["sessions"] = unassigned["sessions"][:10]
    return {
        "groups": groups + [unassigned],
        "errors": errors,
        "session_count": len(sessions),
        "active_link_count": len(active_links),
    }


def _safe_file_level(path: Path, char_limit: int) -> dict[str, Any]:
    try:
        if not path.exists():
            return {
                "path": str(path),
                "exists": False,
                "bytes": 0,
                "chars": 0,
                "lines": 0,
                "limit_chars": char_limit,
                "percent_used": 0,
            }
        raw = path.read_text(encoding="utf-8", errors="replace")
        chars = len(raw)
        percent = int(round((chars / char_limit) * 100)) if char_limit > 0 else 0
        return {
            "path": str(path),
            "exists": True,
            "bytes": path.stat().st_size,
            "chars": chars,
            "lines": len(raw.splitlines()),
            "limit_chars": char_limit,
            "percent_used": percent,
        }
    except Exception as exc:
        return {
            "path": str(path),
            "exists": False,
            "bytes": 0,
            "chars": 0,
            "lines": 0,
            "limit_chars": char_limit,
            "percent_used": 0,
            "error": str(exc),
        }


def _mount_point_for_path(path: Path) -> str:
    try:
        resolved = path.resolve(strict=False)
    except Exception:
        resolved = path.absolute()
    if os.name == "nt":
        return Path(resolved.anchor or resolved.drive or str(resolved)).as_posix()

    best = Path("/")
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        mounts = []
    for line in mounts:
        parts = line.split()
        if len(parts) < 2:
            continue
        mount = Path(parts[1].replace("\\040", " "))
        try:
            resolved.relative_to(mount)
        except ValueError:
            continue
        if len(mount.parts) > len(best.parts):
            best = mount
    return str(best)


def _profile_mount_usage(path: Path) -> dict[str, Any]:
    mount_path = _mount_point_for_path(path)
    try:
        usage_path = path
        while not usage_path.exists() and usage_path.parent != usage_path:
            usage_path = usage_path.parent
        usage = shutil.disk_usage(usage_path)
    except Exception as exc:
        return {
            "path": mount_path,
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "percent_used": 0,
            "error": str(exc),
        }
    percent_used = int(round((usage.used / usage.total) * 100)) if usage.total > 0 else 0
    return {
        "path": mount_path,
        "total_bytes": int(usage.total),
        "used_bytes": int(usage.used),
        "free_bytes": int(usage.free),
        "percent_used": percent_used,
    }


def _path_disk_usage_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        if path.is_file() or path.is_symlink():
            return int(path.stat().st_size)
        total = 0
        try:
            total += int(path.lstat().st_size)
        except OSError:
            pass
        for root, dirs, files in os.walk(path):
            for name in files:
                try:
                    total += int((Path(root) / name).lstat().st_size)
                except OSError:
                    continue
            for name in dirs:
                try:
                    total += int((Path(root) / name).lstat().st_size)
                except OSError:
                    continue
        return total
    except Exception:
        return 0


def _safe_storage_level(path: Path) -> dict[str, Any]:
    try:
        return {
            "path": str(path),
            "exists": path.exists(),
            "bytes": _path_disk_usage_bytes(path),
        }
    except Exception as exc:
        return {
            "path": str(path),
            "exists": False,
            "bytes": 0,
            "error": str(exc),
        }


def _sum_storage_levels(levels: list[dict[str, Any]]) -> int:
    return sum(int(level.get("bytes") or 0) for level in levels)


def _profile_data_storage(profile_name: str, home: Path) -> dict[str, Any]:
    if profile_name == "default":
        components = {
            "state": _safe_storage_level(home / "state.db"),
            "sessions": _safe_storage_level(home / "sessions"),
            "memories": _safe_storage_level(home / "memories"),
        }
        return {
            "path": str(home),
            "scope": "default_profile_state_sessions_memories",
            "exists": home.exists(),
            "bytes": _sum_storage_levels(list(components.values())),
            "components": components,
        }

    components = {
        "state": _safe_storage_level(home / "state.db"),
        "sessions": _safe_storage_level(home / "sessions"),
        "memories": _safe_storage_level(home / "memories"),
    }
    return {
        "path": str(home),
        "scope": "profile_directory",
        "exists": home.exists(),
        "bytes": _path_disk_usage_bytes(home),
        "components": components,
    }


def _profile_memory_storage_projection() -> dict[str, Any]:
    now = time.monotonic()
    cached = _PROFILE_STORAGE_CACHE.get("payload")
    if cached is not None and now < float(_PROFILE_STORAGE_CACHE.get("expires_at") or 0):
        return cached

    errors: list[dict[str, str]] = []
    try:
        from hermes_cli import profiles as profiles_mod
    except Exception as exc:
        return {"profiles": [], "errors": [{"profile": "all", "error": str(exc)}]}

    try:
        targets = [(info.name, Path(info.path)) for info in profiles_mod.list_profiles()]
    except Exception as exc:
        errors.append({"profile": "all", "error": str(exc)})
        targets = [("default", profiles_mod.get_profile_dir("default"))]
    if not targets:
        targets = [("default", profiles_mod.get_profile_dir("default"))]

    profiles: list[dict[str, Any]] = []
    total_profile_data_bytes = 0
    total_memory_bytes = 0
    total_user_bytes = 0
    mount_errors: list[dict[str, str]] = []
    for profile_name, home in targets:
        memory_file = _safe_file_level(Path(home) / "memories" / "MEMORY.md", 2200)
        user_file = _safe_file_level(Path(home) / "memories" / "USER.md", 1375)
        recall_file_bytes = int(memory_file.get("bytes") or 0) + int(user_file.get("bytes") or 0)
        profile_data = _profile_data_storage(profile_name, Path(home))
        mount = _profile_mount_usage(Path(home))
        if mount.get("error"):
            mount_errors.append({"profile": profile_name, "error": str(mount["error"])})
        total_profile_data_bytes += int(profile_data.get("bytes") or 0)
        total_memory_bytes += int(memory_file.get("bytes") or 0)
        total_user_bytes += int(user_file.get("bytes") or 0)
        profiles.append({
            "profile": profile_name,
            "home": str(home),
            "data": profile_data,
            "memory": memory_file,
            "mount": mount,
            "recall_file_bytes": recall_file_bytes,
            "user": user_file,
            "total_bytes": int(profile_data.get("bytes") or 0),
        })

    payload = {
        "profiles": profiles,
        "profile_count": len(profiles),
        "total_profile_data_bytes": total_profile_data_bytes,
        "total_memory_bytes": total_memory_bytes,
        "total_recall_file_bytes": total_memory_bytes + total_user_bytes,
        "total_user_bytes": total_user_bytes,
        "total_bytes": total_profile_data_bytes,
        "errors": [*errors, *mount_errors],
    }
    _PROFILE_STORAGE_CACHE["payload"] = payload
    _PROFILE_STORAGE_CACHE["expires_at"] = now + PROFILE_STORAGE_CACHE_SECONDS
    return payload


def _build_project_record(payload: dict[str, Any]) -> ProjectRecord:
    name = _workspace_text(payload.get("name"), max_chars=120)
    if not name:
        raise HTTPException(status_code=422, detail="project name is required")
    now = _utc_now()
    project_id = _workspace_text(payload.get("project_id"), max_chars=120) or f"project-{uuid.uuid4().hex[:12]}"
    return ProjectRecord(
        project_id=project_id,
        name=name,
        status=_workspace_text(payload.get("status"), max_chars=240),
        current_goal=_workspace_text(payload.get("current_goal")),
        next_recommended_lane=_workspace_text(payload.get("next_recommended_lane")),
        mistakes_guards=_workspace_text(payload.get("mistakes_guards")),
        source_of_truth=_workspace_text(payload.get("source_of_truth"), max_chars=240),
        profile=_workspace_text(payload.get("profile"), max_chars=80),
        created_at=now,
        updated_at=now,
        metadata={"source": "mission_control_project_workspace_pr_a"},
    )


def _build_project_brief_record(payload: dict[str, Any]) -> ProjectBriefRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    name = _workspace_text(payload.get("name"), max_chars=120)
    outcome = _workspace_text(payload.get("outcome"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not name:
        raise HTTPException(status_code=422, detail="project brief name is required")
    if not outcome:
        raise HTTPException(status_code=422, detail="project outcome is required")
    now = _utc_now()
    brief_id = _workspace_text(payload.get("brief_id"), max_chars=120) or f"project-brief-{uuid.uuid4().hex[:12]}"
    status = _normalized_control_plane_status(payload.get("status"), PROJECT_BRIEF_STATUSES, "draft")
    return ProjectBriefRecord(
        brief_id=brief_id,
        project_id=project_id,
        name=name,
        outcome=outcome,
        audience=_workspace_text(payload.get("audience")),
        source_of_truth=_workspace_text(payload.get("source_of_truth"), max_chars=240),
        success_criteria=_workspace_list(payload.get("success_criteria")),
        constraints=_workspace_list(payload.get("constraints")),
        forbidden_actions=_workspace_list(payload.get("forbidden_actions")),
        approval_rules=_workspace_list(payload.get("approval_rules")),
        context_pack_path=_workspace_text(payload.get("context_pack_path"), max_chars=240),
        status=status,
        created_at=now,
        updated_at=now,
        metadata={
            "source": "mission_control_project_intake_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "challenge_gate_required": True,
        },
    )


def _build_challenge_review_record(payload: dict[str, Any]) -> ChallengeReviewRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    request_summary = _workspace_text(payload.get("request_summary"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not request_summary:
        raise HTTPException(status_code=422, detail="request_summary is required")
    decision_state = _normalized_control_plane_status(
        payload.get("decision_state"),
        CHALLENGE_DECISION_STATES,
        "needs_spec_first",
    )
    now = _utc_now()
    review_id = _workspace_text(payload.get("review_id"), max_chars=120) or f"challenge-review-{uuid.uuid4().hex[:12]}"
    status = _normalized_control_plane_status(payload.get("status"), CHALLENGE_REVIEW_STATUSES, "draft")
    return ChallengeReviewRecord(
        review_id=review_id,
        project_id=project_id,
        request_summary=request_summary,
        decision_state=decision_state,
        challenge_categories=_workspace_enum_list(
            payload.get("challenge_categories"),
            CHALLENGE_REVIEW_CATEGORIES,
            "challenge_categories",
        ),
        blocking_verdicts=_workspace_enum_list(
            payload.get("blocking_verdicts"),
            CHALLENGE_BLOCKING_VERDICTS,
            "blocking_verdicts",
        ),
        recommended_path=_workspace_text(payload.get("recommended_path"), max_chars=MAX_WORKSPACE_PROMPT_CHARS),
        concerns=_workspace_list(payload.get("concerns")),
        questions=_workspace_list(payload.get("questions")),
        required_spec_updates=_workspace_list(payload.get("required_spec_updates")),
        required_approvals=_workspace_list(payload.get("required_approvals")),
        suggested_lane_title=_workspace_text(payload.get("suggested_lane_title"), max_chars=180),
        status=status,
        created_at=now,
        reviewed_by=_workspace_text(payload.get("reviewed_by"), max_chars=80),
        metadata={
            "source": "mission_control_challenge_gate_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "can_start_lane": decision_state == "clear_and_safe",
            "challenge_category_options": sorted(CHALLENGE_REVIEW_CATEGORIES),
            "blocking_verdict_options": sorted(CHALLENGE_BLOCKING_VERDICTS),
        },
    )


def _build_lane_request_record(payload: dict[str, Any]) -> LaneRequestRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    title = _workspace_text(payload.get("title"), max_chars=180)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not title:
        raise HTTPException(status_code=422, detail="lane request title is required")
    now = _utc_now()
    lane_request_id = _workspace_text(payload.get("lane_request_id"), max_chars=120) or f"lane-request-{uuid.uuid4().hex[:12]}"
    draft_prompt = _workspace_text(payload.get("draft_prompt"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    return LaneRequestRecord(
        lane_request_id=lane_request_id,
        project_id=project_id,
        title=title,
        mode=_workspace_text(payload.get("mode"), max_chars=160) or "read-only/manual-copy",
        objective=_workspace_text(payload.get("objective")),
        allowed_actions=_workspace_list(payload.get("allowed_actions")),
        forbidden_actions=_workspace_list(payload.get("forbidden_actions")),
        stop_conditions=_workspace_list(payload.get("stop_conditions")),
        expected_report_format=_workspace_list(payload.get("expected_report_format")),
        draft_prompt=draft_prompt,
        status="draft",
        created_at=now,
        updated_at=now,
        metadata={
            "source": "mission_control_project_workspace_pr_a",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
        },
    )


def _build_jenny_report_record(payload: dict[str, Any]) -> JennyReportRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    summary = _workspace_text(payload.get("summary"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not summary:
        raise HTTPException(status_code=422, detail="report summary is required")
    now = _utc_now()
    report_id = _workspace_text(payload.get("report_id"), max_chars=120) or f"jenny-report-{uuid.uuid4().hex[:12]}"
    return JennyReportRecord(
        report_id=report_id,
        project_id=project_id,
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        summary=summary,
        result=_workspace_text(payload.get("result"), max_chars=MAX_WORKSPACE_PROMPT_CHARS),
        changed_files=_workspace_list(payload.get("changed_files")),
        tests=_workspace_list(payload.get("tests")),
        risks=_workspace_list(payload.get("risks")),
        next_recommended_lane=_workspace_text(payload.get("next_recommended_lane")),
        created_at=now,
        metadata={
            "source": "mission_control_manual_jenny_report_inbox_pr_b",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "artifact_links": _workspace_list(payload.get("artifact_links")),
        },
    )


def _build_jenny_bridge_request_record(payload: dict[str, Any]) -> JennyBridgeMessageRequestRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    message = _workspace_text(payload.get("message"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    user_message = _workspace_text(payload.get("user_message"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    now = _utc_now()
    request_id = _workspace_text(payload.get("request_id"), max_chars=120) or f"jenny-bridge-request-{uuid.uuid4().hex[:12]}"
    return JennyBridgeMessageRequestRecord(
        request_id=request_id,
        project_id=project_id,
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        sender=_workspace_text(payload.get("sender"), max_chars=80) or "travis",
        target_agent=_workspace_text(payload.get("target_agent"), max_chars=80) or "jenny",
        message=message,
        status=_workspace_text(payload.get("status"), max_chars=80) or "queued",
        ack_key=_workspace_text(payload.get("ack_key"), max_chars=160),
        created_at=now,
        metadata={
            "source": "mission_control_jenny_bridge_v1",
            "bridge_direction": "outbound",
            "manual_copy_only": False,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "execution_enabled": False,
            "requires_external_jenny_poller": True,
            "dedupe_key": _workspace_text(payload.get("dedupe_key"), max_chars=160),
            "user_message": user_message,
        },
    )


def _build_jenny_bridge_response_record(payload: dict[str, Any]) -> JennyBridgeMessageResponseRecord:
    request_id = _workspace_text(payload.get("request_id"), max_chars=120)
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    message = _workspace_text(payload.get("message"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not request_id:
        raise HTTPException(status_code=422, detail="request_id is required")
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    now = _utc_now()
    response_id = _workspace_text(payload.get("response_id"), max_chars=120) or f"jenny-bridge-response-{uuid.uuid4().hex[:12]}"
    return JennyBridgeMessageResponseRecord(
        response_id=response_id,
        request_id=request_id,
        project_id=project_id,
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        responder=_workspace_text(payload.get("responder"), max_chars=80) or "jenny",
        message=message,
        status=_workspace_text(payload.get("status"), max_chars=80) or "received",
        created_at=now,
        metadata={
            "source": "mission_control_jenny_bridge_v1",
            "bridge_direction": "inbound",
            "manual_copy_only": False,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "execution_enabled": False,
            "external_jenny_response": True,
        },
    )


JENNY_REPLY_REVIEW_DECISIONS = {"accepted", "needs_evidence", "needs_safer_plan"}


def _build_jenny_reply_review_record(payload: dict[str, Any]) -> JennyReplyReviewRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    response_id = _workspace_text(payload.get("response_id"), max_chars=160)
    decision = _workspace_text(payload.get("decision"), max_chars=80)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not response_id:
        raise HTTPException(status_code=422, detail="response_id is required")
    if decision not in JENNY_REPLY_REVIEW_DECISIONS:
        raise HTTPException(status_code=422, detail="decision must be one of: accepted, needs_evidence, needs_safer_plan")
    now = _utc_now()
    review_id = _workspace_text(payload.get("review_id"), max_chars=120) or f"jenny-reply-review-{uuid.uuid4().hex[:12]}"
    return JennyReplyReviewRecord(
        review_id=review_id,
        project_id=project_id,
        response_id=response_id,
        request_id=_workspace_text(payload.get("request_id"), max_chars=160),
        decision=decision,
        reviewer=_workspace_text(payload.get("reviewer"), max_chars=80) or "travis",
        note=_workspace_text(payload.get("note"), max_chars=MAX_WORKSPACE_PROMPT_CHARS),
        created_at=now,
        metadata={
            "source": "mission_control_jenny_reply_review_v1",
            "display_only": True,
            "manual_start_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "execution_enabled": False,
            "worker_enabled": False,
            "timer_enabled": False,
            "trusted_for_execution": False,
            "inert_context_only": True,
        },
    )


def _normalized_control_plane_status(value: Any, allowed: set[str], default: str) -> str:
    status = _workspace_text(value, max_chars=80) or default
    if status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of: {', '.join(sorted(allowed))}")
    return status


def _normalized_control_plane_action_class(value: Any) -> str:
    action_class = _workspace_text(value, max_chars=80)
    if action_class not in APPROVAL_ACTION_CLASSES:
        raise HTTPException(status_code=422, detail="invalid action_class")
    return action_class


def _normalized_run_lane_type(value: Any) -> str:
    lane_type = _workspace_text(value, max_chars=80)
    if lane_type not in RUN_LANE_TYPES:
        raise HTTPException(status_code=422, detail="invalid lane_type")
    return lane_type


def _looks_broad_approval(value: str) -> bool:
    text = value.strip().lower()
    if not text:
        return True
    if text in BROAD_APPROVAL_VALUES:
        return True
    return any(phrase in text for phrase in ("all actions", "any action", "global execution", "unlimited approval"))


def _reject_broad_actions(actions: tuple[str, ...]) -> None:
    for action in actions:
        if action.strip().lower() in BROAD_APPROVAL_VALUES:
            raise HTTPException(status_code=422, detail="broad approval actions are not allowed")


def _build_approval_record(payload: dict[str, Any]) -> ApprovalRecord:
    action_class = _normalized_control_plane_action_class(payload.get("action_class"))
    status = _normalized_control_plane_status(payload.get("status"), APPROVAL_STATUSES, "proposed")
    approval_scope = _workspace_text(payload.get("approval_scope"), max_chars=MAX_WORKSPACE_TEXT_CHARS)
    approved_actions = _workspace_list(payload.get("approved_actions"))
    forbidden_actions = _workspace_list(payload.get("forbidden_actions"))
    if _looks_broad_approval(approval_scope):
        raise HTTPException(status_code=422, detail="approval_scope must be exact and bounded")
    _reject_broad_actions(approved_actions)
    if action_class in DANGEROUS_APPROVAL_ACTION_CLASSES and status != "proposed":
        raise HTTPException(status_code=422, detail="dangerous approvals may only be proposed/display-only in this backend foundation")
    approval_mode = _workspace_text(payload.get("approval_mode"), max_chars=40) or "one_time"
    if approval_mode != "one_time":
        raise HTTPException(status_code=422, detail="approval_mode must be one_time in this backend foundation")
    now = _utc_now()
    return ApprovalRecord(
        approval_id=_workspace_text(payload.get("approval_id"), max_chars=120) or f"approval-{uuid.uuid4().hex[:12]}",
        project_id=_workspace_text(payload.get("project_id"), max_chars=120),
        session_id=_workspace_text(payload.get("session_id"), max_chars=160),
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        run_id=_workspace_text(payload.get("run_id"), max_chars=120),
        action_class=action_class,
        approval_scope=approval_scope,
        approved_actions=approved_actions,
        forbidden_actions=forbidden_actions,
        status=status,
        approval_mode=approval_mode,
        approved_by=_workspace_text(payload.get("approved_by"), max_chars=120),
        approval_source=_workspace_text(payload.get("approval_source"), max_chars=80),
        approval_text=_workspace_text(payload.get("approval_text"), max_chars=MAX_WORKSPACE_TEXT_CHARS),
        created_at=_workspace_text(payload.get("created_at"), max_chars=80) or now,
        approved_at=_workspace_text(payload.get("approved_at"), max_chars=80),
        expires_at=_workspace_text(payload.get("expires_at"), max_chars=80) or None,
        consumed_at=_workspace_text(payload.get("consumed_at"), max_chars=80),
        baseline_runtime_path=_workspace_text(payload.get("baseline_runtime_path"), max_chars=240),
        baseline_head=_workspace_text(payload.get("baseline_head"), max_chars=80),
        packet_hash=_workspace_text(payload.get("packet_hash"), max_chars=80),
        scope_fingerprint=_workspace_text(payload.get("scope_fingerprint"), max_chars=120),
        metadata={
            "source": "mission_control_control_plane_approval_backend_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
            "dangerous_action_display_only": action_class in DANGEROUS_APPROVAL_ACTION_CLASSES,
        },
    )


def _build_run_record(payload: dict[str, Any]) -> RunRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    lane_type = _normalized_run_lane_type(payload.get("lane_type"))
    status = _normalized_control_plane_status(payload.get("status"), RUN_STATUSES, "requested")
    execution_mode = _workspace_text(payload.get("execution_mode"), max_chars=80) or "manual_copy"
    if execution_mode != "manual_copy":
        raise HTTPException(status_code=422, detail="execution_mode must remain manual_copy in this backend foundation")
    return RunRecord(
        run_id=_workspace_text(payload.get("run_id"), max_chars=120) or f"run-{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        approval_id=_workspace_text(payload.get("approval_id"), max_chars=120),
        lane_type=lane_type,
        title=_workspace_text(payload.get("title"), max_chars=180),
        objective=_workspace_text(payload.get("objective"), max_chars=MAX_WORKSPACE_TEXT_CHARS),
        status=status,
        execution_mode=execution_mode,
        allowed_actions=_workspace_list(payload.get("allowed_actions")),
        forbidden_actions=_workspace_list(payload.get("forbidden_actions")),
        stop_conditions=_workspace_list(payload.get("stop_conditions")),
        baseline_runtime_path=_workspace_text(payload.get("baseline_runtime_path"), max_chars=240),
        baseline_head=_workspace_text(payload.get("baseline_head"), max_chars=80),
        runtime_guard_state=_workspace_text(payload.get("runtime_guard_state"), max_chars=80),
        dispatch_state=False,
        active_lane_count_at_start=_workspace_int(payload.get("active_lane_count_at_start")),
        agent_identity=_workspace_text(payload.get("agent_identity"), max_chars=120),
        session_id=_workspace_text(payload.get("session_id"), max_chars=160),
        source=_workspace_text(payload.get("source"), max_chars=80),
        started_at=_workspace_text(payload.get("started_at"), max_chars=80),
        stopped_at=_workspace_text(payload.get("stopped_at"), max_chars=80),
        stop_reason=_workspace_text(payload.get("stop_reason"), max_chars=MAX_WORKSPACE_TEXT_CHARS),
        safety_gate_status=_workspace_text(payload.get("safety_gate_status"), max_chars=80),
        safety_gate_reasons=_workspace_list(payload.get("safety_gate_reasons")),
        report_ids=_workspace_list(payload.get("report_ids")),
        result_record_ids=_workspace_list(payload.get("result_record_ids")),
        metadata={
            "source": "mission_control_control_plane_run_backend_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
        },
    )


def _build_report_record(payload: dict[str, Any]) -> ReportRecord:
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    summary = _workspace_text(payload.get("summary"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    if not project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    if not summary:
        raise HTTPException(status_code=422, detail="summary is required")
    status = _normalized_control_plane_status(payload.get("status"), REPORT_STATUSES, "received")
    now = _utc_now()
    return ReportRecord(
        report_id=_workspace_text(payload.get("report_id"), max_chars=120) or f"report-{uuid.uuid4().hex[:12]}",
        run_id=_workspace_text(payload.get("run_id"), max_chars=120),
        approval_id=_workspace_text(payload.get("approval_id"), max_chars=120),
        project_id=project_id,
        lane_request_id=_workspace_text(payload.get("lane_request_id"), max_chars=120),
        status=status,
        report_kind=_workspace_text(payload.get("report_kind"), max_chars=80) or "jenny_result",
        summary=summary,
        result=_workspace_text(payload.get("result"), max_chars=MAX_WORKSPACE_PROMPT_CHARS),
        risks=_workspace_list(payload.get("risks")),
        blockers=_workspace_list(payload.get("blockers")),
        changed_files=_workspace_list(payload.get("changed_files")),
        tests=_workspace_list(payload.get("tests")),
        next_recommended_lane=_workspace_text(payload.get("next_recommended_lane")),
        evidence_refs=_workspace_list(payload.get("evidence_refs")),
        artifact_refs=_workspace_list(payload.get("artifact_refs")),
        submitted_by=_workspace_text(payload.get("submitted_by"), max_chars=120),
        submitted_from=_workspace_text(payload.get("submitted_from"), max_chars=120),
        created_at=_workspace_text(payload.get("created_at"), max_chars=80) or now,
        reviewed_at=_workspace_text(payload.get("reviewed_at"), max_chars=80),
        reviewed_by=_workspace_text(payload.get("reviewed_by"), max_chars=120),
        redaction_status=_workspace_text(payload.get("redaction_status"), max_chars=120) or "operator_supplied_redacted",
        metadata={
            "source": "mission_control_control_plane_report_backend_v1",
            "manual_copy_only": True,
            "send_to_jenny_enabled": False,
            "dispatch_enabled": False,
        },
    )


def _safe_records_limit(limit: str | None) -> int:
    if limit is None:
        return DEFAULT_RECORDS_LIMIT
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_RECORDS_LIMIT
    if parsed <= 0:
        return DEFAULT_RECORDS_LIMIT
    return min(parsed, MAX_RECORDS_LIMIT)


def _record_counts_with_state() -> tuple[int, Counter[str], str, str | None]:
    path = record_store_path()
    state = _record_store_state(path)
    if state != "ok":
        return 0, Counter(), state, None

    store = JsonlRecordStore(path)
    counts: Counter[str] = Counter()
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                entry = store._decode_line(line, line_number)
                decoded = store._decode_record(entry, line_number)
                counts[_record_type(decoded)] += 1
    except RecordStoreError as exc:
        return 0, Counter(), "malformed", str(exc)
    if not counts:
        return 0, Counter(), "empty", None
    return sum(counts.values()), counts, "ok", None


def _record_type(record: Any) -> str:
    return str(getattr(record, "record_type", type(record).__name__))


def _strip_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_metadata(item)
            for key, item in value.items()
            if key != "metadata"
        }
    if isinstance(value, list):
        return [_strip_metadata(item) for item in value]
    return value


def _record_payload(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
        if isinstance(payload, dict):
            metadata = payload.pop("metadata", {}) or {}
            payload = _strip_metadata(payload)
            if isinstance(record, OperatorAction):
                if isinstance(metadata, dict) and "source" in metadata:
                    payload["source"] = metadata["source"]
            if isinstance(record, (GoalContract, TaskControlEnvelope)):
                record_id = payload.get("goal_id") or payload.get("envelope_id") or ""
                linked_task = linked_kanban_task_payload(record, record_id=record_id)
                if linked_task is not None:
                    payload["linked_kanban_task"] = linked_task
            return payload
    return {}


def _serialized_indexed_records(records: tuple[tuple[int, Any], ...]) -> list[dict[str, Any]]:
    return [
        {
            "record_index": index,
            "record_type": _record_type(record),
            "record": _record_payload(record),
        }
        for index, record in records
    ]


def _envelope_summary(envelope: Any) -> dict[str, Any]:
    payload = _record_payload(envelope)
    summary = {
        "envelope_id": payload.get("envelope_id", ""),
        "active_lane": payload.get("active_lane", ""),
        "mode": payload.get("mode", ""),
        "allowed_actions": list(payload.get("allowed_actions") or ()),
        "forbidden_actions": list(payload.get("forbidden_actions") or ()),
        "current_repo": payload.get("current_repo", ""),
        "expected_systems_files": list(payload.get("expected_systems_files") or ()),
        "stop_condition": payload.get("stop_condition", ""),
        "other_threads_excluded": list(payload.get("other_threads_excluded") or ()),
        "report_requirements": list(payload.get("report_requirements") or ()),
        "risk_level": payload.get("risk_level", ""),
        "approval_required": bool(payload.get("approval_required", False)),
        "approval_slice_ids": list(payload.get("approval_slice_ids") or ()),
        "evidence_ids": list(payload.get("evidence_ids") or ()),
        "token_context_policy": payload.get("token_context_policy", ""),
        "created_at": payload.get("created_at", ""),
        "status": payload.get("status", ""),
    }
    linked_task = linked_kanban_task_payload(envelope, record_id=summary["envelope_id"])
    if linked_task is not None:
        summary["linked_kanban_task"] = linked_task
    return summary


def _empty_start_gate_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "has_active_envelope": False,
        "source": "none",
        "record_index": None,
        "mission_id": None,
        "mission_title": None,
        "mission_created_at": None,
        "envelope": None,
    }


def _empty_approval_slices_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "none",
        "count": 0,
        "approval_slices": [],
    }


def _empty_evidence_cards_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "none",
        "count": 0,
        "evidence_cards": [],
    }


def _empty_operator_actions_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "none",
        "count": 0,
        "operator_actions": [],
    }


def _empty_task_control_envelopes_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "none",
        "count": 0,
        "task_control_envelopes": [],
    }


def _empty_start_gate_checks_payload(store_status: str, error: str | None) -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "none",
        "count": 0,
        "start_gate_checks": [],
    }


def _bounded_latest(items: tuple[Any, ...], limit: int = 10) -> tuple[Any, ...]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def _approval_summary(approval: Any, evidence_count: int | None = None) -> dict[str, Any]:
    metadata = getattr(approval, "metadata", {}) or {}
    has_legacy_fields = any(
        (
            getattr(approval, "lane", ""),
            getattr(approval, "mode", ""),
            getattr(approval, "approved_actions", ()) or (),
            getattr(approval, "forbidden_actions", ()) or (),
            getattr(approval, "approver", ""),
            getattr(approval, "approved_at", ""),
        )
    )
    if has_legacy_fields:
        summary = {
            "approval_id": getattr(approval, "approval_id", "")
            or getattr(approval, "approval_slice_id", ""),
            "lane": getattr(approval, "lane", ""),
            "mode": getattr(approval, "mode", ""),
            "approver": getattr(approval, "approver", ""),
            "approved_at": getattr(approval, "approved_at", ""),
            "expires_at": getattr(approval, "expires_at", None),
            "approved_action_count": len(getattr(approval, "approved_actions", ()) or ()),
            "forbidden_action_count": len(getattr(approval, "forbidden_actions", ()) or ()),
        }
        if evidence_count is not None:
            summary["evidence_count"] = evidence_count
    else:
        approval_evidence_count = len(getattr(approval, "evidence_ids", ()) or ())
        summary = {
            "approval_slice_id": getattr(approval, "approval_slice_id", ""),
            "related_action_id": getattr(approval, "related_action_id", ""),
            "approval_type": getattr(approval, "approval_type", ""),
            "decision_state": getattr(approval, "decision_state", ""),
            "required_by": getattr(approval, "required_by", ""),
            "reason": getattr(approval, "reason", ""),
            "safety_condition_count": len(getattr(approval, "safety_conditions", ()) or ()),
            "evidence_count": evidence_count if evidence_count is not None else approval_evidence_count,
            "created_at": getattr(approval, "created_at", ""),
            "expires_at": getattr(approval, "expires_at", None),
        }
    for key in ("status", "reason", "risk_class", "required_approver"):
        if key in metadata:
            summary[key] = metadata[key]
    return summary


def _evidence_summary(evidence: Any) -> dict[str, Any]:
    metadata = getattr(evidence, "metadata", {}) or {}
    artifact_refs = tuple(getattr(evidence, "artifact_refs", ()) or ())
    summary = {
        "evidence_id": getattr(evidence, "evidence_id", ""),
        "summary": getattr(evidence, "summary", ""),
        "artifact_count": len(artifact_refs),
        "artifact_refs_count": len(artifact_refs),
    }
    for key in (
        "related_lane",
        "related_action_id",
        "related_record_type",
        "evidence_type",
        "source_label",
        "created_at",
    ):
        value = getattr(evidence, key, "")
        if value:
            summary[key] = value
    risk_notes = tuple(getattr(evidence, "risk_notes", ()) or ())
    if risk_notes:
        summary["risk_note_count"] = len(risk_notes)
    for key in ("title", "type", "source"):
        if key in metadata:
            summary[key] = metadata[key]
    return summary


def _operator_action_summary(action: Any) -> dict[str, Any]:
    metadata = getattr(action, "metadata", {}) or {}
    evidence_ids = tuple(getattr(action, "evidence_ids", ()) or ())
    summary = {
        "action_id": getattr(action, "action_id", ""),
        "title": getattr(action, "title", ""),
        "lane": getattr(action, "lane", ""),
        "mode": getattr(action, "mode", ""),
        "requested_action": getattr(action, "requested_action", ""),
        "risk_level": getattr(action, "risk_level", ""),
        "status": getattr(action, "status", ""),
        "required_approval": getattr(action, "required_approval", ""),
        "approval_id": getattr(action, "approval_id", ""),
        "evidence_count": len(evidence_ids),
        "stop_condition": getattr(action, "stop_condition", ""),
        "created_at": getattr(action, "created_at", ""),
        "expires_at": getattr(action, "expires_at", None),
    }
    if "source" in metadata:
        summary["source"] = metadata["source"]
    return summary


def _task_control_envelope_summary(envelope: Any) -> dict[str, Any]:
    approval_slice_ids = tuple(getattr(envelope, "approval_slice_ids", ()) or ())
    evidence_ids = tuple(getattr(envelope, "evidence_ids", ()) or ())
    summary = {
        "envelope_id": getattr(envelope, "envelope_id", ""),
        "active_lane": getattr(envelope, "active_lane", ""),
        "mode": getattr(envelope, "mode", ""),
        "allowed_action_count": len(getattr(envelope, "allowed_actions", ()) or ()),
        "forbidden_action_count": len(getattr(envelope, "forbidden_actions", ()) or ()),
        "stop_condition": getattr(envelope, "stop_condition", ""),
        "report_requirement_count": len(getattr(envelope, "report_requirements", ()) or ()),
        "risk_level": getattr(envelope, "risk_level", ""),
        "approval_required": bool(getattr(envelope, "approval_required", False)),
        "approval_slice_count": len(approval_slice_ids),
        "evidence_count": len(evidence_ids),
        "token_context_policy": getattr(envelope, "token_context_policy", ""),
        "created_at": getattr(envelope, "created_at", ""),
        "status": getattr(envelope, "status", ""),
    }
    linked_task = linked_kanban_task_payload(envelope, record_id=summary["envelope_id"])
    if linked_task is not None:
        summary["linked_kanban_task"] = linked_task
    return summary


def _start_gate_check_summary(check: Any) -> dict[str, Any]:
    return {
        "start_gate_id": getattr(check, "start_gate_id", ""),
        "envelope_id": getattr(check, "envelope_id", ""),
        "decision_state": getattr(check, "decision_state", ""),
        "reason_count": len(getattr(check, "reasons", ()) or ()),
        "blocked_action_count": len(getattr(check, "blocked_actions", ()) or ()),
        "required_approval_count": len(getattr(check, "required_approvals", ()) or ()),
        "dirty_worktree_state": getattr(check, "dirty_worktree_state", ""),
        "branch_safety_state": getattr(check, "branch_safety_state", ""),
        "secret_safety_state": getattr(check, "secret_safety_state", ""),
        "token_context_state": getattr(check, "token_context_state", ""),
        "created_at": getattr(check, "created_at", ""),
    }


def _sanitize_verifier_evidence_text(value: Any, *, max_chars: int = 240) -> str:
    text = str(value or "")
    text = _SECRET_LIKE_RE.sub("[redacted]", text)
    text = _PATH_LIKE_RE.sub("[path]", text)
    text = " ".join(text.split())
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def _sanitize_verifier_evidence_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    return [
        _sanitize_verifier_evidence_text(item)
        for item in items[:MAX_EVALUATION_LIST_ITEMS]
        if str(item).strip()
    ]


def _verifier_record_context(payload: dict[str, Any]) -> dict[str, str]:
    context: dict[str, str] = {}
    for key in sorted(_VERIFIER_EVIDENCE_FIELDS):
        context[key] = _sanitize_verifier_evidence_text(payload.get(key), max_chars=160)
    if not context.get("source"):
        context["source"] = "caller_supplied_workflow_state"
    return context


def _verifier_evidence_summary(record: VerifierWorkflowEvidenceRecord) -> dict[str, Any]:
    return record.to_dict()


def _build_verifier_evidence_record(
    payload: dict[str, Any],
    result: dict[str, Any],
) -> VerifierWorkflowEvidenceRecord:
    context = _verifier_record_context(payload)
    return VerifierWorkflowEvidenceRecord(
        record_id=f"verifier-workflow-{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        source=context["source"],
        lane_id=context["lane_id"],
        task_id=context["task_id"],
        domain_id=context["domain_id"],
        action_class=context["action_class"],
        decision_state=_sanitize_verifier_evidence_text(result.get("decision_state"), max_chars=80),
        would_block=bool(result.get("would_block", False)),
        reasons=tuple(_sanitize_verifier_evidence_list(result.get("reasons"))),
        blocked_actions=tuple(_sanitize_verifier_evidence_list(result.get("blocked_actions"))),
        required_approvals=tuple(_sanitize_verifier_evidence_list(result.get("required_approvals"))),
        unresolved_policy_fields=tuple(_sanitize_verifier_evidence_list(result.get("unresolved_policy_fields"))),
        dry_run_only=True,
        enforces_runtime=False,
    )


def _bounded_text(value: Any) -> str:
    text = str(value or "")
    if len(text) > MAX_EVALUATION_STRING_CHARS:
        return text[:MAX_EVALUATION_STRING_CHARS]
    return text


def _bounded_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    return [
        _bounded_text(item)
        for item in items[:MAX_EVALUATION_LIST_ITEMS]
        if str(item).strip()
    ]


def _bounded_evaluation_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    metadata: dict[str, str] = {}
    for key in sorted(_EVALUATION_METADATA_FIELDS):
        if key in value and len(metadata) < MAX_EVALUATION_METADATA_ITEMS:
            metadata[key] = _bounded_text(value[key])
    return metadata


def _compact_evaluation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in sorted(_EVALUATION_FIELDS):
        if key not in payload:
            continue
        if key in _EVALUATION_LIST_FIELDS:
            compact[key] = _bounded_text_list(payload[key])
        elif key == "approval_required":
            compact[key] = bool(payload[key])
        elif key == "metadata":
            compact[key] = _bounded_evaluation_metadata(payload[key])
        else:
            compact[key] = _bounded_text(payload[key])
    return compact


async def _read_compact_json_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_EVALUATION_BODY_BYTES:
        raise HTTPException(status_code=413, detail="evaluation payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return _compact_evaluation_payload(payload)


def _compact_guard_observed_state(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in sorted(_GUARD_OBSERVED_FIELDS):
        if key not in payload:
            continue
        if key in _GUARD_BOOL_FIELDS:
            compact[key] = payload[key] is True
        elif key in _GUARD_INT_FIELDS:
            try:
                compact[key] = int(payload[key])
            except (TypeError, ValueError):
                compact[key] = 0
        elif key in _GUARD_LIST_FIELDS:
            compact[key] = _bounded_text_list(payload[key])
        else:
            compact[key] = _bounded_text(payload[key])
    return compact


async def _read_guard_observed_json_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_EVALUATION_BODY_BYTES:
        raise HTTPException(status_code=413, detail="evaluation payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return _compact_guard_observed_state(payload)


def _compact_storage_observed_state(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in sorted(_STORAGE_OBSERVED_FIELDS):
        if key not in payload:
            continue
        if key in _STORAGE_BOOL_FIELDS:
            compact[key] = payload[key] is True
        elif key in _STORAGE_NUMBER_FIELDS:
            try:
                compact[key] = float(payload[key])
            except (TypeError, ValueError):
                compact[key] = 0.0
        else:
            compact[key] = _bounded_text(payload[key])
    return compact


async def _read_storage_observed_json_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_EVALUATION_BODY_BYTES:
        raise HTTPException(status_code=413, detail="evaluation payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return _compact_storage_observed_state(payload)


def _compact_verifier_observed_state(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in sorted(_VERIFIER_OBSERVED_FIELDS):
        if key not in payload:
            continue
        if key in _VERIFIER_BOOL_FIELDS:
            compact[key] = payload[key] is True
        else:
            compact[key] = _bounded_text(payload[key])
    return compact


async def _read_verifier_json_body(request: Request) -> tuple[dict[str, Any], dict[str, Any]]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_EVALUATION_BODY_BYTES:
        raise HTTPException(status_code=413, detail="evaluation payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return _compact_verifier_observed_state(payload), payload


def _compact_pr_merge_gate_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact: dict[str, Any] = {}
    for key in sorted(_PR_MERGE_GATE_EVIDENCE_FIELDS):
        if key not in value:
            continue
        if key in _PR_MERGE_GATE_BOOL_FIELDS:
            compact[key] = value[key] is True
        elif key in _PR_MERGE_GATE_LIST_FIELDS:
            compact[key] = _bounded_text_list(value[key])
        else:
            compact[key] = _bounded_text(value[key])
    return compact


def _compact_pr_merge_gate_state(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in sorted(_PR_MERGE_GATE_FIELDS):
        if key not in payload:
            continue
        if key == "verifier_evidence":
            compact[key] = _compact_pr_merge_gate_evidence(payload[key])
        else:
            compact[key] = _bounded_text(payload[key])
    return compact


async def _read_pr_merge_gate_json_body(request: Request) -> dict[str, Any]:
    payload = await _read_json_object_body(request)
    return _compact_pr_merge_gate_state(payload)


async def _read_json_object_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise HTTPException(status_code=415, detail="JSON body required")
    body = await request.body()
    if len(body) > MAX_EVALUATION_BODY_BYTES:
        raise HTTPException(status_code=413, detail="evaluation payload is too large")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="malformed JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return payload


def _compact_pr_merge_gate_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    enabled = (
        ((value.get("mission_control") or {}).get("enforcement") or {})
        .get("pr_merge_verifier_gate_enabled")
        is True
    )
    return {
        "mission_control": {
            "enforcement": {
                "pr_merge_verifier_gate_enabled": enabled,
            },
        },
    }


def _pr_merge_visibility_payload(config: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_pr_merge_lane_guard(config, packet)
    required_approvals = _bounded_text_list(result.get("required_approvals"))
    unresolved_policy_fields = _bounded_text_list(result.get("unresolved_policy_fields"))
    reasons = _bounded_text_list(result.get("reasons"))
    missing_reason_items = [
        reason
        for reason in reasons
        if "missing" in reason.casefold()
    ]
    missing_requirements = list(dict.fromkeys(
        item
        for item in missing_reason_items + required_approvals + unresolved_policy_fields
        if item
    ))
    evidence = packet.get("verifier_evidence") if isinstance(packet.get("verifier_evidence"), dict) else {}
    return {
        "guard_id": result.get("guard_id", "pr_merge_verifier_gate_v1"),
        "visibility_only": True,
        "label": "Visibility only. No approval, merge, deploy, or enforcement.",
        "enabled": bool(result.get("enabled", False)),
        "advisory_only": bool(result.get("advisory_only", True)),
        "stop_merge_lane": bool(result.get("stop_merge_lane", False)),
        "would_block": bool(result.get("would_block", False)),
        "decision_state": str(result.get("decision_state") or "unknown"),
        "repo": _bounded_text(packet.get("repo")),
        "pr_number": _bounded_text(packet.get("pr_number")),
        "base_branch": _bounded_text(packet.get("base_branch")),
        "head_commit": _bounded_text(packet.get("head_commit")),
        "packet_hash": _bounded_text(packet.get("packet_hash")),
        "evidence_record_id": _bounded_text(
            packet.get("verifier_evidence_record_id") or evidence.get("record_id")
        ),
        "reasons": reasons,
        "blocked_actions": _bounded_text_list(result.get("blocked_actions")),
        "missing_requirements": missing_requirements[:MAX_EVALUATION_LIST_ITEMS],
        "required_approvals": required_approvals,
        "unresolved_policy_fields": unresolved_policy_fields,
        "dry_run_only": True,
        "enforces_runtime": False,
    }


def _start_gate_decision_payload(check: StartGateCheck) -> dict[str, Any]:
    return {
        "start_gate_id": check.start_gate_id,
        "envelope_id": check.envelope_id,
        "decision_state": check.decision_state,
        "reasons": list(check.reasons),
        "blocked_actions": list(check.blocked_actions),
        "required_approvals": list(check.required_approvals),
        "dirty_worktree_state": check.dirty_worktree_state,
        "branch_safety_state": check.branch_safety_state,
        "secret_safety_state": check.secret_safety_state,
        "token_context_state": check.token_context_state,
        "created_at": check.created_at,
    }


def _sample_lane_preflight_envelope() -> TaskControlEnvelope:
    return TaskControlEnvelope(
        envelope_id="lane-preflight-fixed-sample",
        active_lane="PR-P read-only lane-preflight result visibility",
        mode="bounded implementation in a new clean worktree only",
        allowed_actions=(
            "add read-only lane preflight visibility",
            "run targeted tests",
        ),
        forbidden_actions=(
            "live enforcement",
            "tool execution",
            "approval execution",
            "persistent writes",
            "broad context loading",
        ),
        stop_condition="Stop after draft PR status report.",
        report_requirements=(
            "files changed",
            "tests run",
            "safety confirmation",
        ),
        approval_required=False,
        approval_slice_ids=(),
        token_context_policy="compact fixed sample only",
    )


def _sample_lane_preflight_request() -> dict[str, Any]:
    envelope = _sample_lane_preflight_envelope()
    return {
        "active_lane": envelope.active_lane,
        "mode": envelope.mode,
        "allowed_actions": list(envelope.allowed_actions),
        "forbidden_actions": list(envelope.forbidden_actions),
        "stop_condition": envelope.stop_condition,
        "report_requirements": list(envelope.report_requirements),
        "repo_target": "Travisaggie04/hermes-agent",
        "branch": "pr-p-lane-preflight-result-visibility",
        "worktree_state": "clean sample",
        "token_context_policy": envelope.token_context_policy,
        "requested_actions": [
            "add read-only lane preflight visibility",
        ],
        "approval_required": envelope.approval_required,
        "approval_slice_ids": list(envelope.approval_slice_ids),
    }


def _lane_preflight_visibility_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_state": str(result.get("decision_state") or ""),
        "would_block": bool(result.get("would_block", False)),
        "would_require_approval": bool(result.get("would_require_approval", False)),
        "reasons": _bounded_text_list(result.get("reasons")),
        "blocked_actions": _bounded_text_list(result.get("blocked_actions")),
        "required_approvals": _bounded_text_list(result.get("required_approvals")),
        "default_off": bool(result.get("default_off", True)),
        "dry_run_only": bool(result.get("dry_run_only", True)),
        "enforces_runtime": bool(result.get("enforces_runtime", False)),
    }


def _latest_mission_with_items(field_name: str) -> tuple[tuple[int, Any] | None, str, str | None]:
    missions, store_status, error = _load_latest_records_with_state(MissionBrief, limit=10)
    for index, record in reversed(missions):
        if getattr(record, field_name, ()):  # compact embedded context
            return (index, record), store_status, error
    return None, store_status, error


def _record_schema() -> dict[str, dict[str, Any]]:
    schema: dict[str, dict[str, Any]] = {}
    for record_type, record_class in sorted(RECORD_TYPES.items()):
        record_fields = fields(record_class) if is_dataclass(record_class) else ()
        schema[record_type] = {
            "fields": [
                field.name
                for field in record_fields
                if field.init
            ],
        }
    return schema


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "plugin": PLUGIN_NAME,
        **INERT_FLAGS,
    }


@router.get("/summary")
async def summary() -> dict[str, Any]:
    record_count, counts, store_status, error = _record_counts_with_state()
    latest_missions, mission_status, mission_error = _load_latest_records_with_state(MissionBrief, limit=1)
    if store_status == "ok" and mission_status == "malformed":
        store_status = mission_status
        error = mission_error
    latest_mission = latest_missions[-1][1] if latest_missions and store_status == "ok" else None
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "record_count": record_count,
        "record_types": dict(sorted(counts.items())),
        "latest_mission_title": getattr(latest_mission, "title", None),
        "latest_mission_created_at": getattr(latest_mission, "created_at", None),
    }


@router.get("/approval-slices")
async def approval_slices() -> dict[str, Any]:
    mission_match, store_status, error = _latest_mission_with_items("approvals")
    if mission_match is not None:
        _, mission = mission_match
        items = _bounded_latest(tuple(getattr(mission, "approvals", ()) or ()))
        evidence_count = len(getattr(mission, "evidence", ()) or ())
        summaries = [_approval_summary(item, evidence_count) for item in items]
        return {
            **INERT_FLAGS,
            "store_status": store_status,
            "error": error,
            "source": "MissionBrief.approvals",
            "count": len(summaries),
            "approval_slices": summaries,
        }

    standalone, standalone_status, standalone_error = _load_latest_records_with_state(ApprovalSlice, limit=10)
    if not standalone:
        return _empty_approval_slices_payload(standalone_status, standalone_error)
    summaries = [
        {"record_index": index, **_approval_summary(record)}
        for index, record in standalone
    ]
    return {
        **INERT_FLAGS,
        "store_status": standalone_status,
        "error": standalone_error,
        "source": "ApprovalSlice",
        "count": len(summaries),
        "approval_slices": summaries,
    }


@router.get("/evidence-cards")
async def evidence_cards() -> dict[str, Any]:
    mission_match, store_status, error = _latest_mission_with_items("evidence")
    if mission_match is not None:
        _, mission = mission_match
        items = _bounded_latest(tuple(getattr(mission, "evidence", ()) or ()))
        summaries = [_evidence_summary(item) for item in items]
        return {
            **INERT_FLAGS,
            "store_status": store_status,
            "error": error,
            "source": "MissionBrief.evidence",
            "count": len(summaries),
            "evidence_cards": summaries,
        }

    standalone, standalone_status, standalone_error = _load_latest_records_with_state(EvidenceCard, limit=10)
    if not standalone:
        return _empty_evidence_cards_payload(standalone_status, standalone_error)
    summaries = [
        {"record_index": index, **_evidence_summary(record)}
        for index, record in standalone
    ]
    return {
        **INERT_FLAGS,
        "store_status": standalone_status,
        "error": standalone_error,
        "source": "EvidenceCard",
        "count": len(summaries),
        "evidence_cards": summaries,
    }


@router.get("/operator-actions")
async def operator_actions() -> dict[str, Any]:
    standalone, store_status, error = _load_latest_records_with_state(OperatorAction, limit=10)
    if not standalone:
        return _empty_operator_actions_payload(store_status, error)
    summaries = [
        {"record_index": index, **_operator_action_summary(record)}
        for index, record in standalone
    ]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "OperatorAction",
        "count": len(summaries),
        "operator_actions": summaries,
    }


@router.get("/task-control-envelopes")
async def task_control_envelopes() -> dict[str, Any]:
    standalone, store_status, error = _load_latest_records_with_state(TaskControlEnvelope, limit=10)
    if not standalone:
        return _empty_task_control_envelopes_payload(store_status, error)
    summaries = [
        {"record_index": index, **_task_control_envelope_summary(record)}
        for index, record in standalone
    ]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "TaskControlEnvelope",
        "count": len(summaries),
        "task_control_envelopes": summaries,
    }


@router.get("/start-gate-checks")
async def start_gate_checks() -> dict[str, Any]:
    standalone, store_status, error = _load_latest_records_with_state(StartGateCheck, limit=10)
    if not standalone:
        return _empty_start_gate_checks_payload(store_status, error)
    summaries = [
        {"record_index": index, **_start_gate_check_summary(record)}
        for index, record in standalone
    ]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "StartGateCheck",
        "count": len(summaries),
        "start_gate_checks": summaries,
    }


@router.get("/global-resource-guard")
async def global_resource_guard() -> dict[str, Any]:
    guard = get_global_resource_guard_policy()
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "mission_control.global_resource_guard",
        "guard": guard,
    }


@router.post("/global-resource-guard/evaluate")
async def global_resource_guard_evaluate(request: Request) -> dict[str, Any]:
    observed_state = await _read_guard_observed_json_body(request)
    result = evaluate_global_resource_guard(observed_state)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "caller_supplied_observed_state",
        "stored": False,
        **result,
    }


@router.get("/storage-guard")
async def storage_guard() -> dict[str, Any]:
    guard = get_storage_guard_policy()
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "mission_control.storage_guard",
        "guard": guard,
    }


@router.post("/storage-guard/evaluate")
async def storage_guard_evaluate(request: Request) -> dict[str, Any]:
    observed_state = await _read_storage_observed_json_body(request)
    result = evaluate_storage_guard(observed_state)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "caller_supplied_storage_state",
        "stored": False,
        **result,
    }


@router.post("/storage-guard/cleanup-manifest")
async def storage_guard_cleanup_manifest(request: Request) -> dict[str, Any]:
    payload = await _read_json_object_body(request)
    manifest = build_storage_cleanup_manifest(payload)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        **manifest,
    }


@router.get("/verifier-workflow")
async def verifier_workflow() -> dict[str, Any]:
    workflow = get_verifier_workflow_policy()
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "mission_control.verifier_workflow",
        "workflow": workflow,
    }


@router.get("/pr-merge-verifier-gate")
async def pr_merge_verifier_gate() -> dict[str, Any]:
    gate = get_pr_merge_verifier_gate_policy()
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "mission_control.pr_merge_verifier_gate",
        "gate": gate,
    }


@router.get("/workspace-status")
async def workspace_status() -> dict[str, Any]:
    status = build_workspace_status_from_records(records_path=record_store_path())
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        **status,
    }


@router.get("/workspace/profile-memory-storage")
async def workspace_profile_memory_storage() -> dict[str, Any]:
    return {
        **INERT_FLAGS,
        "dispatch_enabled": False,
        "display_only": True,
        "dry_run_only": True,
        "stored": False,
        "source": "profile_memory_storage_projection",
        **_profile_memory_storage_projection(),
    }


@router.post("/workspace-status/preview")
async def workspace_status_preview(request: Request) -> dict[str, Any]:
    payload = await _read_json_object_body(request)
    status = build_workspace_status(payload)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        **status,
        "source": "caller_supplied_workspace_status_preview",
        "stored": False,
    }


@router.post("/pr-merge-verifier-gate/evaluate")
async def pr_merge_verifier_gate_evaluate(request: Request) -> dict[str, Any]:
    observed_state = await _read_pr_merge_gate_json_body(request)
    result = evaluate_pr_merge_verifier_gate(observed_state)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "caller_supplied_pr_merge_packet_state",
        "stored": False,
        **result,
    }


@router.post("/pr-merge-verifier-gate/visibility")
async def pr_merge_verifier_gate_visibility(request: Request) -> dict[str, Any]:
    payload = await _read_json_object_body(request)
    config = _compact_pr_merge_gate_config(payload.get("config"))
    packet_source = payload.get("merge_packet")
    if not isinstance(packet_source, dict):
        packet_source = payload.get("packet")
    if not isinstance(packet_source, dict):
        packet_source = {}
    packet = _compact_pr_merge_gate_state(packet_source)
    visibility = _pr_merge_visibility_payload(config, packet)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "caller_supplied_pr_merge_packet_visibility",
        "stored": False,
        **visibility,
    }


@router.get("/verifier-workflow/evidence")
async def verifier_workflow_evidence(limit: int = Query(10, ge=1, le=MAX_RECORDS_LIMIT)) -> dict[str, Any]:
    records, store_status, error = _load_latest_records_with_state(
        VerifierWorkflowEvidenceRecord,
        limit=min(limit, MAX_VERIFIER_EVIDENCE_RECORDS),
    )
    summaries = [
        {"record_index": index, **_verifier_evidence_summary(record)}
        for index, record in records
    ]
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "VerifierWorkflowEvidenceRecord",
        "store_status": store_status,
        "error": error,
        "count": len(summaries),
        "records": summaries,
    }


@router.post("/verifier-workflow/evaluate")
async def verifier_workflow_evaluate(request: Request) -> dict[str, Any]:
    observed_state, payload = await _read_verifier_json_body(request)
    result = evaluate_verifier_workflow(observed_state)
    should_record = payload.get("evaluate_and_record") is True
    record_payload: dict[str, Any] | None = None
    if should_record:
        record = _build_verifier_evidence_record(payload, result)
        JsonlRecordStore(record_store_path()).append(record)
        record_payload = record.to_dict()
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        "source": "caller_supplied_workflow_state",
        "stored": should_record,
        "record": record_payload,
        **result,
    }


@router.get("/model-registry")
async def model_registry() -> dict[str, Any]:
    records = list(get_model_registry_records())
    return {
        **INERT_FLAGS,
        "routing_enabled": False,
        "display_only": True,
        "source": "mission_control.model_registry",
        "count": len(records),
        "model_registry": records,
    }


@router.get("/domain-governance")
async def domain_governance() -> dict[str, Any]:
    policies = list(get_domain_governance_policies())
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "display_only": True,
        "source": "mission_control.domain_governance",
        "count": len(policies),
        "domain_policies": policies,
    }


@router.get("/start-gate")
async def start_gate() -> dict[str, Any]:
    missions, store_status, error = _load_latest_records_with_state(MissionBrief, limit=1)
    if missions:
        index, record = missions[-1]
        if getattr(record, "control", None) is not None:
            return {
                **INERT_FLAGS,
                "store_status": store_status,
                "error": error,
                "has_active_envelope": True,
                "source": "MissionBrief.control",
                "record_index": index,
                "mission_id": getattr(record, "mission_id", None),
                "mission_title": getattr(record, "title", None),
                "mission_created_at": getattr(record, "created_at", None),
                "envelope": _envelope_summary(getattr(record, "control")),
            }

    envelopes, envelope_status, envelope_error = _load_latest_records_with_state(TaskControlEnvelope, limit=1)
    if envelopes:
        index, record = envelopes[-1]
        return {
            **INERT_FLAGS,
            "store_status": envelope_status,
            "error": envelope_error,
            "has_active_envelope": True,
            "source": "TaskControlEnvelope",
            "record_index": index,
            "mission_id": None,
            "mission_title": None,
            "mission_created_at": None,
            "envelope": _envelope_summary(record),
        }

    if store_status == "malformed":
        return _empty_start_gate_payload(store_status, error)
    return _empty_start_gate_payload(envelope_status, envelope_error)


@router.post("/start-gate/evaluate")
async def start_gate_evaluate(request: Request) -> dict[str, Any]:
    envelope = await _read_compact_json_body(request)
    check = evaluate_start_gate(envelope)
    metadata = check.metadata if isinstance(check.metadata, dict) else {}
    return {
        **INERT_FLAGS,
        "default_off": bool(metadata.get("default_off", True)),
        "inert": bool(metadata.get("inert", True)),
        "enforces_runtime": bool(metadata.get("enforces_runtime", False)),
        "source": "proposed_envelope",
        "stored": False,
        "decision": _start_gate_decision_payload(check),
    }


@router.post("/lane-preflight/evaluate")
async def lane_preflight_evaluate() -> dict[str, Any]:
    envelope = _sample_lane_preflight_envelope()
    result = run_lane_start_preflight(_sample_lane_preflight_request())
    return {
        **INERT_FLAGS,
        "source": "fixed_lane_start_sample",
        "stored": False,
        "input_mode": "bounded_fixed_sample",
        "linked_kanban_task": linked_kanban_task_payload(
            envelope,
            record_id=envelope.envelope_id,
            include_missing=True,
        ),
        **_lane_preflight_visibility_payload(result),
    }


@router.get("/workspace/project-templates")
async def workspace_project_templates() -> dict[str, Any]:
    existing_projects = JsonlRecordStore(record_store_path()).read_all(ProjectRecord)
    templates = [_project_template_payload(template, existing_projects) for template in PROJECT_ONBOARDING_TEMPLATES]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "stored": False,
        "count": len(templates),
        "templates": templates,
    }


@router.post("/workspace/projects/seed-defaults")
async def workspace_projects_seed_defaults() -> dict[str, Any]:
    result = _seed_project_templates()
    return {
        **INERT_FLAGS,
        "stored": bool(result["created"]),
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "created_count": len(result["created"]),
        "skipped_count": len(result["skipped"]),
        "created": result["created"],
        "skipped": result["skipped"],
    }


@router.get("/workspace/projects")
async def workspace_projects(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    projects = _latest_workspace_records(ProjectRecord, applied_limit)
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "count": len(projects),
        "projects": projects,
    }


@router.post("/workspace/projects/create")
async def workspace_project_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_project_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "project": _project_payload(record),
    }


@router.get("/workspace/project-briefs")
async def workspace_project_briefs(
    project_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    project_filter = _workspace_text(project_id, max_chars=120) if project_id else ""
    records = _latest_workspace_records(ProjectBriefRecord, applied_limit)
    if project_filter:
        records = [item for item in records if item.get("record", {}).get("project_id") == project_filter]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": project_filter,
        "count": len(records),
        "project_briefs": records,
    }


@router.post("/workspace/project-briefs/create")
async def workspace_project_brief_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_project_brief_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "project_brief": _record_payload(record),
    }


@router.get("/workspace/challenge-reviews")
async def workspace_challenge_reviews(
    project_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    project_filter = _workspace_text(project_id, max_chars=120) if project_id else ""
    records = _latest_workspace_records(ChallengeReviewRecord, applied_limit)
    if project_filter:
        records = [item for item in records if item.get("record", {}).get("project_id") == project_filter]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": project_filter,
        "count": len(records),
        "challenge_reviews": records,
    }


@router.post("/workspace/challenge-reviews/create")
async def workspace_challenge_review_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_challenge_review_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "challenge_review": _record_payload(record),
    }


@router.get("/workspace/lane-requests")
async def workspace_lane_requests(
    project_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    project_filter = _workspace_text(project_id, max_chars=120) if project_id else ""
    records = _latest_workspace_records(LaneRequestRecord, applied_limit)
    if project_filter:
        records = [item for item in records if item.get("record", {}).get("project_id") == project_filter]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": project_filter,
        "count": len(records),
        "lane_requests": records,
    }


@router.post("/workspace/lane-requests/create")
async def workspace_lane_request_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_lane_request_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "lane_request": _lane_request_payload(record),
    }


@router.get("/workspace/session-project-links")
async def workspace_session_project_links(
    project_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    records = _latest_workspace_records(SessionProjectLinkRecord, applied_limit)
    if safe_project_id:
        records = [item for item in records if item.get("record", {}).get("project_id") == safe_project_id]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": safe_project_id,
        "count": len(records),
        "session_project_links": records,
    }


@router.post("/workspace/session-project-links/create")
async def workspace_session_project_link_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_session_project_link_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "session_project_link": _session_project_link_payload(record),
    }


@router.get("/workspace/project-sessions")
async def workspace_project_sessions(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    projection = _project_sessions_projection(applied_limit)
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "stored": False,
        "count": len(projection["groups"]),
        "session_count": projection["session_count"],
        "active_link_count": projection["active_link_count"],
        "groups": projection["groups"],
        "errors": projection["errors"],
    }


@router.get("/workspace/project-state")
async def workspace_project_state(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    states = _project_state_projection(applied_limit)
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "stored": False,
        "count": len(states),
        "project_states": states,
    }


@router.get("/workspace/reports")
async def workspace_jenny_reports(
    project_id: str | None = Query(default=None),
    lane_request_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    safe_lane_request_id = _workspace_text(lane_request_id, max_chars=120) if lane_request_id else ""
    reports = _latest_workspace_records(JennyReportRecord, applied_limit)
    if safe_project_id:
        reports = [item for item in reports if item.get("record", {}).get("project_id") == safe_project_id]
    if safe_lane_request_id:
        reports = [item for item in reports if item.get("record", {}).get("lane_request_id") == safe_lane_request_id]
    return {
        **INERT_FLAGS,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": safe_project_id,
        "lane_request_id": safe_lane_request_id,
        "count": len(reports),
        "reports": reports,
    }


@router.post("/workspace/reports/create")
async def workspace_jenny_report_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_jenny_report_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": True,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "report": _jenny_report_payload(record),
    }


@router.get("/workspace/jenny-bridge/outbox")
async def workspace_jenny_bridge_outbox(
    project_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    safe_status = _workspace_text(status, max_chars=80) if status else ""
    response_request_ids = _jenny_bridge_response_request_ids()
    requests = [
        _annotate_jenny_bridge_request(item, response_request_ids)
        for item in _latest_workspace_records(JennyBridgeMessageRequestRecord, applied_limit)
    ]
    if safe_project_id:
        requests = [item for item in requests if item.get("record", {}).get("project_id") == safe_project_id]
    if safe_status:
        requests = [item for item in requests if item.get("bridge_state") == safe_status]
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": safe_project_id,
        "status": safe_status,
        "count": len(requests),
        "requests": requests,
    }


@router.get("/workspace/jenny-bridge/pending")
async def workspace_jenny_bridge_pending(
    project_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    requests = _pending_jenny_bridge_requests(project_id=safe_project_id, limit=applied_limit)
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "relay_ready": True,
        "poller_required": True,
        "project_id": safe_project_id,
        "count": len(requests),
        "requests": requests,
        "relay_packet": _jenny_bridge_relay_packet(requests),
    }


@router.get("/workspace/jenny-bridge/poller-status")
async def workspace_jenny_bridge_poller_status(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    projection = _jenny_bridge_poller_status_projection(applied_limit)
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_start_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        **projection,
    }


@router.get("/workspace/jenny-reply-reviews")
async def workspace_jenny_reply_reviews(
    project_id: str | None = Query(default=None),
    response_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    safe_response_id = _workspace_text(response_id, max_chars=160) if response_id else ""
    reviews = _latest_workspace_records(JennyReplyReviewRecord, applied_limit)
    if safe_project_id:
        reviews = [item for item in reviews if item.get("record", {}).get("project_id") == safe_project_id]
    if safe_response_id:
        reviews = [item for item in reviews if item.get("record", {}).get("response_id") == safe_response_id]
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_start_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "project_id": safe_project_id,
        "response_id": safe_response_id,
        "count": len(reviews),
        "reply_reviews": reviews,
    }


@router.post("/workspace/jenny-reply-reviews/create")
async def workspace_jenny_reply_review_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_jenny_reply_review_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_start_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "reply_review": _jenny_reply_review_payload(record),
    }


@router.get("/workspace/github-bridge/status")
async def workspace_github_bridge_status(
    limit: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    projection = _github_bridge_mailbox_status_projection(
        applied_limit,
        _workspace_text(project_id, max_chars=120),
    )
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_start_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        **projection,
    }


@router.get("/workspace/async-agent-status")
async def workspace_async_agent_status() -> dict[str, Any]:
    return _async_agent_capability_projection()


@router.post("/workspace/github-bridge/outbox/create")
async def workspace_github_bridge_outbox_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    request_id = _workspace_text(payload.get("request_id") or f"github-bridge-request-{uuid.uuid4().hex[:12]}", max_chars=120)
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    message = _workspace_text(payload.get("message"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    user_message = _workspace_text(payload.get("user_message"), max_chars=MAX_WORKSPACE_PROMPT_CHARS)
    from_agent = _workspace_text(payload.get("from_agent") or "travis", max_chars=40)
    to_agent = _workspace_text(payload.get("to_agent") or "jenny", max_chars=40)
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        result = post_github_message(
            request_id=request_id,
            project_id=project_id,
            from_agent=from_agent,
            to_agent=to_agent,
            status="queued",
            message=message,
            user_message=user_message,
            path=record_store_path(),
            operator="mission-control-ui",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub bridge send failed: {exc}") from exc

    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": False,
        "manual_start_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": True,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "github_bridge_enabled": True,
        **result,
    }


@router.post("/workspace/github-bridge/answer-once")
async def workspace_github_bridge_answer_once(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    project_id = _workspace_text(payload.get("project_id"), max_chars=120)
    request_id = _workspace_text(payload.get("request_id"), max_chars=120)
    confirmed = payload.get("confirm_manual_hermes_answer") is True
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id is required")
    if not confirmed:
        raise HTTPException(status_code=400, detail="confirm_manual_hermes_answer is required")

    try:
        result = answer_pending_with_hermes(
            project_id=project_id,
            request_id=request_id,
            path=record_store_path(),
            operator="mission-control-ui",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub bridge answer failed: {exc}") from exc

    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": False,
        "manual_start_only": True,
        "manual_hermes_answer_enabled": True,
        "requires_explicit_manual_confirmation": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": True,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "execution_enabled": False,
        "worker_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "github_bridge_enabled": True,
        **result,
    }


@router.post("/workspace/jenny-bridge/outbox/create")
async def workspace_jenny_bridge_outbox_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_jenny_bridge_request_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "request": _jenny_bridge_request_payload(record),
    }


@router.get("/workspace/jenny-bridge/inbox")
async def workspace_jenny_bridge_inbox(
    project_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    limit: str | None = Query(default=None),
) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    safe_project_id = _workspace_text(project_id, max_chars=120) if project_id else ""
    safe_request_id = _workspace_text(request_id, max_chars=120) if request_id else ""
    responses = _latest_workspace_records(JennyBridgeMessageResponseRecord, applied_limit)
    if safe_project_id:
        responses = [item for item in responses if item.get("record", {}).get("project_id") == safe_project_id]
    if safe_request_id:
        responses = [item for item in responses if item.get("record", {}).get("request_id") == safe_request_id]
    return {
        **INERT_FLAGS,
        "stored": False,
        "display_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "project_id": safe_project_id,
        "request_id": safe_request_id,
        "count": len(responses),
        "responses": responses,
    }


@router.post("/workspace/jenny-bridge/inbox/create")
async def workspace_jenny_bridge_inbox_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_jenny_bridge_response_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **INERT_FLAGS,
        "stored": True,
        "display_only": True,
        "manual_copy_only": False,
        "send_to_jenny_enabled": False,
        "dispatch_enabled": False,
        "record_index": index,
        "record_type": record.record_type,
        "response": _jenny_bridge_response_payload(record),
    }


@router.get("/workspace/approvals")
async def workspace_approvals(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    approvals = _latest_workspace_records(ApprovalRecord, applied_limit)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": False,
        "count": len(approvals),
        "approvals": approvals,
    }


@router.post("/workspace/approvals/create")
async def workspace_approval_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_approval_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": True,
        "record_index": index,
        "record_type": record.record_type,
        "approval": record.to_dict(),
    }


@router.get("/workspace/runs")
async def workspace_runs(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    runs = _latest_workspace_records(RunRecord, applied_limit)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": False,
        "count": len(runs),
        "runs": runs,
    }


@router.post("/workspace/runs/create")
async def workspace_run_create(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_run_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": True,
        "record_index": index,
        "record_type": record.record_type,
        "run": record.to_dict(),
    }


@router.get("/workspace/report-inbox")
async def workspace_report_inbox(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    reports = _latest_workspace_records(ReportRecord, applied_limit)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": False,
        "count": len(reports),
        "reports": reports,
    }


@router.post("/workspace/reports/ingest")
async def workspace_report_ingest(request: Request) -> dict[str, Any]:
    payload = await _read_workspace_json_body(request)
    record = _build_report_record(payload)
    index = JsonlRecordStore(record_store_path()).append(record)
    return {
        **CONTROL_PLANE_INERT_FLAGS,
        "stored": True,
        "record_index": index,
        "record_type": record.record_type,
        "report": record.to_dict(),
    }


@router.get("/records")
async def records(limit: str | None = Query(default=None)) -> dict[str, Any]:
    applied_limit = _safe_records_limit(limit)
    loaded, store_status, error = _load_latest_records_with_state(limit=applied_limit)
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "limit": applied_limit,
        "count": len(loaded),
        "records": _serialized_indexed_records(loaded),
    }


@router.get("/schema")
async def schema() -> dict[str, Any]:
    path = record_store_path()
    return {
        **INERT_FLAGS,
        "record_store": {
            "path": str(path),
            "status": _record_store_state(path),
        },
        "record_types": _record_schema(),
    }


@router.get("/records/{record_index}")
async def record_detail(record_index: int) -> dict[str, Any]:
    loaded, store_status, error = _load_records_with_state()
    if store_status == "malformed":
        raise HTTPException(status_code=409, detail="record store is malformed")
    if record_index < 0 or record_index >= len(loaded):
        raise HTTPException(status_code=404, detail="record index not found")
    record = loaded[record_index]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "record_index": record_index,
        "record_type": _record_type(record),
        "record": _record_payload(record),
    }
