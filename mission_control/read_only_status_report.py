"""Guarded supervised read-only status-report lifecycle helpers."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mission_control.records import (
    ApprovalRecord,
    JsonlRecordStore,
    ReportRecord,
    RunRecord,
)
from mission_control.records.models import RECORD_TYPES
from mission_control.workspace_status_records import build_workspace_status_from_records, default_record_store_path


PROJECT_ID = "project-hermes-mission-control"
APPROVAL_SCOPE = "project-hermes-mission-control:supervised_read_only_status_report"
LANE_TYPE = "supervised_read_only_status_report"
EXECUTION_MODE = "one_run_read_only"
REPORT_CONTRACT_KIND = "supervised_read_only_status_report_contract"
REPORT_RESULT_KIND = "supervised_read_only_status_report_result"

FORBIDDEN_ACTIONS = (
    "source/runtime file writes outside approved Mission Control record appends",
    "shell/write/patch tools",
    "patch",
    "shell",
    "commits",
    "PR creation",
    "merge",
    "deploy",
    "restart",
    "runtime switch",
    "AcceptedBaselineRecord append",
    "dispatch",
    "session-send execution",
    "worker dispatch",
    "queue mutation",
    "Waha",
    "social posting",
    "payment",
    "model routing",
    "worker activation",
    "timer activation",
    "daemon activation",
    "secrets access",
)


@dataclass(frozen=True)
class SupervisedReadOnlyStatusRecordSet:
    approval: ApprovalRecord
    run: RunRecord
    report_contract: ReportRecord


def build_record_set(
    *,
    head: str,
    runtime_path: str,
    now: datetime | None = None,
    suffix: str | None = None,
    expires_minutes: int = 30,
) -> SupervisedReadOnlyStatusRecordSet:
    """Build unique linked records for exactly one supervised read-only status report."""

    timestamp = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    safe_suffix = suffix or uuid.uuid4().hex[:12]
    approval_id = f"approval-pr402-supervised-read-only-status-{safe_suffix}"
    run_id = f"run-pr402-supervised-read-only-status-{safe_suffix}"
    report_id = f"report-pr402-supervised-read-only-status-contract-{safe_suffix}"
    expires_at = timestamp + timedelta(minutes=max(1, expires_minutes))
    common_metadata = {
        "one_run_only": True,
        "read_only_status_report_only": True,
        "file_write_allowed": False,
        "shell_allowed": False,
        "patch_allowed": False,
        "commit_allowed": False,
        "pr_creation_allowed": False,
        "merge_allowed": False,
        "deploy_allowed": False,
        "restart_allowed": False,
        "runtime_switch_allowed": False,
        "accepted_baseline_append_allowed": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "queue_mutation_enabled": False,
        "waha_enabled": False,
        "social_enabled": False,
        "payment_enabled": False,
        "model_routing_enabled": False,
        "secrets_access_allowed": False,
        "would_execute": False,
        "execution_enabled": False,
        "project_context_name": "Hermes / Mission Control",
    }
    approval = ApprovalRecord(
        approval_id=approval_id,
        project_id=PROJECT_ID,
        run_id=run_id,
        action_class=LANE_TYPE,
        approval_scope=APPROVAL_SCOPE,
        approved_actions=("run exactly one supervised read-only Mission Control status report",),
        forbidden_actions=FORBIDDEN_ACTIONS,
        status="approved",
        approval_mode="one_time",
        approved_by="operator",
        approval_source="manual_record_only_renewal",
        approval_text=(
            "Fresh short-lived approval for exactly one supervised read-only "
            "Mission Control status-report test. It does not approve code edits, "
            "PRs, deploy, restart, runtime switch, dispatch, session-send, "
            "worker dispatch, external side effects, or secrets access."
        ),
        created_at=_iso(timestamp),
        approved_at=_iso(timestamp),
        expires_at=_iso(expires_at),
        consumed_at="",
        baseline_runtime_path=runtime_path,
        baseline_head=head,
        metadata=common_metadata,
    )
    run = RunRecord(
        run_id=run_id,
        project_id=PROJECT_ID,
        approval_id=approval_id,
        lane_type=LANE_TYPE,
        title="Supervised read-only Mission Control status report",
        objective="Run exactly one read-only Mission Control status report without external side effects.",
        status="requested",
        execution_mode=EXECUTION_MODE,
        allowed_actions=("read Mission Control status surfaces", "write one linked status report record"),
        forbidden_actions=FORBIDDEN_ACTIONS,
        baseline_runtime_path=runtime_path,
        baseline_head=head,
        runtime_guard_state="CLEAN_AND_ALIGNED",
        dispatch_state=False,
        active_lane_count_at_start=0,
        agent_identity="jenny-supervised-read-only",
        source="mission_control_read_only_status_report",
        safety_gate_status="pending_trusted_one_run_packet",
        report_ids=(report_id,),
        metadata=common_metadata,
    )
    report_contract = ReportRecord(
        report_id=report_id,
        run_id=run_id,
        approval_id=approval_id,
        project_id=PROJECT_ID,
        status="reviewed",
        report_kind=REPORT_CONTRACT_KIND,
        summary="Read-only status-report contract is ready; no Jenny execution has occurred.",
        result="Contract only. The status report result must be appended by the guarded one-run backend path.",
        risks=("Execution remains limited to one read-only status report.",),
        tests=("workspace status gate must return trusted one-run packet before result append",),
        next_recommended_lane="Run the guarded read-only status-report executor once if the gate approves.",
        evidence_refs=(f"accepted runtime head {head}",),
        submitted_by="operator",
        submitted_from="manual-record-only-renewal",
        created_at=_iso(timestamp),
        reviewed_at=_iso(timestamp),
        reviewed_by="operator",
        metadata={
            **common_metadata,
            "no_jenny_execution": True,
            "jenny_executed": False,
            "safety_confirmation": (
                "No Jenny execution, dispatch, session-send, worker dispatch, "
                "source/runtime edit, shell, patch, external side effect, or secrets access occurred."
            ),
        },
    )
    return SupervisedReadOnlyStatusRecordSet(approval=approval, run=run, report_contract=report_contract)


def append_record_set(
    *,
    records_path: str | Path | None = None,
    head: str,
    runtime_path: str,
    suffix: str | None = None,
    now: datetime | None = None,
) -> SupervisedReadOnlyStatusRecordSet:
    record_set = build_record_set(head=head, runtime_path=runtime_path, suffix=suffix, now=now)
    store = JsonlRecordStore(records_path or default_record_store_path())
    for record in (record_set.approval, record_set.run, record_set.report_contract):
        store.append(record)
    return record_set


def run_once_if_trusted(
    *,
    records_path: str | Path | None = None,
    now: datetime | None = None,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Append one read-only status report result only when the backend gate trusts the packet."""

    path = Path(records_path) if records_path is not None else default_record_store_path()
    timestamp = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    status = build_workspace_status_from_records({"now": _iso(timestamp)}, records_path=path)
    packet = status.get("execution_packet_preview") if isinstance(status, dict) else {}
    packet = packet if isinstance(packet, dict) else {}
    packet_body = packet.get("packet") if isinstance(packet.get("packet"), dict) else {}
    if packet.get("trusted_for_execution") is not True or packet.get("one_run_authorized") is not True:
        return _blocked("execution packet is not trusted for the supervised one-run status report", status)
    if packet.get("eligible") is not True:
        return _blocked("execution packet is not eligible", status)
    if any(
        packet.get(flag) is True
        for flag in (
            "dispatch_enabled",
            "session_send_enabled",
            "worker_dispatch_enabled",
            "would_dispatch",
            "would_session_send",
        )
    ):
        return _blocked("execution packet would require dispatch, session-send, or worker dispatch", status)
    if packet_body.get("mode") != "read_only":
        return _blocked("execution packet mode is not read_only", status)
    if packet_body.get("status_report_only") is not True:
        return _blocked("execution packet is not limited to a status report", status)
    if any(
        packet_body.get(flag) is True
        for flag in (
            "uses_bridge",
            "uses_dispatch",
            "uses_session_send",
            "uses_worker_dispatch",
            "uses_write_tools",
        )
    ):
        return _blocked("execution packet would use a bridge, dispatcher, worker, or write tools", status)

    run_id = str(packet_body.get("run_id") or "")
    approval_id = str(packet_body.get("approval_id") or "")
    project_id = str(packet_body.get("project_id") or PROJECT_ID)
    if not run_id or not approval_id:
        return _blocked("execution packet is missing run_id or approval_id", status)

    result_report_id = f"report-pr402-supervised-read-only-status-result-{uuid.uuid4().hex[:12]}"
    store = JsonlRecordStore(path)
    report = ReportRecord(
        report_id=result_report_id,
        run_id=run_id,
        approval_id=approval_id,
        project_id=project_id,
        status="accepted",
        report_kind=REPORT_RESULT_KIND,
        summary="Jenny supervised read-only status report completed without external side effects.",
        result=_status_report_text(status, record_counts=_record_counts(store), current_run_id=run_id),
        blockers=tuple(status.get("operator_decision_packet", {}).get("blocked_reasons", ())[:8])
        if isinstance(status.get("operator_decision_packet"), dict)
        else (),
        tests=(
            "guarded read-only status-report backend trusted one-run packet and appended only approved records",
        ),
        next_recommended_lane="Review this first execution-tested read-only report before enabling any broader execution.",
        evidence_refs=("workspace status projection", "accepted baseline record", "runtime provenance projection"),
        submitted_by="jenny-supervised-read-only",
        submitted_from="mission_control_guarded_one_run_backend",
        created_at=_iso(timestamp),
        reviewed_at=_iso(timestamp),
        reviewed_by="mission-control-gate",
        metadata={
            "one_run_only": True,
            "read_only_status_report_only": True,
            "approved_record_appends_only": True,
            "no_unapproved_file_edits": True,
            "no_source_or_runtime_file_edits": True,
            "no_git_changes": True,
            "no_dispatch": True,
            "no_session_send": True,
            "no_worker_dispatch": True,
            "no_external_side_effects": True,
            "no_secrets_printed": True,
            "safety_confirmation": (
                "The guarded backend appended only this status report result and terminal "
                "RunRecord update; no source/runtime edit, dispatch, session-send, worker dispatch, "
                "shell, patch, external side effect, or secrets access occurred."
            ),
            "timeout_seconds": timeout_seconds,
        },
    )
    accepted_baseline = _mapping(status.get("accepted_baseline_record"))
    completed_run = RunRecord(
        run_id=run_id,
        project_id=project_id,
        approval_id=approval_id,
        lane_type=LANE_TYPE,
        title="Supervised read-only Mission Control status report",
        objective="Run exactly one read-only Mission Control status report without external side effects.",
        status="completed",
        execution_mode=EXECUTION_MODE,
        allowed_actions=("read Mission Control status surfaces", "write one linked status report record"),
        forbidden_actions=FORBIDDEN_ACTIONS,
        baseline_runtime_path=str(accepted_baseline.get("runtime_path") or ""),
        baseline_head=str(accepted_baseline.get("head") or ""),
        runtime_guard_state=str(_mapping(status.get("runtime_provenance")).get("primary_status") or ""),
        dispatch_state=False,
        agent_identity="jenny-supervised-read-only",
        source="mission_control_read_only_status_report",
        stopped_at=_iso(timestamp),
        stop_reason="completed one supervised read-only status report",
        safety_gate_status="trusted_one_run_completed",
        report_ids=(result_report_id,),
        result_record_ids=(result_report_id,),
        metadata={
            "one_run_only": True,
            "read_only_status_report_only": True,
            "execution_packet_trusted": True,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
        },
    )
    report_index = store.append(report)
    run_index = store.append(completed_run)
    return {
        "started": True,
        "completed": True,
        "run_id": run_id,
        "approval_id": approval_id,
        "report_id": result_report_id,
        "report_record_index": report_index,
        "run_record_index": run_index,
        "status_report_summary": report.summary,
        "status_report": report.result,
        "timeout_seconds": timeout_seconds,
    }


def _status_report_text(
    status: dict[str, Any],
    *,
    record_counts: dict[str, int],
    current_run_id: str,
) -> str:
    baseline = _mapping(status.get("accepted_baseline_record"))
    dashboard = _mapping(status.get("dashboard_runtime"))
    gateway = _mapping(status.get("gateway_runtime"))
    runtime = _mapping(status.get("runtime_provenance"))
    readiness = _mapping(status.get("orchestration_readiness"))
    records = _mapping(status.get("control_plane_records"))
    run_lifecycle = _mapping(status.get("run_lifecycle"))
    states = _mapping(readiness.get("states"))
    packet = _mapping(status.get("execution_packet_preview"))
    packet_body = _mapping(packet.get("packet"))
    project_id = str(packet_body.get("project_id") or "")
    project_name = str(packet_body.get("project_name") or "")
    project_label = project_id
    if project_name:
        project_label = f"{project_id} ({project_name})" if project_id else project_name
    active_runs = _safe_int(records.get("active_run_count"))
    active_run_ids = tuple(str(run_id) for run_id in run_lifecycle.get("active_run_ids", ()) if run_id)
    current_run_is_active = current_run_id in active_run_ids or (
        not active_run_ids and records.get("latest_active_run_id") == current_run_id
    )
    post_run_active_runs = max(active_runs - 1, 0) if current_run_is_active else active_runs
    summary = (
        "SAFE for this one supervised read-only status report; broader autonomy remains blocked."
        if packet.get("trusted_for_execution") is True and packet.get("one_run_authorized") is True
        else "BLOCKED until an exact one-run read-only packet is approved."
    )
    readonly = _mapping(readiness.get("supervised_read_only_autonomy"))
    scoped_pr = _mapping(readiness.get("scoped_pr_creation"))
    worker = _mapping(readiness.get("laptop_codex_worker_node"))
    return "\n".join(
        [
            f"Operator summary: {summary}",
            f"Project context: {project_label or 'unavailable in execution packet'}",
            f"Accepted runtime/head: {baseline.get('runtime_path', '')} {baseline.get('head', '')}",
            f"Dashboard runtime/head: {dashboard.get('path', '')} {dashboard.get('head', '')}",
            f"Gateway runtime/head: {gateway.get('path', '')} {gateway.get('head', '')}",
            f"Latest baseline ID: {baseline.get('baseline_id', '')}",
            f"Rollback: {runtime.get('informational_statuses', [])}",
            "Record counts: "
            + ", ".join(f"{name}={count}" for name, count in record_counts.items()),
            (
                "Lane state: "
                f"report-time active lanes={active_runs}; "
                f"current run active={str(current_run_is_active).lower()}; "
                f"post-run active lanes=expected {post_run_active_runs} after terminal RunRecord append; "
                "report-time may include this running status report."
            ),
            f"Record activity: pending approvals {records.get('pending_approval_count', '')}, available approvals {records.get('available_approval_count', '')}",
            "Flags: dispatch=false, session-send=false, worker-dispatch=false",
            f"Supervised read-only autonomy: {states.get('supervised_read_only_autonomy', '')}",
            f"Scoped PR classification: {states.get('scoped_pr_creation', '')}",
            f"Read-only autonomy blockers: {readonly.get('blocked_reasons', [])}",
            f"Scoped PR blockers: {scoped_pr.get('blocked_reasons', [])}",
            f"Worker-node/laptop blockers: {worker.get('blocked_reasons', [])}",
            "Live operations blockers: deploy/restart/runtime-switch/baseline append are not approved for this lane.",
            "External action blockers: Waha/social/payment/model-routing/queue remain disabled.",
            "UI/operator concerns: keep blocked controls explicit and review this report before another lane.",
            (
                "Safety verification: approved record appends only; source/runtime files edited=no; "
                "git commits/PRs=no; deploy/restart/runtime switch=no; baseline append=no; "
                "dispatch/session-send/worker=no; external actions=no; secrets printed=no."
            ),
            f"Remaining blockers: {readiness.get('blocked_reasons', [])}",
            "Next recommended action: review this report, then approve one bounded read-only lane if the report is acceptable.",
        ]
    )


def _record_counts(store: JsonlRecordStore) -> dict[str, int]:
    records = store.read_all()
    by_type = Counter(getattr(record, "record_type", type(record).__name__) for record in records)
    counts = {"total": len(records)}
    counts.update({record_type: by_type.get(record_type, 0) for record_type in RECORD_TYPES})
    return counts


def _blocked(reason: str, status: dict[str, Any]) -> dict[str, Any]:
    packet = status.get("execution_packet_preview") if isinstance(status, dict) else {}
    return {
        "started": False,
        "completed": False,
        "blocked_reason": reason,
        "packet": packet if isinstance(packet, dict) else {},
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
