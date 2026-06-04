"""Local inert Mission Brief persistence for Mission Control.

Mission Brief references are user-entered opaque strings. This module stores
them as text only; it does not resolve paths, expand ``~``, fetch URLs, hash,
preview, stat, or parse referenced artifacts.
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

from hermes_cli.mission_control import redact_text, redact_value


BRIEF_STATUSES = {"active", "archived"}
MAX_TEXT_CHARS = 100_000
MAX_REFERENCES = 100
MAX_REFERENCE_CHARS = 4_000
_LOCK = threading.RLock()


class MissionBriefError(ValueError):
    """Raised for invalid Mission Brief requests."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_dir() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "mission-briefs"


def audit_path() -> Path:
    from hermes_constants import get_hermes_home

    return Path(get_hermes_home()) / "state" / "mission-control" / "mission-briefs-audit.jsonl"


def _brief_path(brief_id: str) -> Path:
    if not re.fullmatch(r"brief_[0-9TZ]+_[a-f0-9]{12}", brief_id):
        raise MissionBriefError("Invalid brief id")
    return state_dir() / f"{brief_id}.json"


def _new_brief_id(created_at: str) -> str:
    stamp = re.sub(r"[^0-9TZ]", "", created_at.replace("+00:00", "Z"))
    return f"brief_{stamp}_{secrets.token_hex(6)}"


def _bounded_text(value: Any, *, field: str, required: bool = False) -> str:
    if value is None:
        if required:
            raise MissionBriefError(f"Missing required field: {field}")
        return ""
    text = str(value)
    if required and not text.strip():
        raise MissionBriefError(f"Missing required field: {field}")
    return text[:MAX_TEXT_CHARS]


def _references(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MissionBriefError("references must be a list of strings")
    refs: list[str] = []
    for item in value[:MAX_REFERENCES]:
        if not isinstance(item, str):
            raise MissionBriefError("references must be a list of strings")
        if item:
            refs.append(item[:MAX_REFERENCE_CHARS])
    return refs


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(redact_value(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_audit(event: str, brief: dict[str, Any] | None = None, *, result: str = "ok") -> None:
    record = {
        "timestamp": _now_iso(),
        "event": event,
        "actor": redact_text(str((brief or {}).get("author") or "dashboard")),
        "surface": "dashboard",
        "brief_id": (brief or {}).get("id"),
        "status": (brief or {}).get("status"),
        "trusted_for_execution": False,
        "inert_context_only": True,
        "result": redact_text(result),
    }
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact_value(record), sort_keys=True) + "\n")


def _summary(brief: dict[str, Any]) -> dict[str, Any]:
    return redact_value(
        {
            "id": brief["id"],
            "title": brief["title"],
            "summary": brief.get("summary", ""),
            "status": brief["status"],
            "reference_count": len(brief.get("references") or []),
            "created_at": brief["created_at"],
            "updated_at": brief["updated_at"],
            "archived_at": brief.get("archived_at"),
            "trusted_for_execution": False,
            "inert_context_only": True,
        }
    )


def _read_brief_unlocked(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise MissionBriefError("Mission Brief file is invalid")
    return data


def create_brief(data: dict[str, Any]) -> dict[str, Any]:
    created_at = _now_iso()
    brief = {
        "id": _new_brief_id(created_at),
        "title": redact_text(_bounded_text(data.get("title"), field="title", required=True)),
        "summary": redact_text(_bounded_text(data.get("summary"), field="summary")),
        "references": redact_value(_references(data.get("references"))),
        "status": "active",
        "author": redact_text(str(data.get("author") or "dashboard")),
        "created_at": created_at,
        "updated_at": created_at,
        "archived_at": None,
        "trusted_for_execution": False,
        "inert_context_only": True,
    }
    with _LOCK:
        path = _brief_path(brief["id"])
        _atomic_write_json(path, brief)
        _append_audit("brief_created", brief)
    return redact_value(brief)


def list_briefs() -> dict[str, Any]:
    with _LOCK:
        directory = state_dir()
        directory.mkdir(parents=True, exist_ok=True)
        briefs: list[dict[str, Any]] = []
        for path in sorted(directory.glob("brief_*.json")):
            try:
                briefs.append(_read_brief_unlocked(path))
            except Exception:
                continue
    briefs.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return {"items": [_summary(brief) for brief in briefs], "warnings": []}


def get_brief(brief_id: str) -> dict[str, Any]:
    with _LOCK:
        path = _brief_path(brief_id)
        try:
            brief = _read_brief_unlocked(path)
        except FileNotFoundError:
            raise
    return {"brief": redact_value(brief)}


def update_brief(brief_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        path = _brief_path(brief_id)
        try:
            brief = _read_brief_unlocked(path)
        except FileNotFoundError:
            raise
        if "title" in data:
            brief["title"] = redact_text(_bounded_text(data.get("title"), field="title", required=True))
        if "summary" in data:
            brief["summary"] = redact_text(_bounded_text(data.get("summary"), field="summary"))
        if "references" in data:
            brief["references"] = redact_value(_references(data.get("references")))
        if "author" in data:
            brief["author"] = redact_text(str(data.get("author") or "dashboard"))
        brief["trusted_for_execution"] = False
        brief["inert_context_only"] = True
        brief["updated_at"] = _now_iso()
        _atomic_write_json(path, brief)
        _append_audit("brief_updated", brief)
    return {"brief": redact_value(brief)}


def archive_brief(brief_id: str) -> dict[str, Any]:
    with _LOCK:
        path = _brief_path(brief_id)
        try:
            brief = _read_brief_unlocked(path)
        except FileNotFoundError:
            raise
        now = _now_iso()
        brief["status"] = "archived"
        brief["archived_at"] = now
        brief["updated_at"] = now
        brief["trusted_for_execution"] = False
        brief["inert_context_only"] = True
        _atomic_write_json(path, brief)
        _append_audit("brief_archived", brief)
    return {"brief": redact_value(brief)}
