from __future__ import annotations

from mission_control.records import (
    AcceptedBaselineRecord,
    ApprovalRecord,
    ChildRunRecord,
    JsonlRecordStore,
    ReportRecord,
    RunRecord,
    WorkerNodeRunRecord,
)
from mission_control.workspace_status_records import build_workspace_status_from_records


def test_record_sourced_workspace_status_uses_latest_baseline_and_idle_when_no_runs(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        AcceptedBaselineRecord(
            baseline_id="old",
            runtime_path="/home/jenny/.hermes/hermes-runtime-old",
            head="1" * 40,
            rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-rollback-old",
            rollback_head="2" * 40,
            active_kanban=1,
        )
    )
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted-pr69-control-plane-af1eafe",
            runtime_path="/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe",
            head="af1eafe23eb25eabd92496e0ea04db39e099acdf",
            rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-manual-session-link-ui-d7d1e0d",
            rollback_head="d7d1e0d758a64783f4de435f06450be218e8a2bf",
            active_kanban=0,
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["accepted_baseline_source"] == "record"
    assert status["accepted_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe"
    assert status["accepted_baseline"]["head"] == "af1eafe23eb25eabd92496e0ea04db39e099acdf"
    assert status["rollback_baseline"]["head"] == "d7d1e0d758a64783f4de435f06450be218e8a2bf"
    assert status["lane"]["active_lane"] == ""
    assert status["lane"]["active_lane_count"] == 0
    assert status["activity"]["active_runs"] == 0
    assert status["control_plane_records"]["active_run_count"] == 0
    assert status["record_store"]["status"] == "ok"
    assert "accepted_baseline_source_missing" not in status["stale_context"]["warnings"]


def test_record_sourced_workspace_status_projects_real_active_runs_and_approvals(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted",
            runtime_path="/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe",
            head="af1eafe23eb25eabd92496e0ea04db39e099acdf",
            rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-manual-session-link-ui-d7d1e0d",
            rollback_head="d7d1e0d758a64783f4de435f06450be218e8a2bf",
            active_kanban=0,
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-1",
            project_id="project-hermes-mission-control",
            action_class="read_only_lane",
            approval_scope="one bounded read-only Mission Control diagnostic",
            status="proposed",
        )
    )
    store.append(
        RunRecord(
            run_id="run-1",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Read-only status reconciliation",
            status="running",
            execution_mode="manual_copy",
            baseline_head="af1eafe23eb25eabd92496e0ea04db39e099acdf",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["accepted_baseline_source"] == "record"
    assert status["lane"]["active_lane"] == "Read-only status reconciliation"
    assert status["lane"]["active_lane_count"] == 1
    assert status["activity"]["active_runs"] == 1
    assert status["control_plane_records"]["active_run_count"] == 1
    assert status["control_plane_records"]["latest_active_run_id"] == "run-1"
    assert status["control_plane_records"]["pending_approval_count"] == 1
    warnings = set(status["stale_context"]["warnings"])
    assert "active_workers_tasks_or_runs_present" in warnings
    assert "MISSING_RUNTIME_PATH" in warnings
    assert status["runtime_provenance"]["autonomy_blocked"] is True
    assert status["read_only_autonomy_eligibility"]["eligible"] is False


def test_record_sourced_workspace_status_uses_latest_run_by_id_for_active_counts(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted",
            runtime_path="/runtime/current",
            head="8ef64e370a51bc19e97fec1526f5bb3d42025a09",
            rollback_runtime_path="/runtime/rollback",
            rollback_head="8ef64e370a51bc19e97fec1526f5bb3d42025a09",
        )
    )
    store.append(
        RunRecord(
            run_id="run-1",
            project_id="project-hermes-mission-control",
            lane_type="pr_creation",
            title="Scoped PR lane",
            status="running",
        )
    )
    store.append(
        RunRecord(
            run_id="run-1",
            project_id="project-hermes-mission-control",
            lane_type="pr_creation",
            title="Scoped PR lane",
            status="completed",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["control_plane_records"]["active_run_count"] == 0
    assert status["control_plane_records"]["active_mutation_lane_count"] == 0
    assert status["lane"]["active_lane_count"] == 0
    assert status["control_plane_lifecycle"]["latest_runs_by_id"]["run-1"]["status"] == "completed"


def test_record_sourced_workspace_status_projects_child_and_worker_node_runs(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        ChildRunRecord(
            child_run_id="child-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="running",
            objective="Inspect a bounded context packet.",
            report_id="report-child",
        )
    )
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="blocked",
            objective="Prepare a scoped PR.",
            blocked_reasons=("worker node offline",),
            report_contract_status="missing",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-child",
            run_id="child-run-1",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Child run reported evidence.",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    child = status["child_agent_orchestration"]
    worker = status["worker_node_orchestration"]
    assert child["active_count"] == 1
    assert child["active_runs"][0]["child_run_id"] == "child-run-1"
    assert child["dispatch_enabled"] is False
    assert worker["active_count"] == 1
    assert worker["active_runs"][0]["worker_host_label"] == "laptop-codex"
    assert worker["blocked_reasons"] == ["worker node offline"]
    assert worker["worker_dispatch_enabled"] is False
    assert status["control_plane_records"]["active_child_run_count"] == 1
    assert status["control_plane_records"]["active_worker_node_run_count"] == 1


def test_record_sourced_workspace_status_projects_report_lifecycle_blockers(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        RunRecord(
            run_id="run-reportless",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Finished without report",
            status="completed",
        )
    )
    store.append(
        RunRecord(
            run_id="run-missing-linked-report",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Finished with stale report pointer",
            status="completed",
            report_ids=("report-missing",),
        )
    )
    store.append(
        RunRecord(
            run_id="run-with-report",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Finished with received report",
            status="completed",
            report_ids=("report-duplicate",),
        )
    )
    store.append(
        ReportRecord(
            report_id="report-duplicate",
            run_id="run-with-report",
            project_id="project-hermes-mission-control",
            status="received",
            summary="First append-only report record.",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-accepted",
            run_id="run-reviewed",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Accepted report.",
            reviewed_at="2026-06-19T10:00:00Z",
            reviewed_by="jenny",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-duplicate",
            run_id="run-with-report",
            project_id="project-hermes-mission-control",
            status="needs_review",
            summary="Second append-only report record.",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    lifecycle = status["report_lifecycle"]
    assert lifecycle["display_only"] is True
    assert lifecycle["trusted_for_execution"] is False
    assert lifecycle["execution_enabled"] is False
    assert lifecycle["dispatch_enabled"] is False
    assert lifecycle["session_send_enabled"] is False
    assert lifecycle["worker_dispatch_enabled"] is False
    assert lifecycle["append_only_projection"] is True
    assert lifecycle["raw_report_count"] == 3
    assert lifecycle["report_count"] == 2
    assert lifecycle["status_counts"] == {"accepted": 1, "needs_review": 1}
    assert lifecycle["duplicate_report_ids"] == ["report-duplicate"]
    assert lifecycle["open_report_ids"] == ["report-duplicate"]
    assert lifecycle["terminal_report_ids"] == ["report-accepted"]
    assert lifecycle["reviewed_report_ids"] == ["report-accepted"]
    assert lifecycle["runs_missing_report"] == ["run-reportless"]
    assert lifecycle["runs_with_missing_linked_report_ids"] == {
        "run-missing-linked-report": ["report-missing"]
    }
    assert lifecycle["reports_by_run_id"] == {
        "run-reviewed": ["report-accepted"],
        "run-with-report": ["report-duplicate"],
    }
    assert lifecycle["blocked"] is True
    assert "report_id report-duplicate has multiple append-only records" in lifecycle["blocked_reasons"]
    assert "run_id run-reportless has no linked report" in lifecycle["blocked_reasons"]
    assert (
        "run_id run-missing-linked-report links missing report ids: report-missing"
        in lifecycle["blocked_reasons"]
    )
    assert "report_id report-duplicate still needs review" in lifecycle["blocked_reasons"]
