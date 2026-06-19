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
