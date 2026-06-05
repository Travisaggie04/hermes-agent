"""Read-only Mission Control governance dashboard API."""

from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from hermes_constants import get_hermes_home
from mission_control.records.errors import RecordStoreError
from mission_control.records.models import RECORD_TYPES
from mission_control.records import JsonlRecordStore


PLUGIN_NAME = "mission-control-governance"
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


def _record_type(record: Any) -> str:
    return str(getattr(record, "record_type", type(record).__name__))


def _record_payload(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
        if isinstance(payload, dict):
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


def _envelope_summary(envelope: Any) -> dict[str, Any]:
    payload = _record_payload(envelope)
    return {
        "active_lane": payload.get("active_lane", ""),
        "mode": payload.get("mode", ""),
        "allowed_actions": list(payload.get("allowed_actions") or ()),
        "forbidden_actions": list(payload.get("forbidden_actions") or ()),
        "current_repo": payload.get("current_repo", ""),
        "expected_systems_files": list(payload.get("expected_systems_files") or ()),
        "stop_condition": payload.get("stop_condition", ""),
        "other_threads_excluded": list(payload.get("other_threads_excluded") or ()),
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


def _bounded_latest(items: tuple[Any, ...], limit: int = 10) -> tuple[Any, ...]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def _approval_summary(approval: Any, evidence_count: int | None = None) -> dict[str, Any]:
    metadata = getattr(approval, "metadata", {}) or {}
    summary = {
        "approval_id": getattr(approval, "approval_id", ""),
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
    for key in ("title", "type", "source"):
        if key in metadata:
            summary[key] = metadata[key]
    return summary


def _latest_mission_with_items(records: tuple[Any, ...], field_name: str) -> tuple[int, Any] | None:
    for index, record in reversed(tuple(enumerate(records))):
        if _record_type(record) == "MissionBrief" and getattr(record, field_name, ()):  # compact embedded context
            return index, record
    return None


def _standalone_records(records: tuple[Any, ...], record_type: str) -> tuple[tuple[int, Any], ...]:
    return tuple(
        (index, record)
        for index, record in enumerate(records)
        if _record_type(record) == record_type
    )


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
    records, store_status, error = _load_records_with_state()
    counts = Counter(_record_type(record) for record in records)
    latest_mission = next(
        (
            record
            for record in reversed(records)
            if _record_type(record) == "MissionBrief"
        ),
        None,
    )
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "record_count": len(records),
        "record_types": dict(sorted(counts.items())),
        "latest_mission_title": getattr(latest_mission, "title", None),
        "latest_mission_created_at": getattr(latest_mission, "created_at", None),
    }


@router.get("/approval-slices")
async def approval_slices() -> dict[str, Any]:
    loaded, store_status, error = _load_records_with_state()
    if not loaded:
        return _empty_approval_slices_payload(store_status, error)

    mission_match = _latest_mission_with_items(loaded, "approvals")
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

    standalone = _bounded_latest(_standalone_records(loaded, "ApprovalSlice"))
    if not standalone:
        return _empty_approval_slices_payload(store_status, error)
    summaries = [_approval_summary(record) for _, record in standalone]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "ApprovalSlice",
        "count": len(summaries),
        "approval_slices": summaries,
    }


@router.get("/evidence-cards")
async def evidence_cards() -> dict[str, Any]:
    loaded, store_status, error = _load_records_with_state()
    if not loaded:
        return _empty_evidence_cards_payload(store_status, error)

    mission_match = _latest_mission_with_items(loaded, "evidence")
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

    standalone = _bounded_latest(_standalone_records(loaded, "EvidenceCard"))
    if not standalone:
        return _empty_evidence_cards_payload(store_status, error)
    summaries = [_evidence_summary(record) for _, record in standalone]
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "source": "EvidenceCard",
        "count": len(summaries),
        "evidence_cards": summaries,
    }


@router.get("/start-gate")
async def start_gate() -> dict[str, Any]:
    loaded, store_status, error = _load_records_with_state()
    if not loaded:
        return _empty_start_gate_payload(store_status, error)

    for index, record in reversed(tuple(enumerate(loaded))):
        if _record_type(record) == "MissionBrief" and getattr(record, "control", None) is not None:
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

    for index, record in reversed(tuple(enumerate(loaded))):
        if _record_type(record) == "TaskControlEnvelope":
            return {
                **INERT_FLAGS,
                "store_status": store_status,
                "error": error,
                "has_active_envelope": True,
                "source": "TaskControlEnvelope",
                "record_index": index,
                "mission_id": None,
                "mission_title": None,
                "mission_created_at": None,
                "envelope": _envelope_summary(record),
            }

    return _empty_start_gate_payload(store_status, error)


@router.get("/records")
async def records() -> dict[str, Any]:
    loaded, store_status, error = _load_records_with_state()
    return {
        **INERT_FLAGS,
        "store_status": store_status,
        "error": error,
        "count": len(loaded),
        "records": _serialized_records(loaded),
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
