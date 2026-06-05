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
