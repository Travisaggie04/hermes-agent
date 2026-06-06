"""Read-only Mission Control governance dashboard plugin tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mission_control.records import (
    ApprovalSlice,
    ArtifactRef,
    EvidenceCard,
    GoalContract,
    JsonlRecordStore,
    MissionBrief,
    OperatorAction,
    StartGateCheck,
    TaskControlEnvelope,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "mission-control-governance"
API_PATH = PLUGIN_DIR / "api.py"


def _load_api_module():
    spec = importlib.util.spec_from_file_location(
        "mission_control_governance_plugin_api_test",
        API_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_api(tmp_path, monkeypatch):
    module = _load_api_module()
    records_path = tmp_path / "mission-control" / "records.jsonl"
    monkeypatch.setattr(module, "record_store_path", lambda: records_path)
    return module


@pytest.fixture
def client(plugin_api):
    app = FastAPI()
    app.include_router(plugin_api.router, prefix="/api/plugins/mission-control-governance")
    return TestClient(app)


def _seed_records(path: Path) -> None:
    store = JsonlRecordStore(path)
    goal = GoalContract(
        goal_id="goal-1",
        statement="Keep governance records inert.",
        success_criteria=("read-only summary renders",),
        constraints=("no execution",),
    )
    control = TaskControlEnvelope(
        active_lane="PR-B Mission Control governance plugin MVP",
        mode="code/test only",
        allowed_actions=("read records",),
        forbidden_actions=("execute tools", "load transcripts"),
        current_repo="/tmp/hermes",
        stop_condition="Stop before commit.",
    )
    store.append(goal)
    store.append(control)
    store.append(
        ApprovalSlice(
            approval_id="approval-1",
            lane=control.active_lane,
            mode=control.mode,
            approved_actions=("create read-only plugin",),
            forbidden_actions=("execute approval",),
            approver="Travis",
            approved_at="2026-06-04T00:00:00Z",
        )
    )
    store.append(
        MissionBrief(
            mission_id="mission-1",
            title="Governance plugin MVP",
            created_at="2026-06-04T00:01:00Z",
            goal=goal,
            control=control,
        )
    )


def _seed_goal_records(path: Path, count: int) -> None:
    store = JsonlRecordStore(path)
    for index in range(count):
        store.append(
            GoalContract(
                goal_id=f"goal-{index}",
                statement=f"Governance record {index}",
                success_criteria=("bounded records response",),
                constraints=("read-only",),
                metadata={"raw_context": f"secret raw context {index}"},
            )
        )


def test_plugin_manifest_loads():
    manifest = yaml.safe_load((PLUGIN_DIR / "plugin.yaml").read_text())
    assert manifest["name"] == "mission-control-governance"
    assert manifest["version"]
    assert manifest.get("hooks") in (None, [])
    assert manifest.get("provides_tools") in (None, [])

    dashboard = yaml.safe_load((PLUGIN_DIR / "dashboard" / "manifest.json").read_text())
    assert dashboard["name"] == "mission-control-governance"
    assert dashboard["entry"] == "dist/index.js"
    assert dashboard["api"] == "plugin_api.py"


def test_api_routes_are_get_only(plugin_api, client):
    methods_by_path = {
        route.path: route.methods
        for route in plugin_api.router.routes
        if getattr(route, "path", "").startswith("/")
    }
    assert methods_by_path == {
        "/health": {"GET"},
        "/summary": {"GET"},
        "/start-gate": {"GET"},
        "/task-control-envelopes": {"GET"},
        "/start-gate-checks": {"GET"},
        "/approval-slices": {"GET"},
        "/evidence-cards": {"GET"},
        "/operator-actions": {"GET"},
        "/records": {"GET"},
        "/schema": {"GET"},
        "/records/{record_index}": {"GET"},
    }

    for path in (
        "/health",
        "/summary",
        "/start-gate",
        "/task-control-envelopes",
        "/start-gate-checks",
        "/approval-slices",
        "/evidence-cards",
        "/operator-actions",
        "/records",
        "/schema",
        "/records/0",
    ):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)(
                f"/api/plugins/mission-control-governance{path}"
            )
            assert response.status_code == 405


def test_health_is_read_only_and_inert(client):
    response = client.get("/api/plugins/mission-control-governance/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "plugin": "mission-control-governance",
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
    }


def test_summary_and_records_return_inert_fields(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    summary = client.get("/api/plugins/mission-control-governance/summary").json()
    assert summary["trusted_for_execution"] is False
    assert summary["inert_context_only"] is True
    assert summary["execution_enabled"] is False
    assert summary["record_count"] == 4
    assert summary["record_types"] == {
        "ApprovalSlice": 1,
        "GoalContract": 1,
        "MissionBrief": 1,
        "TaskControlEnvelope": 1,
    }
    assert summary["latest_mission_title"] == "Governance plugin MVP"

    records = client.get("/api/plugins/mission-control-governance/records").json()
    assert records["trusted_for_execution"] is False
    assert records["inert_context_only"] is True
    assert records["execution_enabled"] is False
    assert records["count"] == 4
    assert records["store_status"] == "ok"
    assert records["error"] is None
    assert [item["record_type"] for item in records["records"]] == [
        "GoalContract",
        "TaskControlEnvelope",
        "ApprovalSlice",
        "MissionBrief",
    ]
    assert records["records"][0]["record"]["statement"] == "Keep governance records inert."


def test_records_defaults_to_bounded_latest_page(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get("/api/plugins/mission-control-governance/records")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 25
    assert payload["count"] == 25
    assert payload["returned_count"] == 25
    assert payload["has_more"] is True
    assert [item["record_index"] for item in payload["records"]] == list(range(5, 30))
    assert payload["records"][0]["record"]["statement"] == "Governance record 5"
    assert "metadata" not in payload["records"][0]["record"]
    assert "secret raw context" not in str(payload).lower()


def test_records_caps_oversized_limit(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 60)

    response = client.get("/api/plugins/mission-control-governance/records?limit=500")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    assert payload["count"] == 50
    assert payload["returned_count"] == 50
    assert payload["has_more"] is True
    assert [item["record_index"] for item in payload["records"]] == list(range(10, 60))


def test_records_non_positive_limit_falls_back_to_default(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get("/api/plugins/mission-control-governance/records?limit=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 25
    assert payload["returned_count"] == 25
    assert [item["record_index"] for item in payload["records"]] == list(range(5, 30))


def test_records_invalid_limit_is_rejected_without_dumping_records(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get("/api/plugins/mission-control-governance/records?limit=not-a-number")

    assert response.status_code == 422
    assert "Governance record" not in response.text


def test_start_gate_returns_no_active_envelope_for_missing_store(client):
    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    assert response.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "has_active_envelope": False,
        "source": "none",
        "record_index": None,
        "mission_id": None,
        "mission_title": None,
        "mission_created_at": None,
        "envelope": None,
    }


def test_start_gate_prefers_latest_mission_brief_control(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old_control = TaskControlEnvelope(
        active_lane="Older standalone lane",
        mode="inventory only",
        allowed_actions=("read records",),
        forbidden_actions=("change records",),
        current_repo="/tmp/old",
        stop_condition="Stop before edits.",
    )
    latest_control = TaskControlEnvelope(
        active_lane="Latest mission lane",
        mode="focused tests only",
        allowed_actions=("add GET endpoint", "update dashboard panel"),
        forbidden_actions=("run broad tests", "load transcripts"),
        current_repo="/tmp/latest",
        expected_systems_files=("plugins/mission-control-governance/api.py",),
        stop_condition="Stop after focused tests.",
        other_threads_excluded=("unrelated PR",),
    )
    goal = GoalContract(goal_id="goal-latest", statement="Expose inert start gate summary.")
    store.append(old_control)
    store.append(
        MissionBrief(
            mission_id="mission-latest",
            title="Start Gate UI",
            created_at="2026-06-05T00:00:00Z",
            goal=goal,
            control=latest_control,
        )
    )

    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["has_active_envelope"] is True
    assert payload["source"] == "MissionBrief.control"
    assert payload["record_index"] == 1
    assert payload["mission_id"] == "mission-latest"
    assert payload["mission_title"] == "Start Gate UI"
    assert payload["mission_created_at"] == "2026-06-05T00:00:00Z"
    assert payload["envelope"] == {
        "envelope_id": "",
        "active_lane": "Latest mission lane",
        "mode": "focused tests only",
        "allowed_actions": ["add GET endpoint", "update dashboard panel"],
        "forbidden_actions": ["run broad tests", "load transcripts"],
        "current_repo": "/tmp/latest",
        "expected_systems_files": ["plugins/mission-control-governance/api.py"],
        "stop_condition": "Stop after focused tests.",
        "other_threads_excluded": ["unrelated PR"],
        "report_requirements": [],
        "risk_level": "",
        "approval_required": False,
        "approval_slice_ids": [],
        "evidence_ids": [],
        "token_context_policy": "",
        "created_at": "",
        "status": "",
    }


def test_start_gate_uses_standalone_envelope_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    control = TaskControlEnvelope(
        active_lane="Standalone lane",
        mode="read-only summary",
        allowed_actions=("read envelope",),
        forbidden_actions=("write records",),
        current_repo="/tmp/standalone",
        stop_condition="Stop after response.",
    )
    store.append(control)

    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_active_envelope"] is True
    assert payload["source"] == "TaskControlEnvelope"
    assert payload["record_index"] == 0
    assert payload["mission_id"] is None
    assert payload["mission_title"] is None
    assert payload["mission_created_at"] is None
    assert payload["envelope"]["active_lane"] == "Standalone lane"
    assert payload["envelope"]["mode"] == "read-only summary"
    assert "metadata" not in payload["envelope"]


def test_schema_lists_record_types_without_loading_records(client):
    response = client.get("/api/plugins/mission-control-governance/schema")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["record_store"]["status"] == "missing"
    assert "GoalContract" in payload["record_types"]
    assert payload["record_types"]["GoalContract"]["fields"] == [
        "goal_id",
        "statement",
        "success_criteria",
        "constraints",
        "metadata",
    ]
    assert "ArtifactRef" in payload["record_types"]


def test_record_detail_returns_zero_based_record_index(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    response = client.get("/api/plugins/mission-control-governance/records/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["record_index"] == 1
    assert payload["record_type"] == "TaskControlEnvelope"
    assert payload["record"]["active_lane"] == "PR-B Mission Control governance plugin MVP"


def test_operator_action_metadata_is_not_exposed_by_record_apis(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-sensitive-metadata",
            title="Review safe summary only",
            lane="PR-G",
            mode="read-only",
            requested_action="Review bounded queue summary.",
            metadata={
                "source": "planning",
                "transcript": "secret transcript value",
                "artifact_blob": "secret artifact value",
                "arbitrary_key": "arbitrary secret value",
            },
        )
    )

    records_payload = client.get("/api/plugins/mission-control-governance/records").json()
    detail_payload = client.get("/api/plugins/mission-control-governance/records/0").json()

    for record in (
        records_payload["records"][0]["record"],
        detail_payload["record"],
    ):
        assert record["action_id"] == "action-sensitive-metadata"
        assert record["source"] == "planning"
        assert "metadata" not in record
        assert "transcript" not in record
        assert "artifact_blob" not in record
        assert "arbitrary_key" not in record

    lowered = f"{records_payload} {detail_payload}".lower()
    assert "secret transcript value" not in lowered
    assert "secret artifact value" not in lowered
    assert "arbitrary secret value" not in lowered


def test_approval_and_evidence_metadata_is_not_exposed_by_record_apis(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        ApprovalSlice(
            approval_slice_id="approval-sensitive-metadata",
            related_action_id="action-sensitive",
            approval_type="operator",
            decision_state="pending",
            required_by="Travis",
            reason="Needs focused verification.",
            safety_conditions=("no deploy",),
            evidence_ids=("evidence-sensitive-metadata",),
            created_at="2026-06-06T00:00:00Z",
            metadata={
                "transcript": "secret approval transcript",
                "raw_decision": "secret approval metadata",
            },
        )
    )
    store.append(
        EvidenceCard(
            evidence_id="evidence-sensitive-metadata",
            related_lane="PR-H",
            related_action_id="action-sensitive",
            related_record_type="OperatorAction",
            summary="Safe compact evidence summary.",
            evidence_type="test",
            source_label="pytest",
            created_at="2026-06-06T00:01:00Z",
            risk_notes=("metadata must stay private",),
            metadata={
                "raw_log": "secret evidence log",
                "transcript": "secret evidence transcript",
            },
        )
    )

    records_payload = client.get("/api/plugins/mission-control-governance/records").json()
    approval_detail = client.get("/api/plugins/mission-control-governance/records/0").json()
    evidence_detail = client.get("/api/plugins/mission-control-governance/records/1").json()

    assert "metadata" not in records_payload["records"][0]["record"]
    assert "metadata" not in records_payload["records"][1]["record"]
    assert "metadata" not in approval_detail["record"]
    assert "metadata" not in evidence_detail["record"]
    lowered = f"{records_payload} {approval_detail} {evidence_detail}".lower()
    assert "secret approval transcript" not in lowered
    assert "secret approval metadata" not in lowered
    assert "secret evidence log" not in lowered
    assert "secret evidence transcript" not in lowered


def test_task_control_envelopes_endpoint_is_bounded_and_metadata_safe(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            TaskControlEnvelope(
                envelope_id=f"envelope-{index}",
                active_lane=f"lane-{index}",
                mode="read-only",
                allowed_actions=("read records",),
                forbidden_actions=("execute tools",),
                stop_condition="Stop after report.",
                report_requirements=("files changed",),
                risk_level="low",
                approval_required=index % 2 == 0,
                approval_slice_ids=(f"approval-{index}",),
                evidence_ids=(f"evidence-{index}",),
                token_context_policy="summary-first latest-10 only",
                created_at=f"2026-06-06T00:{index:02d}:00Z",
                status="active",
                metadata={
                    "raw_context": "secret envelope context",
                    "transcript": "secret envelope transcript",
                },
            )
        )

    response = client.get("/api/plugins/mission-control-governance/task-control-envelopes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "TaskControlEnvelope"
    assert payload["count"] == 10
    assert [item["envelope_id"] for item in payload["task_control_envelopes"]] == [
        f"envelope-{index}" for index in range(2, 12)
    ]
    first = payload["task_control_envelopes"][0]
    assert first["record_index"] == 2
    assert first["active_lane"] == "lane-2"
    assert first["allowed_action_count"] == 1
    assert first["forbidden_action_count"] == 1
    assert first["approval_required"] is True
    assert first["approval_slice_count"] == 1
    assert first["evidence_count"] == 1
    lowered = str(payload).lower()
    assert "metadata" not in lowered
    assert "secret envelope context" not in lowered
    assert "secret envelope transcript" not in lowered


def test_start_gate_checks_endpoint_is_descriptive_bounded_and_metadata_safe(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            StartGateCheck(
                start_gate_id=f"start-gate-{index}",
                envelope_id=f"envelope-{index}",
                decision_state="blocked" if index == 11 else "informational",
                reasons=(f"reason {index}",),
                blocked_actions=("deploy", "merge"),
                required_approvals=(f"approval-{index}",),
                dirty_worktree_state="clean",
                branch_safety_state="exact base",
                secret_safety_state="not touched",
                token_context_state="bounded",
                created_at=f"2026-06-06T01:{index:02d}:00Z",
                metadata={
                    "raw_scan": "secret start gate scan",
                    "transcript": "secret start gate transcript",
                },
            )
        )

    response = client.get("/api/plugins/mission-control-governance/start-gate-checks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "StartGateCheck"
    assert payload["count"] == 10
    assert [item["start_gate_id"] for item in payload["start_gate_checks"]] == [
        f"start-gate-{index}" for index in range(2, 12)
    ]
    latest = payload["start_gate_checks"][-1]
    assert latest["record_index"] == 11
    assert latest["decision_state"] == "blocked"
    assert latest["reason_count"] == 1
    assert latest["blocked_action_count"] == 2
    assert latest["required_approval_count"] == 1
    lowered = str(payload).lower()
    assert "metadata" not in lowered
    assert "secret start gate scan" not in lowered
    assert "secret start gate transcript" not in lowered


def test_record_detail_returns_404_for_missing_index(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    response = client.get("/api/plugins/mission-control-governance/records/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "record index not found"


def test_empty_store_returns_empty_inert_payload(client):
    summary = client.get("/api/plugins/mission-control-governance/summary").json()
    records = client.get("/api/plugins/mission-control-governance/records").json()

    assert summary["record_count"] == 0
    assert summary["record_types"] == {}
    assert records["count"] == 0
    assert records["records"] == []
    assert summary["store_status"] == "missing"
    assert summary["error"] is None
    assert records["store_status"] == "missing"
    assert records["error"] is None
    assert summary["trusted_for_execution"] is False
    assert records["execution_enabled"] is False


def test_empty_store_returns_empty_approval_and_evidence_payloads(client):
    approvals = client.get("/api/plugins/mission-control-governance/approval-slices")
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards")
    actions = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert approvals.status_code == 200
    assert evidence.status_code == 200
    assert actions.status_code == 200
    assert approvals.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "approval_slices": [],
    }
    assert evidence.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "evidence_cards": [],
    }
    assert actions.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "operator_actions": [],
    }


def test_approval_and_evidence_routes_are_get_only(client):
    for path in (
        "/approval-slices",
        "/evidence-cards",
        "/operator-actions",
        "/task-control-envelopes",
        "/start-gate-checks",
    ):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)(
                f"/api/plugins/mission-control-governance{path}"
            )
            assert response.status_code == 405


def test_approval_slices_prefers_latest_mission_brief_approvals(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old = ApprovalSlice(
        approval_id="standalone-old",
        lane="old lane",
        mode="old mode",
        approved_actions=("old action",),
    )
    latest = ApprovalSlice(
        approval_id="mission-latest",
        lane="latest lane",
        mode="focused tests only",
        approved_actions=("add GET endpoint", "add compact panel"),
        forbidden_actions=("push", "deploy"),
        approver="Travis",
        approved_at="2026-06-05T01:00:00Z",
        expires_at="2026-06-06T01:00:00Z",
        metadata={
            "status": "active",
            "reason": "bounded implementation",
            "risk_class": "low",
            "required_approver": "Travis",
            "internal_note": "do not expose this",
        },
    )
    goal = GoalContract(goal_id="goal-approval", statement="Summarize approvals.")
    control = TaskControlEnvelope(active_lane="latest lane", mode="focused tests only")
    store.append(old)
    store.append(
        MissionBrief(
            mission_id="mission-approval",
            title="Approval summaries",
            created_at="2026-06-05T01:01:00Z",
            goal=goal,
            control=control,
            approvals=(latest,),
            evidence=(EvidenceCard(evidence_id="ev-linked", summary="Supports approval"),),
        )
    )

    response = client.get("/api/plugins/mission-control-governance/approval-slices")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "MissionBrief.approvals"
    assert payload["count"] == 1
    assert payload["approval_slices"] == [
        {
            "approval_id": "mission-latest",
            "lane": "latest lane",
            "mode": "focused tests only",
            "approver": "Travis",
            "approved_at": "2026-06-05T01:00:00Z",
            "expires_at": "2026-06-06T01:00:00Z",
            "approved_action_count": 2,
            "forbidden_action_count": 2,
            "evidence_count": 1,
            "status": "active",
            "reason": "bounded implementation",
            "risk_class": "low",
            "required_approver": "Travis",
        }
    ]
    assert "metadata" not in payload["approval_slices"][0]
    assert "internal_note" not in str(payload)


def test_approval_slices_uses_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        ApprovalSlice(
            approval_slice_id="standalone-approval",
            related_action_id="action-1",
            approval_type="operator",
            decision_state="pending",
            required_by="Travis",
            reason="Bounded read-only inspection.",
            safety_conditions=("write records",),
            evidence_ids=("evidence-1",),
            created_at="2026-06-05T02:00:00Z",
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/approval-slices").json()

    assert payload["source"] == "ApprovalSlice"
    assert payload["count"] == 1
    assert payload["approval_slices"][0] == {
        "record_index": 0,
        "approval_slice_id": "standalone-approval",
        "related_action_id": "action-1",
        "approval_type": "operator",
        "decision_state": "pending",
        "required_by": "Travis",
        "reason": "Bounded read-only inspection.",
        "safety_condition_count": 1,
        "evidence_count": 1,
        "created_at": "2026-06-05T02:00:00Z",
        "expires_at": None,
    }


def test_evidence_cards_prefers_latest_mission_brief_evidence(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old = EvidenceCard(evidence_id="standalone-old", summary="Old evidence")
    latest = EvidenceCard(
        evidence_id="mission-evidence",
        summary="Focused tests demonstrate inert summaries.",
        artifact_refs=(
            ArtifactRef(
                ref_id="artifact-1",
                kind="test-log",
                location="tests/plugins/test_mission_control_governance_plugin.py",
                description="focused test",
                metadata={"blob": "do not dump"},
            ),
        ),
        metadata={
            "title": "Focused test log",
            "type": "test",
            "source": "pytest",
            "transcript": "do not include transcript",
            "artifact_blob": "do not include blob",
        },
    )
    goal = GoalContract(goal_id="goal-evidence", statement="Summarize evidence.")
    control = TaskControlEnvelope(active_lane="evidence lane", mode="focused tests only")
    store.append(old)
    store.append(
        MissionBrief(
            mission_id="mission-evidence",
            title="Evidence summaries",
            created_at="2026-06-05T03:00:00Z",
            goal=goal,
            control=control,
            evidence=(latest,),
        )
    )

    response = client.get("/api/plugins/mission-control-governance/evidence-cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "MissionBrief.evidence"
    assert payload["count"] == 1
    assert payload["evidence_cards"] == [
        {
            "evidence_id": "mission-evidence",
            "summary": "Focused tests demonstrate inert summaries.",
            "artifact_count": 1,
            "artifact_refs_count": 1,
            "title": "Focused test log",
            "type": "test",
            "source": "pytest",
        }
    ]
    assert "metadata" not in payload["evidence_cards"][0]
    assert "artifact_refs" not in payload["evidence_cards"][0]
    assert "transcript" not in str(payload).lower()
    assert "blob" not in str(payload).lower()


def test_evidence_cards_uses_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        EvidenceCard(
            evidence_id="standalone-evidence",
            related_lane="PR-H",
            related_action_id="action-1",
            related_record_type="OperatorAction",
            summary="Fallback evidence summary.",
            evidence_type="test",
            source_label="pytest",
            created_at="2026-06-05T03:00:00Z",
            risk_notes=("No raw metadata exposed.",),
            artifact_refs=(ArtifactRef(ref_id="artifact-1", kind="log", location="focused.log"),),
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/evidence-cards").json()

    assert payload["source"] == "EvidenceCard"
    assert payload["count"] == 1
    assert payload["evidence_cards"][0] == {
        "record_index": 0,
        "evidence_id": "standalone-evidence",
        "related_lane": "PR-H",
        "related_action_id": "action-1",
        "related_record_type": "OperatorAction",
        "summary": "Fallback evidence summary.",
        "evidence_type": "test",
        "source_label": "pytest",
        "created_at": "2026-06-05T03:00:00Z",
        "risk_note_count": 1,
        "artifact_count": 1,
        "artifact_refs_count": 1,
    }



def test_summary_style_routes_do_not_call_read_all(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    goal = GoalContract(goal_id="goal-bounded", statement="Bounded summaries only.")
    control = TaskControlEnvelope(active_lane="bounded lane", mode="focused tests only")
    store.append(TaskControlEnvelope(active_lane="fallback lane", mode="read-only"))
    store.append(
        ApprovalSlice(
            approval_id="standalone-approval",
            lane="bounded lane",
            mode="focused tests only",
        )
    )
    store.append(EvidenceCard(evidence_id="standalone-evidence", summary="Standalone evidence"))
    store.append(StartGateCheck(start_gate_id="gate-bounded", envelope_id="envelope-bounded"))
    store.append(
        MissionBrief(
            mission_id="mission-bounded",
            title="Bounded summaries",
            created_at="2026-06-05T04:00:00Z",
            goal=goal,
            control=control,
            approvals=(
                ApprovalSlice(
                    approval_id="mission-approval",
                    lane="bounded lane",
                    mode="focused tests only",
                ),
            ),
            evidence=(EvidenceCard(evidence_id="mission-evidence", summary="Mission evidence"),),
        )
    )

    def fail_read_all(self, record_class=None):
        raise AssertionError("summary route unexpectedly called read_all")

    monkeypatch.setattr(JsonlRecordStore, "read_all", fail_read_all)

    summary = client.get("/api/plugins/mission-control-governance/summary")
    start_gate = client.get("/api/plugins/mission-control-governance/start-gate")
    approvals = client.get("/api/plugins/mission-control-governance/approval-slices")
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards")
    actions = client.get("/api/plugins/mission-control-governance/operator-actions")
    envelopes = client.get("/api/plugins/mission-control-governance/task-control-envelopes")
    checks = client.get("/api/plugins/mission-control-governance/start-gate-checks")

    assert summary.status_code == 200
    assert start_gate.status_code == 200
    assert approvals.status_code == 200
    assert evidence.status_code == 200
    assert actions.status_code == 200
    assert envelopes.status_code == 200
    assert checks.status_code == 200
    assert summary.json()["record_count"] == 5
    assert start_gate.json()["source"] == "MissionBrief.control"
    assert approvals.json()["source"] == "MissionBrief.approvals"
    assert evidence.json()["source"] == "MissionBrief.evidence"
    assert envelopes.json()["source"] == "TaskControlEnvelope"
    assert checks.json()["source"] == "StartGateCheck"


def test_latest_standalone_fallback_preserves_original_record_index(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(GoalContract(goal_id="goal-index", statement="Unrelated record"))
    store.append(TaskControlEnvelope(active_lane="fallback lane", mode="read-only"))

    payload = client.get("/api/plugins/mission-control-governance/start-gate").json()

    assert payload["source"] == "TaskControlEnvelope"
    assert payload["record_index"] == 1


def test_approval_and_evidence_summaries_are_bounded_to_latest_10(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            ApprovalSlice(
                approval_id=f"approval-{index}",
                lane="bounded lane",
                mode="read-only",
            )
        )
        store.append(
            EvidenceCard(
                evidence_id=f"evidence-{index}",
                summary=f"Evidence {index}",
            )
        )

    approvals = client.get("/api/plugins/mission-control-governance/approval-slices").json()
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards").json()

    assert approvals["source"] == "ApprovalSlice"
    assert approvals["count"] == 10
    assert [item["approval_id"] for item in approvals["approval_slices"]] == [
        f"approval-{index}" for index in range(2, 12)
    ]
    assert evidence["source"] == "EvidenceCard"
    assert evidence["count"] == 10
    assert [item["evidence_id"] for item in evidence["evidence_cards"]] == [
        f"evidence-{index}" for index in range(2, 12)
    ]

def test_malformed_store_returns_inert_error_payload(plugin_api, client):
    path = plugin_api.record_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json}\n", encoding="utf-8")

    summary = client.get("/api/plugins/mission-control-governance/summary")
    records = client.get("/api/plugins/mission-control-governance/records")
    detail = client.get("/api/plugins/mission-control-governance/records/0")

    assert summary.status_code == 200
    assert records.status_code == 200
    assert detail.status_code == 409

    summary_payload = summary.json()
    records_payload = records.json()
    assert summary_payload["record_count"] == 0
    assert summary_payload["record_types"] == {}
    assert summary_payload["store_status"] == "malformed"
    assert "line 1" in summary_payload["error"]
    assert records_payload["count"] == 0
    assert records_payload["records"] == []
    assert records_payload["store_status"] == "malformed"
    assert "line 1" in records_payload["error"]
    assert detail.json()["detail"] == "record store is malformed"


def test_plugin_has_no_runtime_tool_gateway_or_subprocess_imports():
    forbidden = (
        "subprocess",
        "tools.",
        "tools import",
        "gateway.",
        "gateway import",
        "run_agent",
        "resolve_gateway_approval",
        "tools.approval",
        "transcript",
    )
    for path in (
        PLUGIN_DIR / "__init__.py",
        PLUGIN_DIR / "api.py",
        PLUGIN_DIR / "dashboard" / "plugin_api.py",
    ):
        text = path.read_text()
        lowered = text.lower()
        assert not any(token in lowered for token in forbidden), path


def test_dashboard_bundle_registers_read_only_tab_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    lowered = bundle.lower()

    assert '__HERMES_PLUGINS__.register("mission-control-governance"' in bundle
    assert "/api/plugins/mission-control-governance/summary" in bundle
    assert "/api/plugins/mission-control-governance/start-gate" in bundle
    assert "/api/plugins/mission-control-governance/task-control-envelopes" in bundle
    assert "/api/plugins/mission-control-governance/start-gate-checks" in bundle
    assert "/api/plugins/mission-control-governance/approval-slices" in bundle
    assert "/api/plugins/mission-control-governance/evidence-cards" in bundle
    assert "/api/plugins/mission-control-governance/operator-actions" in bundle
    assert "Operator Action Queue" in bundle
    assert "Task Control Envelopes" in bundle
    assert "Start Gate Checks" in bundle
    assert "/api/plugins/mission-control-governance/records" in bundle
    assert "/api/plugins/mission-control-governance/schema" in bundle
    assert "RECORD_DETAIL_URL" in bundle
    assert "method:" not in lowered
    for token in (
        "post(",
        "put(",
        "patch(",
        "delete(",
        "execute",
        "approve(",
        "deny(",
        "transcript",
        "resolve_gateway_approval",
        "tools.approval",
    ):
        assert token not in lowered


def test_operator_actions_empty_missing_store_returns_bounded_empty_payload(client):
    response = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert response.status_code == 200
    assert response.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "operator_actions": [],
    }


def test_operator_actions_uses_latest_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(GoalContract(goal_id="goal-action", statement="Unrelated record"))
    store.append(
        OperatorAction(
            action_id="action-standalone",
            title="Review bounded queue",
            lane="PR-G",
            mode="focused tests only",
            requested_action="Review requested action summary.",
            risk_level="low",
            status="requested",
            required_approval="manual approval",
            approval_id="approval-1",
            evidence_ids=("evidence-1", "evidence-2"),
            stop_condition="Stop after tests.",
            created_at="2026-06-05T12:00:00Z",
            expires_at="2026-06-06T12:00:00Z",
            metadata={
                "source": "planning",
                "transcript": "do not expose",
                "artifact_blob": "do not expose",
                "broad_context": "do not expose",
            },
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "OperatorAction"
    assert payload["count"] == 1
    assert payload["operator_actions"] == [
        {
            "record_index": 1,
            "action_id": "action-standalone",
            "title": "Review bounded queue",
            "lane": "PR-G",
            "mode": "focused tests only",
            "requested_action": "Review requested action summary.",
            "risk_level": "low",
            "status": "requested",
            "required_approval": "manual approval",
            "approval_id": "approval-1",
            "evidence_count": 2,
            "stop_condition": "Stop after tests.",
            "created_at": "2026-06-05T12:00:00Z",
            "expires_at": "2026-06-06T12:00:00Z",
            "source": "planning",
        }
    ]
    assert "metadata" not in payload["operator_actions"][0]
    assert "evidence_ids" not in payload["operator_actions"][0]
    lowered = str(payload).lower()
    assert "transcript" not in lowered
    assert "artifact_blob" not in lowered
    assert "broad_context" not in lowered


def test_operator_actions_are_bounded_to_latest_10(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            OperatorAction(
                action_id=f"action-{index}",
                title=f"Action {index}",
                lane="bounded lane",
                mode="read-only",
                requested_action=f"Review action {index}.",
            )
        )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["source"] == "OperatorAction"
    assert payload["count"] == 10
    assert [item["action_id"] for item in payload["operator_actions"]] == [
        f"action-{index}" for index in range(2, 12)
    ]


def test_operator_actions_are_descriptive_context_only(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-inert",
            title="Request manual review",
            lane="governance lane",
            mode="read-only",
            requested_action="Review this summary manually.",
            metadata={"can_run": True, "command": "ignored"},
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["operator_actions"][0]["status"] == "requested"
    assert "can_run" not in str(payload)
    assert "command" not in str(payload)


def test_operator_actions_do_not_read_mission_brief_metadata(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        MissionBrief(
            mission_id="mission-action-metadata",
            title="Metadata requested action",
            created_at="2026-06-05T13:00:00Z",
            goal=GoalContract(goal_id="goal-action-metadata", statement="Do not infer actions."),
            control=TaskControlEnvelope(active_lane="metadata lane", mode="read-only"),
            metadata={
                "operator_actions": [
                    {
                        "action_id": "metadata-action",
                        "title": "Do not expose",
                        "requested_action": "Do not infer from mission metadata.",
                    }
                ]
            },
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["source"] == "none"
    assert payload["count"] == 0
    assert payload["operator_actions"] == []


def test_summary_style_routes_include_operator_actions_without_read_all(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-bounded",
            title="Bounded action",
            lane="bounded lane",
            mode="read-only",
            requested_action="Read compact summary.",
        )
    )

    def fail_read_all(self, record_class=None):
        raise AssertionError("summary route unexpectedly called read_all")

    monkeypatch.setattr(JsonlRecordStore, "read_all", fail_read_all)

    response = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert response.status_code == 200
    assert response.json()["source"] == "OperatorAction"
