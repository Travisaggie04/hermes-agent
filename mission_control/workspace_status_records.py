"""Record-sourced Mission Control workspace status projection.

This module keeps the pure status normalizer separate from filesystem reads,
while giving diagnostics and read-only APIs one canonical way to inject the
latest append-only Mission Control records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from mission_control.records import (
    AcceptedBaselineRecord,
    ApprovalRecord,
    ChildRunRecord,
    JsonlRecordStore,
    OperatingWorkspaceHandoffRecord,
    ReportRecord,
    RunRecord,
    WorkerNodeRunRecord,
)
from mission_control.records.errors import RecordStoreError
from mission_control.workspace_status import (
    build_workspace_status,
    default_workspace_status_input,
)


ACTIVE_RUN_STATUSES = {"requested", "preflight_passed", "running", "stopping"}
ACTIVE_ORCHESTRATION_STATUSES = {"requested", "assigned", "preflight_passed", "running", "stopping", "blocked"}
PENDING_APPROVAL_STATUSES = {"proposed"}
AVAILABLE_APPROVAL_STATUSES = {"approved"}
APPROVAL_TERMINAL_STATUSES = {"cancelled", "consumed", "expired", "rejected", "revoked"}
REPORT_OPEN_STATUSES = {"received", "needs_review"}
REPORT_REVIEWED_STATUSES = {"reviewed"}
REPORT_TERMINAL_STATUSES = {"accepted", "rejected", "superseded"}
RUN_REPORT_REQUIRED_STATUSES = {"completed", "failed", "blocked", "stopped", "cancelled"}
RUN_TERMINAL_STATUSES = {"completed", "failed", "blocked", "stopped", "cancelled"}
RUN_STOP_CANCEL_STATUSES = {"stopping", "stopped", "cancelled"}
MUTATION_LANE_TYPES = {
    "implementation",
    "pr_creation",
    "deploy",
    "runtime_switch",
    "payment",
    "waha",
    "social_post",
    "model_routing",
    "queue_mutation",
    "worker_timer_enablement",
}


def default_record_store_path() -> Path:
    return get_hermes_home() / "mission-control" / "records.jsonl"


def build_workspace_status_from_records(
    payload: dict[str, Any] | None = None,
    *,
    records_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build workspace status using the latest append-only records.

    The returned payload remains display-only and inert. Missing or malformed
    stores fail closed into the pure status builder's static fallback warnings;
    no records are written or mutated.
    """
    path = Path(records_path) if records_path is not None else default_record_store_path()
    status_input = _merge_status_input(default_workspace_status_input(), payload or {})
    store = JsonlRecordStore(path)
    store_status = _record_store_state(path)
    store_error = ""

    if store_status == "ok":
        try:
            latest_baseline = _latest_record_payload(store, AcceptedBaselineRecord)
            latest_handoff = _latest_record_payload(store, OperatingWorkspaceHandoffRecord)
            recent_runs_raw = tuple(
                record for _index, record in store.read_latest(RunRecord, limit=50)
            )
            recent_approvals_raw = tuple(
                record for _index, record in store.read_latest(ApprovalRecord, limit=50)
            )
            recent_reports_raw = tuple(
                record for _index, record in store.read_latest(ReportRecord, limit=50)
            )
            recent_runs = tuple(_latest_records_by_id(recent_runs_raw, "run_id").values())
            recent_approvals = tuple(_latest_records_by_id(recent_approvals_raw, "approval_id").values())
            recent_reports = tuple(_latest_records_by_id(recent_reports_raw, "report_id").values())
            recent_child_runs = tuple(
                _latest_records_by_id(
                    tuple(record for _index, record in store.read_latest(ChildRunRecord, limit=50)),
                    "child_run_id",
                ).values()
            )
            recent_worker_runs = tuple(
                _latest_records_by_id(
                    tuple(record for _index, record in store.read_latest(WorkerNodeRunRecord, limit=50)),
                    "worker_run_id",
                ).values()
            )
        except RecordStoreError as exc:
            store_status = "malformed"
            store_error = type(exc).__name__
            latest_baseline = {}
            latest_handoff = {}
            recent_runs_raw = ()
            recent_approvals_raw = ()
            recent_runs = ()
            recent_approvals = ()
            recent_reports = ()
            recent_reports_raw = ()
            recent_child_runs = ()
            recent_worker_runs = ()
    else:
        latest_baseline = {}
        latest_handoff = {}
        recent_runs_raw = ()
        recent_approvals_raw = ()
        recent_runs = ()
        recent_approvals = ()
        recent_reports = ()
        recent_reports_raw = ()
        recent_child_runs = ()
        recent_worker_runs = ()

    if latest_baseline:
        status_input["accepted_baseline_record"] = latest_baseline
    if latest_handoff:
        status_input["latest_handoff"] = latest_handoff

    active_runs = tuple(record for record in recent_runs if record.status in ACTIVE_RUN_STATUSES)
    active_mutation_runs = tuple(
        record
        for record in active_runs
        if record.lane_type in MUTATION_LANE_TYPES or record.dispatch_state is True
    )
    if active_runs:
        latest_active_run = active_runs[-1]
        status_input["lane"] = _merge_status_input(
            status_input.get("lane") if isinstance(status_input.get("lane"), dict) else {},
            {
                "active_lane": latest_active_run.title
                or latest_active_run.objective
                or latest_active_run.run_id,
                "mode": latest_active_run.execution_mode,
                "declared_baseline_head": latest_active_run.baseline_head or latest_baseline.get("head", ""),
                "active_lane_count": len(active_runs),
            },
        )
        latest_approval = _latest_matching_approval(recent_approvals, latest_active_run.approval_id)
        status_input["autonomy_eligibility"] = _merge_status_input(
            status_input.get("autonomy_eligibility") if isinstance(status_input.get("autonomy_eligibility"), dict) else {},
            {
                "approval": latest_approval.to_dict() if latest_approval else {},
                "run": latest_active_run.to_dict(),
                "report_inbox_ready": store_status == "ok",
                "report": recent_reports[-1].to_dict() if recent_reports else {},
                "active_mutation_lane_count": len(active_mutation_runs),
            },
        )
    status_input["activity"] = _merge_status_input(
        status_input.get("activity") if isinstance(status_input.get("activity"), dict) else {},
        {"active_runs": len(active_runs)},
    )
    status_input["control_plane_lifecycle"] = _control_plane_lifecycle_payload(
        approvals=recent_approvals,
        runs=recent_runs,
        reports=recent_reports,
        active_mutation_lane_count=len(active_mutation_runs),
    )

    active_child_runs = tuple(record for record in recent_child_runs if record.status in ACTIVE_ORCHESTRATION_STATUSES)
    active_worker_runs = tuple(record for record in recent_worker_runs if record.status in ACTIVE_ORCHESTRATION_STATUSES)
    reports_by_id, reports_by_run_id = _report_lookup_maps(recent_reports)

    status = build_workspace_status(status_input)
    status["child_agent_orchestration"] = _orchestration_projection(
        records=recent_child_runs,
        active_records=active_child_runs,
        id_field="child_run_id",
        reports_by_id=reports_by_id,
        reports_by_run_id=reports_by_run_id,
        source="ChildRunRecord",
    )
    status["worker_node_orchestration"] = _orchestration_projection(
        records=recent_worker_runs,
        active_records=active_worker_runs,
        id_field="worker_run_id",
        reports_by_id=reports_by_id,
        reports_by_run_id=reports_by_run_id,
        source="WorkerNodeRunRecord",
    )
    status["control_plane_lifecycle"] = status_input["control_plane_lifecycle"]
    status["approval_lifecycle"] = _approval_lifecycle_payload(
        approvals=recent_approvals,
        raw_approvals=recent_approvals_raw,
        runs=recent_runs,
        now=_safe_text(status_input.get("now")),
    )
    status["run_lifecycle"] = _run_lifecycle_payload(
        runs=recent_runs,
        raw_runs=recent_runs_raw,
        reports=recent_reports,
        active_mutation_lane_count=len(active_mutation_runs),
    )
    status["report_lifecycle"] = _report_lifecycle_payload(
        reports=recent_reports,
        raw_reports=recent_reports_raw,
        runs=recent_runs,
    )
    status["record_store"] = {
        "status": store_status,
        "error": store_error,
        "records_path_configured": bool(records_path),
    }
    status["control_plane_records"] = {
        "source": "mission_control_records_jsonl",
        "active_run_count": len(active_runs),
        "latest_active_run_id": active_runs[-1].run_id if active_runs else "",
        "pending_approval_count": sum(
            1 for record in recent_approvals if record.status in PENDING_APPROVAL_STATUSES
        ),
        "available_approval_count": sum(
            1 for record in recent_approvals if record.status in AVAILABLE_APPROVAL_STATUSES
        ),
        "active_mutation_lane_count": len(active_mutation_runs),
        "active_child_run_count": len(active_child_runs),
        "active_worker_node_run_count": len(active_worker_runs),
    }
    status["next_safe_actions"] = _next_safe_actions_payload(status)
    return status


def _record_store_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.stat().st_size == 0:
        return "empty"
    return "ok"


def _latest_record_payload(store: JsonlRecordStore, record_class: type[Any]) -> dict[str, Any]:
    records = store.read_latest(record_class, limit=1)
    if not records:
        return {}
    _index, record = records[-1]
    return record.to_dict()


def _latest_matching_approval(records: tuple[ApprovalRecord, ...], approval_id: str) -> ApprovalRecord | None:
    if not approval_id:
        return None
    for record in reversed(records):
        if record.approval_id == approval_id:
            return record
    return None


def _control_plane_lifecycle_payload(
    *,
    approvals: tuple[ApprovalRecord, ...],
    runs: tuple[RunRecord, ...],
    reports: tuple[ReportRecord, ...],
    active_mutation_lane_count: int,
) -> dict[str, Any]:
    return {
        "source": "mission_control_records_jsonl",
        "latest_approvals_by_id": _latest_by_id(approvals, "approval_id"),
        "latest_runs_by_id": _latest_by_id(runs, "run_id"),
        "latest_reports_by_id": _latest_by_id(reports, "report_id"),
        "active_mutation_lane_count": active_mutation_lane_count,
        "append_only_projection": True,
    }


def _approval_lifecycle_payload(
    *,
    approvals: tuple[ApprovalRecord, ...],
    raw_approvals: tuple[ApprovalRecord, ...],
    runs: tuple[RunRecord, ...],
    now: str = "",
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    available_approval_ids: list[str] = []
    expired_approval_ids: list[str] = []
    consumed_approval_ids: list[str] = []
    rejected_or_cancelled_approval_ids: list[str] = []
    pending_approval_ids: list[str] = []
    terminal_approval_ids: list[str] = []
    for approval in approvals:
        status = str(approval.status or "proposed")
        status_counts[status] = status_counts.get(status, 0) + 1
        expired = _approval_is_expired(approval, now=now)
        consumed = bool(approval.consumed_at) or status == "consumed"
        rejected_or_cancelled = status in {"cancelled", "rejected", "revoked"}
        if status in PENDING_APPROVAL_STATUSES:
            pending_approval_ids.append(approval.approval_id)
        if expired:
            expired_approval_ids.append(approval.approval_id)
        if consumed:
            consumed_approval_ids.append(approval.approval_id)
        if rejected_or_cancelled:
            rejected_or_cancelled_approval_ids.append(approval.approval_id)
        if expired or consumed or status in APPROVAL_TERMINAL_STATUSES:
            terminal_approval_ids.append(approval.approval_id)
        if status in AVAILABLE_APPROVAL_STATUSES and not expired and not consumed:
            available_approval_ids.append(approval.approval_id)

    approvals_by_id = {approval.approval_id: approval for approval in approvals if approval.approval_id}
    unavailable_approval_ids = (
        set(expired_approval_ids)
        | set(consumed_approval_ids)
        | set(rejected_or_cancelled_approval_ids)
    )
    runs_by_approval_id: dict[str, list[str]] = {}
    runs_missing_approval_id: list[str] = []
    runs_with_missing_approval_record: dict[str, str] = {}
    runs_with_unavailable_approval: dict[str, str] = {}
    for run in runs:
        if run.status not in ACTIVE_RUN_STATUSES:
            continue
        if not run.approval_id:
            runs_missing_approval_id.append(run.run_id)
            continue
        runs_by_approval_id.setdefault(run.approval_id, []).append(run.run_id)
        if run.approval_id not in approvals_by_id:
            runs_with_missing_approval_record[run.run_id] = run.approval_id
        elif run.approval_id in unavailable_approval_ids:
            runs_with_unavailable_approval[run.run_id] = run.approval_id

    duplicate_approval_ids = _duplicate_record_ids(raw_approvals, "approval_id")
    blocked_reasons: list[str] = []
    for approval_id in duplicate_approval_ids:
        blocked_reasons.append(f"approval_id {approval_id} has multiple append-only records")
    for run_id in runs_missing_approval_id:
        blocked_reasons.append(f"active run_id {run_id} has no approval_id")
    for run_id, approval_id in runs_with_missing_approval_record.items():
        blocked_reasons.append(f"run_id {run_id} references missing approval_id {approval_id}")
    for run_id, approval_id in runs_with_unavailable_approval.items():
        blocked_reasons.append(f"run_id {run_id} references unavailable approval_id {approval_id}")

    return {
        "source": "ApprovalRecord",
        "display_only": True,
        "trusted_for_execution": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "append_only_projection": True,
        "approval_count": len(approvals),
        "raw_approval_count": len(raw_approvals),
        "status_counts": status_counts,
        "available_approval_ids": available_approval_ids,
        "pending_approval_ids": pending_approval_ids,
        "expired_approval_ids": expired_approval_ids,
        "consumed_approval_ids": consumed_approval_ids,
        "rejected_or_cancelled_approval_ids": rejected_or_cancelled_approval_ids,
        "terminal_approval_ids": terminal_approval_ids,
        "duplicate_approval_ids": duplicate_approval_ids,
        "runs_by_approval_id": runs_by_approval_id,
        "runs_missing_approval_id": runs_missing_approval_id,
        "runs_with_missing_approval_record": runs_with_missing_approval_record,
        "runs_with_unavailable_approval": runs_with_unavailable_approval,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def _run_lifecycle_payload(
    *,
    runs: tuple[RunRecord, ...],
    raw_runs: tuple[RunRecord, ...],
    reports: tuple[ReportRecord, ...],
    active_mutation_lane_count: int,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    active_run_ids: list[str] = []
    active_mutation_run_ids: list[str] = []
    terminal_run_ids: list[str] = []
    stop_cancel_run_ids: list[str] = []
    runs_by_status: dict[str, list[str]] = {}
    report_ids = {report.report_id for report in reports}
    reports_by_run_id = {report.run_id for report in reports if report.run_id}
    terminal_runs_missing_report: list[str] = []
    terminal_runs_with_missing_linked_report_ids: dict[str, list[str]] = {}
    for run in runs:
        status = str(run.status or "requested")
        status_counts[status] = status_counts.get(status, 0) + 1
        runs_by_status.setdefault(status, []).append(run.run_id)
        if status in ACTIVE_RUN_STATUSES:
            active_run_ids.append(run.run_id)
        if status in ACTIVE_RUN_STATUSES and (run.lane_type in MUTATION_LANE_TYPES or run.dispatch_state is True):
            active_mutation_run_ids.append(run.run_id)
        if status in RUN_TERMINAL_STATUSES:
            terminal_run_ids.append(run.run_id)
        if status in RUN_STOP_CANCEL_STATUSES:
            stop_cancel_run_ids.append(run.run_id)
        if status in RUN_REPORT_REQUIRED_STATUSES and not run.report_ids and run.run_id not in reports_by_run_id:
            terminal_runs_missing_report.append(run.run_id)
        missing_report_ids = [report_id for report_id in run.report_ids if report_id not in report_ids]
        if status in RUN_REPORT_REQUIRED_STATUSES and missing_report_ids:
            terminal_runs_with_missing_linked_report_ids[run.run_id] = missing_report_ids

    duplicate_run_ids = _duplicate_record_ids(raw_runs, "run_id")
    blocked_reasons: list[str] = []
    for run_id in duplicate_run_ids:
        blocked_reasons.append(f"run_id {run_id} has multiple append-only records")
    if active_mutation_lane_count > 1:
        blocked_reasons.append("active mutation lane count exceeds one")
    for run_id in terminal_runs_missing_report:
        blocked_reasons.append(f"terminal run_id {run_id} has no linked report")
    for run_id, missing_report_ids in terminal_runs_with_missing_linked_report_ids.items():
        blocked_reasons.append(f"run_id {run_id} links missing report ids: {', '.join(missing_report_ids)}")

    return {
        "source": "RunRecord",
        "display_only": True,
        "trusted_for_execution": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "append_only_projection": True,
        "run_count": len(runs),
        "raw_run_count": len(raw_runs),
        "status_counts": status_counts,
        "runs_by_status": runs_by_status,
        "active_run_ids": active_run_ids,
        "active_mutation_run_ids": active_mutation_run_ids,
        "active_mutation_lane_count": active_mutation_lane_count,
        "one_active_mutation_lane_rule_passed": active_mutation_lane_count <= 1,
        "terminal_run_ids": terminal_run_ids,
        "stop_cancel_run_ids": stop_cancel_run_ids,
        "duplicate_run_ids": duplicate_run_ids,
        "terminal_runs_missing_report": terminal_runs_missing_report,
        "terminal_runs_with_missing_linked_report_ids": terminal_runs_with_missing_linked_report_ids,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def _report_lifecycle_payload(
    *,
    reports: tuple[ReportRecord, ...],
    raw_reports: tuple[ReportRecord, ...],
    runs: tuple[RunRecord, ...],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    reports_by_run_id: dict[str, list[str]] = {}
    open_report_ids: list[str] = []
    terminal_report_ids: list[str] = []
    reviewed_report_ids: list[str] = []
    for report in reports:
        status = str(report.status or "received")
        reviewed = status in REPORT_REVIEWED_STATUSES or bool(report.reviewed_at or report.reviewed_by)
        status_counts[status] = status_counts.get(status, 0) + 1
        if report.run_id:
            reports_by_run_id.setdefault(report.run_id, []).append(report.report_id)
        if status in REPORT_OPEN_STATUSES or (status not in REPORT_TERMINAL_STATUSES and not reviewed):
            open_report_ids.append(report.report_id)
        if status in REPORT_TERMINAL_STATUSES:
            terminal_report_ids.append(report.report_id)
        if reviewed:
            reviewed_report_ids.append(report.report_id)

    duplicate_report_ids = _duplicate_record_ids(raw_reports, "report_id")
    report_ids = {report.report_id for report in reports}
    run_ids_with_reports = set(reports_by_run_id)
    runs_missing_report = [
        run.run_id
        for run in runs
        if run.status in RUN_REPORT_REQUIRED_STATUSES
        and not run.report_ids
        and run.run_id not in run_ids_with_reports
    ]
    runs_with_missing_linked_report_ids = {
        run.run_id: [report_id for report_id in run.report_ids if report_id not in report_ids]
        for run in runs
        if run.status in RUN_REPORT_REQUIRED_STATUSES
        and run.report_ids
        and any(report_id not in report_ids for report_id in run.report_ids)
    }
    blocked_reasons: list[str] = []
    for report_id in duplicate_report_ids:
        blocked_reasons.append(f"report_id {report_id} has multiple append-only records")
    for run_id in runs_missing_report:
        blocked_reasons.append(f"run_id {run_id} has no linked report")
    for run_id, report_ids in runs_with_missing_linked_report_ids.items():
        blocked_reasons.append(f"run_id {run_id} links missing report ids: {', '.join(report_ids)}")
    for report_id in open_report_ids:
        blocked_reasons.append(f"report_id {report_id} still needs review")

    return {
        "source": "ReportRecord",
        "display_only": True,
        "trusted_for_execution": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "append_only_projection": True,
        "report_count": len(reports),
        "raw_report_count": len(raw_reports),
        "status_counts": status_counts,
        "open_report_ids": open_report_ids,
        "terminal_report_ids": terminal_report_ids,
        "reviewed_report_ids": reviewed_report_ids,
        "duplicate_report_ids": duplicate_report_ids,
        "runs_missing_report": runs_missing_report,
        "runs_with_missing_linked_report_ids": runs_with_missing_linked_report_ids,
        "reports_by_run_id": reports_by_run_id,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def _next_safe_actions_payload(status: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    def extend_blockers(values: list[str]) -> None:
        blocked_reasons.extend(values)

    def add_action(
        *,
        action_id: str,
        label: str,
        reason: str,
        blocked_until: str,
        priority: int,
        requires_approval: bool = False,
    ) -> None:
        if any(action.get("action_id") == action_id for action in actions):
            return
        actions.append(
            {
                "action_id": action_id,
                "label": label,
                "reason": reason,
                "priority": priority,
                "requires_approval": requires_approval,
                "manual_only": True,
                "blocked_until": blocked_until,
            }
        )

    runtime_provenance = _mapping(status.get("runtime_provenance"))
    provenance_reasons = _text_list(runtime_provenance.get("autonomy_blocked_reasons"))
    if runtime_provenance.get("autonomy_blocked") is True or provenance_reasons:
        extend_blockers(provenance_reasons)
        add_action(
            action_id="review_runtime_provenance_blockers",
            label="Review runtime provenance blockers",
            reason=_first_reason(provenance_reasons, "Mission Control cannot prove runtime/source truth is clean."),
            blocked_until="runtime provenance is clean and aligned",
            priority=10,
        )

    approval_lifecycle = _mapping(status.get("approval_lifecycle"))
    approval_reasons = _text_list(approval_lifecycle.get("blocked_reasons"))
    if approval_lifecycle.get("blocked") is True or approval_reasons:
        extend_blockers(approval_reasons)
        add_action(
            action_id="review_approval_lifecycle_blockers",
            label="Review approval lifecycle blockers",
            reason=_first_reason(approval_reasons, "Approval records are incomplete or unavailable."),
            blocked_until="approval chain is exact, available, and append-only consistent",
            priority=20,
        )

    run_lifecycle = _mapping(status.get("run_lifecycle"))
    run_reasons = _text_list(run_lifecycle.get("blocked_reasons"))
    if run_lifecycle.get("blocked") is True or run_reasons:
        extend_blockers(run_reasons)
        add_action(
            action_id="review_run_lifecycle_blockers",
            label="Review run lifecycle blockers",
            reason=_first_reason(run_reasons, "Run records are incomplete or unsafe for orchestration."),
            blocked_until="run lifecycle is consistent and mutation lanes obey the one-lane rule",
            priority=30,
        )

    report_lifecycle = _mapping(status.get("report_lifecycle"))
    report_reasons = _text_list(report_lifecycle.get("blocked_reasons"))
    if report_lifecycle.get("blocked") is True or report_reasons:
        extend_blockers(report_reasons)
        add_action(
            action_id="review_report_lifecycle_blockers",
            label="Review report lifecycle blockers",
            reason=_first_reason(report_reasons, "Reports are missing, duplicated, stale, or waiting for review."),
            blocked_until="required reports are linked and reviewed",
            priority=40,
        )

    worker_projection = _mapping(status.get("worker_node_orchestration"))
    worker_reasons = _text_list(worker_projection.get("blocked_reasons"))
    if worker_reasons:
        extend_blockers(worker_reasons)
        add_action(
            action_id="review_worker_node_blockers",
            label="Review laptop Codex worker-node blockers",
            reason=_first_reason(worker_reasons, "The laptop Codex worker-node is not ready for a reviewed report loop."),
            blocked_until="worker-node status and report contract are clear",
            priority=50,
        )

    child_projection = _mapping(status.get("child_agent_orchestration"))
    child_reasons = _text_list(child_projection.get("blocked_reasons"))
    if child_reasons:
        extend_blockers(child_reasons)
        add_action(
            action_id="review_child_agent_blockers",
            label="Review child-agent blockers",
            reason=_first_reason(child_reasons, "Child-agent records need review before delegation can be trusted."),
            blocked_until="child-agent reports and blockers are reviewed",
            priority=60,
        )

    tool_permissions = _mapping(status.get("tool_permission_classification"))
    tool_reasons = _text_list(tool_permissions.get("blocked_reasons"))
    write_capable_path_ids = _text_list(tool_permissions.get("write_capable_path_ids"))
    if tool_reasons or write_capable_path_ids or tool_permissions.get("read_only_safe") is False:
        extend_blockers(tool_reasons)
        extend_blockers([f"write-capable tool path: {path_id}" for path_id in write_capable_path_ids])
        add_action(
            action_id="review_tool_permission_blockers",
            label="Review write-capable tool paths",
            reason=_first_reason(
                [*tool_reasons, *write_capable_path_ids],
                "A bridge or tool path is not safe for read-only autonomy.",
            ),
            blocked_until="tool paths are manual-only or read-only safe",
            priority=70,
        )

    read_only_eligibility = _mapping(status.get("read_only_autonomy_eligibility"))
    read_only_reasons = _text_list(read_only_eligibility.get("blocked_reasons"))
    if read_only_eligibility.get("eligible") is False and read_only_reasons:
        extend_blockers(read_only_reasons)
        add_action(
            action_id="review_read_only_autonomy_blockers",
            label="Review read-only autonomy blockers",
            reason=_first_reason(read_only_reasons, "Read-only autonomy is not preview-ready."),
            blocked_until="read-only preview eligibility is satisfied",
            priority=80,
        )

    scoped_pr_eligibility = _mapping(status.get("scoped_pr_lane_eligibility"))
    scoped_pr_reasons = _text_list(scoped_pr_eligibility.get("blocked_reasons"))
    if scoped_pr_eligibility.get("eligible") is False and scoped_pr_reasons:
        extend_blockers(scoped_pr_reasons)
        add_action(
            action_id="review_scoped_pr_lane_blockers",
            label="Review scoped PR lane blockers",
            reason=_first_reason(scoped_pr_reasons, "Scoped PR creation is not preview-ready."),
            blocked_until="scoped PR preview eligibility is satisfied",
            priority=90,
        )

    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    if not actions and scoped_pr_eligibility.get("eligible") is True:
        add_action(
            action_id="prepare_scoped_pr_preview",
            label="Prepare a scoped PR preview packet",
            reason="Scoped PR eligibility is preview-ready; keep implementation and review manual.",
            blocked_until="human approval and PR review are complete",
            priority=100,
            requires_approval=True,
        )
    if not actions and read_only_eligibility.get("eligible") is True:
        add_action(
            action_id="prepare_read_only_preview",
            label="Prepare a supervised read-only preview packet",
            reason="Read-only eligibility is preview-ready; keep work packet execution disabled.",
            blocked_until="human approval confirms the exact read-only packet",
            priority=110,
            requires_approval=True,
        )
    if not actions:
        add_action(
            action_id="keep_preview_only_and_wait_for_approval",
            label="Keep Mission Control preview-only and wait for exact approval",
            reason="No executable action is enabled by this projection.",
            blocked_until="Travis approves a bounded next lane",
            priority=120,
            requires_approval=True,
        )

    primary_action = actions[0] if actions else {}
    return {
        "source": "mission_control_next_safe_actions_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "action_count": len(actions),
        "primary_action": primary_action,
        "primary_action_id": str(primary_action.get("action_id") or ""),
        "primary_action_label": str(primary_action.get("label") or ""),
        "actions": actions,
    }


def _latest_by_id(records: tuple[Any, ...], field_name: str) -> dict[str, dict[str, Any]]:
    return {
        record_id: record.to_dict()
        for record_id, record in _latest_records_by_id(records, field_name).items()
    }


def _latest_records_by_id(records: tuple[Any, ...], field_name: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for record in records:
        record_id = str(getattr(record, field_name, "") or "")
        if record_id:
            output.pop(record_id, None)
            output[record_id] = record
    return output


def _duplicate_record_ids(records: tuple[Any, ...], field_name: str) -> list[str]:
    counts: dict[str, int] = {}
    for record in records:
        record_id = str(getattr(record, field_name, "") or "")
        if record_id:
            counts[record_id] = counts.get(record_id, 0) + 1
    return [record_id for record_id, count in counts.items() if count > 1]


def _report_lookup_maps(
    reports: tuple[ReportRecord, ...],
) -> tuple[dict[str, ReportRecord], dict[str, ReportRecord]]:
    reports_by_id: dict[str, ReportRecord] = {}
    reports_by_run_id: dict[str, ReportRecord] = {}
    for report in reports:
        if report.report_id:
            reports_by_id[report.report_id] = report
        if report.run_id:
            reports_by_run_id[report.run_id] = report
    return reports_by_id, reports_by_run_id


def _orchestration_projection(
    *,
    records: tuple[Any, ...],
    active_records: tuple[Any, ...],
    id_field: str,
    reports_by_id: dict[str, ReportRecord],
    reports_by_run_id: dict[str, ReportRecord],
    source: str,
) -> dict[str, Any]:
    record_payloads = tuple(
        _orchestration_payload(
            record,
            id_field=id_field,
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        for record in records
    )
    active_payloads = tuple(
        _orchestration_payload(
            record,
            id_field=id_field,
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        for record in active_records
    )
    return {
        "source": source,
        "display_only": True,
        "trusted_for_execution": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "active_count": len(active_records),
        "latest_by_id": _latest_payloads_by_id(record_payloads, id_field),
        "active_runs": list(active_payloads),
        "blocked_reasons": _unique_reasons(
            [
                *_projection_blocked_reasons(active_records),
                *_projection_report_blocked_reasons(active_payloads, id_field),
            ]
        ),
    }


def _orchestration_payload(
    record: Any,
    *,
    id_field: str,
    reports_by_id: dict[str, ReportRecord],
    reports_by_run_id: dict[str, ReportRecord],
) -> dict[str, Any]:
    payload = record.to_dict()
    record_id = str(payload.get(id_field) or "")
    report_id = str(payload.get("report_id") or "")
    report = reports_by_id.get(report_id) if report_id else None
    report = report or reports_by_run_id.get(record_id)
    if report:
        review_status = _linked_report_review_status(report)
        payload["report_id"] = report_id or report.report_id
        payload["report_link_status"] = "linked_report_found"
        payload["linked_report"] = _linked_report_payload(report, review_status=review_status)
        payload["linked_report_status"] = report.status or "received"
        payload["linked_report_review_status"] = review_status
        payload["linked_report_summary"] = report.summary
        if not payload.get("report_review_status"):
            payload["report_review_status"] = review_status
    elif report_id:
        payload["report_link_status"] = "linked_report_missing"
    else:
        payload["report_link_status"] = "no_report_id_recorded"
    return payload


def _linked_report_payload(report: ReportRecord, *, review_status: str) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "run_id": report.run_id,
        "status": report.status or "received",
        "review_status": review_status,
        "summary": report.summary,
        "reviewed_at": report.reviewed_at,
        "reviewed_by": report.reviewed_by,
    }


def _linked_report_review_status(report: ReportRecord) -> str:
    status = str(report.status or "received")
    if status in REPORT_TERMINAL_STATUSES:
        return status
    if status in REPORT_REVIEWED_STATUSES or report.reviewed_at or report.reviewed_by:
        return "reviewed"
    return "needs_review"


def _latest_payloads_by_id(payloads: tuple[dict[str, Any], ...], field_name: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        record_id = str(payload.get(field_name) or "")
        if record_id:
            output.pop(record_id, None)
            output[record_id] = payload
    return output


def _projection_report_blocked_reasons(
    payloads: tuple[dict[str, Any], ...],
    id_field: str,
) -> list[str]:
    reasons: list[str] = []
    for payload in payloads:
        record_id = str(payload.get(id_field) or "")
        report_id = str(payload.get("report_id") or "")
        link_status = str(payload.get("report_link_status") or "")
        if report_id and link_status == "linked_report_missing":
            reasons.append(f"{id_field} {record_id} links missing report_id {report_id}")
        if report_id and payload.get("linked_report_review_status") == "needs_review":
            reasons.append(f"report_id {report_id} still needs review")
    return reasons


def _projection_blocked_reasons(records: tuple[Any, ...]) -> list[str]:
    reasons: list[str] = []
    for record in records:
        for item in getattr(record, "blocked_reasons", ()) or ():
            text = str(item).strip()
            if text and text not in reasons:
                reasons.append(text)
        failure_reason = str(getattr(record, "failure_reason", "") or "").strip()
        if failure_reason and failure_reason not in reasons:
            reasons.append(failure_reason)
    return reasons


def _unique_reasons(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_text(item) for item in value if _safe_text(item)]


def _first_reason(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def _approval_is_expired(approval: ApprovalRecord, *, now: str = "") -> bool:
    if not approval.expires_at:
        return False
    parsed_expires_at = _parse_datetime(approval.expires_at)
    if parsed_expires_at is None:
        return True
    parsed_now = _parse_datetime(now) if now else datetime.now(timezone.utc)
    return parsed_now is None or parsed_expires_at <= parsed_now


def _parse_datetime(value: str | None) -> datetime | None:
    text = _safe_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_text(value: Any, *, max_chars: int = 240) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\x00", "")[:max_chars]


def _merge_status_input(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_status_input(merged[key], value)
        else:
            merged[key] = value
    return merged
