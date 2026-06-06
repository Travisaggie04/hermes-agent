"""Read-only Mission Control governance dashboard API."""

from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from hermes_constants import get_hermes_home
from mission_control.records.errors import RecordStoreError
from mission_control.records.models import RECORD_TYPES
from mission_control.records import (
    ApprovalSlice,
    EvidenceCard,
    JsonlRecordStore,
    MissionBrief,
    OperatorAction,
    StartGateCheck,
    TaskControlEnvelope,
)


PLUGIN_NAME = "mission-control-governance"
RECORDS_DEFAULT_LIMIT = 25
RECORDS_MAX_LIMIT = 50
INERT_FLAGS = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "execution_enabled": False,
}

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


def _normalize_records_limit(limit: int | None) -> int:
    if limit is None or limit <= 0:
        return RECORDS_DEFAULT_LIMIT
    return min(limit, RECORDS_MAX_LIMIT)


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
            return payload
    return {}


def _serialized_records(records: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [
        {
            "record_index": index,
            "record_type": _record_type(record),
            "record": _record_payload(record),
        }
        for index, record in enumerate(records)
    ]


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
    return {
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
    return {
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


@router.get("/records")
async def records(limit: int | None = Query(default=None)) -> dict[str, Any]:
    normalized_limit = _normalize_records_limit(limit)
    loaded, store_status, error = _load_latest_records_with_state(limit=normalized_limit)
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "count": len(loaded),
        "limit": normalized_limit,
        "returned_count": len(loaded),
        "has_more": bool(loaded and loaded[0][0] > 0),
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
