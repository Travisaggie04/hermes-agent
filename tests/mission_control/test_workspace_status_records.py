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
    assert "no bypassing Codex safety checks" in instruction["forbidden_actions"]
    assert instruction["worker_safety_hardness"] == [
        "Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.",
        "A Jenny packet is not permission to bypass Codex safety checks.",
    ]
    assert "worker node offline" in instruction["blocked_reasons"]
    assert "Manual handoff only" in instruction["manual_handoff_prompt"]
    assert "Worker safety hardness:" in instruction["manual_handoff_prompt"]
    assert "Codex must independently enforce repo/worktree" in instruction["manual_handoff_prompt"]
    assert "Report contract:" in instruction["manual_handoff_prompt"]


def test_record_sourced_workspace_status_projects_worker_node_presence(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-online",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="running",
            objective="Prepare scoped engineering evidence.",
            presence_status="online",
            last_seen_at="2026-06-19T12:00:00Z",
            worker_version="codex-desktop-1.2.3",
            capability_summary="repo-local engineering worker with guarded shell and patch tools",
        )
    )

    status = build_workspace_status_from_records(
        {"now": "2026-06-19T12:05:00Z"},
        records_path=records_path,
    )

    presence = status["worker_node_presence"]
    assert presence["source"] == "mission_control_worker_node_presence_v1"
    assert presence["display_only"] is True
    assert presence["trusted_for_execution"] is False
    assert presence["would_execute"] is False
    assert presence["execution_enabled"] is False
    assert presence["dispatch_enabled"] is False
    assert presence["session_send_enabled"] is False
    assert presence["worker_dispatch_enabled"] is False
    assert presence["stored"] is False
    assert presence["dry_run_only"] is True
    assert presence["presence_state"] == "online"
    assert presence["online"] is True
    assert presence["blocked"] is False
    assert presence["blocked_reasons"] == []
    assert presence["worker_run_id"] == "worker-run-online"
    assert presence["worker_host_label"] == "laptop-codex"
    assert presence["last_seen_age_seconds"] == 300
    assert presence["stale_after_seconds"] == 900
    assert presence["worker_version"] == "codex-desktop-1.2.3"
    assert presence["capability_summary"] == "repo-local engineering worker with guarded shell and patch tools"

    readiness = status["orchestration_readiness"]["laptop_codex_worker_node"]
    assert readiness["state"] == "preview_ready"
    assert readiness["online"] is True
    assert readiness["presence_state"] == "online"
    assert readiness["execution_ready"] is False


def test_record_sourced_workspace_status_blocks_worker_node_when_presence_unknown(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-unknown",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="running",
            objective="Prepare scoped engineering evidence.",
        )
    )

    status = build_workspace_status_from_records(
        {"now": "2026-06-19T12:05:00Z"},
        records_path=records_path,
    )

    presence = status["worker_node_presence"]
    assert presence["presence_state"] == "unknown"
    assert presence["online"] is False
    assert presence["blocked"] is True
    assert "worker-node presence_status is not recorded" in presence["blocked_reasons"]

    readiness = status["orchestration_readiness"]["laptop_codex_worker_node"]
    assert readiness["state"] == "blocked"
    assert readiness["online"] is False
    assert readiness["presence_state"] == "unknown"
    assert "worker-node presence_status is not recorded" in readiness["blocked_reasons"]
    assert "worker-node presence is not confirmed online" in readiness["blocked_reasons"]

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_worker_node_presence" in action_ids


def test_record_sourced_workspace_status_projects_execution_packet_preview(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    head = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
    forbidden_actions = (
        "merge",
        "deploy",
        "restart",
        "runtime switch",
        "waha",
        "social",
        "payment",
        "model routing",
        "queue",
        "worker",
        "timer",
        "daemon",
        "dispatch",
        "session-send",
    )
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted",
            runtime_path="/runtime/current",
            head=head,
            rollback_runtime_path="/runtime/rollback",
            rollback_head=head,
            max_active_lane=1,
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-pr-1",
            project_id="project-hermes-mission-control",
            action_class="pr_creation",
            approval_scope="project-hermes-mission-control scoped PR for mission_control/workspace_status_records.py",
            status="approved",
            expires_at="2099-01-01T00:00:00Z",
            metadata={"files": ["mission_control/workspace_status_records.py"]},
        )
    )
    store.append(
        RunRecord(
            run_id="run-pr-1",
            project_id="project-hermes-mission-control",
            approval_id="approval-pr-1",
            lane_type="pr_creation",
            title="Scoped PR packet preview",
            objective="Prepare bounded worker-node packet evidence.",
            status="running",
            allowed_actions=("edit scoped files", "run focused tests"),
            forbidden_actions=forbidden_actions,
            metadata={"files": ["mission_control/workspace_status_records.py"]},
        )
    )
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-1",
            parent_run_id="run-pr-1",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="running",
            objective="Prepare bounded worker-node packet evidence.",
            allowed_actions=("edit scoped files", "run focused tests"),
            forbidden_actions=forbidden_actions,
            assigned_packet_id="packet-1",
            assigned_packet_summary="Scoped PR packet preview.",
            report_contract_status="present",
            presence_status="online",
            last_seen_at="2026-06-19T12:00:00Z",
        )
    )

    status = build_workspace_status_from_records(
        {
            "now": "2026-06-19T12:05:00Z",
            "source_control": {"accepted_live_head": head},
            "dashboard_runtime": {"path": "/runtime/current", "head": head},
            "gateway_runtime": {"path": "/runtime/current", "head": head},
            "rollback_runtime": {"path": "/runtime/rollback", "head": head},
            "tool_permissions": {"paths": [{"path_id": "manual_packet_copy", "manual_only": True}]},
        },
        records_path=records_path,
    )

    packet = status["execution_packet_preview"]
    assert packet["source"] == "mission_control_execution_packet_preview_v1"
    assert packet["display_only"] is True
    assert packet["trusted_for_execution"] is False
    assert packet["would_execute"] is False
    assert packet["would_dispatch"] is False
    assert packet["would_session_send"] is False
    assert packet["execution_enabled"] is False
    assert packet["dispatch_enabled"] is False
    assert packet["session_send_enabled"] is False
    assert packet["worker_dispatch_enabled"] is False
    assert packet["eligible"] is True
    assert packet["packet"]["mode"] == "worker_node"
    assert packet["packet"]["run_id"] == "run-pr-1"
    assert packet["packet"]["approval_id"] == "approval-pr-1"
    assert packet["packet"]["scope"]["files"] == ["mission_control/workspace_status_records.py"]
    assert packet["packet"]["worker_node_contract"]["worker_identity"] == "codex"
    assert packet["packet"]["worker_node_contract"]["worker_host_label"] == "laptop-codex"
    assert packet["packet"]["worker_node_contract"]["parent_run_id"] == "run-pr-1"
    assert packet["packet"]["worker_node_contract"]["manual_handoff_only"] is True
    assert packet["packet"]["worker_node_contract"]["worker_dispatch_enabled"] is False

    execution_mode = status["execution_mode_classification"]
    assert execution_mode["source"] == "mission_control_execution_mode_classification_v1"
    assert execution_mode["display_only"] is True
    assert execution_mode["trusted_for_execution"] is False
    assert execution_mode["would_execute"] is False
    assert execution_mode["execution_enabled"] is False
    assert execution_mode["dispatch_enabled"] is False
    assert execution_mode["session_send_enabled"] is False
    assert execution_mode["worker_dispatch_enabled"] is False
    assert execution_mode["stored"] is False
    assert execution_mode["dry_run_only"] is True
    assert execution_mode["mode_family"] == "worker_node_preview"
    assert execution_mode["preview_ready"] is True
    assert execution_mode["manual_handoff_only"] is True

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["execution_mode_family"] == "worker_node_preview"
    assert operator_packet["execution_packet_mode"] == "worker_node"
    assert operator_packet["execution_packet_eligible"] is True
    assert "Execution mode: worker_node_preview; execution disabled." in operator_packet["plain_language_summary"]
    assert "Execution packet preview: worker_node, eligible true; execution disabled." in operator_packet["plain_language_summary"]


def test_record_sourced_workspace_status_blocks_higher_risk_execution_mode(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    head = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted",
            runtime_path="/runtime/current",
            head=head,
            rollback_runtime_path="/runtime/rollback",
            rollback_head=head,
            max_active_lane=1,
        )
    )
    store.append(
        ApprovalRecord(
            approval_id="approval-deploy-1",
            project_id="project-hermes-mission-control",
            action_class="deploy",
            approval_scope="deploy Hermes runtime",
            status="approved",
            expires_at="2099-01-01T00:00:00Z",
        )
    )
    store.append(
        RunRecord(
            run_id="run-deploy-1",
            project_id="project-hermes-mission-control",
            approval_id="approval-deploy-1",
            lane_type="deploy",
            title="Deploy runtime",
            status="running",
            execution_mode="deploy",
        )
    )

    status = build_workspace_status_from_records(
        {
            "now": "2026-06-19T12:05:00Z",
            "source_control": {"accepted_live_head": head},
            "dashboard_runtime": {"path": "/runtime/current", "head": head},
            "gateway_runtime": {"path": "/runtime/current", "head": head},
            "rollback_runtime": {"path": "/runtime/rollback", "head": head},
        },
        records_path=records_path,
    )

    execution_mode = status["execution_mode_classification"]
    assert execution_mode["mode_family"] == "higher_risk_blocked"
    assert execution_mode["preview_ready"] is False
    assert execution_mode["blocked"] is True
    assert "deploy" in execution_mode["protected_action_markers"]
    assert execution_mode["would_execute"] is False
    assert execution_mode["execution_enabled"] is False
    assert execution_mode["dispatch_enabled"] is False
    assert execution_mode["session_send_enabled"] is False
    assert execution_mode["worker_dispatch_enabled"] is False
    assert "action_class deploy is not eligible for autonomous execution" in execution_mode["blocked_reasons"]

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_execution_mode_classification" in action_ids
    assert "action_class deploy is not eligible for autonomous execution" in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["execution_mode_family"] == "higher_risk_blocked"
    assert "action_class deploy is not eligible for autonomous execution" in operator_packet["execution_mode_blocked_reasons"]
    assert "Execution mode: higher_risk_blocked; execution disabled." in operator_packet["plain_language_summary"]


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

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["source"] == "mission_control_operator_decision_packet_v1"
    assert operator_packet["display_only"] is True
    assert operator_packet["trusted_for_execution"] is False
    assert operator_packet["would_execute"] is False
    assert operator_packet["execution_enabled"] is False
    assert operator_packet["dispatch_enabled"] is False
    assert operator_packet["session_send_enabled"] is False
    assert operator_packet["worker_dispatch_enabled"] is False
    assert operator_packet["stored"] is False
    assert operator_packet["dry_run_only"] is True
    assert operator_packet["manual_operator_review_only"] is True
    assert operator_packet["execution_ready"] is False
    assert operator_packet["approval_required"] is True
    assert operator_packet["jenny_review_required"] is True
    assert operator_packet["state"] == "report_review_required"
    assert operator_packet["report_review_queue_count"] == 3
    assert operator_packet["top_report_review_item_id"] == "report:report-worker"
    assert operator_packet["top_report_review_label"] == "Laptop Codex reported scoped PR evidence."
    assert operator_packet["recommended_operator_instruction"] == (
        "Jenny reviews Laptop Codex reported scoped PR evidence. before issuing another worker instruction."
    )
    assert "Approval required: yes." in operator_packet["plain_language_summary"]
    assert "Top report review: Laptop Codex reported scoped PR evidence." in operator_packet["plain_language_summary"]
    assert "worker activation" in operator_packet["plain_language_summary"]
    assert "report_id report-worker still needs Jenny review" in operator_packet["blocked_reasons"]

    worker_instruction = status["worker_node_instruction_preview"]
    assert worker_instruction["blocked"] is True
    assert worker_instruction["worker_dispatch_enabled"] is False
    assert worker_instruction["report_id"] == "report-worker"
    assert worker_instruction["report_review_status"] == "needs_review"
    assert "report_id report-worker still needs Jenny review" in worker_instruction["blocked_reasons"]


def test_record_sourced_workspace_status_projects_result_ingestion_contract(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-complete",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="completed",
            objective="Prepare scoped PR evidence.",
            report_id="report-ready",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-ready",
            run_id="worker-run-complete",
            project_id="project-hermes-mission-control",
            status="reviewed",
            summary="Worker report is linked and redacted.",
            result="Prepared the bounded projection.",
            risks=("focused checks only",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Jenny review.",
            evidence_refs=("pytest output",),
            submitted_by="codex",
            submitted_from="laptop-codex",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )
    store.append(
        ReportRecord(
            report_id="report-unsafe",
            run_id="missing-run",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Older unsafe report record.",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-unsafe",
            run_id="",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Unsafe unlinked report.",
            redaction_status="raw",
            metadata={"raw_log": "forbidden", "token": "placeholder-token"},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    ingestion = status["result_ingestion_contract"]
    assert ingestion["source"] == "mission_control_result_ingestion_contract_v1"
    assert ingestion["display_only"] is True
    assert ingestion["trusted_for_execution"] is False
    assert ingestion["would_execute"] is False
    assert ingestion["execution_enabled"] is False
    assert ingestion["dispatch_enabled"] is False
    assert ingestion["session_send_enabled"] is False
    assert ingestion["worker_dispatch_enabled"] is False
    assert ingestion["stored"] is False
    assert ingestion["dry_run_only"] is True
    assert ingestion["manual_review_only"] is True
    assert ingestion["raw_report_count"] == 3
    assert ingestion["report_count"] == 2
    assert ingestion["ingestion_ready_count"] == 1
    assert ingestion["blocked_report_count"] == 1
    assert ingestion["duplicate_report_count"] == 1
    assert ingestion["missing_link_count"] == 1
    assert ingestion["unsafe_redaction_count"] == 1
    assert ingestion["forbidden_metadata_count"] == 1
    assert ingestion["missing_safety_confirmation_count"] == 1
    assert ingestion["blocked"] is True
    assert "report_id report-unsafe has multiple append-only records" in ingestion["blocked_reasons"]
    assert "report_id report-unsafe is not linked to a run, child, or worker record" in ingestion["blocked_reasons"]
    assert "report_id report-unsafe redaction_status raw is not accepted" in ingestion["blocked_reasons"]
    assert "report_id report-unsafe metadata contains forbidden keys: raw_log, token" in ingestion["blocked_reasons"]
    assert "report_id report-unsafe is missing safety confirmation for ingestion" in ingestion["blocked_reasons"]

    items = {item["report_id"]: item for item in ingestion["items"]}
    assert items["report-ready"]["ingestion_ready"] is True
    assert items["report-ready"]["linked_record_type"] == "worker_node_run"
    assert items["report-ready"]["safety_confirmation_present"] is True
    assert items["report-unsafe"]["ingestion_ready"] is False
    assert items["report-unsafe"]["forbidden_metadata_keys"] == ["raw_log", "token"]
    assert "placeholder-token" not in str(ingestion)

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_result_ingestion_contract" in action_ids
    assert "report_id report-unsafe metadata contains forbidden keys: raw_log, token" in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["result_ingestion_blocked_count"] == 1
    assert "report_id report-unsafe redaction_status raw is not accepted" in operator_packet["result_ingestion_blocked_reasons"]
    assert "Result ingestion: 1 ready, 1 blocked." in operator_packet["plain_language_summary"]


def test_record_sourced_workspace_status_projects_report_contract_compliance(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="completed",
            objective="Prepare scoped PR evidence.",
            report_id="report-complete",
        )
    )
    store.append(
        ChildRunRecord(
            child_run_id="child-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="completed",
            objective="Inspect bounded evidence.",
            report_id="report-incomplete",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-complete",
            run_id="worker-run-1",
            project_id="project-hermes-mission-control",
            status="reviewed",
            summary="Worker completed scoped PR evidence.",
            result="Changed one bounded status projection and verified tests.",
            risks=("focused coverage only",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Jenny review and PR check wait.",
            evidence_refs=("pytest output",),
            submitted_by="codex",
            submitted_from="laptop-codex",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, or secrets."},
        )
    )
    store.append(
        ReportRecord(
            report_id="report-incomplete",
            run_id="child-run-1",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Child found a possible gap.",
            blockers=("needs tests",),
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    compliance = status["report_contract_compliance"]
    assert compliance["source"] == "mission_control_report_contract_compliance_v1"
    assert compliance["display_only"] is True
    assert compliance["trusted_for_execution"] is False
    assert compliance["would_execute"] is False
    assert compliance["execution_enabled"] is False
    assert compliance["dispatch_enabled"] is False
    assert compliance["session_send_enabled"] is False
    assert compliance["worker_dispatch_enabled"] is False
    assert compliance["stored"] is False
    assert compliance["dry_run_only"] is True
    assert compliance["manual_review_only"] is True
    assert compliance["report_count"] == 2
    assert compliance["complete_report_count"] == 1
    assert compliance["incomplete_report_count"] == 1
    assert compliance["blocked"] is True
    assert compliance["primary_item_id"] == "report-contract:report-incomplete"
    incomplete = {item["report_id"]: item for item in compliance["items"]}["report-incomplete"]
    assert incomplete["linked_record_type"] == "child_run"
    assert incomplete["linked_record_id"] == "child-run-1"
    assert incomplete["missing_fields"] == ["result", "evidence", "tests", "next lane", "safety confirmation"]
    assert "report_id report-incomplete missing contract fields: result, evidence, tests, next lane, safety confirmation" in compliance["blocked_reasons"]

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_report_contract_compliance" in action_ids

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["report_contract_incomplete_count"] == 1
    assert operator_packet["report_contract_primary_item_id"] == "report-contract:report-incomplete"
    assert "Report contract completeness: 1 complete, 1 incomplete." in operator_packet["plain_language_summary"]


def test_record_sourced_workspace_status_projects_report_completion_path(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        RunRecord(
            run_id="run-ready",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Ready terminal run",
            status="completed",
            report_ids=("report-ready",),
        )
    )
    store.append(
        ChildRunRecord(
            child_run_id="child-needs-review",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="completed",
            objective="Inspect bounded evidence.",
            report_id="report-needs-review",
        )
    )
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-missing",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="completed",
            objective="Prepare missing report evidence.",
        )
    )
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-rejected",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="completed",
            objective="Prepare rejected report evidence.",
            report_id="report-rejected",
        )
    )
    store.append(
        RunRecord(
            run_id="run-reviewed-only",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Reviewed but not accepted terminal run",
            status="completed",
            report_ids=("report-reviewed-only",),
        )
    )
    store.append(
        ReportRecord(
            report_id="report-ready",
            run_id="run-ready",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Ready report.",
            result="Finished the bounded review.",
            risks=("none beyond focused evidence",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Jenny can close this item.",
            evidence_refs=("pytest output",),
            reviewed_at="2026-06-19T10:00:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )
    store.append(
        ReportRecord(
            report_id="report-reviewed-only",
            run_id="run-reviewed-only",
            project_id="project-hermes-mission-control",
            status="reviewed",
            summary="Reviewed report that still needs explicit acceptance.",
            result="Finished the bounded review.",
            risks=("none beyond focused evidence",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Jenny can decide whether to accept this item.",
            evidence_refs=("pytest output",),
            reviewed_at="2026-06-19T10:30:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )
    store.append(
        ReportRecord(
            report_id="report-needs-review",
            run_id="child-needs-review",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Child report still needs Jenny review.",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-rejected",
            run_id="worker-rejected",
            project_id="project-hermes-mission-control",
            status="rejected",
            summary="Rejected worker report.",
            result="The evidence was not sufficient.",
            risks=("needs rework",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Ask for a corrected report.",
            evidence_refs=("pytest output",),
            reviewed_at="2026-06-19T11:00:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    completion = status["report_completion_path"]
    assert completion["source"] == "mission_control_report_completion_path_v1"
    assert completion["display_only"] is True
    assert completion["trusted_for_execution"] is False
    assert completion["would_execute"] is False
    assert completion["execution_enabled"] is False
    assert completion["dispatch_enabled"] is False
    assert completion["session_send_enabled"] is False
    assert completion["worker_dispatch_enabled"] is False
    assert completion["stored"] is False
    assert completion["dry_run_only"] is True
    assert completion["manual_review_only"] is True
    assert completion["terminal_item_count"] == 5
    assert completion["completion_ready_count"] == 1
    assert completion["blocked_completion_count"] == 4
    assert completion["missing_report_count"] == 1
    assert completion["needs_review_count"] == 1
    assert completion["rejected_report_count"] == 1
    assert completion["contract_incomplete_count"] == 2
    assert completion["ingestion_blocked_count"] == 1
    assert completion["duplicate_report_count"] == 0
    assert completion["blocked"] is True
    assert "worker_node_run worker-missing has no linked completion report" in completion["blocked_reasons"]
    assert "report_id report-needs-review still needs Jenny review before completion" in completion["blocked_reasons"]
    assert "report_id report-needs-review missing completion contract fields: result, risks/blockers, evidence, tests, next lane, safety confirmation" in completion["blocked_reasons"]
    assert "report_id report-rejected completion report is rejected" in completion["blocked_reasons"]
    assert "report_id report-reviewed-only completion report is reviewed but not accepted" in completion["blocked_reasons"]

    items = {item["item_id"]: item for item in completion["items"]}
    assert items["report-completion:run:run-ready"]["completion_ready"] is True
    assert items["report-completion:run:run-ready"]["report_review_status"] == "accepted"
    assert items["report-completion:run:run-reviewed-only"]["completion_ready"] is False
    assert items["report-completion:run:run-reviewed-only"]["report_review_status"] == "reviewed"
    assert items["report-completion:run:run-reviewed-only"]["report_contract_complete"] is True
    assert items["report-completion:run:run-reviewed-only"]["result_ingestion_ready"] is True
    assert items["report-completion:child_run:child-needs-review"]["completion_ready"] is False
    assert items["report-completion:child_run:child-needs-review"]["result_ingestion_ready"] is False
    assert items["report-completion:worker_node_run:worker-missing"]["report_link_status"] == "missing_linked_report"
    assert items["report-completion:worker_node_run:worker-rejected"]["report_review_status"] == "rejected"

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_report_completion_path" in action_ids
    assert "report_id report-rejected completion report is rejected" in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["report_completion_blocked_count"] == 4
    assert "worker_node_run worker-missing has no linked completion report" in operator_packet["report_completion_blocked_reasons"]
    assert "report_id report-reviewed-only completion report is reviewed but not accepted" in operator_packet["report_completion_blocked_reasons"]
    assert "Report completion path: 1 ready, 4 blocked." in operator_packet["plain_language_summary"]
    assert operator_packet["jenny_review_required"] is True


def test_record_sourced_workspace_status_projects_stop_cancel_control(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        RunRecord(
            run_id="run-stopping",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Stopping run",
            status="stopping",
        )
    )
    store.append(
        ChildRunRecord(
            child_run_id="child-stopped",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="stopped",
            objective="Stop child safely.",
            stopped_at="2026-06-19T12:05:00Z",
            stop_reason="Operator stopped after evidence was enough.",
            report_id="report-child-stop",
        )
    )
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-cancelled",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="cancelled",
            objective="Prepare scoped PR evidence.",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-child-stop",
            run_id="child-stopped",
            project_id="project-hermes-mission-control",
            status="received",
            summary="Child stopped after reporting enough evidence.",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    stop_control = status["orchestration_stop_control"]
    assert stop_control["source"] == "mission_control_orchestration_stop_control_v1"
    assert stop_control["display_only"] is True
    assert stop_control["trusted_for_execution"] is False
    assert stop_control["would_execute"] is False
    assert stop_control["execution_enabled"] is False
    assert stop_control["dispatch_enabled"] is False
    assert stop_control["session_send_enabled"] is False
    assert stop_control["worker_dispatch_enabled"] is False
    assert stop_control["stored"] is False
    assert stop_control["dry_run_only"] is True
    assert stop_control["manual_review_only"] is True
    assert stop_control["stop_cancel_count"] == 3
    assert stop_control["active_stop_count"] == 1
    assert stop_control["terminal_stop_count"] == 2
    assert stop_control["needs_report_count"] == 2
    assert stop_control["needs_review_count"] == 1
    assert stop_control["blocked"] is True
    assert "run run-stopping is stopping and needs manual stop confirmation" in stop_control["blocked_reasons"]
    assert "run run-stopping has no linked stop/cancel report" in stop_control["blocked_reasons"]
    assert "report_id report-child-stop still needs Jenny review" in stop_control["blocked_reasons"]
    assert "worker_node_run worker-cancelled has no stop_reason" in stop_control["blocked_reasons"]
    assert "worker_node_run worker-cancelled has no linked stop/cancel report" in stop_control["blocked_reasons"]

    items = {item["item_id"]: item for item in stop_control["items"]}
    assert items["child_run:child-stopped"]["report_link_status"] == "linked_report_found"
    assert items["child_run:child-stopped"]["report_review_status"] == "needs_review"
    assert items["worker_node_run:worker-cancelled"]["report_link_status"] == "missing_linked_report"

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_stop_cancel_control" in action_ids
    assert "worker_node_run worker-cancelled has no stop_reason" in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["stop_cancel_count"] == 3
    assert "worker_node_run worker-cancelled has no stop_reason" in operator_packet["stop_cancel_blocked_reasons"]
    assert "Stop/cancel control: 3 items, blocked true." in operator_packet["plain_language_summary"]
    assert operator_packet["jenny_review_required"] is True


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
