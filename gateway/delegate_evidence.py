"""Safe evidence records for delegate_task runs.

Records are kept in process memory for fast current-turn access and mirrored
to a small HERMES_HOME JSON store so final reports and recovery can inspect
delegation after a gateway restart. The durable store keeps only redacted
metadata, never full prompts, raw session keys, or child result bodies.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from utils import atomic_json_write


DELEGATE_EVIDENCE_LANES = (
    "implementation",
    "review",
    "verification",
    "safety",
    "deployment",
    "domain",
)

TRUSTED_DELEGATE_PROVENANCE = "internal_delegate_tool"
_MAX_RECORDS = 200
_MAX_SUMMARY_CHARS = 500
_records: deque[dict[str, Any]] = deque(maxlen=_MAX_RECORDS)
_records_lock = threading.Lock()
_store_lock = threading.Lock()

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9._-]{8,}\b"),
    re.compile(r"\b[A-Za-z0-9_]*(?:token|secret|password|api[_-]?key)[A-Za-z0-9_]*\s*[:=]\s*\S+", re.I),
    re.compile(r"private prompt[^.\n,;]*", re.I),
    re.compile(r"confidential prompt[^.\n,;]*", re.I),
    re.compile(r"\b(?:prompt|message)\b[^.\n]*(?:[.\n]|$)", re.I),
    re.compile(r"\b(?:user|assistant|system)\s*:[^.\n]*(?:[.\n]|$)", re.I),
    re.compile(r"\bplatform:[A-Za-z0-9:._-]{8,}\b", re.I),
    re.compile(r"\b(?:session|thread|channel|message|discord)[-_:\s]*(?:id[-_:\s]*)?[A-Za-z0-9:._-]{12,}\b", re.I),
    re.compile(r"\b\d{17,20}\b"),
    re.compile(r"\b(?=[A-Za-z0-9._-]{32,}\b)(?=[A-Za-z0-9._-]*[A-Za-z])(?=[A-Za-z0-9._-]*\d)[A-Za-z0-9._-]{32,}\b"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_ref(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]}"


def get_delegate_evidence_store_path() -> Path:
    return get_hermes_home() / "delegate_evidence.json"


def redact_delegate_text(value: Any, *, max_chars: int = _MAX_SUMMARY_CHARS) -> str:
    """Return a short, secret-scrubbed text summary."""
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern in _SECRET_PATTERNS:
        replacement = "[redacted-id]" if pattern.pattern in {
            r"\bplatform:[A-Za-z0-9:._-]{8,}\b",
            r"\b(?:session|thread|channel|message|discord)[-_:\s]*(?:id[-_:\s]*)?[A-Za-z0-9:._-]{12,}\b",
            r"\b\d{17,20}\b",
        } else "[redacted]"
        text = pattern.sub(replacement, text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 15].rstrip() + " ...[truncated]"
    return text


def normalize_delegate_lane(lane: Any = None, *, task_goal: Any = None, context: Any = None) -> str:
    explicit = str(lane or "").strip().lower()
    if explicit in DELEGATE_EVIDENCE_LANES:
        return explicit

    folded = f"{task_goal or ''} {context or ''}".lower()
    if any(term in folded for term in ("review", "audit", "critique")):
        return "review"
    if any(term in folded for term in ("verify", "test", "validation", "check")):
        return "verification"
    if any(term in folded for term in ("safe", "security", "secret", "risk")):
        return "safety"
    if any(term in folded for term in ("deploy", "restart", "runtime", "production")):
        return "deployment"
    if any(term in folded for term in ("research", "domain", "analyze")):
        return "domain"
    return "implementation"


def normalize_delegate_status(status: Any) -> str:
    folded = str(status or "").strip().lower()
    if folded in {"completed", "complete", "succeeded", "success", "ok"}:
        return "succeeded"
    if folded in {"pending"}:
        return "pending"
    if folded in {"interrupted", "timeout", "failed", "failure", "error"}:
        return "failed"
    if folded == "skipped":
        return "skipped"
    return "failed"


def is_real_delegate_evidence(record: Any) -> bool:
    """Return True only for trusted evidence emitted by Hermes delegate_task."""
    if not isinstance(record, dict):
        return False
    if record.get("provenance") != TRUSTED_DELEGATE_PROVENANCE:
        return False
    if record.get("evidence_source") != "delegate_task":
        return False
    if record.get("delegate_name") != "delegate_task":
        return False
    if record.get("delegate_type") != "subagent":
        return False
    if record.get("status") not in {"succeeded", "failed", "pending", "skipped"}:
        return False
    evidence_id = str(record.get("evidence_id") or "")
    if not evidence_id.startswith("delegate-"):
        return False
    for known in _merged_records():
        if not isinstance(known, dict) or known.get("evidence_id") != evidence_id:
            continue
        return known == record
    return False


def record_delegate_evidence(
    *,
    lane: Any = None,
    task_goal: Any = None,
    context: Any = None,
    delegate_name: str = "delegate_task",
    delegate_type: str = "subagent",
    invoked_at: str | None = None,
    completed_at: str | None = None,
    status: Any = "pending",
    result_summary: Any = "",
    evidence_pointer: Any = None,
    session_key: Any = None,
    child_session_id: Any = None,
    active_task_id: Any = None,
    goal_id: Any = None,
    final_report_id: Any = None,
    repo_path: Any = None,
    branch: Any = None,
    head: Any = None,
    evidence_source: str = "delegate_task",
    process_id: Any = None,
) -> dict[str, Any]:
    """Append and return a redacted delegate evidence record."""
    normalized_lane = normalize_delegate_lane(lane, task_goal=task_goal, context=context)
    session_key_hash = _hash_ref(session_key)
    task_ref = session_key_hash or _hash_ref(task_goal)
    pointer = _hash_ref(evidence_pointer) or _hash_ref(child_session_id)
    invoked = invoked_at or _now_iso()
    record = {
        "evidence_id": f"delegate-{uuid.uuid4().hex[:16]}",
        "provenance": TRUSTED_DELEGATE_PROVENANCE if evidence_source == "delegate_task" else "untrusted",
        "task_ref": task_ref,
        "session_key_hash": session_key_hash,
        "active_task_id": _hash_ref(active_task_id),
        "goal_id": _hash_ref(goal_id),
        "final_report_id": _hash_ref(final_report_id),
        "lane": normalized_lane,
        "delegate_name": str(delegate_name or "delegate_task"),
        "delegate_type": str(delegate_type or "subagent"),
        "invoked_at": invoked,
        "completed_at": completed_at,
        "status": normalize_delegate_status(status),
        "safe_result_summary": redact_delegate_text(result_summary),
        "evidence_pointer": pointer,
        "evidence_source": evidence_source if evidence_source in {"delegate_task", "checklist_fallback"} else "untrusted",
        "process_id_hash": _hash_ref(process_id),
        "repo_path": redact_delegate_text(repo_path, max_chars=300),
        "branch": redact_delegate_text(branch, max_chars=120),
        "head": redact_delegate_text(head, max_chars=80),
    }
    record = {key: value for key, value in record.items() if value not in (None, "")}
    with _records_lock:
        _records.append(dict(record))
    _append_durable_record(record)
    return record


def _read_durable_records_unlocked(path: Path | None = None) -> list[dict[str, Any]]:
    store_path = path or get_delegate_evidence_store_path()
    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError):
        return []
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return []
    return [dict(item) for item in records if isinstance(item, dict)]


def _append_durable_record(record: dict[str, Any]) -> None:
    path = get_delegate_evidence_store_path()
    with _store_lock:
        records = _read_durable_records_unlocked(path)
        records.append(dict(record))
        records = records[-_MAX_RECORDS:]
        try:
            atomic_json_write(path, {"records": records}, indent=2)
        except OSError:
            return


def _merged_records() -> list[dict[str, Any]]:
    with _store_lock:
        records = _read_durable_records_unlocked()
    with _records_lock:
        records.extend(dict(item) for item in _records)
    by_id: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for record in records:
        evidence_id = record.get("evidence_id")
        if evidence_id:
            by_id[str(evidence_id)] = record
        else:
            anonymous.append(record)
    return anonymous + list(by_id.values())


def get_recent_delegate_evidence(
    limit: int = 20,
    *,
    session_key: Any = None,
    session_id: Any = None,
) -> list[dict[str, Any]]:
    records = _merged_records()
    ref_filter = _hash_ref(session_key) or _hash_ref(session_id)
    if ref_filter:
        records = [
            record
            for record in records
            if record.get("task_ref") == ref_filter
            or record.get("session_key_hash") == ref_filter
        ]
    records = records[-max(0, int(limit)) :]
    return [dict(record) for record in records]


def clear_delegate_evidence_records(*, clear_durable: bool = False) -> None:
    """Test helper; production callers should not need this."""
    with _records_lock:
        _records.clear()
    if clear_durable:
        try:
            get_delegate_evidence_store_path().unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def summarize_delegate_evidence(records: list[dict[str, Any]] | None = None) -> str:
    items = records if records is not None else get_recent_delegate_evidence()
    safe_items = [item for item in items if isinstance(item, dict)]
    if not safe_items:
        return ""
    parts = []
    for item in safe_items[:5]:
        lane = item.get("lane") or "unknown"
        status = item.get("status") or "unknown"
        summary = item.get("safe_result_summary") or "no summary"
        parts.append(f"lane={lane}; status={status}; summary={summary}")
    return " | ".join(parts)
