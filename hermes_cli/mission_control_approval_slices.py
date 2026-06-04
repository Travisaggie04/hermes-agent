"""Local inert Approval Slice persistence for Mission Control.

Approval Slice path and locality fields are user-entered opaque strings. This
module stores them as data only; it does not resolve paths, expand ``~``, fetch
URLs, stat files, normalize for authorization, execute commands, or integrate
with runtime approval/enforcement systems.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_cli.goal_contract_spec import ACTION_CATEGORIES, CHECKPOINT_KINDS, CREATED_FROM_VALUES
from hermes_cli.mission_control import redact_text, redact_value


APPROVAL_SLICE_STATUSES = {"active", "revoked", "expired", "completed"}
MAX_TEXT_CHARS = 100_000
MAX_LIST_ITEMS = 100
MAX_LIST_ITEM_CHARS = 4_000
_LOCK = threading.RLock()


class ApprovalSliceError(ValueError):
    """Raised for invalid Approval Slice requests."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_dir() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "approval-slices"


def audit_path() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "approval-slices-audit.jsonl"


def _slice_path(slice_id: str) -> Path:
    if not re.fullmatch(r"slice_[0-9TZ]+_[a-f0-9]{12}", slice_id):
        raise ApprovalSliceError("Invalid approval slice id")
    return state_dir() / f"{slice_id}.json"


def _new_slice_id(created_at: str) -> str:
    stamp = re.sub(r"[^0-9TZ]", "", created_at.replace("+00:00", "Z"))
    return f"slice_{stamp}_{secrets.token_hex(6)}"


def _bounded_text(value: Any, *, field: str, required: bool = False) -> str:
    if value is None:
        if required:
            raise ApprovalSliceError(f"Missing required field: {field}")
        return ""
    text = str(value)
    if required and not text.strip():
        raise ApprovalSliceError(f"Missing required field: {field}")
    return text[:MAX_TEXT_CHARS]


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ApprovalSliceError(f"{field} must be a list of strings")
    items: list[str] = []
    for item in value[:MAX_LIST_ITEMS]:
        if not isinstance(item, str):
            raise ApprovalSliceError(f"{field} must be a list of strings")
        if item:
            items.append(item[:MAX_LIST_ITEM_CHARS])
    return items


def _validate_status(value: Any, *, default: str = "active") -> str:
    status = str(value or default)
    if status not in APPROVAL_SLICE_STATUSES:
        raise ApprovalSliceError("status must be one of: active, revoked, expired, completed")
    return status


def _validate_create_status(value: Any) -> str:
    status = _validate_status(value)
    if status != "active":
        raise ApprovalSliceError("status must be active on create")
    return status


def _validate_actions(value: Any, *, field: str) -> list[str]:
    actions = _string_list(value, field=field)
    invalid = [action for action in actions if action not in ACTION_CATEGORIES]
    if invalid:
        raise ApprovalSliceError(f"{field} contains unknown G1 action: {invalid[0]}")
    return actions


def _validate_checkpoint(value: Any, *, field: str, required: bool = False) -> str:
    text = _bounded_text(value, field=field, required=required)
    if text and text not in CHECKPOINT_KINDS:
        raise ApprovalSliceError(f"{field} must be a G1 checkpoint kind")
    return text


def _validate_created_from(value: Any) -> str:
    text = _bounded_text(value, field="created_from", required=True)
    if text not in CREATED_FROM_VALUES:
        raise ApprovalSliceError("created_from must be a G1 source value")
    return text


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(redact_value(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _append_audit(event: str, approval_slice: dict[str, Any] | None = None, *, result: str = "ok") -> None:
    record = {
        "timestamp": _now_iso(),
        "event": event,
        "actor": "dashboard",
        "surface": "dashboard",
        "slice_id": (approval_slice or {}).get("id"),
        "status": (approval_slice or {}).get("status"),
        "trusted_for_execution": False,
        "inert_context_only": True,
        "result": redact_text(result),
    }
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact_value(record), sort_keys=True) + "\n")


def _summary(approval_slice: dict[str, Any]) -> dict[str, Any]:
    return redact_value(
        {
            "id": approval_slice["id"],
            "status": approval_slice["status"],
            "title": approval_slice["title"],
            "repo_path": approval_slice.get("repo_path", ""),
            "allowed_actions": approval_slice.get("allowed_actions", []),
            "forbidden_actions": approval_slice.get("forbidden_actions", []),
            "checkpoint": approval_slice.get("checkpoint", ""),
            "linked_goal_contract_id": approval_slice.get("linked_goal_contract_id", ""),
            "created_by": approval_slice.get("created_by", ""),
            "created_from": approval_slice.get("created_from", ""),
            "created_at": approval_slice["created_at"],
            "updated_at": approval_slice["updated_at"],
            "revoked_at": approval_slice.get("revoked_at"),
            "expired_at": approval_slice.get("expired_at"),
            "completed_at": approval_slice.get("completed_at"),
            "trusted_for_execution": False,
            "inert_context_only": True,
            "vocabulary_version": "g1",
        }
    )


def _read_slice_unlocked(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ApprovalSliceError("Approval Slice file is invalid")
    return data


def create_approval_slice(data: dict[str, Any]) -> dict[str, Any]:
    created_at = _now_iso()
    status = _validate_create_status(data.get("status"))
    raw_title = data.get("title", data.get("short_label"))
    approval_slice = {
        "id": _new_slice_id(created_at),
        "status": status,
        "title": redact_text(_bounded_text(raw_title, field="title", required=True)),
        "repo_path": redact_text(_bounded_text(data.get("repo_path"), field="repo_path")),
        "allowed_paths": redact_value(_string_list(data.get("allowed_paths"), field="allowed_paths")),
        "forbidden_paths": redact_value(_string_list(data.get("forbidden_paths"), field="forbidden_paths")),
        "expected_locality": redact_text(_bounded_text(data.get("expected_locality"), field="expected_locality")),
        "allowed_actions": _validate_actions(data.get("allowed_actions"), field="allowed_actions"),
        "forbidden_actions": _validate_actions(data.get("forbidden_actions"), field="forbidden_actions"),
        "stop_condition": _validate_checkpoint(data.get("stop_condition"), field="stop_condition", required=True),
        "checkpoint": _validate_checkpoint(data.get("checkpoint"), field="checkpoint", required=True),
        "linked_goal_contract_id": _bounded_text(
            data.get("linked_goal_contract_id"),
            field="linked_goal_contract_id",
        ),
        "created_by": redact_text(_bounded_text(data.get("created_by"), field="created_by", required=True)),
        "created_from": _validate_created_from(data.get("created_from")),
        "raw_user_approval": redact_text(
            _bounded_text(data.get("raw_user_approval"), field="raw_user_approval")
        ),
        "created_at": created_at,
        "updated_at": created_at,
        "revoked_at": None,
        "expired_at": None,
        "completed_at": None,
        "trusted_for_execution": False,
        "inert_context_only": True,
        "vocabulary_version": "g1",
    }
    if isinstance(data.get("metadata"), dict):
        approval_slice["metadata"] = redact_value(data["metadata"])
    with _LOCK:
        path = _slice_path(approval_slice["id"])
        _atomic_write_json(path, approval_slice)
        _append_audit("approval_slice_created", approval_slice)
    return redact_value(approval_slice)


def list_approval_slices(*, include_inactive: bool = False) -> dict[str, Any]:
    with _LOCK:
        directory = state_dir()
        directory.mkdir(parents=True, exist_ok=True)
        approval_slices: list[dict[str, Any]] = []
        for path in sorted(directory.glob("slice_*.json")):
            try:
                approval_slice = _read_slice_unlocked(path)
            except Exception:
                continue
            if include_inactive or approval_slice.get("status") == "active":
                approval_slices.append(approval_slice)
    approval_slices.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return {"items": [_summary(approval_slice) for approval_slice in approval_slices], "warnings": []}


def get_approval_slice(slice_id: str) -> dict[str, Any]:
    with _LOCK:
        path = _slice_path(slice_id)
        try:
            approval_slice = _read_slice_unlocked(path)
        except FileNotFoundError:
            raise
    return {"approval_slice": redact_value(approval_slice)}


def transition_approval_slice(slice_id: str, status: str) -> dict[str, Any]:
    if status not in {"revoked", "expired", "completed"}:
        raise ApprovalSliceError("Invalid approval slice transition")
    timestamp_field = {
        "revoked": "revoked_at",
        "expired": "expired_at",
        "completed": "completed_at",
    }[status]
    with _LOCK:
        path = _slice_path(slice_id)
        try:
            approval_slice = _read_slice_unlocked(path)
        except FileNotFoundError:
            raise
        now = _now_iso()
        approval_slice["status"] = status
        approval_slice[timestamp_field] = now
        approval_slice["updated_at"] = now
        approval_slice["trusted_for_execution"] = False
        approval_slice["inert_context_only"] = True
        approval_slice["vocabulary_version"] = "g1"
        _atomic_write_json(path, approval_slice)
        _append_audit(f"approval_slice_{status}", approval_slice)
    return {"approval_slice": redact_value(approval_slice)}
