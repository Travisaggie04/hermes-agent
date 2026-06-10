"""Read-only Mission Control governance dashboard API."""

from __future__ import annotations

import json
import re
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
from mission_control.storage_guard import evaluate_storage_guard, get_storage_guard_policy
from mission_control.verifier_workflow import (
    evaluate_verifier_workflow,
    get_verifier_workflow_policy,
)
from mission_control.workspace_status import build_workspace_status, default_workspace_status_input
from mission_control.lane_preflight import run_lane_start_preflight
from mission_control.records.errors import RecordStoreError
from mission_control.records.models import RECORD_TYPES
from mission_control.kanban_linkage import linked_kanban_task_payload
from mission_control.start_gate import evaluate_start_gate
from mission_control.records import (
    AcceptedBaselineRecord,
    ApprovalSlice,
    EvidenceCard,
    GoalContract,
    JsonlRecordStore,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectRecord,
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


def _workspace_record_payload(record: Any) -> dict[str, Any]:
    if isinstance(record, ProjectRecord):
        return _project_payload(record)
    if isinstance(record, LaneRequestRecord):
        return _lane_request_payload(record)
    if isinstance(record, JennyReportRecord):
        return _jenny_report_payload(record)
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


def _project_state_projection(limit: int) -> list[dict[str, Any]]:
    projects = _latest_workspace_records(ProjectRecord, limit)
    lanes = _latest_workspace_records(LaneRequestRecord, limit)
    reports = _latest_workspace_records(JennyReportRecord, limit)

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
        last_updated = (
            report.get("created_at")
            or lane.get("updated_at")
            or lane.get("created_at")
            or project.get("updated_at")
            or project.get("created_at")
            or ""
        )
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
            "last_updated": last_updated,
            "source_record_indexes": {
                "project": item.get("record_index"),
                "lane_request": lane_item.get("record_index") if lane_item else None,
                "jenny_report": report_item.get("record_index") if report_item else None,
            },
        })
    return states


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
    payload = default_workspace_status_input()
    latest_baseline = _latest_accepted_baseline_payload()
    if latest_baseline:
        payload["accepted_baseline_record"] = latest_baseline
    latest_handoff = _latest_handoff_payload()
    if latest_handoff:
        payload["latest_handoff"] = latest_handoff
    status = build_workspace_status(payload)
    return {
        **INERT_FLAGS,
        "enforcement_enabled": False,
        "dry_run_only": True,
        "display_only": True,
        **status,
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
