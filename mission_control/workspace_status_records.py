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
ORCHESTRATION_STOP_CANCEL_STATUSES = {"stopping", "stopped", "cancelled"}
WORKER_NODE_PRESENCE_STALE_SECONDS = 15 * 60
RESULT_INGESTION_ACCEPTED_REDACTION_STATUSES = {
    "operator_supplied_redacted",
    "redacted",
    "reviewed_redacted",
    "system_redacted",
}
RESULT_INGESTION_FORBIDDEN_METADATA_KEYS = {
    "api_key",
    "api_response",
    "auth_header",
    "auth_token",
    "authorization",
    "bearer_token",
    "canonical_packet_json",
    "client_secret",
    "comments",
    "cookie",
    "cookies",
    "discord_history",
    "discord_messages",
    "dotenv",
    "env_file",
    "env_secret",
    "environment_secret",
    "full_observed_state",
    "github_response",
    "local_path",
    "password",
    "path",
    "private_key",
    "pr_body",
    "raw_log",
    "raw_logs",
    "refresh_token",
    "secret",
    "session_cookie",
    "service_status",
    "token",
    "transcript",
    "transcripts",
}
RESULT_INGESTION_FORBIDDEN_METADATA_KEY_MARKERS = (
    "api_key",
    "auth_header",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "dotenv",
    "env_secret",
    "environment_secret",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
)
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
LIVE_EXECUTION_FLAG_NAMES = (
    "would_execute",
    "would_dispatch",
    "would_session_send",
    "execution_enabled",
    "dispatch_enabled",
    "session_send_enabled",
    "worker_dispatch_enabled",
)
INERT_PROJECTION_FLAGS = {
    "display_only": True,
    "trusted_for_execution": False,
    "inert_context_only": True,
    "would_execute": False,
    "would_dispatch": False,
    "would_session_send": False,
    "execution_enabled": False,
    "dispatch_enabled": False,
    "session_send_enabled": False,
    "worker_dispatch_enabled": False,
    "stored": False,
    "dry_run_only": True,
}
HARD_BOUNDARY_FORBIDDEN_ACTIONS = (
    "live deploy",
    "restart",
    "runtime switch",
    "AcceptedBaselineRecord append",
    "live state.db mutation",
    "live config mutation",
    "live record mutation",
    "live POST/PUT/PATCH/DELETE endpoint call",
    "live dispatch activation",
    "live session-send activation",
    "Waha/social/payment/model-routing/queue/worker/timer activation",
    "secrets inspection or output",
    "PR merge",
    "operational reconciliation of gateway/dashboard/baseline",
    "9121 /api/status gate",
)
HARD_BOUNDARY_SEPARATE_APPROVAL_ACTIONS = (
    "live operational reconciliation",
    "AcceptedBaselineRecord append",
    "live worker dispatch",
    "deploy/restart/runtime switch",
    "PR merge",
)


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
    latest_active_run = active_runs[-1] if active_runs else None
    latest_approval = (
        _latest_matching_approval(recent_approvals, latest_active_run.approval_id)
        if latest_active_run is not None
        else None
    )
    if active_runs:
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
    status_input["execution_mode_classification"] = _record_execution_mode_classification_input(
        latest_active_run=latest_active_run,
        latest_approval=latest_approval,
        active_worker_runs=active_worker_runs,
    )
    status_input["execution_packet_preview"] = _record_execution_packet_preview_input(
        latest_active_run=latest_active_run,
        latest_approval=latest_approval,
        active_mutation_lane_count=len(active_mutation_runs),
        active_worker_runs=active_worker_runs,
    )

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
    status["worker_node_presence"] = _worker_node_presence_payload(
        worker_runs=recent_worker_runs,
        active_worker_runs=active_worker_runs,
        now=_safe_text(status_input.get("now")),
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
    status["orchestration_run_graph"] = _orchestration_run_graph_payload(
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
        reports=recent_reports,
    )
    status["report_review_queue"] = _report_review_queue_payload(
        reports=recent_reports,
        raw_reports=recent_reports_raw,
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
    )
    status["result_ingestion_contract"] = _result_ingestion_contract_payload(
        reports=recent_reports,
        raw_reports=recent_reports_raw,
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
    )
    status["report_contract_compliance"] = _report_contract_compliance_payload(
        reports=recent_reports,
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
    )
    status["report_completion_path"] = _report_completion_path_payload(
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
        reports=recent_reports,
        raw_reports=recent_reports_raw,
    )
    status["orchestration_stop_control"] = _orchestration_stop_control_payload(
        runs=recent_runs,
        child_runs=recent_child_runs,
        worker_runs=recent_worker_runs,
        reports=recent_reports,
    )
    return decorate_workspace_status_operator_projections(status)


def decorate_workspace_status_operator_projections(status: dict[str, Any]) -> dict[str, Any]:
    """Attach inert operator-facing Mission Control projections to a status payload."""

    status["hard_boundary_contract"] = _hard_boundary_contract_payload(status)
    status["next_safe_actions"] = _next_safe_actions_payload(status)
    status["orchestration_readiness"] = _orchestration_readiness_payload(status)
    status["child_agent_instruction_preview"] = _child_agent_instruction_preview(status)
    status["worker_node_instruction_preview"] = _worker_node_instruction_preview(status)
    status["operator_decision_packet"] = _operator_decision_packet_payload(status)
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


def _record_execution_mode_classification_input(
    *,
    latest_active_run: RunRecord | None,
    latest_approval: ApprovalRecord | None,
    active_worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, Any]:
    worker = active_worker_runs[-1] if active_worker_runs else None
    run_payload = latest_active_run.to_dict() if latest_active_run is not None else {}
    worker_payload = worker.to_dict() if worker is not None else {}
    lane_type = _safe_text(
        run_payload.get("lane_type")
        or worker_payload.get("lane_mode")
        or worker_payload.get("mode")
    )
    if worker is not None:
        mode = "worker_node"
    elif lane_type in {"pr_creation", "scoped_pr"}:
        mode = "scoped_pr"
    elif lane_type in {"read_only_lane", "read_only_design", "read_only_inspection"} or lane_type.startswith("read_only"):
        mode = "read_only"
    else:
        mode = _safe_text(run_payload.get("execution_mode"))
    return {
        "mode": mode,
        "run": run_payload,
        "approval": _approval_packet_payload(latest_approval),
        "lane": {
            "lane_type": lane_type,
            "objective": _safe_text(
                run_payload.get("objective")
                or worker_payload.get("objective")
                or run_payload.get("title"),
                max_chars=800,
            ),
        },
        "worker_node": worker_payload,
    }


def _record_execution_packet_preview_input(
    *,
    latest_active_run: RunRecord | None,
    latest_approval: ApprovalRecord | None,
    active_mutation_lane_count: int,
    active_worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, Any]:
    worker = active_worker_runs[-1] if active_worker_runs else None
    run_payload = latest_active_run.to_dict() if latest_active_run is not None else {}
    approval_payload = _approval_packet_payload(latest_approval)
    worker_payload = worker.to_dict() if worker is not None else {}
    lane_type = _safe_text(
        run_payload.get("lane_type")
        or worker_payload.get("lane_mode")
        or worker_payload.get("mode")
    )
    if worker is not None:
        mode = "worker_node"
    elif lane_type in {"pr_creation", "scoped_pr"}:
        mode = "scoped_pr"
    elif lane_type in {"read_only_lane", "read_only_design", "read_only_inspection"} or lane_type.startswith("read_only"):
        mode = "read_only"
    else:
        mode = "blocked"

    lane_payload = {
        "lane_type": lane_type,
        "objective": _safe_text(
            run_payload.get("objective")
            or worker_payload.get("objective")
            or run_payload.get("title"),
            max_chars=800,
        ),
        "allowed_actions": _metadata_list(latest_active_run, "allowed_actions", "allowed_actions"),
        "forbidden_actions": _metadata_list(latest_active_run, "forbidden_actions", "forbidden_actions"),
        "files": _metadata_list(latest_active_run, "files", "allowed_files", "approved_files"),
        "directories": _metadata_list(latest_active_run, "directories", "allowed_directories", "approved_directories"),
    }
    contract_required = latest_active_run is not None or worker is not None
    return {
        "mode": mode,
        "run": run_payload,
        "approval": approval_payload,
        "lane": lane_payload,
        "worker_node": worker_payload,
        "report_contract": {
            "required": contract_required,
            "tests_required": mode in {"scoped_pr", "worker_node"},
            "review_required": contract_required,
            "result_summary_required": contract_required,
        },
        "active_mutation_lane_count": active_mutation_lane_count,
    }


def _approval_packet_payload(approval: ApprovalRecord | None) -> dict[str, Any]:
    if approval is None:
        return {}
    payload = approval.to_dict()
    metadata = approval.metadata if isinstance(approval.metadata, dict) else {}
    for key in ("approved_files", "files", "approved_directories", "directories"):
        values = _text_values(metadata.get(key))
        if values:
            payload[key] = values
    return payload


def _metadata_list(record: Any, field_name: str, *metadata_keys: str) -> list[str]:
    if record is None:
        return []
    direct = getattr(record, field_name, ())
    values = _text_values(direct)
    metadata = getattr(record, "metadata", {})
    if isinstance(metadata, dict):
        for key in metadata_keys:
            values.extend(_text_values(metadata.get(key)))
    return _unique_reasons(values)


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        text = _safe_text(value)
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        return [_safe_text(item) for item in value if _safe_text(item)]
    return []


def _control_plane_lifecycle_payload(
    *,
    approvals: tuple[ApprovalRecord, ...],
    runs: tuple[RunRecord, ...],
    reports: tuple[ReportRecord, ...],
    active_mutation_lane_count: int,
) -> dict[str, Any]:
    return {
        **INERT_PROJECTION_FLAGS,
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
        **INERT_PROJECTION_FLAGS,
        "source": "ApprovalRecord",
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
        **INERT_PROJECTION_FLAGS,
        "source": "RunRecord",
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
    overwrite_conflicts = _report_overwrite_conflicts(raw_reports)
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
    for report_id, fields in overwrite_conflicts.items():
        blocked_reasons.append(
            f"report_id {report_id} attempts to overwrite append-only report fields: {', '.join(fields)}"
        )
    for run_id in runs_missing_report:
        blocked_reasons.append(f"run_id {run_id} has no linked report")
    for run_id, report_ids in runs_with_missing_linked_report_ids.items():
        blocked_reasons.append(f"run_id {run_id} links missing report ids: {', '.join(report_ids)}")
    for report_id in open_report_ids:
        blocked_reasons.append(f"report_id {report_id} still needs review")

    return {
        **INERT_PROJECTION_FLAGS,
        "source": "ReportRecord",
        "append_only_projection": True,
        "report_count": len(reports),
        "raw_report_count": len(raw_reports),
        "status_counts": status_counts,
        "open_report_ids": open_report_ids,
        "terminal_report_ids": terminal_report_ids,
        "reviewed_report_ids": reviewed_report_ids,
        "duplicate_report_ids": duplicate_report_ids,
        "report_overwrite_conflict_ids": list(overwrite_conflicts),
        "report_overwrite_conflicts": overwrite_conflicts,
        "report_overwrite_conflict_count": len(overwrite_conflicts),
        "runs_missing_report": runs_missing_report,
        "runs_with_missing_linked_report_ids": runs_with_missing_linked_report_ids,
        "reports_by_run_id": reports_by_run_id,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def _report_overwrite_conflicts(raw_reports: tuple[ReportRecord, ...]) -> dict[str, list[str]]:
    grouped: dict[str, list[ReportRecord]] = {}
    for report in raw_reports:
        report_id = _safe_text(report.report_id)
        if report_id:
            grouped.setdefault(report_id, []).append(report)

    conflicts: dict[str, list[str]] = {}
    identity_fields = (
        "run_id",
        "approval_id",
        "project_id",
        "lane_request_id",
        "report_kind",
        "submitted_by",
        "submitted_from",
    )
    review_fields = ("status", "reviewed_at", "reviewed_by", "redaction_status")
    for report_id, reports_for_id in grouped.items():
        if len(reports_for_id) < 2:
            continue
        differing_fields = [
            field_name
            for field_name in (*identity_fields, *review_fields)
            if len({_safe_text(getattr(report, field_name, "")) for report in reports_for_id}) > 1
        ]
        if differing_fields:
            conflicts[report_id] = differing_fields
    return conflicts


def _hard_boundary_contract_payload(status: dict[str, Any]) -> dict[str, Any]:
    execution_packet = _mapping(status.get("execution_packet_preview"))
    execution_packet_body = _mapping(execution_packet.get("packet"))
    worker_contract = _mapping(execution_packet_body.get("worker_node_contract"))
    live_flag_payloads = (
        ("accepted baseline", status.get("accepted_baseline")),
        ("rollback baseline", status.get("rollback_baseline")),
        ("latest handoff", status.get("latest_handoff")),
        ("read-only eligibility", status.get("read_only_autonomy_eligibility")),
        ("scoped PR eligibility", status.get("scoped_pr_lane_eligibility")),
        ("tool permissions", status.get("tool_permission_classification")),
        ("execution mode", status.get("execution_mode_classification")),
        ("execution packet", execution_packet),
        ("execution packet body", execution_packet_body),
        ("worker contract", worker_contract),
        ("approval lifecycle", status.get("approval_lifecycle")),
        ("run lifecycle", status.get("run_lifecycle")),
        ("report lifecycle", status.get("report_lifecycle")),
        ("report review queue", status.get("report_review_queue")),
        ("result ingestion", status.get("result_ingestion_contract")),
        ("report contract", status.get("report_contract_compliance")),
        ("report completion", status.get("report_completion_path")),
        ("stop/cancel control", status.get("orchestration_stop_control")),
        ("orchestration run graph", status.get("orchestration_run_graph")),
        ("child orchestration", status.get("child_agent_orchestration")),
        ("worker orchestration", status.get("worker_node_orchestration")),
        ("worker presence", status.get("worker_node_presence")),
    )
    live_flag_violations = _unique_reasons(
        [
            *_execution_lock_blockers(*live_flag_payloads),
            *_execution_lock_reason_blockers(*live_flag_payloads),
        ]
    )
    blocked_reasons = live_flag_violations
    state = "live_flag_violation" if live_flag_violations else "separate_approval_required"
    summary = (
        "Hard boundary violation: live execution, dispatch, session-send, or worker flags are enabled in a "
        "display-only projection. Stop and review before any handoff."
        if live_flag_violations
        else (
            "This goal is code-side only. Live deploy, restart, runtime switch, record/state/config mutation, "
            "dispatch/session-send, worker activation, PR merge, secrets, and operational reconciliation all "
            "require separate approval."
        )
    )
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_hard_boundary_contract_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "separate_approval_required": True,
        "live_operations_goal": False,
        "live_operations_enabled": False,
        "execution_ready": False,
        "state": state,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "forbidden_actions": list(HARD_BOUNDARY_FORBIDDEN_ACTIONS),
        "forbidden_action_count": len(HARD_BOUNDARY_FORBIDDEN_ACTIONS),
        "separate_approval_actions": list(HARD_BOUNDARY_SEPARATE_APPROVAL_ACTIONS),
        "separate_approval_action_count": len(HARD_BOUNDARY_SEPARATE_APPROVAL_ACTIONS),
        "live_flag_violations": live_flag_violations,
        "live_flag_violation_count": len(live_flag_violations),
        "live_operational_reconciliation_state": "separate_approval_required",
        "plain_language_summary": summary,
    }


def hard_boundary_contract_payload(status: dict[str, Any]) -> dict[str, Any]:
    """Return the inert hard-boundary contract for a workspace status preview."""

    return _hard_boundary_contract_payload(status)


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

    hard_boundary = _mapping(status.get("hard_boundary_contract"))
    hard_boundary_reasons = _unique_reasons(
        [
            *_text_list(hard_boundary.get("blocked_reasons")),
            *_text_list(hard_boundary.get("live_flag_violations")),
        ]
    )
    if hard_boundary.get("blocked") is True or hard_boundary_reasons:
        extend_blockers(hard_boundary_reasons)
        add_action(
            action_id="review_hard_boundary_contract",
            label="Review hard-boundary contract",
            reason=_first_reason(
                hard_boundary_reasons,
                "Mission Control detected a live operation flag inside a display-only projection.",
            ),
            blocked_until="all live execution, dispatch, session-send, and worker flags are disabled",
            priority=1,
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

    report_review_queue = _mapping(status.get("report_review_queue"))
    report_queue_reasons = _text_list(report_review_queue.get("blocked_reasons"))
    if report_review_queue.get("queue_count", 0) or report_queue_reasons:
        extend_blockers(report_queue_reasons)
        add_action(
            action_id="review_report_review_queue",
            label="Review Jenny report queue",
            reason=_safe_text(
                report_review_queue.get("primary_review_reason"),
                max_chars=800,
            )
            or _first_reason(report_queue_reasons, "Reports are waiting for Jenny review or remediation."),
            blocked_until="Jenny reviews required reports and missing report links",
            priority=45,
        )

    result_ingestion = _mapping(status.get("result_ingestion_contract"))
    result_ingestion_reasons = _text_list(result_ingestion.get("blocked_reasons"))
    if result_ingestion.get("blocked") is True or result_ingestion_reasons:
        extend_blockers(result_ingestion_reasons)
        add_action(
            action_id="review_result_ingestion_contract",
            label="Review result ingestion contract",
            reason=_first_reason(result_ingestion_reasons, "One or more reports are not safe for Jenny to ingest."),
            blocked_until="reports are linked, redacted, and include safety confirmation",
            priority=46,
        )

    report_contract_compliance = _mapping(status.get("report_contract_compliance"))
    report_contract_reasons = _text_list(report_contract_compliance.get("blocked_reasons"))
    if report_contract_compliance.get("blocked") is True or report_contract_reasons:
        extend_blockers(report_contract_reasons)
        add_action(
            action_id="review_report_contract_compliance",
            label="Review report contract completeness",
            reason=_first_reason(report_contract_reasons, "One or more reports are missing required result fields."),
            blocked_until="reports include summary, result, evidence, risks/blockers, tests, next lane, and safety confirmation",
            priority=47,
        )

    report_completion = _mapping(status.get("report_completion_path"))
    report_completion_reasons = _text_list(report_completion.get("blocked_reasons"))
    if report_completion.get("blocked") is True or report_completion_reasons:
        extend_blockers(report_completion_reasons)
        add_action(
            action_id="review_report_completion_path",
            label="Review report completion path",
            reason=_first_reason(
                report_completion_reasons,
                "One or more terminal runs cannot be closed from reviewed report evidence.",
            ),
            blocked_until="terminal runs have linked, reviewed, complete, ingestion-safe reports",
            priority=48,
        )

    stop_control = _mapping(status.get("orchestration_stop_control"))
    stop_control_reasons = _text_list(stop_control.get("blocked_reasons"))
    if stop_control.get("blocked") is True or stop_control_reasons:
        extend_blockers(stop_control_reasons)
        add_action(
            action_id="review_stop_cancel_control",
            label="Review stop/cancel control",
            reason=_first_reason(stop_control_reasons, "A stopped or cancelled run needs manual review."),
            blocked_until="stopped/cancelled runs have a stop reason, linked report, and Jenny review",
            priority=48,
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

    worker_presence = _mapping(status.get("worker_node_presence"))
    worker_presence_reasons = _text_list(worker_presence.get("blocked_reasons"))
    if worker_presence_reasons:
        extend_blockers(worker_presence_reasons)
        add_action(
            action_id="review_worker_node_presence",
            label="Review laptop Codex worker-node presence",
            reason=_first_reason(worker_presence_reasons, "The laptop Codex worker-node is not proven online."),
            blocked_until="worker-node presence is explicitly online and recent",
            priority=55,
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

    run_graph = _mapping(status.get("orchestration_run_graph"))
    run_graph_reasons = _text_list(run_graph.get("blocked_reasons"))
    if run_graph_reasons:
        extend_blockers(run_graph_reasons)
        add_action(
            action_id="review_orchestration_run_graph_blockers",
            label="Review orchestration run graph blockers",
            reason=_first_reason(run_graph_reasons, "Parent, child, worker-node, or report lineage is incomplete."),
            blocked_until="run graph parent/report lineage is complete",
            priority=65,
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

    execution_mode = _mapping(status.get("execution_mode_classification"))
    execution_mode_reasons = _text_list(execution_mode.get("blocked_reasons"))
    if execution_mode.get("blocked") is True or execution_mode_reasons:
        extend_blockers(execution_mode_reasons)
        add_action(
            action_id="review_execution_mode_classification",
            label="Review execution mode classification",
            reason=_first_reason(execution_mode_reasons, "The requested mode is not eligible for preview-only orchestration."),
            blocked_until="mode is read-only, scoped PR, or worker-node preview with execution disabled",
            priority=75,
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

    execution_packet = _mapping(status.get("execution_packet_preview"))
    execution_packet_reasons = _text_list(execution_packet.get("blocked_reasons"))
    if execution_packet.get("eligible") is False and execution_packet_reasons:
        extend_blockers(execution_packet_reasons)
        add_action(
            action_id="review_execution_packet_preview",
            label="Review bounded work-packet preview",
            reason=_first_reason(execution_packet_reasons, "The bounded work packet is not preview-ready."),
            blocked_until="packet mode, scope, report contract, and disabled execution flags are safe",
            priority=95,
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
        **INERT_PROJECTION_FLAGS,
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


def _orchestration_run_graph_payload(
    *,
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
    reports: tuple[ReportRecord, ...],
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    blocked_reasons: list[str] = []
    run_ids = {record.run_id for record in runs if record.run_id}
    child_run_ids = {record.child_run_id for record in child_runs if record.child_run_id}
    worker_run_ids = {record.worker_run_id for record in worker_runs if record.worker_run_id}
    report_ids = {record.report_id for record in reports if record.report_id}
    reports_by_run_id, reports_by_id = _graph_report_maps(reports)

    for run in runs:
        nodes.append(
            _graph_node(
                node_id=run.run_id,
                node_type="run",
                status=run.status,
                label=run.title or run.objective or run.run_id,
                report_id=",".join(run.report_ids),
                report_review_status="",
            )
        )
        for report_id in run.report_ids:
            if report_id in report_ids:
                edges.append(_graph_edge(run.run_id, report_id, "declared_report"))
            else:
                blocked_reasons.append(f"run_id {run.run_id} links missing report_id {report_id}")
        if run.status in RUN_REPORT_REQUIRED_STATUSES and not run.report_ids and run.run_id not in reports_by_run_id:
            blocked_reasons.append(f"run_id {run.run_id} has no linked report")

    for child in child_runs:
        child_report = reports_by_id.get(child.report_id) if child.report_id else reports_by_run_id.get(child.child_run_id)
        nodes.append(
            _graph_node(
                node_id=child.child_run_id,
                node_type="child_run",
                status=child.status,
                label=child.objective or child.agent_identity or child.child_run_id,
                parent_run_id=child.parent_run_id,
                report_id=child_report.report_id if child_report else child.report_id,
                report_review_status=_linked_report_review_status(child_report) if child_report else "",
            )
        )
        if child.parent_run_id:
            if child.parent_run_id in run_ids:
                edges.append(_graph_edge(child.parent_run_id, child.child_run_id, "child_run"))
            else:
                blocked_reasons.append(f"child_run_id {child.child_run_id} references missing parent run_id {child.parent_run_id}")
        else:
            blocked_reasons.append(f"child_run_id {child.child_run_id} has no parent run_id")
        _append_report_graph_edge(
            record_id=child.child_run_id,
            record_label="child_run_id",
            report_id=child.report_id,
            status=child.status,
            report=child_report,
            edges=edges,
            blocked_reasons=blocked_reasons,
        )
        for dependency_id in child.depends_on_child_run_ids:
            if dependency_id in child_run_ids:
                edges.append(_graph_edge(dependency_id, child.child_run_id, "depends_on_child_run"))
            else:
                blocked_reasons.append(f"child_run_id {child.child_run_id} depends on missing child_run_id {dependency_id}")

    for worker in worker_runs:
        worker_report = reports_by_id.get(worker.report_id) if worker.report_id else reports_by_run_id.get(worker.worker_run_id)
        nodes.append(
            _graph_node(
                node_id=worker.worker_run_id,
                node_type="worker_node_run",
                status=worker.status,
                label=worker.objective or worker.worker_identity or worker.worker_run_id,
                parent_run_id=worker.parent_run_id,
                report_id=worker_report.report_id if worker_report else worker.report_id,
                report_review_status=_linked_report_review_status(worker_report) if worker_report else worker.report_review_status,
            )
        )
        if worker.parent_run_id:
            if worker.parent_run_id in run_ids:
                edges.append(_graph_edge(worker.parent_run_id, worker.worker_run_id, "worker_node_run"))
            else:
                blocked_reasons.append(f"worker_run_id {worker.worker_run_id} references missing parent run_id {worker.parent_run_id}")
        else:
            blocked_reasons.append(f"worker_run_id {worker.worker_run_id} has no parent run_id")
        _append_report_graph_edge(
            record_id=worker.worker_run_id,
            record_label="worker_run_id",
            report_id=worker.report_id,
            status=worker.status,
            report=worker_report,
            edges=edges,
            blocked_reasons=blocked_reasons,
        )

    known_run_like_ids = run_ids | child_run_ids | worker_run_ids
    for report in reports:
        nodes.append(
            _graph_node(
                node_id=report.report_id,
                node_type="report",
                status=report.status or "received",
                label=report.summary or report.report_id,
                parent_run_id=report.run_id,
                report_id=report.report_id,
                report_review_status=_linked_report_review_status(report),
            )
        )
        if report.run_id:
            if report.run_id in known_run_like_ids:
                edges.append(_graph_edge(report.run_id, report.report_id, "produced_report"))
            else:
                blocked_reasons.append(f"report_id {report.report_id} references unknown run_id {report.run_id}")

    unique_edges = _unique_graph_edges(edges)
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_orchestration_run_graph_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "node_count": len(nodes),
        "edge_count": len(unique_edges),
        "run_node_count": len(runs),
        "child_run_node_count": len(child_runs),
        "worker_node_run_count": len(worker_runs),
        "report_node_count": len(reports),
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "nodes": nodes,
        "edges": unique_edges,
    }


def _report_review_queue_payload(
    *,
    reports: tuple[ReportRecord, ...],
    raw_reports: tuple[ReportRecord, ...],
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, Any]:
    reports_by_id, reports_by_run_id = _report_lookup_maps(reports)
    duplicate_report_ids = set(_duplicate_record_ids(raw_reports, "report_id"))
    items: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for report in reports:
        review_status = _linked_report_review_status(report)
        duplicate = report.report_id in duplicate_report_ids
        linked = _report_review_linked_record(
            report=report,
            runs=runs,
            child_runs=child_runs,
            worker_runs=worker_runs,
        )
        link_mismatch_reason = _report_link_mismatch_reason(report, linked)
        if review_status != "needs_review" and not duplicate and not link_mismatch_reason:
            continue
        reasons = []
        if review_status == "needs_review":
            reasons.append(f"report_id {report.report_id} still needs Jenny review")
        if duplicate:
            reasons.append(f"report_id {report.report_id} has multiple append-only records")
        if link_mismatch_reason:
            reasons.append(link_mismatch_reason)
        reason = "; ".join(reasons)
        blocked_reasons.extend(reasons)
        items.append(
            _report_review_queue_item(
                item_id=f"report:{report.report_id}",
                item_type=(
                    "report_link_mismatch"
                    if link_mismatch_reason and review_status != "needs_review" and not duplicate
                    else "report_needs_review"
                ),
                priority=_report_review_priority(linked, duplicate=duplicate),
                report_id=report.report_id,
                run_id=report.run_id,
                linked_record_type=linked.get("linked_record_type", ""),
                linked_record_id=linked.get("linked_record_id", ""),
                status=report.status or "received",
                review_status=review_status,
                summary=report.summary,
                reason=reason,
                recommended_action="Jenny reviews the report evidence, blockers, changed files, and tests before any next instruction.",
                submitted_by=report.submitted_by,
                submitted_from=report.submitted_from,
                created_at=report.created_at,
                blockers=report.blockers,
                risks=report.risks,
                tests=report.tests,
                report_link_mismatch=bool(link_mismatch_reason),
            )
        )

    for run in runs:
        if run.status not in RUN_REPORT_REQUIRED_STATUSES:
            continue
        if not run.report_ids and run.run_id not in reports_by_run_id:
            reason = f"run_id {run.run_id} has no linked report"
            blocked_reasons.append(reason)
            items.append(
                _report_review_queue_item(
                    item_id=f"missing-report:run:{run.run_id}",
                    item_type="missing_required_report",
                    priority=25,
                    run_id=run.run_id,
                    linked_record_type="run",
                    linked_record_id=run.run_id,
                    status=run.status,
                    review_status="missing_report",
                    summary=run.title or run.objective or run.run_id,
                    reason=reason,
                    recommended_action="Find or request the terminal run report before marking the lane complete.",
                )
            )
        for report_id in run.report_ids:
            if report_id not in reports_by_id:
                reason = f"run_id {run.run_id} links missing report_id {report_id}"
                blocked_reasons.append(reason)
                items.append(
                    _report_review_queue_item(
                        item_id=f"missing-link:run:{run.run_id}:{report_id}",
                        item_type="missing_linked_report",
                        priority=30,
                        report_id=report_id,
                        run_id=run.run_id,
                        linked_record_type="run",
                        linked_record_id=run.run_id,
                        status=run.status,
                        review_status="missing_report",
                        summary=run.title or run.objective or run.run_id,
                        reason=reason,
                        recommended_action="Repair the append-only evidence chain in a later approved record lane.",
                    )
                )

    for child in child_runs:
        child_report = reports_by_id.get(child.report_id) if child.report_id else reports_by_run_id.get(child.child_run_id)
        if child.status in RUN_REPORT_REQUIRED_STATUSES and child_report is None:
            reason = f"child_run_id {child.child_run_id} has no linked report"
            blocked_reasons.append(reason)
            items.append(
                _report_review_queue_item(
                    item_id=f"missing-report:child:{child.child_run_id}",
                    item_type="missing_child_report",
                    priority=35,
                    report_id=child.report_id,
                    run_id=child.child_run_id,
                    linked_record_type="child_run",
                    linked_record_id=child.child_run_id,
                    status=child.status,
                    review_status="missing_report",
                    summary=child.objective or child.agent_identity or child.child_run_id,
                    reason=reason,
                    recommended_action="Request a child-agent report before trusting the delegation result.",
                )
            )

    for worker in worker_runs:
        worker_report = reports_by_id.get(worker.report_id) if worker.report_id else reports_by_run_id.get(worker.worker_run_id)
        if worker.status in RUN_REPORT_REQUIRED_STATUSES and worker_report is None:
            reason = f"worker_run_id {worker.worker_run_id} has no linked report"
            blocked_reasons.append(reason)
            items.append(
                _report_review_queue_item(
                    item_id=f"missing-report:worker:{worker.worker_run_id}",
                    item_type="missing_worker_report",
                    priority=20,
                    report_id=worker.report_id,
                    run_id=worker.worker_run_id,
                    linked_record_type="worker_node_run",
                    linked_record_id=worker.worker_run_id,
                    status=worker.status,
                    review_status="missing_report",
                    summary=worker.objective or worker.assigned_packet_summary or worker.worker_run_id,
                    reason=reason,
                    recommended_action="Have the laptop Codex worker provide its structured report before Jenny gives another instruction.",
                )
            )

    items.sort(key=lambda item: (int(item.get("priority", 999)), str(item.get("item_id", ""))))
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    primary_item = items[0] if items else {}
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_report_review_queue_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "queue_count": len(items),
        "needs_review_count": sum(1 for item in items if item.get("review_status") == "needs_review"),
        "missing_report_count": sum(1 for item in items if item.get("review_status") == "missing_report"),
        "link_mismatch_count": sum(1 for item in items if item.get("report_link_mismatch") is True),
        "duplicate_report_count": len(duplicate_report_ids),
        "blocked": bool(items or unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "primary_review_item": primary_item,
        "primary_review_item_id": _safe_text(primary_item.get("item_id")),
        "primary_review_label": _safe_text(primary_item.get("summary"), max_chars=800),
        "primary_review_reason": _safe_text(primary_item.get("reason"), max_chars=800),
        "items": items,
    }


def _result_ingestion_contract_payload(
    *,
    reports: tuple[ReportRecord, ...],
    raw_reports: tuple[ReportRecord, ...],
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, Any]:
    duplicate_report_ids = set(_duplicate_record_ids(raw_reports, "report_id"))
    items: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for report in reports:
        linked = _report_review_linked_record(
            report=report,
            runs=runs,
            child_runs=child_runs,
            worker_runs=worker_runs,
        )
        link_mismatch_reason = _report_link_mismatch_reason(report, linked)
        metadata = report.metadata if isinstance(report.metadata, dict) else {}
        forbidden_metadata_keys = _result_ingestion_forbidden_metadata_keys(metadata)
        safety_confirmation_present = _result_ingestion_safety_confirmation_present(metadata)
        redaction_status = _safe_text(report.redaction_status) or "missing"
        review_status = _linked_report_review_status(report)
        item_reasons: list[str] = []

        if report.report_id in duplicate_report_ids:
            item_reasons.append(f"report_id {report.report_id} has multiple append-only records")
        if not linked.get("linked_record_type") or not linked.get("linked_record_id"):
            item_reasons.append(f"report_id {report.report_id} is not linked to a run, child, or worker record")
        if link_mismatch_reason:
            item_reasons.append(link_mismatch_reason)
        if redaction_status not in RESULT_INGESTION_ACCEPTED_REDACTION_STATUSES:
            item_reasons.append(f"report_id {report.report_id} redaction_status {redaction_status} is not accepted")
        if forbidden_metadata_keys:
            item_reasons.append(
                f"report_id {report.report_id} metadata contains forbidden keys: {', '.join(forbidden_metadata_keys)}"
            )
        if not safety_confirmation_present:
            item_reasons.append(f"report_id {report.report_id} is missing safety confirmation for ingestion")

        blocked_reasons.extend(item_reasons)
        items.append(
            {
                "item_id": f"result-ingestion:{report.report_id}",
                "report_id": report.report_id,
                "run_id": report.run_id,
                "linked_record_type": linked.get("linked_record_type", ""),
                "linked_record_id": linked.get("linked_record_id", ""),
                "report_link_mismatch": bool(link_mismatch_reason),
                "status": report.status or "received",
                "review_status": review_status,
                "summary": report.summary,
                "submitted_by": report.submitted_by,
                "submitted_from": report.submitted_from,
                "redaction_status": redaction_status,
                "safety_confirmation_present": safety_confirmation_present,
                "forbidden_metadata_keys": forbidden_metadata_keys,
                "ingestion_ready": not item_reasons,
                "manual_review_required": True,
                "blocked_reasons": item_reasons,
                "recommended_action": (
                    "Jenny reviews the linked, redacted report and safety confirmation before relying on it."
                ),
            }
        )

    blocked_items = [item for item in items if item.get("ingestion_ready") is not True]
    primary_item = blocked_items[0] if blocked_items else {}
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_result_ingestion_contract_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "report_count": len(items),
        "raw_report_count": len(raw_reports),
        "ingestion_ready_count": len(items) - len(blocked_items),
        "blocked_report_count": len(blocked_items),
        "duplicate_report_count": len(duplicate_report_ids),
        "missing_link_count": sum(1 for item in items if not item.get("linked_record_type")),
        "link_mismatch_count": sum(1 for item in items if item.get("report_link_mismatch") is True),
        "unsafe_redaction_count": sum(
            1
            for item in items
            if item.get("redaction_status") not in RESULT_INGESTION_ACCEPTED_REDACTION_STATUSES
        ),
        "forbidden_metadata_count": sum(1 for item in items if item.get("forbidden_metadata_keys")),
        "missing_safety_confirmation_count": sum(
            1 for item in items if item.get("safety_confirmation_present") is not True
        ),
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "primary_item": primary_item,
        "primary_item_id": _safe_text(primary_item.get("item_id")),
        "primary_item_label": _safe_text(primary_item.get("summary"), max_chars=800),
        "items": items,
    }


def _result_ingestion_forbidden_metadata_keys(metadata: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for key in metadata:
        normalized = _normalized_metadata_key(key)
        if normalized in RESULT_INGESTION_FORBIDDEN_METADATA_KEYS or any(
            marker in normalized for marker in RESULT_INGESTION_FORBIDDEN_METADATA_KEY_MARKERS
        ):
            keys.append(normalized)
    return sorted(set(keys))


def _normalized_metadata_key(value: Any) -> str:
    return (
        _safe_text(value)
        .lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )


def _result_ingestion_safety_confirmation_present(metadata: dict[str, Any]) -> bool:
    safety_confirmation = (
        metadata.get("safety_confirmation")
        or metadata.get("safety")
        or metadata.get("safety_confirmed")
    )
    return bool(_safe_text(safety_confirmation))


def _report_contract_compliance_payload(
    *,
    reports: tuple[ReportRecord, ...],
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for report in reports:
        linked = _report_review_linked_record(
            report=report,
            runs=runs,
            child_runs=child_runs,
            worker_runs=worker_runs,
        )
        missing_fields = _report_contract_missing_fields(report)
        complete = not missing_fields
        if missing_fields:
            blocked_reasons.append(
                f"report_id {report.report_id} missing contract fields: {', '.join(missing_fields)}"
            )
        items.append(
            {
                "item_id": f"report-contract:{report.report_id}",
                "report_id": report.report_id,
                "run_id": report.run_id,
                "linked_record_type": linked.get("linked_record_type", ""),
                "linked_record_id": linked.get("linked_record_id", ""),
                "status": report.status or "received",
                "review_status": _linked_report_review_status(report),
                "summary": report.summary,
                "complete": complete,
                "missing_fields": missing_fields,
                "required_fields": [
                    "summary",
                    "result",
                    "risks/blockers",
                    "evidence",
                    "tests",
                    "next lane",
                    "safety confirmation",
                ],
                "changed_files": list(report.changed_files),
                "tests": list(report.tests),
                "risks": list(report.risks),
                "blockers": list(report.blockers),
                "evidence_refs": list(report.evidence_refs),
                "artifact_refs": list(report.artifact_refs),
                "submitted_by": report.submitted_by,
                "submitted_from": report.submitted_from,
                "manual_only": True,
                "recommended_action": (
                    "Jenny reviews the report contract fields before accepting the worker or child result."
                ),
            }
        )

    incomplete_items = [item for item in items if item.get("complete") is not True]
    primary_item = incomplete_items[0] if incomplete_items else {}
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_report_contract_compliance_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "report_count": len(items),
        "complete_report_count": len(items) - len(incomplete_items),
        "incomplete_report_count": len(incomplete_items),
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "primary_item": primary_item,
        "primary_item_id": _safe_text(primary_item.get("item_id")),
        "primary_item_label": _safe_text(primary_item.get("summary"), max_chars=800),
        "items": items,
    }


def _report_contract_missing_fields(report: ReportRecord) -> list[str]:
    missing: list[str] = []
    if not _safe_text(report.summary):
        missing.append("summary")
    if not _safe_text(report.result):
        missing.append("result")
    if not report.risks and not report.blockers:
        missing.append("risks/blockers")
    if not report.changed_files and not report.evidence_refs and not report.artifact_refs:
        missing.append("evidence")
    if not report.tests:
        missing.append("tests")
    if not _safe_text(report.next_recommended_lane):
        missing.append("next lane")
    metadata = report.metadata if isinstance(report.metadata, dict) else {}
    safety_confirmation = (
        metadata.get("safety_confirmation")
        or metadata.get("safety")
        or metadata.get("safety_confirmed")
    )
    if not _safe_text(safety_confirmation):
        missing.append("safety confirmation")
    return missing


def _report_completion_path_payload(
    *,
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
    reports: tuple[ReportRecord, ...],
    raw_reports: tuple[ReportRecord, ...],
) -> dict[str, Any]:
    reports_by_id, reports_by_run_id = _report_lookup_maps(reports)
    duplicate_report_ids = set(_duplicate_record_ids(raw_reports, "report_id"))
    items: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for run in runs:
        if run.status not in RUN_REPORT_REQUIRED_STATUSES:
            continue
        report = _record_stop_report(
            record_id=run.run_id,
            report_ids=run.report_ids,
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _report_completion_path_item(
            record_type="run",
            record_id=run.run_id,
            parent_run_id="",
            status=run.status,
            label=run.title or run.objective or run.run_id,
            report=report,
            duplicate_report_ids=duplicate_report_ids,
        )
        items.append(item)
        blocked_reasons.extend(_text_list(item.get("blocked_reasons")))

    for child in child_runs:
        if child.status not in RUN_REPORT_REQUIRED_STATUSES:
            continue
        report = _record_stop_report(
            record_id=child.child_run_id,
            report_ids=(child.report_id,),
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _report_completion_path_item(
            record_type="child_run",
            record_id=child.child_run_id,
            parent_run_id=child.parent_run_id,
            status=child.status,
            label=child.objective or child.agent_identity or child.child_run_id,
            report=report,
            duplicate_report_ids=duplicate_report_ids,
        )
        items.append(item)
        blocked_reasons.extend(_text_list(item.get("blocked_reasons")))

    for worker in worker_runs:
        if worker.status not in RUN_REPORT_REQUIRED_STATUSES:
            continue
        report = _record_stop_report(
            record_id=worker.worker_run_id,
            report_ids=(worker.report_id,),
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _report_completion_path_item(
            record_type="worker_node_run",
            record_id=worker.worker_run_id,
            parent_run_id=worker.parent_run_id,
            status=worker.status,
            label=worker.objective or worker.assigned_packet_summary or worker.worker_run_id,
            report=report,
            duplicate_report_ids=duplicate_report_ids,
        )
        items.append(item)
        blocked_reasons.extend(_text_list(item.get("blocked_reasons")))

    blocked_items = [item for item in items if item.get("completion_ready") is not True]
    primary_item = blocked_items[0] if blocked_items else {}
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_report_completion_path_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "terminal_item_count": len(items),
        "completion_ready_count": len(items) - len(blocked_items),
        "blocked_completion_count": len(blocked_items),
        "missing_report_count": sum(1 for item in items if item.get("report_link_status") != "linked_report_found"),
        "needs_review_count": sum(1 for item in items if item.get("report_review_status") == "needs_review"),
        "rejected_report_count": sum(
            1 for item in items if item.get("report_review_status") in {"rejected", "superseded"}
        ),
        "contract_incomplete_count": sum(1 for item in items if item.get("report_contract_complete") is not True),
        "ingestion_blocked_count": sum(
            1
            for item in items
            if item.get("report_link_status") == "linked_report_found"
            and item.get("result_ingestion_ready") is not True
        ),
        "duplicate_report_count": sum(1 for item in items if item.get("duplicate_report") is True),
        "link_mismatch_count": sum(1 for item in items if item.get("report_link_mismatch") is True),
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "primary_item": primary_item,
        "primary_item_id": _safe_text(primary_item.get("item_id")),
        "primary_item_label": _safe_text(primary_item.get("label"), max_chars=800),
        "items": items,
    }


def _report_completion_path_item(
    *,
    record_type: str,
    record_id: str,
    parent_run_id: str,
    status: str,
    label: str,
    report: ReportRecord | None,
    duplicate_report_ids: set[str],
) -> dict[str, Any]:
    report_id = report.report_id if report else ""
    review_status = _linked_report_review_status(report) if report else "missing_report"
    report_link_status = "linked_report_found" if report else "missing_linked_report"
    contract_missing_fields = _report_contract_missing_fields(report) if report else []
    metadata = report.metadata if report and isinstance(report.metadata, dict) else {}
    redaction_status = _safe_text(report.redaction_status) if report else ""
    forbidden_metadata_keys = _result_ingestion_forbidden_metadata_keys(metadata) if report else []
    safety_confirmation_present = _result_ingestion_safety_confirmation_present(metadata) if report else False
    duplicate_report = report_id in duplicate_report_ids if report_id else False
    link_mismatch_reason = (
        _report_link_mismatch_reason(
            report,
            {"linked_record_type": record_type, "linked_record_id": record_id},
        )
        if report
        else ""
    )
    blocked_reasons: list[str] = []

    if report is None:
        blocked_reasons.append(f"{record_type} {record_id} has no linked completion report")
    elif duplicate_report:
        blocked_reasons.append(f"report_id {report_id} has multiple append-only records")
    if link_mismatch_reason:
        blocked_reasons.append(link_mismatch_reason)

    if report is not None and review_status != "accepted":
        if review_status in {"rejected", "superseded"}:
            blocked_reasons.append(f"report_id {report_id} completion report is {review_status}")
        elif review_status == "reviewed":
            blocked_reasons.append(f"report_id {report_id} completion report is reviewed but not accepted")
        else:
            blocked_reasons.append(f"report_id {report_id} still needs Jenny review before completion")
    if contract_missing_fields:
        blocked_reasons.append(
            f"report_id {report_id} missing completion contract fields: {', '.join(contract_missing_fields)}"
        )
    if report is not None and redaction_status not in RESULT_INGESTION_ACCEPTED_REDACTION_STATUSES:
        blocked_reasons.append(f"report_id {report_id} redaction_status {redaction_status or 'missing'} is not accepted")
    if forbidden_metadata_keys:
        blocked_reasons.append(
            f"report_id {report_id} metadata contains forbidden keys: {', '.join(forbidden_metadata_keys)}"
        )
    if report is not None and not safety_confirmation_present:
        blocked_reasons.append(f"report_id {report_id} is missing safety confirmation for completion")

    result_ingestion_ready = (
        report is not None
        and not duplicate_report
        and not link_mismatch_reason
        and redaction_status in RESULT_INGESTION_ACCEPTED_REDACTION_STATUSES
        and not forbidden_metadata_keys
        and safety_confirmation_present
    )
    return {
        "item_id": f"report-completion:{record_type}:{record_id}",
        "record_type": record_type,
        "record_id": record_id,
        "parent_run_id": parent_run_id,
        "status": status,
        "label": _safe_text(label, max_chars=800),
        "report_id": report_id,
        "report_link_status": report_link_status,
        "report_review_status": review_status,
        "report_contract_complete": report is not None and not contract_missing_fields,
        "contract_missing_fields": contract_missing_fields,
        "result_ingestion_ready": result_ingestion_ready,
        "duplicate_report": duplicate_report,
        "report_link_mismatch": bool(link_mismatch_reason),
        "redaction_status": redaction_status,
        "safety_confirmation_present": safety_confirmation_present,
        "forbidden_metadata_keys": forbidden_metadata_keys,
        "completion_ready": not blocked_reasons,
        "manual_review_required": True,
        "blocked_reasons": blocked_reasons,
        "recommended_action": (
            "Jenny reviews the linked report, contract fields, ingestion safety, and final run status "
            "before treating this work as complete."
        ),
    }


def _report_review_linked_record(
    *,
    report: ReportRecord,
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
) -> dict[str, str]:
    if report.run_id:
        for worker in worker_runs:
            if worker.worker_run_id == report.run_id or worker.report_id == report.report_id:
                return {"linked_record_type": "worker_node_run", "linked_record_id": worker.worker_run_id}
        for child in child_runs:
            if child.child_run_id == report.run_id or child.report_id == report.report_id:
                return {"linked_record_type": "child_run", "linked_record_id": child.child_run_id}
        for run in runs:
            if run.run_id == report.run_id or report.report_id in run.report_ids:
                return {"linked_record_type": "run", "linked_record_id": run.run_id}
    for worker in worker_runs:
        if worker.report_id == report.report_id:
            return {"linked_record_type": "worker_node_run", "linked_record_id": worker.worker_run_id}
    for child in child_runs:
        if child.report_id == report.report_id:
            return {"linked_record_type": "child_run", "linked_record_id": child.child_run_id}
    for run in runs:
        if report.report_id in run.report_ids:
            return {"linked_record_type": "run", "linked_record_id": run.run_id}
    return {"linked_record_type": "", "linked_record_id": ""}


def _report_link_mismatch_reason(report: ReportRecord | None, linked: dict[str, str]) -> str:
    if report is None:
        return ""
    report_run_id = _safe_text(report.run_id)
    linked_record_id = _safe_text(linked.get("linked_record_id"))
    if not report_run_id or not linked_record_id or report_run_id == linked_record_id:
        return ""
    linked_record_type = _safe_text(linked.get("linked_record_type")) or "record"
    return (
        f"report_id {report.report_id} run_id {report_run_id} "
        f"does not match linked {linked_record_type} {linked_record_id}"
    )


def _report_review_priority(linked: dict[str, str], *, duplicate: bool) -> int:
    if linked.get("linked_record_type") == "worker_node_run":
        return 10
    if linked.get("linked_record_type") == "child_run":
        return 15
    if duplicate:
        return 20
    return 40


def _report_review_queue_item(
    *,
    item_id: str,
    item_type: str,
    priority: int,
    report_id: str = "",
    run_id: str = "",
    linked_record_type: str = "",
    linked_record_id: str = "",
    status: str = "",
    review_status: str = "",
    summary: str = "",
    reason: str = "",
    recommended_action: str = "",
    submitted_by: str = "",
    submitted_from: str = "",
    created_at: str = "",
    blockers: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    tests: tuple[str, ...] = (),
    report_link_mismatch: bool = False,
) -> dict[str, Any]:
    return {
        "item_id": _safe_text(item_id),
        "item_type": _safe_text(item_type),
        "priority": priority,
        "report_id": _safe_text(report_id),
        "run_id": _safe_text(run_id),
        "linked_record_type": _safe_text(linked_record_type),
        "linked_record_id": _safe_text(linked_record_id),
        "status": _safe_text(status),
        "review_status": _safe_text(review_status),
        "summary": _safe_text(summary, max_chars=800),
        "reason": _safe_text(reason, max_chars=800),
        "recommended_action": _safe_text(recommended_action, max_chars=800),
        "submitted_by": _safe_text(submitted_by),
        "submitted_from": _safe_text(submitted_from),
        "created_at": _safe_text(created_at),
        "blockers": [_safe_text(item) for item in blockers if _safe_text(item)],
        "risks": [_safe_text(item) for item in risks if _safe_text(item)],
        "tests": [_safe_text(item) for item in tests if _safe_text(item)],
        "report_link_mismatch": report_link_mismatch,
        "manual_only": True,
    }


def _orchestration_stop_control_payload(
    *,
    runs: tuple[RunRecord, ...],
    child_runs: tuple[ChildRunRecord, ...],
    worker_runs: tuple[WorkerNodeRunRecord, ...],
    reports: tuple[ReportRecord, ...],
) -> dict[str, Any]:
    reports_by_id, reports_by_run_id = _report_lookup_maps(reports)
    items: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    for run in runs:
        status = _safe_text(run.status) or "requested"
        if status not in RUN_STOP_CANCEL_STATUSES:
            continue
        report = _record_stop_report(
            record_id=run.run_id,
            report_ids=run.report_ids,
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _stop_control_item(
            record_type="run",
            record_id=run.run_id,
            parent_run_id="",
            status=status,
            stop_reason=run.stop_reason,
            stopped_at=run.stopped_at,
            report=report,
        )
        items.append(item)
        blocked_reasons.extend(_stop_control_blockers(item))

    for child in child_runs:
        status = _safe_text(child.status) or "requested"
        if status not in ORCHESTRATION_STOP_CANCEL_STATUSES:
            continue
        report = _record_stop_report(
            record_id=child.child_run_id,
            report_ids=(child.report_id,),
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _stop_control_item(
            record_type="child_run",
            record_id=child.child_run_id,
            parent_run_id=child.parent_run_id,
            status=status,
            stop_reason=child.stop_reason or child.failure_reason,
            stopped_at=child.stopped_at,
            report=report,
        )
        items.append(item)
        blocked_reasons.extend(_stop_control_blockers(item))

    for worker in worker_runs:
        status = _safe_text(worker.status) or "requested"
        if status not in ORCHESTRATION_STOP_CANCEL_STATUSES:
            continue
        report = _record_stop_report(
            record_id=worker.worker_run_id,
            report_ids=(worker.report_id,),
            reports_by_id=reports_by_id,
            reports_by_run_id=reports_by_run_id,
        )
        item = _stop_control_item(
            record_type="worker_node_run",
            record_id=worker.worker_run_id,
            parent_run_id=worker.parent_run_id,
            status=status,
            stop_reason=worker.stop_reason or worker.failure_reason,
            stopped_at=worker.stopped_at,
            report=report,
        )
        items.append(item)
        blocked_reasons.extend(_stop_control_blockers(item))

    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    primary_item = items[0] if items else {}
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_orchestration_stop_control_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_review_only": True,
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "stop_cancel_count": len(items),
        "active_stop_count": sum(1 for item in items if item.get("status") == "stopping"),
        "terminal_stop_count": sum(1 for item in items if item.get("status") in {"stopped", "cancelled"}),
        "needs_report_count": sum(1 for item in items if item.get("report_link_status") != "linked_report_found"),
        "link_mismatch_count": sum(1 for item in items if item.get("report_link_mismatch") is True),
        "needs_review_count": sum(1 for item in items if item.get("report_review_status") == "needs_review"),
        "primary_item": primary_item,
        "primary_item_id": _safe_text(primary_item.get("item_id")),
        "primary_item_label": _safe_text(primary_item.get("label")),
        "items": items,
    }


def _record_stop_report(
    *,
    record_id: str,
    report_ids: tuple[str, ...],
    reports_by_id: dict[str, ReportRecord],
    reports_by_run_id: dict[str, ReportRecord],
) -> ReportRecord | None:
    for report_id in report_ids:
        report = reports_by_id.get(report_id)
        if report is not None:
            return report
    return reports_by_run_id.get(record_id)


def _stop_control_item(
    *,
    record_type: str,
    record_id: str,
    parent_run_id: str,
    status: str,
    stop_reason: str,
    stopped_at: str,
    report: ReportRecord | None,
) -> dict[str, Any]:
    report_id = report.report_id if report else ""
    report_review_status = _linked_report_review_status(report) if report else "missing"
    link_mismatch_reason = _report_link_mismatch_reason(
        report,
        {"linked_record_type": record_type, "linked_record_id": record_id},
    )
    report_link_status = (
        "linked_report_run_id_mismatch"
        if link_mismatch_reason
        else "linked_report_found"
        if report
        else "missing_linked_report"
    )
    label = f"{record_type} {record_id} {status}"
    return {
        "item_id": f"{record_type}:{record_id}",
        "record_type": record_type,
        "record_id": record_id,
        "parent_run_id": parent_run_id,
        "status": status,
        "label": label,
        "stop_reason": _safe_text(stop_reason, max_chars=800),
        "stopped_at": _safe_text(stopped_at),
        "report_id": report_id,
        "report_link_status": report_link_status,
        "report_link_mismatch": bool(link_mismatch_reason),
        "report_link_mismatch_reason": link_mismatch_reason,
        "report_review_status": report_review_status,
        "manual_review_required": True,
        "recommended_action": (
            "Jenny reviews stop reason, final report, blockers, and safety confirmation "
            "before assigning follow-up work."
        ),
    }


def _stop_control_blockers(item: dict[str, Any]) -> list[str]:
    record_type = _safe_text(item.get("record_type"))
    record_id = _safe_text(item.get("record_id"))
    status = _safe_text(item.get("status"))
    report_id = _safe_text(item.get("report_id"))
    blockers: list[str] = []
    if status == "stopping":
        blockers.append(f"{record_type} {record_id} is stopping and needs manual stop confirmation")
    if status in {"stopped", "cancelled"} and not _safe_text(item.get("stop_reason")):
        blockers.append(f"{record_type} {record_id} has no stop_reason")
    if item.get("report_link_mismatch") is True:
        blockers.append(
            _safe_text(item.get("report_link_mismatch_reason"))
            or f"report_id {report_id} run_id does not match {record_type} {record_id}"
        )
    elif item.get("report_link_status") != "linked_report_found":
        blockers.append(f"{record_type} {record_id} has no linked stop/cancel report")
    if report_id and item.get("report_review_status") == "needs_review":
        blockers.append(f"report_id {report_id} still needs Jenny review")
    return blockers


def _worker_node_presence_payload(
    *,
    worker_runs: tuple[WorkerNodeRunRecord, ...],
    active_worker_runs: tuple[WorkerNodeRunRecord, ...],
    now: str = "",
) -> dict[str, Any]:
    latest_worker = active_worker_runs[-1] if active_worker_runs else worker_runs[-1] if worker_runs else None
    blocked_reasons: list[str] = []
    presence_state = "missing"
    last_seen_age_seconds: int | None = None
    worker_payload: dict[str, Any] = latest_worker.to_dict() if latest_worker else {}

    if latest_worker is None:
        blocked_reasons.append("no laptop Codex worker-node run is recorded")
    else:
        presence_status = _safe_text(getattr(latest_worker, "presence_status", "")).lower()
        last_seen_at = _safe_text(getattr(latest_worker, "last_seen_at", ""))
        parsed_last_seen = _parse_datetime(last_seen_at)
        parsed_now = _parse_datetime(now) if now else datetime.now(timezone.utc)
        if not presence_status:
            presence_state = "unknown"
            blocked_reasons.append("worker-node presence_status is not recorded")
        elif presence_status not in {"online", "offline"}:
            presence_state = "unknown"
            blocked_reasons.append(f"worker-node presence_status {presence_status} is not recognized")
        elif presence_status == "offline":
            presence_state = "offline"
            blocked_reasons.append("worker-node presence_status is offline")
        else:
            if parsed_last_seen is None:
                presence_state = "unknown"
                blocked_reasons.append("worker-node last_seen_at is required to prove online presence")
            elif parsed_now is None:
                presence_state = "unknown"
                blocked_reasons.append("current time is unavailable for worker-node presence freshness")
            else:
                last_seen_age_seconds = max(0, int((parsed_now - parsed_last_seen).total_seconds()))
                if last_seen_age_seconds > WORKER_NODE_PRESENCE_STALE_SECONDS:
                    presence_state = "stale"
                    blocked_reasons.append("worker-node last_seen_at is stale")
                else:
                    presence_state = "online"

    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_worker_node_presence_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "presence_state": presence_state,
        "online": presence_state == "online",
        "blocked": bool(blocked_reasons),
        "blocked_reasons": _unique_reasons(blocked_reasons),
        "worker_run_id": _safe_text(worker_payload.get("worker_run_id")),
        "parent_run_id": _safe_text(worker_payload.get("parent_run_id")),
        "worker_identity": _safe_text(worker_payload.get("worker_identity")) or "codex",
        "worker_host_label": _safe_text(worker_payload.get("worker_host_label")) or "laptop-codex",
        "worker_kind": _safe_text(worker_payload.get("worker_kind")) or "laptop_codex",
        "presence_status": _safe_text(worker_payload.get("presence_status")),
        "last_seen_at": _safe_text(worker_payload.get("last_seen_at")),
        "last_seen_age_seconds": last_seen_age_seconds,
        "stale_after_seconds": WORKER_NODE_PRESENCE_STALE_SECONDS,
        "worker_version": _safe_text(worker_payload.get("worker_version")),
        "capability_summary": _safe_text(worker_payload.get("capability_summary"), max_chars=800),
        "active_worker_node_run_count": len(active_worker_runs),
        "recorded_worker_node_run_count": len(worker_runs),
    }


def _append_report_graph_edge(
    *,
    record_id: str,
    record_label: str,
    report_id: str,
    status: str,
    report: ReportRecord | None,
    edges: list[dict[str, str]],
    blocked_reasons: list[str],
) -> None:
    if report:
        edges.append(_graph_edge(record_id, report.report_id, "linked_report"))
    elif report_id:
        blocked_reasons.append(f"{record_label} {record_id} links missing report_id {report_id}")
    elif status in RUN_REPORT_REQUIRED_STATUSES:
        blocked_reasons.append(f"{record_label} {record_id} has no linked report")


def _graph_node(
    *,
    node_id: str,
    node_type: str,
    status: str,
    label: str,
    parent_run_id: str = "",
    report_id: str = "",
    report_review_status: str = "",
) -> dict[str, str]:
    return {
        "node_id": _safe_text(node_id),
        "node_type": _safe_text(node_type),
        "status": _safe_text(status),
        "label": _safe_text(label, max_chars=800),
        "parent_run_id": _safe_text(parent_run_id),
        "report_id": _safe_text(report_id),
        "report_review_status": _safe_text(report_review_status),
    }


def _graph_edge(source_id: str, target_id: str, edge_type: str) -> dict[str, str]:
    return {
        "source_id": _safe_text(source_id),
        "target_id": _safe_text(target_id),
        "edge_type": _safe_text(edge_type),
    }


def _unique_graph_edges(edges: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        key = (
            str(edge.get("source_id") or ""),
            str(edge.get("target_id") or ""),
            str(edge.get("edge_type") or ""),
        )
        if key[0] and key[1] and key not in seen:
            seen.add(key)
            output.append(edge)
    return output


def _graph_report_maps(
    reports: tuple[ReportRecord, ...],
) -> tuple[dict[str, ReportRecord], dict[str, ReportRecord]]:
    reports_by_run_id: dict[str, ReportRecord] = {}
    reports_by_id: dict[str, ReportRecord] = {}
    for report in reports:
        if report.run_id:
            reports_by_run_id[report.run_id] = report
        if report.report_id:
            reports_by_id[report.report_id] = report
    return reports_by_run_id, reports_by_id


def _orchestration_readiness_payload(status: dict[str, Any]) -> dict[str, Any]:
    read_only = _eligibility_readiness(
        _mapping(status.get("read_only_autonomy_eligibility")),
        default_blocked_reason="read-only preview eligibility is not satisfied",
        disabled_flag_names=(
            "would_execute",
            "execution_enabled",
            "dispatch_enabled",
            "session_send_enabled",
            "worker_dispatch_enabled",
        ),
    )
    scoped_pr = _eligibility_readiness(
        _mapping(status.get("scoped_pr_lane_eligibility")),
        default_blocked_reason="scoped PR preview eligibility is not satisfied",
        disabled_flag_names=(
            "would_execute",
            "would_commit",
            "would_create_pr",
            "execution_enabled",
            "dispatch_enabled",
            "session_send_enabled",
            "worker_dispatch_enabled",
            "merge_enabled",
            "deploy_enabled",
            "runtime_switch_enabled",
        ),
    )
    worker_node = _worker_node_readiness(
        _mapping(status.get("worker_node_orchestration")),
        _mapping(status.get("worker_node_presence")),
    )
    hard_boundary = _mapping(status.get("hard_boundary_contract"))
    hard_boundary_reasons = _unique_reasons(
        [
            *_text_list(hard_boundary.get("blocked_reasons")),
            *_text_list(hard_boundary.get("live_flag_violations")),
        ]
    )
    read_only = _readiness_with_extra_blockers(read_only, hard_boundary_reasons)
    scoped_pr = _readiness_with_extra_blockers(scoped_pr, hard_boundary_reasons)
    worker_node = _readiness_with_extra_blockers(worker_node, hard_boundary_reasons)
    states = {
        "supervised_read_only_autonomy": read_only["state"],
        "scoped_pr_creation": scoped_pr["state"],
        "laptop_codex_worker_node": worker_node["state"],
    }
    summary_lines = [
        _readiness_line("Supervised read-only autonomy", read_only),
        _readiness_line("Scoped PR creation", scoped_pr),
        _readiness_line("Laptop Codex worker-node", worker_node),
    ]
    next_safe_actions = _mapping(status.get("next_safe_actions"))
    next_safe_action_label = _safe_text(next_safe_actions.get("primary_action_label"))
    if next_safe_action_label:
        summary_lines.append(f"Next safe action: {next_safe_action_label}.")
    blocked_reasons = _unique_reasons(
        [
            *_text_list(read_only.get("blocked_reasons")),
            *_text_list(scoped_pr.get("blocked_reasons")),
            *_text_list(worker_node.get("blocked_reasons")),
        ]
    )
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_orchestration_readiness_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "states": states,
        "supervised_read_only_autonomy": read_only,
        "scoped_pr_creation": scoped_pr,
        "laptop_codex_worker_node": worker_node,
        "summary_lines": summary_lines,
        "plain_language_summary": " ".join(summary_lines),
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "next_safe_action_id": _safe_text(next_safe_actions.get("primary_action_id")),
        "next_safe_action_label": next_safe_action_label,
        "execution_ready": False,
    }


def _readiness_with_extra_blockers(payload: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
    if not blockers:
        return payload
    blocked_reasons = _unique_reasons([*_text_list(payload.get("blocked_reasons")), *blockers])
    return {
        **payload,
        "state": "blocked",
        "preview_ready": False,
        "execution_ready": False,
        "blocked_reasons": blocked_reasons,
    }


def _eligibility_readiness(
    payload: dict[str, Any],
    *,
    default_blocked_reason: str,
    disabled_flag_names: tuple[str, ...],
) -> dict[str, Any]:
    blocked_reasons = _text_list(payload.get("blocked_reasons"))
    enabled_flags = [flag for flag in disabled_flag_names if _flag_enabled(payload.get(flag))]
    blocked_reasons.extend(f"{flag} must remain disabled" for flag in enabled_flags)
    if payload.get("eligible") is not True and not blocked_reasons:
        blocked_reasons.append(default_blocked_reason)
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    state = "preview_ready" if payload.get("eligible") is True and not unique_blocked_reasons else "blocked"
    return {
        **INERT_PROJECTION_FLAGS,
        "state": state,
        "eligible": payload.get("eligible") is True,
        "preview_ready": state == "preview_ready",
        "execution_ready": False,
        "blocked_reasons": unique_blocked_reasons,
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _worker_node_readiness(
    worker_projection: dict[str, Any],
    worker_presence: dict[str, Any],
) -> dict[str, Any]:
    blocked_reasons = _text_list(worker_projection.get("blocked_reasons"))
    blocked_reasons.extend(_text_list(worker_presence.get("blocked_reasons")))
    latest_by_id = _mapping(worker_projection.get("latest_by_id"))
    active_runs = worker_projection.get("active_runs")
    active_run_payloads = active_runs if isinstance(active_runs, list) else []
    enabled_flags = _enabled_live_flag_names(
        worker_projection,
        worker_presence,
        *latest_by_id.values(),
        *active_run_payloads,
    )
    blocked_reasons.extend(f"{flag} must remain disabled" for flag in enabled_flags)
    active_count = worker_projection.get("active_count")
    has_worker_record = bool(latest_by_id) or (isinstance(active_count, int) and active_count > 0)
    if not has_worker_record:
        blocked_reasons.append("no laptop Codex worker-node run is recorded")
    if has_worker_record and worker_presence.get("online") is not True:
        blocked_reasons.append("worker-node presence is not confirmed online")
    state = (
        "preview_ready"
        if has_worker_record
        and worker_presence.get("online") is True
        and not blocked_reasons
        and not enabled_flags
        else "blocked"
    )
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    return {
        **INERT_PROJECTION_FLAGS,
        "state": state,
        "recorded": has_worker_record,
        "presence_state": _safe_text(worker_presence.get("presence_state")) or "unknown",
        "online": worker_presence.get("online") is True,
        "active_count": active_count if isinstance(active_count, int) else 0,
        "preview_ready": state == "preview_ready",
        "execution_ready": False,
        "blocked_reasons": unique_blocked_reasons,
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _readiness_line(label: str, payload: dict[str, Any]) -> str:
    if payload.get("state") == "preview_ready":
        return f"{label} is preview-ready; execution remains disabled."
    reason = _first_reason(_text_list(payload.get("blocked_reasons")), "required evidence is missing")
    return f"{label} is blocked: {reason}."


def _worker_node_instruction_preview(status: dict[str, Any]) -> dict[str, Any]:
    worker_projection = _mapping(status.get("worker_node_orchestration"))
    worker_presence = _mapping(status.get("worker_node_presence"))
    worker_record = _latest_projection_payload(worker_projection)
    blocked_reasons: list[str] = []
    if not worker_record:
        blocked_reasons.append("no laptop Codex worker-node run is recorded")
    objective = _safe_text(worker_record.get("objective"), max_chars=800)
    if worker_record and not objective:
        blocked_reasons.append("worker-node objective is required")
    worker_run_id = _safe_text(worker_record.get("worker_run_id"))
    blocked_reasons.extend(_text_list(worker_projection.get("blocked_reasons")))
    blocked_reasons.extend(_text_list(worker_record.get("blocked_reasons")))
    blocked_reasons.extend(_text_list(worker_presence.get("blocked_reasons")))
    failure_reason = _safe_text(worker_record.get("failure_reason"))
    if failure_reason:
        blocked_reasons.append(failure_reason)
    report_id = _safe_text(worker_record.get("report_id"))
    report_review_status = _safe_text(
        worker_record.get("linked_report_review_status")
        or worker_record.get("report_review_status")
    )
    report_link_status = _safe_text(worker_record.get("report_link_status"))
    report_link_mismatch_reason = _safe_text(worker_record.get("report_link_mismatch_reason"))
    if report_id and report_link_status == "linked_report_missing":
        blocked_reasons.append(f"worker_run_id {worker_run_id} links missing report_id {report_id}")
    if report_id and report_link_status == "linked_report_run_id_mismatch":
        blocked_reasons.append(
            report_link_mismatch_reason
            or f"report_id {report_id} run_id does not match worker_run_id {worker_run_id}"
        )
    if report_id and report_review_status == "needs_review":
        blocked_reasons.append(f"report_id {report_id} still needs Jenny review")
    blocked_reasons.extend(
        f"{flag} must remain disabled"
        for flag in _enabled_live_flag_names(worker_projection, worker_record, worker_presence)
    )

    allowed_actions = _text_list(worker_record.get("allowed_actions"))
    recorded_forbidden_actions = _text_list(worker_record.get("forbidden_actions"))
    effective_forbidden_actions = _unique_reasons(
        [
            *recorded_forbidden_actions,
            "no live deploy",
            "no restart",
            "no runtime switch",
            "no live record/state/config mutation",
            "no secrets inspection or output",
            "no worker dispatch activation",
            "no bypassing Codex safety checks",
        ]
    )
    worker_identity = _safe_text(worker_record.get("worker_identity")) or "codex"
    worker_host_label = _safe_text(worker_record.get("worker_host_label")) or "laptop-codex"
    worker_safety_hardness = [
        "Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.",
        "A Jenny packet is not permission to bypass Codex safety checks.",
    ]
    report_contract = (
        "Report changed files, tests/checks, result, blockers, safety confirmation, "
        "and the next suggested chunk."
    )
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    ready_for_handoff = bool(worker_record) and not unique_blocked_reasons
    instruction_lines = [
        f"Worker: {worker_identity} on {worker_host_label}.",
        f"Objective: {objective or 'No objective recorded.'}",
        f"Allowed actions: {_joined_or_none(allowed_actions)}.",
        f"Forbidden actions: {_joined_or_none(effective_forbidden_actions)}.",
        f"Worker safety hardness: {' '.join(worker_safety_hardness)}",
        f"Report contract: {report_contract}",
        (
            "Handoff readiness: ready for manual review copy."
            if ready_for_handoff
            else "Handoff readiness: blocked until worker-node blockers are cleared."
        ),
        "Manual handoff only; execution and worker dispatch remain disabled.",
    ]
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_worker_node_instruction_preview_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_handoff_only": True,
        "available": bool(worker_record),
        "ready_for_handoff": ready_for_handoff,
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "worker_run_id": worker_run_id,
        "parent_run_id": _safe_text(worker_record.get("parent_run_id")),
        "worker_identity": worker_identity,
        "worker_host_label": worker_host_label,
        "presence_state": _safe_text(worker_presence.get("presence_state")) or "unknown",
        "online": worker_presence.get("online") is True,
        "last_seen_at": _safe_text(worker_presence.get("last_seen_at")),
        "last_seen_age_seconds": worker_presence.get("last_seen_age_seconds"),
        "worker_version": _safe_text(worker_presence.get("worker_version")),
        "capability_summary": _safe_text(worker_presence.get("capability_summary"), max_chars=800),
        "objective": objective,
        "assigned_packet_id": _safe_text(worker_record.get("assigned_packet_id")),
        "assigned_packet_summary": _safe_text(worker_record.get("assigned_packet_summary"), max_chars=800),
        "allowed_actions": allowed_actions,
        "forbidden_actions": effective_forbidden_actions,
        "worker_safety_hardness": worker_safety_hardness,
        "report_contract": report_contract,
        "report_id": report_id,
        "report_link_status": report_link_status,
        "report_link_mismatch": worker_record.get("report_link_mismatch") is True,
        "report_link_mismatch_reason": report_link_mismatch_reason,
        "report_review_status": report_review_status,
        "instruction_lines": instruction_lines,
        "manual_handoff_prompt": "\n".join(instruction_lines),
    }


def _child_agent_instruction_preview(status: dict[str, Any]) -> dict[str, Any]:
    child_projection = _mapping(status.get("child_agent_orchestration"))
    child_record = _latest_projection_payload(child_projection)
    blocked_reasons: list[str] = []
    if not child_record:
        blocked_reasons.append("no child-agent run is recorded")
    objective = _safe_text(child_record.get("objective"), max_chars=800)
    if child_record and not objective:
        blocked_reasons.append("child-agent objective is required")
    blocked_reasons.extend(_text_list(child_projection.get("blocked_reasons")))
    blocked_reasons.extend(_text_list(child_record.get("blocked_reasons")))
    failure_reason = _safe_text(child_record.get("failure_reason"))
    if failure_reason:
        blocked_reasons.append(failure_reason)
    report_review_status = _safe_text(
        child_record.get("linked_report_review_status")
        or child_record.get("report_review_status")
    )
    report_id = _safe_text(child_record.get("report_id"))
    report_link_status = _safe_text(child_record.get("report_link_status"))
    report_link_mismatch_reason = _safe_text(child_record.get("report_link_mismatch_reason"))
    child_run_id = _safe_text(child_record.get("child_run_id"))
    if report_id and report_link_status == "linked_report_missing":
        blocked_reasons.append(f"child_run_id {child_run_id} links missing report_id {report_id}")
    if report_id and report_link_status == "linked_report_run_id_mismatch":
        blocked_reasons.append(
            report_link_mismatch_reason
            or f"report_id {report_id} run_id does not match child_run_id {child_run_id}"
        )
    if report_id and report_review_status == "needs_review":
        blocked_reasons.append(f"report_id {report_id} still needs review")
    blocked_reasons.extend(
        f"{flag} must remain disabled"
        for flag in _enabled_live_flag_names(child_projection, child_record)
    )

    allowed_actions = _text_list(child_record.get("allowed_actions"))
    recorded_forbidden_actions = _text_list(child_record.get("forbidden_actions"))
    effective_forbidden_actions = _unique_reasons(
        [
            *recorded_forbidden_actions,
            "no live delegation activation",
            "no live dispatch activation",
            "no live session sending",
            "no worker dispatch activation",
            "no live record/state/config mutation",
            "no secrets inspection or output",
        ]
    )
    agent_identity = _safe_text(child_record.get("agent_identity")) or "child-agent"
    report_contract = (
        "Report evidence, result, blockers, safety confirmation, and the next suggested review step."
    )
    unique_blocked_reasons = _unique_reasons(blocked_reasons)
    ready_for_handoff = bool(child_record) and not unique_blocked_reasons
    instruction_lines = [
        f"Child agent: {agent_identity}.",
        f"Objective: {objective or 'No objective recorded.'}",
        f"Allowed actions: {_joined_or_none(allowed_actions)}.",
        f"Forbidden actions: {_joined_or_none(effective_forbidden_actions)}.",
        f"Report contract: {report_contract}",
        (
            "Handoff readiness: ready for manual review copy."
            if ready_for_handoff
            else "Handoff readiness: blocked until child-agent blockers are cleared."
        ),
        "Manual delegation preview only; execution and dispatch remain disabled.",
    ]
    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_child_agent_instruction_preview_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_handoff_only": True,
        "available": bool(child_record),
        "ready_for_handoff": ready_for_handoff,
        "blocked": bool(unique_blocked_reasons),
        "blocked_reasons": unique_blocked_reasons,
        "child_run_id": _safe_text(child_record.get("child_run_id")),
        "parent_run_id": _safe_text(child_record.get("parent_run_id")),
        "agent_identity": agent_identity,
        "objective": objective,
        "allowed_actions": allowed_actions,
        "forbidden_actions": effective_forbidden_actions,
        "report_contract": report_contract,
        "report_id": report_id,
        "report_link_status": report_link_status,
        "report_link_mismatch": child_record.get("report_link_mismatch") is True,
        "report_link_mismatch_reason": report_link_mismatch_reason,
        "report_review_status": report_review_status,
        "instruction_lines": instruction_lines,
        "manual_handoff_prompt": "\n".join(instruction_lines),
    }


def _report_link_mismatch_keys(*sections: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for section in sections:
        items = section.get("items")
        for item in items if isinstance(items, list) else ():
            item_payload = _mapping(item)
            if item_payload.get("report_link_mismatch") is not True:
                continue
            key = _safe_text(
                item_payload.get("report_id")
                or item_payload.get("item_id")
                or item_payload.get("record_id")
                or item_payload.get("linked_record_id")
            )
            if key:
                keys.append(key)
        primary_item = _mapping(section.get("primary_item") or section.get("primary_review_item"))
        if primary_item.get("report_link_mismatch") is True:
            key = _safe_text(
                primary_item.get("report_id")
                or primary_item.get("item_id")
                or primary_item.get("record_id")
                or primary_item.get("linked_record_id")
            )
            if key:
                keys.append(key)
    return _unique_reasons(keys)


def _operator_decision_packet_payload(status: dict[str, Any]) -> dict[str, Any]:
    runtime_provenance = _mapping(status.get("runtime_provenance"))
    next_safe_actions = _mapping(status.get("next_safe_actions"))
    readiness = _mapping(status.get("orchestration_readiness"))
    report_lifecycle = _mapping(status.get("report_lifecycle"))
    report_queue = _mapping(status.get("report_review_queue"))
    result_ingestion = _mapping(status.get("result_ingestion_contract"))
    report_contract = _mapping(status.get("report_contract_compliance"))
    report_completion = _mapping(status.get("report_completion_path"))
    stop_control = _mapping(status.get("orchestration_stop_control"))
    hard_boundary = _mapping(status.get("hard_boundary_contract"))
    worker_presence = _mapping(status.get("worker_node_presence"))
    worker_instruction = _mapping(status.get("worker_node_instruction_preview"))
    child_instruction = _mapping(status.get("child_agent_instruction_preview"))
    execution_mode = _mapping(status.get("execution_mode_classification"))
    execution_packet = _mapping(status.get("execution_packet_preview"))
    execution_packet_body = _mapping(execution_packet.get("packet"))
    worker_contract = _mapping(execution_packet_body.get("worker_node_contract"))

    queue_count = _safe_int(report_queue.get("queue_count"))
    report_overwrite_conflict_count = _safe_int(report_lifecycle.get("report_overwrite_conflict_count"))
    result_ingestion_blocked_count = _safe_int(result_ingestion.get("blocked_report_count"))
    incomplete_report_contract_count = _safe_int(report_contract.get("incomplete_report_count"))
    report_completion_blocked_count = _safe_int(report_completion.get("blocked_completion_count"))
    stop_cancel_count = _safe_int(stop_control.get("stop_cancel_count"))
    report_queue_link_mismatch_count = _safe_int(report_queue.get("link_mismatch_count"))
    result_ingestion_link_mismatch_count = _safe_int(result_ingestion.get("link_mismatch_count"))
    report_completion_link_mismatch_count = _safe_int(report_completion.get("link_mismatch_count"))
    stop_cancel_link_mismatch_count = _safe_int(stop_control.get("link_mismatch_count"))
    hard_boundary_forbidden_count = _safe_int(hard_boundary.get("forbidden_action_count"))
    hard_boundary_separate_approval_count = _safe_int(hard_boundary.get("separate_approval_action_count"))
    hard_boundary_live_flag_violation_count = _safe_int(hard_boundary.get("live_flag_violation_count"))
    report_link_mismatch_ids = _report_link_mismatch_keys(
        report_queue,
        result_ingestion,
        report_completion,
        stop_control,
    )
    report_link_mismatch_count = len(report_link_mismatch_ids)
    readiness_states = _mapping(readiness.get("states"))
    next_label = _safe_text(next_safe_actions.get("primary_action_label"), max_chars=800)
    next_reason = _safe_text(
        _mapping(next_safe_actions.get("primary_action")).get("reason")
        or next_safe_actions.get("primary_action_reason")
        or _first_reason(_text_list(next_safe_actions.get("blocked_reasons")), ""),
        max_chars=800,
    )
    report_label = _safe_text(report_queue.get("primary_review_label"), max_chars=800)
    report_reason = _safe_text(report_queue.get("primary_review_reason"), max_chars=800)
    worker_presence_state = _safe_text(worker_presence.get("presence_state")) or "unknown"
    worker_last_seen_at = _safe_text(worker_presence.get("last_seen_at"))
    worker_seen_suffix = f" at {worker_last_seen_at}" if worker_last_seen_at else ""
    execution_packet_mode = _safe_text(_mapping(execution_packet.get("packet")).get("mode")) or "unknown"
    execution_packet_eligible = execution_packet.get("eligible") is True
    execution_mode_family = _safe_text(execution_mode.get("mode_family")) or "unknown"
    execution_lock_reasons = _unique_reasons(
        [
            *_text_list(hard_boundary.get("live_flag_violations")),
            *_execution_lock_blockers(
                ("hard boundary", hard_boundary),
                ("execution packet", execution_packet),
                ("execution packet body", execution_packet_body),
                ("worker contract", worker_contract),
            ),
        ]
    )
    blocked_reasons = _unique_reasons(
        [
            *_text_list(runtime_provenance.get("autonomy_blocked_reasons")),
            *_text_list(readiness.get("blocked_reasons")),
            *_text_list(report_lifecycle.get("blocked_reasons")),
            *_text_list(report_queue.get("blocked_reasons")),
            *_text_list(result_ingestion.get("blocked_reasons")),
            *_text_list(report_contract.get("blocked_reasons")),
            *_text_list(report_completion.get("blocked_reasons")),
            *_text_list(stop_control.get("blocked_reasons")),
            *_text_list(hard_boundary.get("blocked_reasons")),
            *_text_list(worker_presence.get("blocked_reasons")),
            *_text_list(execution_mode.get("blocked_reasons")),
            *_text_list(execution_packet.get("blocked_reasons")),
            *execution_lock_reasons,
            *_text_list(next_safe_actions.get("blocked_reasons")),
            *_text_list(worker_instruction.get("blocked_reasons")),
            *_text_list(child_instruction.get("blocked_reasons")),
        ]
    )
    state = _operator_decision_state(
        queue_count=queue_count,
        next_safe_actions=next_safe_actions,
        readiness_states=readiness_states,
        blocked_reasons=blocked_reasons,
    )
    approval_required = True
    summary_lines = [
        f"Operator state: {state.replace('_', ' ')}.",
        f"Approval required: {'yes' if approval_required else 'no'}.",
        f"Runtime provenance: {_safe_text(runtime_provenance.get('primary_status') or runtime_provenance.get('status')) or 'unknown'}.",
        (
            "Readiness: "
            f"read-only {_safe_text(readiness_states.get('supervised_read_only_autonomy')) or 'unknown'}, "
            f"scoped PR {_safe_text(readiness_states.get('scoped_pr_creation')) or 'unknown'}, "
            f"laptop Codex {_safe_text(readiness_states.get('laptop_codex_worker_node')) or 'unknown'}."
        ),
        (
            "Worker presence: "
            f"{worker_presence_state}"
            f"{worker_seen_suffix}."
        ),
        (
            "Execution mode: "
            f"{execution_mode_family}; execution disabled."
        ),
        (
            "Execution packet preview: "
            f"{execution_packet_mode}, eligible {str(execution_packet_eligible).lower()}; execution disabled."
        ),
    ]
    if next_label:
        summary_lines.append(f"Next safe action: {next_label}.")
    if queue_count:
        summary_lines.append(
            f"Top report review: {report_label or 'unlabeled report'}"
            f"{f' because {report_reason}' if report_reason else ''}."
        )
    if report_overwrite_conflict_count:
        summary_lines.append(
            "Report overwrite conflicts: "
            f"{report_overwrite_conflict_count}; duplicate report IDs are quarantined."
        )
    if result_ingestion:
        summary_lines.append(
            "Result ingestion: "
            f"{_safe_int(result_ingestion.get('ingestion_ready_count'))} ready, "
            f"{result_ingestion_blocked_count} blocked."
        )
    if report_contract:
        summary_lines.append(
            "Report contract completeness: "
            f"{_safe_int(report_contract.get('complete_report_count'))} complete, "
            f"{incomplete_report_contract_count} incomplete."
        )
    if report_completion:
        summary_lines.append(
            "Report completion path: "
            f"{_safe_int(report_completion.get('completion_ready_count'))} ready, "
            f"{report_completion_blocked_count} blocked."
        )
    if report_link_mismatch_count:
        summary_lines.append(
            "Report link mismatches: "
            f"unique {report_link_mismatch_count}, "
            f"queue {report_queue_link_mismatch_count}, "
            f"ingestion {result_ingestion_link_mismatch_count}, "
            f"completion {report_completion_link_mismatch_count}, "
            f"stop/cancel {stop_cancel_link_mismatch_count}; Jenny must review lineage before handoff."
        )
    if stop_cancel_count:
        summary_lines.append(
            "Stop/cancel control: "
            f"{stop_cancel_count} item{'s' if stop_cancel_count != 1 else ''}, "
            f"blocked {str(stop_control.get('blocked') is True).lower()}."
        )
    if hard_boundary:
        summary_lines.append(
            "Hard boundary contract: "
            f"{_safe_text(hard_boundary.get('state')) or 'unknown'}; "
            f"forbidden actions {hard_boundary_forbidden_count}; "
            f"separate approval actions {hard_boundary_separate_approval_count}; "
            f"live flag violations {hard_boundary_live_flag_violation_count}."
        )
    worker_instruction_ready = worker_instruction.get("ready_for_handoff") is True
    if worker_instruction.get("available") is True:
        summary_lines.append(
            "Worker instruction: "
            f"{'ready for manual handoff' if worker_instruction_ready else 'preview available but blocked'}; "
            "laptop Codex dispatch remains disabled."
        )
    child_instruction_ready = child_instruction.get("ready_for_handoff") is True
    if child_instruction.get("available") is True:
        summary_lines.append(
            "Child instruction: "
            f"{'ready for manual handoff' if child_instruction_ready else 'preview available but blocked'}; "
            "execution remains disabled."
        )
    summary_lines.append(
        "Hard locks: no deploy, restart, runtime switch, record/state/config mutation, secrets, live dispatch, session sending, or worker activation."
    )
    if execution_lock_reasons:
        summary_lines.append(
            "Execution lock blockers: "
            f"{', '.join(execution_lock_reasons[:6])}."
        )
    recommended_instruction = next_label or "Keep Mission Control preview-only and wait for exact approval."
    if queue_count and report_label:
        recommended_instruction = f"Jenny reviews {report_label} before issuing another worker instruction."

    return {
        **INERT_PROJECTION_FLAGS,
        "source": "mission_control_operator_decision_packet_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "manual_operator_review_only": True,
        "state": state,
        "execution_ready": False,
        "approval_required": approval_required,
        "jenny_review_required": (
            queue_count > 0
            or report_overwrite_conflict_count > 0
            or result_ingestion_blocked_count > 0
            or report_link_mismatch_count > 0
            or incomplete_report_contract_count > 0
            or report_completion_blocked_count > 0
            or stop_cancel_count > 0
            or hard_boundary_live_flag_violation_count > 0
            or bool(execution_lock_reasons)
        ),
        "next_safe_action_id": _safe_text(next_safe_actions.get("primary_action_id")),
        "next_safe_action_label": next_label,
        "next_safe_action_reason": next_reason,
        "report_review_queue_count": queue_count,
        "report_link_mismatch_count": report_link_mismatch_count,
        "report_link_mismatch_ids": report_link_mismatch_ids,
        "report_review_queue_link_mismatch_count": report_queue_link_mismatch_count,
        "result_ingestion_blocked_count": result_ingestion_blocked_count,
        "result_ingestion_blocked_reasons": _text_list(result_ingestion.get("blocked_reasons")),
        "result_ingestion_link_mismatch_count": result_ingestion_link_mismatch_count,
        "result_ingestion_primary_item_id": _safe_text(result_ingestion.get("primary_item_id")),
        "report_contract_incomplete_count": incomplete_report_contract_count,
        "report_contract_blocked_reasons": _text_list(report_contract.get("blocked_reasons")),
        "report_contract_primary_item_id": _safe_text(report_contract.get("primary_item_id")),
        "report_completion_blocked_count": report_completion_blocked_count,
        "report_completion_blocked_reasons": _text_list(report_completion.get("blocked_reasons")),
        "report_completion_link_mismatch_count": report_completion_link_mismatch_count,
        "report_completion_primary_item_id": _safe_text(report_completion.get("primary_item_id")),
        "stop_cancel_count": stop_cancel_count,
        "stop_cancel_blocked_reasons": _text_list(stop_control.get("blocked_reasons")),
        "stop_cancel_link_mismatch_count": stop_cancel_link_mismatch_count,
        "stop_cancel_primary_item_id": _safe_text(stop_control.get("primary_item_id")),
        "hard_boundary_state": _safe_text(hard_boundary.get("state")) or "unknown",
        "hard_boundary_blocked_reasons": _text_list(hard_boundary.get("blocked_reasons")),
        "hard_boundary_forbidden_action_count": hard_boundary_forbidden_count,
        "hard_boundary_separate_approval_action_count": hard_boundary_separate_approval_count,
        "hard_boundary_live_flag_violation_count": hard_boundary_live_flag_violation_count,
        "execution_mode_family": execution_mode_family,
        "execution_mode_blocked_reasons": _text_list(execution_mode.get("blocked_reasons")),
        "execution_packet_mode": execution_packet_mode,
        "execution_packet_eligible": execution_packet_eligible,
        "execution_packet_blocked_reasons": _text_list(execution_packet.get("blocked_reasons")),
        "execution_lock_blocked_reasons": execution_lock_reasons,
        "worker_presence_state": worker_presence_state,
        "worker_online": worker_presence.get("online") is True,
        "worker_last_seen_at": worker_last_seen_at,
        "top_report_review_item_id": _safe_text(report_queue.get("primary_review_item_id")),
        "top_report_review_label": report_label,
        "top_report_review_reason": report_reason,
        "report_overwrite_conflict_count": report_overwrite_conflict_count,
        "report_overwrite_conflict_ids": _text_list(report_lifecycle.get("report_overwrite_conflict_ids")),
        "worker_instruction_available": worker_instruction.get("available") is True,
        "worker_instruction_ready_for_handoff": worker_instruction_ready,
        "child_instruction_available": child_instruction.get("available") is True,
        "child_instruction_ready_for_handoff": child_instruction_ready,
        "summary_lines": summary_lines,
        "plain_language_summary": " ".join(summary_lines),
        "recommended_operator_instruction": _safe_text(recommended_instruction, max_chars=800),
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
    }


def _operator_decision_state(
    *,
    queue_count: int,
    next_safe_actions: dict[str, Any],
    readiness_states: dict[str, Any],
    blocked_reasons: list[str],
) -> str:
    if queue_count > 0:
        return "report_review_required"
    if next_safe_actions.get("blocked") is True or blocked_reasons:
        return "blocked"
    if any(_safe_text(value) == "preview_ready" for value in readiness_states.values()):
        return "preview_ready"
    return "awaiting_exact_approval"


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
        **INERT_PROJECTION_FLAGS,
        "source": source,
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
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
        link_mismatch_reason = _report_link_mismatch_reason(
            report,
            {"linked_record_type": _payload_record_type(id_field), "linked_record_id": record_id},
        )
        payload["report_id"] = report_id or report.report_id
        payload["report_link_status"] = (
            "linked_report_run_id_mismatch" if link_mismatch_reason else "linked_report_found"
        )
        payload["report_link_mismatch"] = bool(link_mismatch_reason)
        payload["report_link_mismatch_reason"] = link_mismatch_reason
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


def _payload_record_type(id_field: str) -> str:
    if id_field == "worker_run_id":
        return "worker_node_run"
    if id_field == "child_run_id":
        return "child_run"
    return "run"


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
        if report_id and link_status == "linked_report_run_id_mismatch":
            reasons.append(
                _safe_text(payload.get("report_link_mismatch_reason"))
                or f"report_id {report_id} run_id does not match {id_field} {record_id}"
            )
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


def _enabled_live_flag_names(*payloads: Any) -> list[str]:
    mapped_payloads = [_mapping(payload) for payload in payloads]
    enabled: list[str] = []
    for flag in LIVE_EXECUTION_FLAG_NAMES:
        if any(_flag_enabled(payload.get(flag)) for payload in mapped_payloads):
            enabled.append(flag)
    return enabled


def _flag_enabled(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}
    return False


def _execution_lock_blockers(*labeled_payloads: tuple[str, Any]) -> list[str]:
    blockers: list[str] = []
    for label, payload in labeled_payloads:
        for flag in _enabled_live_flag_names(payload):
            blockers.append(f"{label} {flag} must remain disabled")
    return _unique_reasons(blockers)


_LIVE_EXECUTION_FLAG_REASON_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("worker_dispatch_enabled", ("worker_dispatch_enabled", "worker dispatch")),
    ("would_execute", ("would_execute", "would execute")),
    ("would_dispatch", ("would_dispatch", "would dispatch")),
    ("would_session_send", ("would_session_send", "would session send", "would session-send")),
    ("execution_enabled", ("execution_enabled", "execution enabled", "worker execution")),
    ("dispatch_enabled", ("dispatch_enabled", "dispatch enabled")),
    ("session_send_enabled", ("session_send_enabled", "session send", "session-send", "session sending")),
)
_LIVE_EXECUTION_DISABLED_REASON_PHRASES = (
    "must remain false",
    "must remain disabled",
    "must stay disabled",
)


def _execution_lock_reason_blockers(*labeled_payloads: tuple[str, Any]) -> list[str]:
    blockers: list[str] = []
    for label, payload in labeled_payloads:
        for reason in _text_list(_mapping(payload).get("blocked_reasons")):
            lowered = reason.lower()
            if not any(phrase in lowered for phrase in _LIVE_EXECUTION_DISABLED_REASON_PHRASES):
                continue
            for flag, markers in _LIVE_EXECUTION_FLAG_REASON_MARKERS:
                if any(marker in lowered for marker in markers):
                    blockers.append(f"{label} {flag} must remain disabled")
                    break
    return _unique_reasons(blockers)


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_text(item) for item in value if _safe_text(item)]


def _first_reason(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def _latest_projection_payload(projection: dict[str, Any]) -> dict[str, Any]:
    active_runs = projection.get("active_runs")
    if isinstance(active_runs, list) and active_runs:
        return _mapping(active_runs[-1])
    latest_by_id = _mapping(projection.get("latest_by_id"))
    latest_payloads = list(latest_by_id.values())
    return _mapping(latest_payloads[-1]) if latest_payloads else {}


def _joined_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "none recorded"


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _merge_status_input(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_status_input(merged[key], value)
        else:
            merged[key] = value
    return merged
