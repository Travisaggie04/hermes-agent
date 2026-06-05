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
    GoalContract,
    JsonlRecordStore,
    MissionBrief,
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
        "/records": {"GET"},
        "/schema": {"GET"},
        "/records/{record_index}": {"GET"},
    }

    for path in ("/health", "/summary", "/start-gate", "/records", "/schema", "/records/0"):
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
        "active_lane": "Latest mission lane",
        "mode": "focused tests only",
        "allowed_actions": ["add GET endpoint", "update dashboard panel"],
        "forbidden_actions": ["run broad tests", "load transcripts"],
        "current_repo": "/tmp/latest",
        "expected_systems_files": ["plugins/mission-control-governance/api.py"],
        "stop_condition": "Stop after focused tests.",
        "other_threads_excluded": ["unrelated PR"],
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
        "approval",
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
    assert "/api/plugins/mission-control-governance/records" in bundle
    assert "/api/plugins/mission-control-governance/schema" in bundle
    assert "RECORD_DETAIL_URL" in bundle
    assert "method:" not in lowered
    for token in ("post(", "put(", "patch(", "delete(", "execute", "approve", "transcript"):
        assert token not in lowered
