"""Read-only Mission Control to Kanban linkage helpers."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_LINK_STATES = {"linked", "missing_link", "stale_link", "scope_mismatch", "unknown"}


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
    board_id = _text(metadata.get("kanban_board_id") or nested_map.get("board_id") or nested_map.get("board"))
    task_id = _text(metadata.get("kanban_task_id") or nested_map.get("task_id") or nested_map.get("task"))
    if not task_id:
        return None

    goal_contract_id = _text(
        metadata.get("goal_contract_id")
        or nested_map.get("goal_contract_id")
        or (record_id if getattr(record, "record_type", "") == "GoalContract" else "")
    )
    envelope_id = _text(
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
        return KanbanLinkValidation("unknown", (read_error,))
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
        "board_id": link.board_id if link else "",
        "board_name": read_kanban_board_name(link.board_id) if link else "",
        "task_id": link.task_id if link else "",
        "task_title": observed.title if observed else "",
        "task_status": observed.status if observed else "",
        "task_workspace": observed.workspace_path if observed else "",
        "task_branch": observed.branch_name if observed else "",
        "linked_goal_contract_id": link.goal_contract_id if link else "",
        "linked_task_control_envelope_id": link.task_control_envelope_id if link else "",
        "reasons": list(validation.reasons),
    }
