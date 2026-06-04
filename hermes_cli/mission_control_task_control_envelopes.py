"""Local inert Task Control Envelope persistence for Mission Control.

Task Control Envelope path and repo fields are user-entered opaque strings.
This module stores them as data only; it does not resolve paths, expand ``~``,
probe git state, stat files, fetch URLs, execute commands, or integrate with
runtime approval, command, gateway, goal, or enforcement systems.
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

from hermes_cli.goal_contract_spec import ACTION_CATEGORIES, CHECKPOINT_KINDS, PRESET_NAMES
from hermes_cli.mission_control import redact_text, redact_value


TASK_CONTROL_ENVELOPE_STATUSES = {"active", "completed", "archived"}
MAX_TEXT_CHARS = 100_000
MAX_LIST_ITEMS = 100
MAX_LIST_ITEM_CHARS = 4_000
_LOCK = threading.RLock()


class TaskControlEnvelopeError(ValueError):
    """Raised for invalid Task Control Envelope requests."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_dir() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "task-control-envelopes"


def audit_path() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "task-control-envelopes-audit.jsonl"


def _envelope_path(envelope_id: str) -> Path:
    if not re.fullmatch(r"envelope_[0-9TZ]+_[a-f0-9]{12}", envelope_id):
        raise TaskControlEnvelopeError("Invalid task control envelope id")
    return state_dir() / f"{envelope_id}.json"


def _new_envelope_id(created_at: str) -> str:
    stamp = re.sub(r"[^0-9TZ]", "", created_at.replace("+00:00", "Z"))
    return f"envelope_{stamp}_{secrets.token_hex(6)}"


def _bounded_text(value: Any, *, field: str, required: bool = False) -> str:
    if value is None:
        if required:
            raise TaskControlEnvelopeError(f"Missing required field: {field}")
        return ""
    text = str(value)
    if required and not text.strip():
        raise TaskControlEnvelopeError(f"Missing required field: {field}")
    return text[:MAX_TEXT_CHARS]


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:MAX_TEXT_CHARS]
    return None if text.lower() == "unknown" else text


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TaskControlEnvelopeError(f"{field} must be a list of strings")
    items: list[str] = []
    for item in value[:MAX_LIST_ITEMS]:
        if not isinstance(item, str):
            raise TaskControlEnvelopeError(f"{field} must be a list of strings")
        if item:
            items.append(item[:MAX_LIST_ITEM_CHARS])
    return items


def _status(value: Any, *, default: str = "active") -> str:
    status = str(value or default)
    if status not in TASK_CONTROL_ENVELOPE_STATUSES:
        raise TaskControlEnvelopeError("status must be one of: active, completed, archived")
    return status


def _create_status(value: Any) -> str:
    status = _status(value)
    if status != "active":
        raise TaskControlEnvelopeError("status must be active on create")
    return status


def _mode(value: Any) -> str:
    mode = _bounded_text(value, field="mode", required=True)
    if mode not in PRESET_NAMES:
        raise TaskControlEnvelopeError("mode must be a G1 preset name")
    return mode


def _validate_actions(value: Any, *, field: str) -> list[str]:
    actions = _string_list(value, field=field)
    invalid = [action for action in actions if action not in ACTION_CATEGORIES]
    if invalid:
        raise TaskControlEnvelopeError(f"{field} contains unknown G1 action: {invalid[0]}")
    return actions


def _validate_checkpoints(value: Any, *, field: str) -> list[str]:
    checkpoints = _string_list(value, field=field)
    invalid = [checkpoint for checkpoint in checkpoints if checkpoint not in CHECKPOINT_KINDS]
    if invalid:
        raise TaskControlEnvelopeError(f"{field} contains unknown G1 checkpoint: {invalid[0]}")
    return checkpoints


def _repo_context(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    dirty_state = source.get("dirty_state")
    dirty_text = str(dirty_state)[:MAX_TEXT_CHARS] if dirty_state is not None else "not_probed"
    if not dirty_text or dirty_text.lower() == "unknown":
        dirty_text = "not_probed"
    return redact_value(
        {
            "path": _bounded_text(source.get("path"), field="repo_context.path"),
            "branch": _optional_text(source.get("branch")),
            "head": _optional_text(source.get("head")),
            "dirty_state": dirty_text,
            "source": _bounded_text(source.get("source"), field="repo_context.source") or "unknown",
        }
    )


def _dict_value(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TaskControlEnvelopeError(f"{field} must be an object")
    return redact_value(value)


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(redact_value(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _append_audit(event: str, envelope: dict[str, Any] | None = None, *, result: str = "ok") -> None:
    record = {
        "timestamp": _now_iso(),
        "event": event,
        "actor": "dashboard",
        "surface": "dashboard",
        "envelope_id": (envelope or {}).get("id"),
        "status": (envelope or {}).get("status"),
        "trusted_for_execution": False,
        "inert_context_only": True,
        "result": redact_text(result),
    }
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact_value(record), sort_keys=True) + "\n")


def _summary(envelope: dict[str, Any]) -> dict[str, Any]:
    return redact_value(
        {
            "id": envelope["id"],
            "schema": envelope["schema"],
            "status": envelope["status"],
            "title": envelope["title"],
            "mode": envelope["mode"],
            "mode_label": envelope.get("mode_label", ""),
            "allowed_actions": envelope.get("allowed_actions", []),
            "forbidden_actions": envelope.get("forbidden_actions", []),
            "checkpoints": envelope.get("checkpoints", []),
            "repo_context": envelope.get("repo_context", {}),
            "source": envelope.get("source", ""),
            "created_at": envelope["created_at"],
            "updated_at": envelope["updated_at"],
            "completed_at": envelope.get("completed_at"),
            "archived_at": envelope.get("archived_at"),
            "trusted_for_execution": False,
            "inert_context_only": True,
            "vocabulary_version": "g1",
        }
    )


def _active_read_summary(envelope: dict[str, Any]) -> dict[str, Any]:
    summary = _summary(envelope)
    return {
        **summary,
        "checkpoint": (summary.get("checkpoints") or [None])[0],
        "lane_lock": redact_value(envelope.get("lane_lock", {})),
    }


def _read_envelope_unlocked(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TaskControlEnvelopeError("Task Control Envelope file is invalid")
    return data


def create_task_control_envelope(data: dict[str, Any]) -> dict[str, Any]:
    created_at = _now_iso()
    envelope = {
        "id": _new_envelope_id(created_at),
        "schema": _bounded_text(data.get("schema"), field="schema")
        or "mission-control.task-control-envelope.v1",
        "status": _create_status(data.get("status")),
        "title": redact_text(_bounded_text(data.get("title"), field="title", required=True)),
        "created_at": created_at,
        "updated_at": created_at,
        "completed_at": None,
        "archived_at": None,
        "mode": _mode(data.get("mode")),
        "mode_label": redact_text(_bounded_text(data.get("mode_label"), field="mode_label")),
        "allowed_actions": _validate_actions(data.get("allowed_actions"), field="allowed_actions"),
        "forbidden_actions": _validate_actions(data.get("forbidden_actions"), field="forbidden_actions"),
        "checkpoints": _validate_checkpoints(data.get("checkpoints"), field="checkpoints"),
        "checkpoint_requirements": _validate_checkpoints(
            data.get("checkpoint_requirements"),
            field="checkpoint_requirements",
        ),
        "repo_context": _repo_context(data.get("repo_context")),
        "lane_lock": _dict_value(data.get("lane_lock"), field="lane_lock"),
        "relationships": _dict_value(data.get("relationships"), field="relationships"),
        "source": redact_text(_bounded_text(data.get("source"), field="source")),
        "raw_user_approval": redact_text(
            _bounded_text(data.get("raw_user_approval"), field="raw_user_approval")
        ),
        "metadata": _dict_value(data.get("metadata"), field="metadata"),
        "trusted_for_execution": False,
        "inert_context_only": True,
        "vocabulary_version": "g1",
    }
    with _LOCK:
        path = _envelope_path(envelope["id"])
        _atomic_write_json(path, envelope)
        _append_audit("task_control_envelope_created", envelope)
    return redact_value(envelope)


def list_task_control_envelopes(*, include_inactive: bool = False) -> dict[str, Any]:
    with _LOCK:
        directory = state_dir()
        directory.mkdir(parents=True, exist_ok=True)
        envelopes: list[dict[str, Any]] = []
        for path in sorted(directory.glob("envelope_*.json")):
            try:
                envelope = _read_envelope_unlocked(path)
            except Exception:
                continue
            if include_inactive or envelope.get("status") == "active":
                envelopes.append(envelope)
    envelopes.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return {"items": [_summary(envelope) for envelope in envelopes], "warnings": []}


def active_task_control_envelope_selection() -> dict[str, Any]:
    """Read the display-only active envelope selection without mutating storage."""
    with _LOCK:
        directory = state_dir()
        if not directory.exists():
            return {"task_control_envelope": None, "selected_from_count": 0, "warnings": []}
        envelopes: list[dict[str, Any]] = []
        for path in sorted(directory.glob("envelope_*.json")):
            try:
                envelope = _read_envelope_unlocked(path)
                if envelope.get("status") != "active":
                    continue
                envelopes.append(_active_read_summary(envelope))
            except Exception:
                continue
    envelopes.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    selected = envelopes[0] if envelopes else None
    return {
        "task_control_envelope": selected,
        "selected_from_count": len(envelopes),
        "warnings": [],
    }


def get_task_control_envelope(envelope_id: str) -> dict[str, Any]:
    with _LOCK:
        path = _envelope_path(envelope_id)
        try:
            envelope = _read_envelope_unlocked(path)
        except FileNotFoundError:
            raise
    return {"task_control_envelope": redact_value(envelope)}


def transition_task_control_envelope(envelope_id: str, status: str) -> dict[str, Any]:
    if status not in {"completed", "archived"}:
        raise TaskControlEnvelopeError("Invalid task control envelope transition")
    timestamp_field = "completed_at" if status == "completed" else "archived_at"
    with _LOCK:
        path = _envelope_path(envelope_id)
        try:
            envelope = _read_envelope_unlocked(path)
        except FileNotFoundError:
            raise
        now = _now_iso()
        envelope["status"] = status
        envelope[timestamp_field] = now
        envelope["updated_at"] = now
        envelope["trusted_for_execution"] = False
        envelope["inert_context_only"] = True
        envelope["vocabulary_version"] = "g1"
        _atomic_write_json(path, envelope)
        _append_audit(f"task_control_envelope_{status}", envelope)
    return {"task_control_envelope": redact_value(envelope)}
