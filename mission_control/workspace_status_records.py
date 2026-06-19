"""Record-sourced Mission Control workspace status projection.

This module keeps the pure status normalizer separate from filesystem reads,
while giving diagnostics and read-only APIs one canonical way to inject the
latest append-only Mission Control records.
"""

from __future__ import annotations

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
            recent_runs = ()
            recent_approvals = ()
            recent_reports = ()
            recent_child_runs = ()
            recent_worker_runs = ()
    else:
        latest_baseline = {}
        latest_handoff = {}
        recent_runs = ()
        recent_approvals = ()
        recent_reports = ()
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

    status = build_workspace_status(status_input)
    status["child_agent_orchestration"] = _orchestration_projection(
        records=recent_child_runs,
        active_records=active_child_runs,
        id_field="child_run_id",
        source="ChildRunRecord",
    )
    status["worker_node_orchestration"] = _orchestration_projection(
        records=recent_worker_runs,
        active_records=active_worker_runs,
        id_field="worker_run_id",
        source="WorkerNodeRunRecord",
    )
    status["control_plane_lifecycle"] = status_input["control_plane_lifecycle"]
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


def _orchestration_projection(
    *,
    records: tuple[Any, ...],
    active_records: tuple[Any, ...],
    id_field: str,
    source: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "display_only": True,
        "trusted_for_execution": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "active_count": len(active_records),
        "latest_by_id": _latest_by_id(records, id_field),
        "active_runs": [record.to_dict() for record in active_records],
        "blocked_reasons": _projection_blocked_reasons(active_records),
    }


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


def _merge_status_input(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_status_input(merged[key], value)
        else:
            merged[key] = value
    return merged
