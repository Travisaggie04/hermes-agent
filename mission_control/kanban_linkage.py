"""Read-only Mission Control to Kanban linkage helpers."""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_LINK_STATES = {"linked", "missing_link", "stale_link", "scope_mismatch", "unknown"}
MAX_LINK_DISPLAY_CHARS = 120
MAX_LINK_REASONS = 5
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MULTISPACE_RE = re.compile(r"\s+")
_SECRET_TOKEN_RE = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{4,}|gh[pousr]_[a-z0-9_]{4,}|akia[a-z0-9]{4,}|"
    r"[a-z0-9_-]*(?:secret|token|api[_-]?key|password)[a-z0-9_-]*\s*[:=]\s*\S+)"
)


@dataclass(frozen=True)
class KanbanLink:
    board_id: str
    task_id: str
    goal_contract_id: str = ""
    task_control_envelope_id: str = ""


@dataclass(frozen=True)
class ObservedKanbanTaskState:
    board_id: str
    task_id: str
    title: str
    status: str
    workspace_path: str = ""
    branch_name: str = ""


@dataclass(frozen=True)
class KanbanLinkValidation:
    state: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.state not in VALID_LINK_STATES:
            raise ValueError(f"unknown Kanban link state: {self.state}")
        object.__setattr__(self, "reasons", tuple(str(reason) for reason in self.reasons if reason))


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bounded_display_text(value: Any, *, max_chars: int = MAX_LINK_DISPLAY_CHARS) -> str:
    text = _ANSI_ESCAPE_RE.sub("", str(value or ""))
    text = _CONTROL_CHARS_RE.sub(" ", text)
    text = _SECRET_TOKEN_RE.sub("[redacted]", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _has_hidden_path_part(value: str) -> bool:
    return any(part.startswith(".") for part in Path(value).parts if part not in (".", "..", os.sep))


def _safe_path_label(value: Any, *, hidden_label: str = "[path hidden]") -> str:
    raw = _bounded_display_text(value, max_chars=512)
    if not raw:
        return ""
    path = Path(raw).expanduser()
    if path.is_absolute() or raw.startswith("~"):
        if _has_hidden_path_part(raw):
            return hidden_label
        return _bounded_display_text(path.name or "[path set]")
    if "/" in raw or "\\" in raw:
        if _has_hidden_path_part(raw):
            return hidden_label
        return _bounded_display_text(Path(raw).name or raw)
    return _bounded_display_text(raw)


def _safe_link_id(value: Any, *, default: str = "") -> str:
    return _safe_path_label(value, hidden_label="[id hidden]") or default


def _safe_workspace_label(value: Any) -> str:
    return _safe_path_label(value, hidden_label="[workspace path hidden]")


def _safe_reasons(reasons: tuple[str, ...]) -> list[str]:
    return [
        reason
        for reason in (_bounded_display_text(item) for item in reasons[:MAX_LINK_REASONS])
        if reason
    ]


def _metadata(record: Any) -> dict[str, Any]:
    value = getattr(record, "metadata", {}) or {}
    return value if isinstance(value, dict) else {}


def extract_kanban_link(record: Any, *, record_id: str = "") -> KanbanLink | None:
    """Extract a sanitized Kanban link from existing record metadata.

    Supports flat keys (``kanban_board_id`` / ``kanban_task_id``) and a nested
    ``kanban`` mapping. Other metadata remains private to callers.
    """
    metadata = _metadata(record)
    nested = metadata.get("kanban")
    nested_map = nested if isinstance(nested, dict) else {}
    board_id = _safe_link_id(metadata.get("kanban_board_id") or nested_map.get("board_id") or nested_map.get("board"))
    task_id = _safe_link_id(metadata.get("kanban_task_id") or nested_map.get("task_id") or nested_map.get("task"))
    if not task_id:
        return None

    goal_contract_id = _safe_link_id(
        metadata.get("goal_contract_id")
        or nested_map.get("goal_contract_id")
        or (record_id if getattr(record, "record_type", "") == "GoalContract" else "")
    )
    envelope_id = _safe_link_id(
        metadata.get("task_control_envelope_id")
        or nested_map.get("task_control_envelope_id")
        or getattr(record, "envelope_id", "")
        or (record_id if getattr(record, "record_type", "") == "TaskControlEnvelope" else "")
    )
    return KanbanLink(
        board_id=board_id or "default",
        task_id=task_id,
        goal_contract_id=goal_contract_id,
        task_control_envelope_id=envelope_id,
    )


def _expected_branch(envelope: Any | None) -> str:
    if envelope is None:
        return ""
    metadata = _metadata(envelope)
    nested = metadata.get("kanban")
    nested_map = nested if isinstance(nested, dict) else {}
    return _text(
        metadata.get("expected_branch")
        or metadata.get("branch_name")
        or nested_map.get("expected_branch")
        or nested_map.get("branch_name")
    )


def validate_kanban_linkage(
    link: KanbanLink | None,
    observed: ObservedKanbanTaskState | None,
    *,
    envelope: Any | None = None,
    read_error: str = "",
) -> KanbanLinkValidation:
    """Return a display-only linkage state; never enforces runtime behavior."""
    if read_error:
        return KanbanLinkValidation("unknown", ("read_error",))
    if link is None:
        return KanbanLinkValidation("missing_link")
    if observed is None:
        return KanbanLinkValidation("stale_link", ("linked Kanban task was not found",))

    reasons: list[str] = []
    if observed.task_id != link.task_id:
        reasons.append("observed Kanban task id does not match link")
    if observed.board_id != link.board_id:
        reasons.append("observed Kanban board does not match link")

    if envelope is not None:
        current_repo = _text(getattr(envelope, "current_repo", ""))
        if current_repo and observed.workspace_path and Path(current_repo) != Path(observed.workspace_path):
            reasons.append("current_repo does not match Kanban workspace")
        expected_branch = _expected_branch(envelope)
        if expected_branch and observed.branch_name and expected_branch != observed.branch_name:
            reasons.append("expected_branch does not match Kanban branch")

    if reasons:
        return KanbanLinkValidation("scope_mismatch", tuple(reasons))
    return KanbanLinkValidation("linked")


def _read_only_sqlite_connect(path: Path) -> sqlite3.Connection:
    uri = "file:" + os.fspath(path.resolve()) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def read_observed_kanban_task(link: KanbanLink) -> tuple[ObservedKanbanTaskState | None, str]:
    """Read linked Kanban task state without creating or mutating a board DB."""
    try:
        from hermes_cli import kanban_db

        db_path = kanban_db.kanban_db_path(link.board_id)
        if not db_path.exists():
            return None, ""
        with _read_only_sqlite_connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT id, title, status, workspace_path, branch_name
                FROM tasks
                WHERE id = ?
                """,
                (link.task_id,),
            ).fetchone()
        if row is None:
            return None, ""
        return (
            ObservedKanbanTaskState(
                board_id=link.board_id,
                task_id=str(row["id"]),
                title=str(row["title"] or ""),
                status=str(row["status"] or ""),
                workspace_path=str(row["workspace_path"] or ""),
                branch_name=str(row["branch_name"] or ""),
            ),
            "",
        )
    except Exception as exc:
        return None, str(exc)


def read_kanban_board_name(board_id: str) -> str:
    try:
        from hermes_cli import kanban_db

        metadata = kanban_db.read_board_metadata(board_id)
    except Exception:
        return board_id
    return _text(metadata.get("name")) or board_id


def linked_kanban_task_payload(record: Any, *, record_id: str = "") -> dict[str, Any] | None:
    link = extract_kanban_link(record, record_id=record_id)
    observed = None
    read_error = ""
    if link is not None:
        observed, read_error = read_observed_kanban_task(link)
    validation = validate_kanban_linkage(link, observed, envelope=record, read_error=read_error)
    if link is None and validation.state == "missing_link":
        return None
    return {
        "link_state": validation.state,
        "board_id": _safe_link_id(link.board_id) if link else "",
        "board_name": _bounded_display_text(read_kanban_board_name(link.board_id)) if link else "",
        "task_id": _safe_link_id(link.task_id) if link else "",
        "task_title": _bounded_display_text(observed.title) if observed else "",
        "task_status": _bounded_display_text(observed.status) if observed else "",
        "task_workspace": _safe_workspace_label(observed.workspace_path) if observed else "",
        "task_branch": _bounded_display_text(observed.branch_name) if observed else "",
        "linked_goal_contract_id": _safe_link_id(link.goal_contract_id) if link else "",
        "linked_task_control_envelope_id": _safe_link_id(link.task_control_envelope_id) if link else "",
        "reasons": _safe_reasons(validation.reasons),
    }
