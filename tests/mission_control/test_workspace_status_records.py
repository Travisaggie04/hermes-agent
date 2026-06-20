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
from mission_control.workspace_status import build_workspace_status
from mission_control.workspace_status_records import (
    _child_agent_instruction_preview,
    _operator_decision_packet_payload,
    _orchestration_readiness_payload,
    _worker_node_instruction_preview,
    build_workspace_status_from_records,
    decorate_workspace_status_operator_projections,
    hard_boundary_contract_payload,
)


HEAD = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
OLD_HEAD = "fe18ce20d6044dd91d115286e949366477a8706b"


def _assert_inert_projection(payload: dict[str, object]) -> None:
    assert payload["display_only"] is True
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["would_execute"] is False
    assert payload["would_dispatch"] is False
    assert payload["would_session_send"] is False
    assert payload["execution_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["worker_dispatch_enabled"] is False
    assert payload["stored"] is False
    assert payload["dry_run_only"] is True


def _runtime(path: str, head: str = HEAD, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "path": path,
        "exists": True,
        "git_healthy": True,
        "head": head,
        "status_short": ["## HEAD (no branch)"],
        "dirty_files": [],
        "untracked_files": [],
        "error": "",
    }
    payload.update(overrides)
    return payload


def _reconciled_baseline_record(**overrides: object) -> AcceptedBaselineRecord:
    payload: dict[str, object] = {
        "baseline_id": "accepted-current",
        "runtime_path": "/runtime/accepted",
        "head": HEAD,
        "rollback_runtime_path": "/runtime/rollback",
        "rollback_head": HEAD,
        "dispatch_in_gateway": False,
        "active_kanban": 0,
        "max_active_lane": 1,
        "source_runtime": {"head": HEAD, "default_branch_head": HEAD},
        "dashboard_runtime": _runtime("/runtime/dashboard", HEAD),
        "gateway_runtime": _runtime("/runtime/gateway", HEAD),
        "rollback_runtime": _runtime("/runtime/rollback", HEAD),
    }
    payload.update(overrides)
    return AcceptedBaselineRecord(**payload)


def _assert_execution_disabled(payload: dict[str, object]) -> None:
    for key in (
        "would_execute",
        "execution_enabled",
        "dispatch_enabled",
        "session_send_enabled",
        "worker_dispatch_enabled",
    ):
        if key in payload:
            assert payload[key] is False


def _forbidden_actions() -> tuple[str, ...]:
    return (
        "file write",
        "patch",
        "shell",
        "commit",
        "PR creation",
        "merge",
        "deploy",
        "restart",
        "runtime switch",
        "Waha",
        "social",
        "payment",
        "model routing",
        "queue mutation",
        "worker dispatch",
        "timer",
        "daemon",
        "dispatch",
        "session-send",
    )


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
    assert status["tool_permission_classification"]["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert "accepted_baseline_source_missing" not in status["stale_context"]["warnings"]
    _assert_inert_projection(status["control_plane_lifecycle"])
    hard_boundary = status["hard_boundary_contract"]
    _assert_inert_projection(hard_boundary)
    assert hard_boundary["source"] == "mission_control_hard_boundary_contract_v1"
    assert hard_boundary["state"] == "separate_approval_required"
    assert hard_boundary["blocked"] is False
    assert hard_boundary["separate_approval_required"] is True
    assert hard_boundary["live_operations_goal"] is False
    assert hard_boundary["live_operations_enabled"] is False
    assert hard_boundary["execution_ready"] is False
    assert "live deploy" in hard_boundary["forbidden_actions"]
    assert "9121 /api/status gate" in hard_boundary["forbidden_actions"]
    assert "PR merge" in hard_boundary["separate_approval_actions"]


def test_record_sourced_workspace_status_projects_reconciled_runtime_facts(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(_reconciled_baseline_record())

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["accepted_baseline_source"] == "record"
    assert status["runtime_provenance"]["primary_status"] == "CLEAN_AND_ALIGNED"
    assert status["runtime_provenance"]["autonomy_blocked"] is False
    assert "MISSING_RUNTIME_PATH" not in status["runtime_provenance"]["statuses"]
    assert "MISSING_RUNTIME_PATH" not in status["stale_context"]["warnings"]
    assert "UNRECORDED_RUNTIME" not in status["runtime_provenance"]["statuses"]
    assert status["dashboard_runtime"]["state"] == "clean"
    assert status["dashboard_runtime"]["path"] == "/runtime/dashboard"
    assert status["gateway_runtime"]["state"] == "clean"
    assert status["gateway_runtime"]["path"] == "/runtime/gateway"
    assert status["source_runtime"]["state"] == "recorded"
    assert status["read_only_autonomy_eligibility"]["eligible"] is False
    for projection in (
        status,
        status["runtime_provenance"],
        status["read_only_autonomy_eligibility"],
        status["scoped_pr_lane_eligibility"],
        status["execution_packet_preview"],
    ):
        _assert_execution_disabled(projection)


def test_record_sourced_workspace_status_treats_previous_rollback_as_available(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        _reconciled_baseline_record(
            rollback_head=OLD_HEAD,
            rollback_runtime=_runtime("/runtime/rollback", OLD_HEAD),
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)
    provenance = status["runtime_provenance"]

    assert provenance["primary_status"] == "CLEAN_AND_ALIGNED"
    assert provenance["autonomy_blocked"] is False
    assert provenance["statuses"] == ["CLEAN_AND_ALIGNED"]
    assert "ROLLBACK_STALE" not in provenance["statuses"]
    assert "ROLLBACK_AVAILABLE_PREVIOUS_VERSION" in provenance["informational_statuses"]
    assert status["rollback_runtime"]["availability"] == "previous_version"
    assert status["rollback_runtime"]["state"] == "clean"
    assert "ROLLBACK_STALE" not in status["stale_context"]["warnings"]
    assert "rollback runtime is stale relative to source HEAD" not in status["stale_context"]["warnings"]
    _assert_execution_disabled(provenance)
    _assert_execution_disabled(status["read_only_autonomy_eligibility"])


def test_record_sourced_read_only_preview_records_make_supervised_preview_ready(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    approval_id = "approval-read-only-preview"
    run_id = "run-read-only-preview"
    report_id = "report-read-only-preview-contract"
    store.append(_reconciled_baseline_record())
    store.append(
        ApprovalRecord(
            approval_id=approval_id,
            project_id="project-hermes-mission-control",
            run_id=run_id,
            action_class="read_only_inspection",
            approval_scope=f"project-hermes-mission-control:supervised-read-only-preview:{HEAD}",
            approved_actions=("render supervised read-only preview packet",),
            forbidden_actions=_forbidden_actions(),
            status="approved",
            approval_mode="one_time",
            approved_by="operator",
            approval_source="manual",
            approved_at="2026-06-19T00:00:00Z",
            expires_at="2099-01-01T00:00:00Z",
            baseline_runtime_path="/runtime/accepted",
            baseline_head=HEAD,
        )
    )
    store.append(
        RunRecord(
            run_id=run_id,
            project_id="project-hermes-mission-control",
            approval_id=approval_id,
            lane_type="read_only_inspection",
            title="Supervised read-only preview readiness",
            objective="Build an inert preview-readiness packet without executing Jenny.",
            status="requested",
            execution_mode="manual_copy",
            allowed_actions=("render supervised read-only preview packet",),
            forbidden_actions=_forbidden_actions(),
            baseline_runtime_path="/runtime/accepted",
            baseline_head=HEAD,
            runtime_guard_state="CLEAN_AND_ALIGNED",
            dispatch_state=False,
            safety_gate_status="preview_ready",
            report_ids=(report_id,),
            metadata={
                "would_execute": False,
                "execution_enabled": False,
                "dispatch_enabled": False,
                "session_send_enabled": False,
                "worker_dispatch_enabled": False,
            },
        )
    )
    store.append(
        ReportRecord(
            report_id=report_id,
            run_id=run_id,
            approval_id=approval_id,
            project_id="project-hermes-mission-control",
            status="reviewed",
            report_kind="read_only_preview_contract",
            summary="Preview readiness contract is present for supervised read-only autonomy.",
            result="Readiness contract only; no Jenny execution occurred.",
            risks=("Execution remains disabled and a later explicit lane is required before any run.",),
            tests=("record-sourced workspace status preview-readiness projection",),
            next_recommended_lane="Stop before execution and request explicit approval for any Jenny run.",
            evidence_refs=("accepted baseline accepted-current", f"runtime head {HEAD}"),
            submitted_by="operator",
            submitted_from="manual-record-only-preview",
            reviewed_at="2026-06-19T00:01:00Z",
            reviewed_by="operator",
            metadata={
                "safety_confirmation": "No Jenny execution, dispatch, session-send, worker dispatch, or mutation occurred.",
                "no_jenny_execution": True,
                "would_execute": False,
                "execution_enabled": False,
                "dispatch_enabled": False,
                "session_send_enabled": False,
                "worker_dispatch_enabled": False,
            },
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["runtime_provenance"]["primary_status"] == "CLEAN_AND_ALIGNED"
    assert status["tool_permission_classification"]["permission_classification"] == "read_only_safe"
    assert status["tool_permission_classification"]["read_only_safe"] is True
    assert status["read_only_preview_report_contract"]["ready"] is True
    read_only = status["read_only_autonomy_eligibility"]
    assert read_only["eligible"] is True
    assert read_only["execution_ready"] is False
    assert read_only["bridge_permissions"]["permission_classification"] == "manual_only"
    assert read_only["tool_permissions"]["permission_classification"] == "read_only_safe"
    assert "bridge path is manual-only; preview must not execute" in read_only["warnings"]
    readiness = status["orchestration_readiness"]
    assert readiness["states"]["supervised_read_only_autonomy"] == "preview_ready"
    assert readiness["supervised_read_only_autonomy"]["execution_ready"] is False
    assert readiness["states"]["scoped_pr_creation"] == "blocked"
    assert readiness["states"]["laptop_codex_worker_node"] == "blocked"
    assert status["scoped_pr_lane_eligibility"]["eligible"] is False
    packet = status["execution_packet_preview"]
    assert packet["eligible"] is True
    assert packet["blocked_reasons"] == []
    assert packet["packet"]["mode"] == "read_only"
    assert packet["packet"]["run_id"] == run_id
    assert packet["packet"]["approval_id"] == approval_id
    assert packet["packet"]["would_execute"] is False
    assert packet["trusted_for_execution"] is False
    assert "bridge path is manual-only; preview must not execute" in packet["warnings"]
    for projection in (
        status,
        status["read_only_autonomy_eligibility"],
        status["tool_permission_classification"],
        status["execution_packet_preview"],
        status["read_only_preview_report_contract"],
    ):
        _assert_execution_disabled(projection)


def test_record_sourced_read_only_preview_requires_explicit_report_contract(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    approval_id = "approval-read-only-preview"
    store.append(_reconciled_baseline_record())
    store.append(
        ApprovalRecord(
            approval_id=approval_id,
            project_id="project-hermes-mission-control",
            action_class="read_only_inspection",
            approval_scope=f"project-hermes-mission-control:supervised-read-only-preview:{HEAD}",
            approved_actions=("render supervised read-only preview packet",),
            forbidden_actions=_forbidden_actions(),
            status="approved",
            approval_mode="one_time",
            expires_at="2099-01-01T00:00:00Z",
            baseline_runtime_path="/runtime/accepted",
            baseline_head=HEAD,
        )
    )
    store.append(
        RunRecord(
            run_id="run-read-only-preview",
            project_id="project-hermes-mission-control",
            approval_id=approval_id,
            lane_type="read_only_inspection",
            status="requested",
            execution_mode="manual_copy",
            allowed_actions=("render supervised read-only preview packet",),
            forbidden_actions=_forbidden_actions(),
            baseline_runtime_path="/runtime/accepted",
            baseline_head=HEAD,
            dispatch_state=False,
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert status["tool_permission_classification"]["permission_classification"] == "read_only_safe"
    assert status["read_only_preview_report_contract"]["ready"] is False
    assert "preview readiness ReportRecord is required" in status["read_only_preview_report_contract"]["blocked_reasons"]
    read_only = status["read_only_autonomy_eligibility"]
    assert read_only["eligible"] is False
    assert "report inbox must be ready" in read_only["blocked_reasons"]
    assert read_only["tool_permissions"]["permission_classification"] == "read_only_safe"
    packet = status["execution_packet_preview"]
    assert packet["eligible"] is False
    assert "report inbox must be ready" in packet["blocked_reasons"]
    assert "bridge path is not read-only safe" not in packet["blocked_reasons"]
    assert "bridge: bridge safety is not proven; defaulting to blocked" not in packet["blocked_reasons"]
    assert status["orchestration_readiness"]["states"]["supervised_read_only_autonomy"] == "blocked"
    _assert_execution_disabled(read_only)
    _assert_execution_disabled(packet)


def test_legacy_baseline_without_service_runtime_facts_is_unrecorded(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted-legacy",
            runtime_path="/runtime/accepted",
            head=HEAD,
            rollback_runtime_path="/runtime/rollback",
            rollback_head=HEAD,
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    warnings = set(status["stale_context"]["warnings"])
    assert "UNRECORDED_RUNTIME" in warnings
    assert "MISSING_RUNTIME_PATH" not in warnings
    assert "UNRECORDED_RUNTIME" in status["runtime_provenance"]["statuses"]
    assert "MISSING_RUNTIME_PATH" not in status["runtime_provenance"]["statuses"]
    assert status["dashboard_runtime"]["state"] == "unrecorded"
    assert status["dashboard_runtime"]["unrecorded"] is True
    assert status["gateway_runtime"]["state"] == "unrecorded"
    assert status["gateway_runtime"]["unrecorded"] is True
    assert status["runtime_provenance"]["autonomy_blocked"] is True


def test_record_sourced_status_missing_accepted_runtime_path_still_blocks(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(_reconciled_baseline_record(runtime_path=""))

    status = build_workspace_status_from_records(records_path=records_path)

    assert "MISSING_RUNTIME_PATH" in status["runtime_provenance"]["statuses"]
    assert "MISSING_RUNTIME_PATH" in status["stale_context"]["warnings"]
    assert (
        "accepted_baseline runtime path is missing or absent"
        in status["runtime_provenance"]["autonomy_blocked_reasons"]
    )
    assert status["runtime_provenance"]["runtimes"]["accepted_baseline"]["state"] == "missing"


def test_record_sourced_status_broken_gateway_metadata_blocks(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        _reconciled_baseline_record(
            gateway_runtime=_runtime(
                "/runtime/gateway",
                HEAD,
                git_healthy=False,
                error="fatal: not a git repository: /runtime/gateway",
            )
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert "BROKEN_GIT_METADATA" in status["runtime_provenance"]["statuses"]
    assert "GATEWAY_UNTRUSTED" in status["runtime_provenance"]["statuses"]
    assert "gateway git metadata is broken" in status["runtime_provenance"]["autonomy_blocked_reasons"]
    assert status["gateway_runtime"]["state"] == "broken_git_metadata"


def test_record_sourced_status_dirty_dashboard_runtime_blocks(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        _reconciled_baseline_record(
            dashboard_runtime=_runtime(
                "/runtime/dashboard",
                HEAD,
                status_short=["## HEAD (no branch)", " M package-lock.json"],
                dirty_files=[" M package-lock.json"],
            )
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    assert "DIRTY_RUNTIME" in status["runtime_provenance"]["statuses"]
    assert "dashboard runtime has dirty or untracked files" in status["runtime_provenance"]["autonomy_blocked_reasons"]
    assert status["dashboard_runtime"]["state"] == "dirty"
    assert status["dashboard_runtime"]["dirty"] is True


def test_hard_boundary_contract_blocks_truthy_live_flags():
    hard_boundary = hard_boundary_contract_payload(
        {
            "read_only_autonomy_eligibility": {
                "send_to_jenny_enabled": "yes",
            },
            "execution_packet_preview": {
                "would_dispatch": "true",
                "packet": {
                    "session_send_enabled": "yes",
                    "worker_node_contract": {
                        "would_session_send": "on",
                        "worker_dispatch_enabled": 1,
                    },
                },
            },
            "worker_node_presence": {"execution_enabled": "enabled"},
        }
    )

    _assert_inert_projection(hard_boundary)
    assert hard_boundary["state"] == "live_flag_violation"
    assert hard_boundary["blocked"] is True
    assert hard_boundary["live_flag_violations"] == [
        "read-only eligibility send_to_jenny_enabled must remain disabled",
        "execution packet would_dispatch must remain disabled",
        "execution packet body session_send_enabled must remain disabled",
        "worker contract would_session_send must remain disabled",
        "worker contract worker_dispatch_enabled must remain disabled",
        "worker presence execution_enabled must remain disabled",
    ]
    assert hard_boundary["blocked_reasons"] == hard_boundary["live_flag_violations"]
    assert hard_boundary["live_flag_violation_count"] == 6
    assert "Hard boundary violation" in hard_boundary["plain_language_summary"]


def test_hard_boundary_contract_blocks_sanitized_live_flag_reasons():
    hard_boundary = hard_boundary_contract_payload(
        {
            "execution_packet_preview": {
                "would_dispatch": False,
                "worker_dispatch_enabled": False,
                "blocked_reasons": [
                    "would_dispatch must remain false in previews",
                    "send_to_jenny_enabled must remain false",
                    "worker dispatch must stay disabled",
                ],
            }
        }
    )

    _assert_inert_projection(hard_boundary)
    assert hard_boundary["state"] == "live_flag_violation"
    assert hard_boundary["blocked"] is True
    assert hard_boundary["live_flag_violations"] == [
        "execution packet would_dispatch must remain disabled",
        "execution packet send_to_jenny_enabled must remain disabled",
        "execution packet worker_dispatch_enabled must remain disabled",
    ]
    assert hard_boundary["blocked_reasons"] == hard_boundary["live_flag_violations"]


def test_hard_boundary_contract_blocks_live_safety_flags():
    status = decorate_workspace_status_operator_projections(
        build_workspace_status(
            {
                "accepted_baseline": {
                    "runtime_path": "/runtime/accepted",
                    "head": "8ef64e370a51bc19e97fec1526f5bb3d42025a09",
                },
                "rollback_baseline": {
                    "runtime_path": "/runtime/rollback",
                    "head": "8ef64e370a51bc19e97fec1526f5bb3d42025a09",
                },
                "lane": {
                    "declared_baseline_head": "8ef64e370a51bc19e97fec1526f5bb3d42025a09",
                    "max_active_lane": 1,
                    "active_lane_count": 0,
                },
                "safety": {
                    "workers_enabled": "yes",
                    "worker_enabled": "true",
                    "timer_enabled": 1,
                    "daemon_enabled": "enabled",
                    "waha_enabled": "on",
                    "social_enabled": "y",
                    "payment_enabled": True,
                    "queue_mutation_enabled": "1",
                    "model_routing_enabled": "yes",
                },
            }
        )
    )

    hard_boundary = status["hard_boundary_contract"]
    _assert_inert_projection(hard_boundary)
    assert hard_boundary["state"] == "live_flag_violation"
    assert hard_boundary["blocked"] is True
    assert hard_boundary["live_flag_violations"] == [
        "safety worker_enabled must remain disabled",
        "safety workers_enabled must remain disabled",
        "safety timer_enabled must remain disabled",
        "safety daemon_enabled must remain disabled",
        "safety waha_enabled must remain disabled",
        "safety social_enabled must remain disabled",
        "safety payment_enabled must remain disabled",
        "safety queue_mutation_enabled must remain disabled",
        "safety model_routing_enabled must remain disabled",
    ]
    assert hard_boundary["blocked_reasons"] == hard_boundary["live_flag_violations"]
    assert hard_boundary["live_flag_violation_count"] == 9
    readiness = status["orchestration_readiness"]
    assert readiness["blocked"] is True
    assert readiness["states"]["supervised_read_only_autonomy"] == "blocked"
    assert readiness["states"]["scoped_pr_creation"] == "blocked"
    assert readiness["states"]["laptop_codex_worker_node"] == "blocked"
    assert "safety workers_enabled must remain disabled" in readiness["blocked_reasons"]
    operator_packet = status["operator_decision_packet"]
    assert operator_packet["state"] == "blocked"
    assert operator_packet["jenny_review_required"] is True
    assert "safety model_routing_enabled must remain disabled" in operator_packet["execution_lock_blocked_reasons"]


def test_operator_projection_decorator_adds_preview_rollups_to_pure_status():
    status = decorate_workspace_status_operator_projections(
        build_workspace_status(
            {
                "execution_packet_preview": {
                    "mode": "worker_node",
                    "would_dispatch": "true",
                    "worker_dispatch_enabled": "true",
                    "worker_node": {
                        "worker_dispatch_enabled": "true",
                        "presence_status": "online",
                        "objective": "Inspect Mission Control report status.",
                        "parent_run_id": "run-worker-preview",
                    },
                    "run": {
                        "run_id": "run-worker-preview",
                        "lane_type": "read_only_lane",
                        "objective": "Inspect Mission Control report status.",
                    },
                    "lane": {
                        "lane_type": "read_only_lane",
                        "objective": "Inspect Mission Control report status.",
                    },
                    "report_contract": {
                        "required": True,
                        "tests_required": True,
                        "review_required": True,
                    },
                },
                "autonomy_eligibility": {
                    "bridge": {
                        "send_to_jenny_enabled": "yes",
                    },
                },
                "control_plane_lifecycle": {"active_mutation_lane_count": 0},
            }
        )
    )

    hard_boundary = status["hard_boundary_contract"]
    _assert_inert_projection(hard_boundary)
    assert hard_boundary["state"] == "live_flag_violation"
    assert hard_boundary["live_flag_violations"] == [
        "read-only eligibility send_to_jenny_enabled must remain disabled",
        "execution packet would_dispatch must remain disabled",
        "execution packet worker_dispatch_enabled must remain disabled",
    ]
    next_safe_actions = status["next_safe_actions"]
    _assert_inert_projection(next_safe_actions)
    assert next_safe_actions["primary_action_id"] == "review_hard_boundary_contract"
    readiness = status["orchestration_readiness"]
    _assert_inert_projection(readiness)
    assert readiness["states"]["laptop_codex_worker_node"] == "blocked"
    assert "execution packet would_dispatch must remain disabled" in readiness["blocked_reasons"]
    operator_packet = status["operator_decision_packet"]
    _assert_inert_projection(operator_packet)
    assert operator_packet["state"] == "blocked"
    assert operator_packet["jenny_review_required"] is True
    assert operator_packet["execution_lock_blocked_reasons"] == hard_boundary["live_flag_violations"]
    assert "read-only eligibility send_to_jenny_enabled must remain disabled" in operator_packet["execution_lock_blocked_reasons"]


def test_orchestration_readiness_honors_hard_boundary_violations():
    status = {
        "read_only_autonomy_eligibility": {
            "eligible": True,
            "would_execute": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
        },
        "scoped_pr_lane_eligibility": {
            "eligible": True,
            "would_execute": False,
            "would_commit": False,
            "would_create_pr": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
            "merge_enabled": False,
            "deploy_enabled": False,
            "runtime_switch_enabled": False,
        },
        "worker_node_presence": {
            "online": True,
            "presence_state": "online",
            "would_execute": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
        },
        "worker_node_orchestration": {
            "active_count": 1,
            "latest_by_id": {
                "worker-run-safe": {
                    "worker_run_id": "worker-run-safe",
                    "parent_run_id": "run-parent",
                    "worker_identity": "codex",
                    "worker_host_label": "laptop-codex",
                    "objective": "Prepare scoped evidence.",
                    "report_review_status": "accepted",
                    "would_execute": False,
                }
            },
            "active_runs": [],
            "blocked_reasons": [],
        },
        "hard_boundary_contract": {
            "blocked": True,
            "blocked_reasons": ["execution packet would_dispatch must remain disabled"],
            "live_flag_violations": ["execution packet would_dispatch must remain disabled"],
        },
        "next_safe_actions": {"primary_action_label": "Review hard-boundary contract"},
    }

    readiness = _orchestration_readiness_payload(status)

    assert readiness["states"] == {
        "supervised_read_only_autonomy": "blocked",
        "scoped_pr_creation": "blocked",
        "laptop_codex_worker_node": "blocked",
    }
    assert readiness["supervised_read_only_autonomy"]["preview_ready"] is False
    assert readiness["scoped_pr_creation"]["preview_ready"] is False
    assert readiness["laptop_codex_worker_node"]["preview_ready"] is False
    assert (
        "execution packet would_dispatch must remain disabled"
        in readiness["blocked_reasons"]
    )
    assert (
        "execution packet would_dispatch must remain disabled"
        in readiness["laptop_codex_worker_node"]["blocked_reasons"]
    )
    assert "Review hard-boundary contract" in readiness["plain_language_summary"]


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
    assert "UNRECORDED_RUNTIME" in warnings
    assert "MISSING_RUNTIME_PATH" not in warnings
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
    _assert_inert_projection(child)
    _assert_inert_projection(worker)
    assert child["active_count"] == 1
    assert child["active_runs"][0]["child_run_id"] == "child-run-1"
    assert child["active_runs"][0]["report_link_status"] == "linked_report_found"
    assert child["active_runs"][0]["linked_report_status"] == "received"
    assert child["active_runs"][0]["linked_report_review_status"] == "needs_review"
    assert child["active_runs"][0]["linked_report_summary"] == "Child run reported evidence."
    assert child["blocked_reasons"] == ["report_id report-child still needs review"]
    assert child["would_execute"] is False
    assert child["dispatch_enabled"] is False
    assert worker["active_count"] == 1
    assert worker["active_runs"][0]["worker_host_label"] == "laptop-codex"
    assert worker["active_runs"][0]["report_link_status"] == "linked_report_found"
    assert worker["active_runs"][0]["linked_report_status"] == "accepted"
    assert worker["active_runs"][0]["linked_report_review_status"] == "accepted"
    assert worker["active_runs"][0]["report_review_status"] == "accepted"
    assert worker["active_runs"][0]["linked_report_summary"] == "Worker node reported PR evidence."
    assert worker["blocked_reasons"] == ["worker node offline"]
    assert worker["would_execute"] is False
    assert worker["worker_dispatch_enabled"] is False
    assert status["control_plane_records"]["active_child_run_count"] == 1
    assert status["control_plane_records"]["active_worker_node_run_count"] == 1

    review_queue = status["report_review_queue"]
    _assert_inert_projection(review_queue)
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
    _assert_inert_projection(graph)
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
    _assert_inert_projection(child_instruction)
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
    assert child_instruction["ready_for_handoff"] is False
    assert child_instruction["blocked"] is True
    assert child_instruction["child_run_id"] == "child-run-1"
    assert child_instruction["agent_identity"] == "jenny-child"
    assert child_instruction["objective"] == "Inspect a bounded context packet."
    assert child_instruction["allowed_actions"] == ["read approved context", "report evidence"]
    assert "dispatch" in child_instruction["forbidden_actions"]
    assert "no live delegation activation" in child_instruction["forbidden_actions"]
    assert "report_id report-child still needs review" in child_instruction["blocked_reasons"]
    assert "Manual delegation preview only" in child_instruction["manual_handoff_prompt"]
    assert "Handoff readiness: blocked until child-agent blockers are cleared." in child_instruction["manual_handoff_prompt"]
    assert "Report contract:" in child_instruction["manual_handoff_prompt"]

    instruction = status["worker_node_instruction_preview"]
    _assert_inert_projection(instruction)
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
    assert instruction["ready_for_handoff"] is False
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
    assert "Handoff readiness: blocked until worker-node blockers are cleared." in instruction["manual_handoff_prompt"]
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

    instruction = status["worker_node_instruction_preview"]
    assert instruction["available"] is True
    assert instruction["ready_for_handoff"] is True
    assert instruction["blocked"] is False
    assert "Handoff readiness: ready for manual review copy." in instruction["manual_handoff_prompt"]


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


def test_orchestration_readiness_and_instruction_previews_block_would_execute_flags():
    status = {
        "read_only_autonomy_eligibility": {
            "eligible": True,
            "would_execute": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
        },
        "scoped_pr_lane_eligibility": {
            "eligible": True,
            "would_execute": False,
            "would_commit": False,
            "would_create_pr": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_dispatch_enabled": False,
            "merge_enabled": "true",
            "deploy_enabled": False,
            "runtime_switch_enabled": False,
        },
        "next_safe_actions": {},
        "worker_node_presence": {
            "online": True,
            "presence_state": "online",
            "would_execute": True,
        },
        "worker_node_orchestration": {
            "active_count": 1,
            "would_execute": True,
            "latest_by_id": {
                "worker-run-unsafe": {
                    "worker_run_id": "worker-run-unsafe",
                    "parent_run_id": "run-parent",
                    "worker_identity": "codex",
                    "worker_host_label": "laptop-codex",
                    "objective": "Prepare scoped evidence.",
                    "would_execute": True,
                    "report_review_status": "accepted",
                }
            },
            "active_runs": [
                {
                    "worker_run_id": "worker-run-unsafe",
                    "parent_run_id": "run-parent",
                    "worker_identity": "codex",
                    "worker_host_label": "laptop-codex",
                    "objective": "Prepare scoped evidence.",
                    "would_execute": True,
                    "report_review_status": "accepted",
                }
            ],
            "blocked_reasons": [],
        },
        "child_agent_orchestration": {
            "active_count": 1,
            "would_execute": True,
            "active_runs": [
                {
                    "child_run_id": "child-run-unsafe",
                    "parent_run_id": "run-parent",
                    "agent_identity": "jenny-child",
                    "objective": "Inspect bounded context.",
                    "would_execute": True,
                }
            ],
            "blocked_reasons": [],
        },
    }

    readiness_projection = _orchestration_readiness_payload(status)
    scoped_pr_readiness = readiness_projection["scoped_pr_creation"]
    assert scoped_pr_readiness["state"] == "blocked"
    assert scoped_pr_readiness["preview_ready"] is False
    assert "merge_enabled must remain disabled" in scoped_pr_readiness["blocked_reasons"]

    readiness = readiness_projection["laptop_codex_worker_node"]
    assert readiness["state"] == "blocked"
    assert readiness["preview_ready"] is False
    assert "would_execute must remain disabled" in readiness["blocked_reasons"]

    worker_instruction = _worker_node_instruction_preview(status)
    assert worker_instruction["ready_for_handoff"] is False
    assert worker_instruction["blocked"] is True
    assert "would_execute must remain disabled" in worker_instruction["blocked_reasons"]

    child_instruction = _child_agent_instruction_preview(status)
    assert child_instruction["ready_for_handoff"] is False
    assert child_instruction["blocked"] is True
    assert "would_execute must remain disabled" in child_instruction["blocked_reasons"]


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
    assert packet["packet"]["would_dispatch"] is False
    assert packet["packet"]["would_session_send"] is False
    assert packet["packet"]["worker_node_contract"]["would_dispatch"] is False
    assert packet["packet"]["worker_node_contract"]["would_session_send"] is False
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
    assert operator_packet["execution_lock_blocked_reasons"] == []


def test_operator_decision_packet_rolls_up_nested_execution_locks():
    operator_packet = _operator_decision_packet_payload(
        {
            "runtime_provenance": {"primary_status": "CLEAN_AND_ALIGNED", "autonomy_blocked_reasons": []},
            "next_safe_actions": {"primary_action_label": "Review execution packet blockers"},
            "orchestration_readiness": {
                "states": {
                    "supervised_read_only_autonomy": "preview_ready",
                    "scoped_pr_creation": "preview_ready",
                    "laptop_codex_worker_node": "preview_ready",
                },
                "blocked_reasons": [],
            },
            "execution_mode_classification": {"mode_family": "worker_node_preview", "blocked_reasons": []},
            "execution_packet_preview": {
                "eligible": True,
                "would_dispatch": "true",
                "packet": {
                    "mode": "worker_node",
                    "session_send_enabled": "yes",
                    "worker_node_contract": {
                        "would_session_send": "on",
                        "worker_dispatch_enabled": 1,
                    },
                },
            },
        }
    )

    _assert_inert_projection(operator_packet)
    assert operator_packet["execution_ready"] is False
    assert operator_packet["execution_lock_blocked_reasons"] == [
        "execution packet would_dispatch must remain disabled",
        "execution packet body session_send_enabled must remain disabled",
        "worker contract would_session_send must remain disabled",
        "worker contract worker_dispatch_enabled must remain disabled",
    ]
    assert operator_packet["blocked_reasons"] == operator_packet["execution_lock_blocked_reasons"]
    assert "Execution lock blockers:" in operator_packet["plain_language_summary"]


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
    assert queue["link_mismatch_count"] == 0
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
    assert operator_packet["worker_instruction_available"] is True
    assert operator_packet["worker_instruction_ready_for_handoff"] is False
    assert operator_packet["child_instruction_available"] is True
    assert operator_packet["child_instruction_ready_for_handoff"] is False
    assert operator_packet["report_review_queue_count"] == 3
    assert operator_packet["top_report_review_item_id"] == "report:report-worker"
    assert operator_packet["top_report_review_label"] == "Laptop Codex reported scoped PR evidence."
    assert operator_packet["recommended_operator_instruction"] == (
        "Jenny reviews Laptop Codex reported scoped PR evidence. before issuing another worker instruction."
    )
    assert "Approval required: yes." in operator_packet["plain_language_summary"]
    assert "Worker instruction: preview available but blocked; laptop Codex dispatch remains disabled." in operator_packet["plain_language_summary"]
    assert "Child instruction: preview available but blocked; execution remains disabled." in operator_packet["plain_language_summary"]
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
            metadata={
                "Authorization": "Bearer fake-token-for-test",
                "OpenAI-API-Key": "fake-api-key-for-test",
                "SessionCookie": "fake-cookie-for-test",
                "env.secret": "fake-env-secret-for-test",
                "raw_log": "forbidden",
                "token": "placeholder-token",
            },
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
    expected_forbidden_keys = [
        "authorization",
        "env_secret",
        "openai_api_key",
        "raw_log",
        "sessioncookie",
        "token",
    ]
    expected_forbidden_reason = (
        "report_id report-unsafe metadata contains forbidden keys: "
        f"{', '.join(expected_forbidden_keys)}"
    )
    assert expected_forbidden_reason in ingestion["blocked_reasons"]
    assert "report_id report-unsafe is missing safety confirmation for ingestion" in ingestion["blocked_reasons"]

    items = {item["report_id"]: item for item in ingestion["items"]}
    assert items["report-ready"]["ingestion_ready"] is True
    assert items["report-ready"]["linked_record_type"] == "worker_node_run"
    assert items["report-ready"]["safety_confirmation_present"] is True
    assert items["report-unsafe"]["ingestion_ready"] is False
    assert items["report-unsafe"]["forbidden_metadata_keys"] == expected_forbidden_keys
    assert "placeholder-token" not in str(ingestion)
    assert "fake-token-for-test" not in str(ingestion)
    assert "fake-api-key-for-test" not in str(ingestion)
    assert "fake-cookie-for-test" not in str(ingestion)
    assert "fake-env-secret-for-test" not in str(ingestion)

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_result_ingestion_contract" in action_ids
    assert expected_forbidden_reason in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["result_ingestion_blocked_count"] == 1
    assert "report_id report-unsafe redaction_status raw is not accepted" in operator_packet["result_ingestion_blocked_reasons"]
    assert "Result ingestion: 1 ready, 1 blocked." in operator_packet["plain_language_summary"]


def test_record_sourced_workspace_status_blocks_mismatched_worker_report_link(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
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
            report_id="report-worker",
            run_id="other-worker-run",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Accepted report attached to the wrong worker run.",
            result="Prepared scoped PR evidence.",
            risks=("none beyond focused evidence",),
            changed_files=("mission_control/workspace_status_records.py",),
            tests=("mission_control status tests passed",),
            next_recommended_lane="Jenny reviews the link mismatch.",
            evidence_refs=("pytest output",),
            submitted_by="codex",
            submitted_from="laptop-codex",
            reviewed_at="2026-06-19T10:00:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    mismatch_reason = (
        "report_id report-worker run_id other-worker-run does not match linked worker_node_run worker-run-1"
    )
    worker = status["worker_node_orchestration"]
    assert worker["active_runs"][0]["report_link_status"] == "linked_report_run_id_mismatch"
    assert worker["active_runs"][0]["report_link_mismatch"] is True
    assert worker["active_runs"][0]["report_link_mismatch_reason"] == mismatch_reason
    assert mismatch_reason in worker["blocked_reasons"]

    queue = status["report_review_queue"]
    assert queue["queue_count"] == 1
    assert queue["link_mismatch_count"] == 1
    assert queue["primary_review_item"]["item_type"] == "report_link_mismatch"
    assert queue["primary_review_item"]["report_link_mismatch"] is True
    assert queue["primary_review_item"]["review_status"] == "accepted"
    assert queue["primary_review_reason"] == mismatch_reason
    assert mismatch_reason in queue["blocked_reasons"]

    ingestion = status["result_ingestion_contract"]
    assert ingestion["ingestion_ready_count"] == 0
    assert ingestion["blocked_report_count"] == 1
    assert ingestion["link_mismatch_count"] == 1
    ingestion_item = {item["report_id"]: item for item in ingestion["items"]}["report-worker"]
    assert ingestion_item["report_link_mismatch"] is True
    assert ingestion_item["ingestion_ready"] is False
    assert mismatch_reason in ingestion["blocked_reasons"]

    completion = status["report_completion_path"]
    assert completion["terminal_item_count"] == 1
    assert completion["completion_ready_count"] == 0
    assert completion["blocked_completion_count"] == 1
    assert completion["ingestion_blocked_count"] == 1
    assert completion["link_mismatch_count"] == 1
    completion_item = completion["items"][0]
    assert completion_item["report_link_mismatch"] is True
    assert completion_item["result_ingestion_ready"] is False
    assert completion_item["completion_ready"] is False
    assert mismatch_reason in completion["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    instruction = status["worker_node_instruction_preview"]
    assert instruction["available"] is True
    assert instruction["ready_for_handoff"] is False
    assert instruction["report_link_status"] == "linked_report_run_id_mismatch"
    assert instruction["report_link_mismatch"] is True
    assert instruction["report_link_mismatch_reason"] == mismatch_reason
    assert mismatch_reason in instruction["blocked_reasons"]

    assert mismatch_reason in operator_packet["blocked_reasons"]
    assert mismatch_reason in operator_packet["result_ingestion_blocked_reasons"]
    assert mismatch_reason in operator_packet["report_completion_blocked_reasons"]
    assert operator_packet["report_link_mismatch_count"] == 1
    assert operator_packet["report_link_mismatch_ids"] == ["report-worker"]
    assert operator_packet["report_review_queue_link_mismatch_count"] == 1
    assert operator_packet["result_ingestion_link_mismatch_count"] == 1
    assert operator_packet["report_completion_link_mismatch_count"] == 1
    assert operator_packet["stop_cancel_link_mismatch_count"] == 0
    assert (
        "Report link mismatches: unique 1, queue 1, ingestion 1, completion 1, stop/cancel 0; "
        "Jenny must review lineage before handoff."
    ) in operator_packet["plain_language_summary"]


def test_child_agent_instruction_preview_blocks_projected_report_link_mismatch(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        ChildRunRecord(
            child_run_id="child-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            agent_identity="jenny-child",
            status="blocked",
            objective="Inspect bounded evidence.",
            report_id="report-child",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-child",
            run_id="other-child-run",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Accepted child report attached to the wrong child run.",
            result="Inspected bounded evidence.",
            risks=("none beyond lineage mismatch",),
            changed_files=("docs/mission-control/evidence.md",),
            tests=("read-only evidence review",),
            next_recommended_lane="Jenny reviews the child report link mismatch.",
            evidence_refs=("child report output",),
            submitted_by="jenny-child",
            submitted_from="child-agent",
            reviewed_at="2026-06-19T10:00:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, delegation activation, record mutation, or secrets."},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    mismatch_reason = (
        "report_id report-child run_id other-child-run does not match linked child_run child-run-1"
    )
    child = status["child_agent_orchestration"]
    assert child["active_runs"][0]["report_link_status"] == "linked_report_run_id_mismatch"
    assert child["active_runs"][0]["report_link_mismatch"] is True
    assert child["active_runs"][0]["report_link_mismatch_reason"] == mismatch_reason
    assert mismatch_reason in child["blocked_reasons"]

    queue = status["report_review_queue"]
    assert queue["queue_count"] == 1
    assert queue["link_mismatch_count"] == 1
    assert queue["primary_review_item"]["report_link_mismatch"] is True

    instruction = status["child_agent_instruction_preview"]
    assert instruction["available"] is True
    assert instruction["ready_for_handoff"] is False
    assert instruction["report_link_status"] == "linked_report_run_id_mismatch"
    assert instruction["report_link_mismatch"] is True
    assert instruction["report_link_mismatch_reason"] == mismatch_reason
    assert instruction["execution_enabled"] is False
    assert instruction["dispatch_enabled"] is False
    assert instruction["session_send_enabled"] is False
    assert instruction["worker_dispatch_enabled"] is False
    assert mismatch_reason in instruction["blocked_reasons"]
    assert "Handoff readiness: blocked until child-agent blockers are cleared." in instruction["manual_handoff_prompt"]

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_child_agent_blockers" in action_ids
    assert mismatch_reason in next_safe_actions["blocked_reasons"]


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


def test_operator_decision_packet_requires_review_for_incomplete_accepted_report_contract(tmp_path):
    records_path = tmp_path / "mission-control" / "records.jsonl"
    store = JsonlRecordStore(records_path)
    store.append(
        WorkerNodeRunRecord(
            worker_run_id="worker-run-1",
            parent_run_id="run-parent",
            project_id="project-hermes-mission-control",
            worker_identity="codex",
            worker_host_label="laptop-codex",
            status="running",
            objective="Prepare scoped PR evidence.",
            report_id="report-incomplete-accepted",
        )
    )
    store.append(
        ReportRecord(
            report_id="report-incomplete-accepted",
            run_id="worker-run-1",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Accepted report missing the full contract.",
            risks=("focused evidence only",),
            reviewed_at="2026-06-19T10:00:00Z",
            reviewed_by="jenny",
            redaction_status="operator_supplied_redacted",
            metadata={"safety_confirmation": "No live dispatch, deploy, restart, runtime switch, records, or secrets."},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["report_review_queue_count"] == 0
    assert operator_packet["result_ingestion_blocked_count"] == 0
    assert operator_packet["report_completion_blocked_count"] == 0
    assert operator_packet["stop_cancel_count"] == 0
    assert operator_packet["report_contract_incomplete_count"] == 1
    assert operator_packet["jenny_review_required"] is True
    assert "Report contract completeness: 0 complete, 1 incomplete." in operator_packet["plain_language_summary"]


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
        RunRecord(
            run_id="run-cancelled-mismatch",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Cancelled run with mismatched report",
            status="cancelled",
            stop_reason="Operator cancelled after mismatch.",
            report_ids=("report-stop-mismatch",),
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
    store.append(
        ReportRecord(
            report_id="report-stop-mismatch",
            run_id="other-run",
            project_id="project-hermes-mission-control",
            status="accepted",
            summary="Accepted stop report attached to the wrong run.",
            reviewed_at="2026-06-19T12:10:00Z",
            reviewed_by="jenny",
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    mismatch_reason = (
        "report_id report-stop-mismatch run_id other-run does not match linked run run-cancelled-mismatch"
    )
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
    assert stop_control["stop_cancel_count"] == 4
    assert stop_control["active_stop_count"] == 1
    assert stop_control["terminal_stop_count"] == 3
    assert stop_control["needs_report_count"] == 3
    assert stop_control["link_mismatch_count"] == 1
    assert stop_control["needs_review_count"] == 1
    assert stop_control["blocked"] is True
    assert "run run-stopping is stopping and needs manual stop confirmation" in stop_control["blocked_reasons"]
    assert "run run-stopping has no linked stop/cancel report" in stop_control["blocked_reasons"]
    assert "report_id report-child-stop still needs Jenny review" in stop_control["blocked_reasons"]
    assert mismatch_reason in stop_control["blocked_reasons"]
    assert "worker_node_run worker-cancelled has no stop_reason" in stop_control["blocked_reasons"]
    assert "worker_node_run worker-cancelled has no linked stop/cancel report" in stop_control["blocked_reasons"]

    items = {item["item_id"]: item for item in stop_control["items"]}
    assert items["run:run-cancelled-mismatch"]["report_link_status"] == "linked_report_run_id_mismatch"
    assert items["run:run-cancelled-mismatch"]["report_link_mismatch"] is True
    assert items["run:run-cancelled-mismatch"]["report_link_mismatch_reason"] == mismatch_reason
    assert items["child_run:child-stopped"]["report_link_status"] == "linked_report_found"
    assert items["child_run:child-stopped"]["report_review_status"] == "needs_review"
    assert items["worker_node_run:worker-cancelled"]["report_link_status"] == "missing_linked_report"

    next_safe_actions = status["next_safe_actions"]
    action_ids = {action["action_id"] for action in next_safe_actions["actions"]}
    assert "review_stop_cancel_control" in action_ids
    assert mismatch_reason in next_safe_actions["blocked_reasons"]
    assert "worker_node_run worker-cancelled has no stop_reason" in next_safe_actions["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    assert operator_packet["stop_cancel_count"] == 4
    assert operator_packet["report_link_mismatch_count"] == 1
    assert operator_packet["report_link_mismatch_ids"] == ["report-stop-mismatch"]
    assert operator_packet["report_review_queue_link_mismatch_count"] == 1
    assert operator_packet["result_ingestion_link_mismatch_count"] == 1
    assert operator_packet["report_completion_link_mismatch_count"] == 1
    assert operator_packet["stop_cancel_link_mismatch_count"] == 1
    assert mismatch_reason in operator_packet["stop_cancel_blocked_reasons"]
    assert "worker_node_run worker-cancelled has no stop_reason" in operator_packet["stop_cancel_blocked_reasons"]
    assert (
        "Report link mismatches: unique 1, queue 1, ingestion 1, completion 1, stop/cancel 1; "
        "Jenny must review lineage before handoff."
    ) in operator_packet["plain_language_summary"]
    assert "Stop/cancel control: 4 items, blocked true." in operator_packet["plain_language_summary"]
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
            result="First result.",
            risks=("first risk",),
            blockers=("first blocker",),
            changed_files=("mission_control/first.py",),
            tests=("first test",),
            next_recommended_lane="first lane",
            evidence_refs=("first evidence",),
            artifact_refs=("first artifact",),
            created_at="2026-06-19T08:00:00Z",
            metadata={"safety_confirmation": "First safety confirmation."},
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
            result="Second result.",
            risks=("second risk",),
            blockers=("second blocker",),
            changed_files=("mission_control/second.py",),
            tests=("second test",),
            next_recommended_lane="second lane",
            evidence_refs=("second evidence",),
            artifact_refs=("second artifact",),
            created_at="2026-06-19T09:00:00Z",
            metadata={"safety_confirmation": "Second safety confirmation."},
        )
    )

    status = build_workspace_status_from_records(records_path=records_path)

    lifecycle = status["report_lifecycle"]
    _assert_inert_projection(lifecycle)
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
    assert lifecycle["report_overwrite_conflict_ids"] == ["report-duplicate"]
    assert lifecycle["report_overwrite_conflicts"] == {
        "report-duplicate": [
            "summary",
            "result",
            "risks",
            "blockers",
            "changed_files",
            "tests",
            "next_recommended_lane",
            "evidence_refs",
            "artifact_refs",
            "created_at",
            "metadata",
            "status",
        ]
    }
    assert lifecycle["report_overwrite_conflict_count"] == 1
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
    assert (
        "report_id report-duplicate attempts to overwrite append-only report fields: "
        "summary, result, risks, blockers, changed_files, tests, next_recommended_lane, "
        "evidence_refs, artifact_refs, created_at, metadata, status"
        in lifecycle["blocked_reasons"]
    )
    assert "run_id run-reportless has no linked report" in lifecycle["blocked_reasons"]
    assert (
        "run_id run-missing-linked-report links missing report ids: report-missing"
        in lifecycle["blocked_reasons"]
    )
    assert "report_id report-duplicate still needs review" in lifecycle["blocked_reasons"]

    operator_packet = status["operator_decision_packet"]
    _assert_inert_projection(operator_packet)
    assert operator_packet["report_overwrite_conflict_count"] == 1
    assert operator_packet["report_overwrite_conflict_ids"] == ["report-duplicate"]
    assert (
        "report_id report-duplicate attempts to overwrite append-only report fields: "
        "summary, result, risks, blockers, changed_files, tests, next_recommended_lane, "
        "evidence_refs, artifact_refs, created_at, metadata, status"
        in operator_packet["blocked_reasons"]
    )
    assert (
        "Report overwrite conflicts: 1; duplicate report IDs are quarantined."
        in operator_packet["plain_language_summary"]
    )


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
    _assert_inert_projection(approvals)
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
    _assert_inert_projection(runs)
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
    _assert_inert_projection(next_safe_actions)
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
    _assert_inert_projection(readiness)
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
