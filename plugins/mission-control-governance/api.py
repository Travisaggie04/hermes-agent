"""Read-only Mission Control governance dashboard API."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from hermes_constants import get_hermes_home
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


def _load_records() -> tuple[Any, ...]:
    return JsonlRecordStore(record_store_path()).read_all()


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
            "record_type": _record_type(record),
            "record": _record_payload(record),
        }
        for record in records
    ]


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "plugin": PLUGIN_NAME,
        **INERT_FLAGS,
    }


@router.get("/summary")
async def summary() -> dict[str, Any]:
    records = _load_records()
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
        "record_count": len(records),
        "record_types": dict(sorted(counts.items())),
        "latest_mission_title": getattr(latest_mission, "title", None),
        "latest_mission_created_at": getattr(latest_mission, "created_at", None),
    }


@router.get("/records")
async def records() -> dict[str, Any]:
    loaded = _load_records()
    return {
        **INERT_FLAGS,
        "count": len(loaded),
        "records": _serialized_records(loaded),
    }
