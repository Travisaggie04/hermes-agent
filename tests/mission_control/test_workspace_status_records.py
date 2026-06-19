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
            allowed_actions=("read approved context", "report evidence"),
            forbidden_actions=("dispatch", "mutate records"),
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
            allowed_actions=("edit scoped files", "run focused tests"),
            forbidden_actions=("deploy", "restart", "runtime switch"),
            blocked_reasons=("worker node offline",),
            report_contract_status="present",
            report_id="report-worker",
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
    store.append(
        ReportRecord(
            report_id="report-worker",
            run_id="worker-run-1",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Worker node reported PR evidence.",
            reviewed_at="2026-06-19T11:00:00Z",
            reviewed_by="jenny",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    child = status["child_agent_orchestration"]
    worker = status["worker_node_orchestration"]
    assert child["active_count"] == 1
    assert child["active_runs"][0]["child_run_id"] == "child-run-1"
    assert child["active_runs"][0]["report_link_status"] == "linked_report_found"
    assert child["active_runs"][0]["linked_report_status"] == "received"
    assert child["active_runs"][0]["linked_report_review_status"] == "needs_review"
    assert child["active_runs"][0]["linked_report_summary"] == "Child run reported evidence."
    assert child["blocked_reasons"] == ["report_id report-child still needs review"]
    assert child["dispatch_enabled"] is False
    assert worker["active_count"] == 1
    assert worker["active_runs"][0]["worker_host_label"] == "laptop-codex"
    assert worker["active_runs"][0]["report_link_status"] == "linked_report_found"
    assert worker["active_runs"][0]["linked_report_status"] == "accepted"
    assert worker["active_runs"][0]["linked_report_review_status"] == "accepted"
    assert worker["active_runs"][0]["report_review_status"] == "accepted"
    assert worker["active_runs"][0]["linked_report_summary"] == "Worker node reported PR evidence."
    assert worker["blocked_reasons"] == ["worker node offline"]
    assert worker["worker_dispatch_enabled"] is False
    assert status["control_plane_records"]["active_child_run_count"] == 1
    assert status["control_plane_records"]["active_worker_node_run_count"] == 1

    review_queue = status["report_review_queue"]
    assert review_queue["display_only"] is True
    assert review_queue["trusted_for_execution"] is False
    assert review_queue["would_execute"] is False
    assert review_queue["execution_enabled"] is False
    assert review_queue["dispatch_enabled"] is False
    assert review_queue["session_send_enabled"] is False
    assert review_queue["worker_dispatch_enabled"] is False
    assert review_queue["stored"] is False
    assert review_queue["dry_run_only"] is True
    assert review_queue["manual_review_only"] is True
    assert review_queue["queue_count"] == 1
    assert review_queue["needs_review_count"] == 1
    assert review_queue["missing_report_count"] == 0
    assert review_queue["primary_review_item_id"] == "report:report-child"
    assert review_queue["primary_review_item"]["linked_record_type"] == "child_run"
    assert review_queue["primary_review_item"]["linked_record_id"] == "child-run-1"
    assert review_queue["primary_review_item"]["manual_only"] is True
    assert "report_id report-child still needs Jenny review" in review_queue["blocked_reasons"]

    graph = status["orchestration_run_graph"]
    assert graph["display_only"] is True
    assert graph["trusted_for_execution"] is False
    assert graph["would_execute"] is False
    assert graph["execution_enabled"] is False
    assert graph["dispatch_enabled"] is False
    assert graph["session_send_enabled"] is False
    assert graph["worker_dispatch_enabled"] is False
    assert graph["stored"] is False
    assert graph["dry_run_only"] is True
    assert graph["node_count"] == 4
    assert graph["child_run_node_count"] == 1
    assert graph["worker_node_run_count"] == 1
    assert graph["report_node_count"] == 2
    assert graph["edge_count"] == 4
    node_ids = {node["node_id"] for node in graph["nodes"]}
    assert {"child-run-1", "worker-run-1", "report-child", "report-worker"} <= node_ids
    assert "child_run_id child-run-1 references missing parent run_id run-parent" in graph["blocked_reasons"]
    assert "worker_run_id worker-run-1 references missing parent run_id run-parent" in graph["blocked_reasons"]

    child_instruction = status["child_agent_instruction_preview"]
    assert child_instruction["display_only"] is True
    assert child_instruction["trusted_for_execution"] is False
    assert child_instruction["would_execute"] is False
    assert child_instruction["execution_enabled"] is False
    assert child_instruction["dispatch_enabled"] is False
    assert child_instruction["session_send_enabled"] is False
    assert child_instruction["worker_dispatch_enabled"] is False
    assert child_instruction["stored"] is False
    assert child_instruction["dry_run_only"] is True
    assert child_instruction["manual_handoff_only"] is True
    assert child_instruction["available"] is True
    assert child_instruction["blocked"] is True
    assert child_instruction["child_run_id"] == "child-run-1"
    assert child_instruction["agent_identity"] == "jenny-child"
    assert child_instruction["objective"] == "Inspect a bounded context packet."
    assert child_instruction["allowed_actions"] == ["read approved context", "report evidence"]
    assert "dispatch" in child_instruction["forbidden_actions"]
    assert "no live delegation activation" in child_instruction["forbidden_actions"]
    assert "report_id report-child still needs review" in child_instruction["blocked_reasons"]
    assert "Manual delegation preview only" in child_instruction["manual_handoff_prompt"]
    assert "Report contract:" in child_instruction["manual_handoff_prompt"]

    instruction = status["worker_node_instruction_preview"]
    assert instruction["display_only"] is True
    assert instruction["trusted_for_execution"] is False
    assert instruction["would_execute"] is False
    assert instruction["execution_enabled"] is False
    assert instruction["dispatch_enabled"] is False
    assert instruction["session_send_enabled"] is False
    assert instruction["worker_dispatch_enabled"] is False
    assert instruction["stored"] is False
    assert instruction["dry_run_only"] is True
    assert instruction["manual_handoff_only"] is True
    assert instruction["available"] is True
    assert instruction["blocked"] is True
    assert instruction["worker_run_id"] == "worker-run-1"
    assert instruction["worker_identity"] == "codex"
    assert instruction["worker_host_label"] == "laptop-codex"
    assert instruction["objective"] == "Prepare a scoped PR."
    assert instruction["allowed_actions"] == ["edit scoped files", "run focused tests"]
    assert "deploy" in instruction["forbidden_actions"]
    assert "no live deploy" in instruction["forbidden_actions"]
    assert "worker node offline" in instruction["blocked_reasons"]
    assert "Manual handoff only" in instruction["manual_handoff_prompt"]
    assert "Report contract:" in instruction["manual_handoff_prompt"]


def test_record_sourced_workspace_status_projects_report_review_queue(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        RunRecord(
            run_id="run-terminal-missing-report",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Terminal run missing report",
            status="completed",
        )
    )
    store.append(
        ChildRunRecord(
            child_run_id="child-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="running",
            objective="Inspect bounded context.",
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
            objective="Prepare scoped PR evidence.",
            report_id="report-worker",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-child",
            run_id="child-run-1",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Child evidence is waiting for Jenny.",
            blockers=("needs provenance check",),
        )
    )
    store.append(
        ReportRecord(
            report_id="report-worker",
            run_id="worker-run-1",
            project_id="project-hermes-mission-control",
            status="needs_review",
            summary="Laptop Codex reported scoped PR evidence.",
            risks=("test coverage is focused",),
            tests=("mission_control status tests passed",),
            submitted_by="codex",
            submitted_from="laptop-codex",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    queue = status["report_review_queue"]
    assert queue["source"] == "mission_control_report_review_queue_v1"
    assert queue["display_only"] is True
    assert queue["trusted_for_execution"] is False
    assert queue["would_execute"] is False
    assert queue["execution_enabled"] is False
    assert queue["dispatch_enabled"] is False
    assert queue["session_send_enabled"] is False
    assert queue["worker_dispatch_enabled"] is False
    assert queue["stored"] is False
    assert queue["dry_run_only"] is True
    assert queue["manual_review_only"] is True
    assert queue["queue_count"] == 3
    assert queue["needs_review_count"] == 2
    assert queue["missing_report_count"] == 1
    assert queue["duplicate_report_count"] == 0
    assert queue["blocked"] is True
    assert queue["primary_review_item_id"] == "report:report-worker"
    assert queue["primary_review_label"] == "Laptop Codex reported scoped PR evidence."
    assert queue["primary_review_reason"] == "report_id report-worker still needs Jenny review"
    primary = queue["primary_review_item"]
    assert primary["linked_record_type"] == "worker_node_run"
    assert primary["linked_record_id"] == "worker-run-1"
    assert primary["manual_only"] is True
    assert primary["submitted_by"] == "codex"
    assert primary["submitted_from"] == "laptop-codex"
    assert primary["risks"] == ["test coverage is focused"]
    assert primary["tests"] == ["mission_control status tests passed"]
    item_ids = {item["item_id"] for item in queue["items"]}
    assert item_ids == {
        "report:report-child",
        "report:report-worker",
        "missing-report:run:run-terminal-missing-report",
    }
    assert "report_id report-worker still needs Jenny review" in queue["blocked_reasons"]
    assert "report_id report-child still needs Jenny review" in queue["blocked_reasons"]
    assert "run_id run-terminal-missing-report has no linked report" in queue["blocked_reasons"]

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_report_review_queue" in action_ids
    assert "report_id report-worker still needs Jenny review" in next_safe_actions["blocked_reasons"]


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
            report_id="report-reviewed-status",
            run_id="run-reviewed-status",
            project_id="project-hermes-mission-control",
            status="reviewed",
            summary="Reviewed report without timestamp.",
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
    assert lifecycle["raw_report_count"] == 4
    assert lifecycle["report_count"] == 3
    assert lifecycle["status_counts"] == {"accepted": 1, "needs_review": 1, "reviewed": 1}
    assert lifecycle["duplicate_report_ids"] == ["report-duplicate"]
    assert lifecycle["open_report_ids"] == ["report-duplicate"]
    assert lifecycle["terminal_report_ids"] == ["report-accepted"]
    assert lifecycle["reviewed_report_ids"] == ["report-accepted", "report-reviewed-status"]
    assert lifecycle["runs_missing_report"] == ["run-reportless"]
    assert lifecycle["runs_with_missing_linked_report_ids"] == {
        "run-missing-linked-report": ["report-missing"]
    }
    assert lifecycle["reports_by_run_id"] == {
        "run-reviewed": ["report-accepted"],
        "run-reviewed-status": ["report-reviewed-status"],
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


def test_record_sourced_workspace_status_projects_approval_and_run_lifecycle_blockers(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        ApprovalRecord(
            approval_id="approval-duplicate",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="proposed",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-duplicate",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="approved",
            expires_at="2026-06-20T00:00:00Z",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-valid",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="approved",
            expires_at="2026-06-20T00:00:00Z",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-expired",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="approved",
            expires_at="2026-06-18T00:00:00Z",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-consumed",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="approved",
            consumed_at="2026-06-19T08:00:00Z",
            expires_at="2026-06-20T00:00:00Z",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-rejected",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="rejected",
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-pending",
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope="project-hermes read-only inspection",
            status="proposed",
        )
    )
    for run_id, approval_id, lane_type in (
        ("run-valid", "approval-valid", "read_only_inspection"),
        ("run-expired", "approval-expired", "read_only_inspection"),
        ("run-consumed", "approval-consumed", "read_only_inspection"),
        ("run-rejected", "approval-rejected", "read_only_inspection"),
        ("run-missing-record", "approval-missing", "read_only_inspection"),
        ("run-mutation-a", "approval-valid", "implementation"),
        ("run-mutation-b", "approval-valid", "pr_creation"),
    ):
        store.append(
            RunRecord(
                run_id=run_id,
                project_id="project-hermes-mission-control",
                approval_id=approval_id,
                lane_type=lane_type,
                status="running",
            )
        )
    store.append(
        RunRecord(
            run_id="run-no-approval",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            status="running",
        )
    )
    store.append(
        RunRecord(
            run_id="run-terminal-missing-report",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            status="completed",
        )
    )
    store.append(
        RunRecord(
            run_id="run-terminal-stale-report",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            status="completed",
            report_ids=("report-missing",),
        )
    )
    store.append(
        RunRecord(
            run_id="run-stopped",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            status="stopped",
            report_ids=("report-stopped",),
        )
    )
    store.append(
        ReportRecord(
            report_id="report-stopped",
            run_id="run-stopped",
            project_id="project-hermes-mission-control",
            status="accepted",
        )
    )

    status = build_workspace_status_from_records(
        {"now": "2026-06-19T12:00:00Z"},
        records_path=records_path,
    )

    approvals = status["approval_lifecycle"]
    assert approvals["display_only"] is True
    assert approvals["execution_enabled"] is False
    assert approvals["dispatch_enabled"] is False
    assert approvals["session_send_enabled"] is False
    assert approvals["worker_dispatch_enabled"] is False
    assert approvals["append_only_projection"] is True
    assert approvals["raw_approval_count"] == 7
    assert approvals["approval_count"] == 6
    assert set(approvals["available_approval_ids"]) == {"approval-duplicate", "approval-valid"}
    assert approvals["pending_approval_ids"] == ["approval-pending"]
    assert approvals["expired_approval_ids"] == ["approval-expired"]
    assert approvals["consumed_approval_ids"] == ["approval-consumed"]
    assert approvals["rejected_or_cancelled_approval_ids"] == ["approval-rejected"]
    assert approvals["duplicate_approval_ids"] == ["approval-duplicate"]
    assert approvals["runs_missing_approval_id"] == ["run-no-approval"]
    assert approvals["runs_with_missing_approval_record"] == {
        "run-missing-record": "approval-missing"
    }
    assert approvals["runs_with_unavailable_approval"] == {
        "run-consumed": "approval-consumed",
        "run-expired": "approval-expired",
        "run-rejected": "approval-rejected",
    }
    assert approvals["blocked"] is True
    assert "approval_id approval-duplicate has multiple append-only records" in approvals["blocked_reasons"]
    assert "active run_id run-no-approval has no approval_id" in approvals["blocked_reasons"]
    assert "run_id run-missing-record references missing approval_id approval-missing" in approvals["blocked_reasons"]
    assert "run_id run-expired references unavailable approval_id approval-expired" in approvals["blocked_reasons"]

    runs = status["run_lifecycle"]
    assert runs["display_only"] is True
    assert runs["execution_enabled"] is False
    assert runs["dispatch_enabled"] is False
    assert runs["session_send_enabled"] is False
    assert runs["worker_dispatch_enabled"] is False
    assert runs["append_only_projection"] is True
    assert runs["active_mutation_lane_count"] == 2
    assert runs["one_active_mutation_lane_rule_passed"] is False
    assert set(runs["active_mutation_run_ids"]) == {"run-mutation-a", "run-mutation-b"}
    assert set(runs["stop_cancel_run_ids"]) == {"run-stopped"}
    assert "run-terminal-missing-report" in runs["terminal_runs_missing_report"]
    assert runs["terminal_runs_with_missing_linked_report_ids"] == {
        "run-terminal-stale-report": ["report-missing"]
    }
    assert runs["blocked"] is True
    assert "active mutation lane count exceeds one" in runs["blocked_reasons"]
    assert "terminal run_id run-terminal-missing-report has no linked report" in runs["blocked_reasons"]
    assert (
        "run_id run-terminal-stale-report links missing report ids: report-missing"
        in runs["blocked_reasons"]
    )

    next_safe_actions = status["next_safe_actions"]
    assert next_safe_actions["display_only"] is True
    assert next_safe_actions["trusted_for_execution"] is False
    assert next_safe_actions["would_execute"] is False
    assert next_safe_actions["execution_enabled"] is False
    assert next_safe_actions["dispatch_enabled"] is False
    assert next_safe_actions["session_send_enabled"] is False
    assert next_safe_actions["worker_dispatch_enabled"] is False
    assert next_safe_actions["stored"] is False
    assert next_safe_actions["dry_run_only"] is True
    assert next_safe_actions["blocked"] is True
    assert next_safe_actions["primary_action_id"] == next_safe_actions["actions"][0]["action_id"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_approval_lifecycle_blockers" in action_ids
    assert "review_run_lifecycle_blockers" in action_ids
    assert "review_report_lifecycle_blockers" in action_ids
    assert "approval_id approval-duplicate has multiple append-only records" in next_safe_actions["blocked_reasons"]
    assert "terminal run_id run-terminal-missing-report has no linked report" in next_safe_actions["blocked_reasons"]
    assert "run_id run-terminal-missing-report has no linked report" in next_safe_actions["blocked_reasons"]

    readiness = status["orchestration_readiness"]
    assert readiness["display_only"] is True
    assert readiness["trusted_for_execution"] is False
    assert readiness["would_execute"] is False
    assert readiness["execution_enabled"] is False
    assert readiness["dispatch_enabled"] is False
    assert readiness["session_send_enabled"] is False
    assert readiness["worker_dispatch_enabled"] is False
    assert readiness["stored"] is False
    assert readiness["dry_run_only"] is True
    assert readiness["execution_ready"] is False
    assert readiness["states"]["supervised_read_only_autonomy"] == "blocked"
    assert readiness["states"]["scoped_pr_creation"] == "blocked"
    assert readiness["states"]["laptop_codex_worker_node"] == "blocked"
    assert readiness["next_safe_action_id"] == next_safe_actions["primary_action_id"]
    assert "no laptop Codex worker-node run is recorded" in readiness["laptop_codex_worker_node"]["blocked_reasons"]
    assert "Supervised read-only autonomy is blocked:" in readiness["plain_language_summary"]
    assert "Next safe action:" in readiness["plain_language_summary"]
