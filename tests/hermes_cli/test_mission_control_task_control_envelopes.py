from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture()
def dashboard_client(_isolate_hermes_home, monkeypatch):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    import hermes_state
    from hermes_constants import get_hermes_home
    from hermes_cli import web_server
    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    monkeypatch.setattr(hermes_state, "DEFAULT_DB_PATH", get_hermes_home() / "state.db")
    monkeypatch.setattr(
        web_server,
        "load_config",
        lambda: {"dashboard": {"task_control_envelopes_enabled": True}},
    )
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def _valid_payload(**overrides):
    payload = {
        "title": "E1C implementation",
        "mode": "implement-slice",
        "mode_label": "Implement slice",
        "allowed_actions": ["inspect_repo", "read_files", "search_files", "edit_files", "run_focused_tests"],
        "forbidden_actions": ["deploy", "restart_service", "external_network"],
        "checkpoints": ["stop_after_validation_report"],
        "checkpoint_requirements": ["stop_on_scope_expansion", "stop_on_restart_or_deploy_needed"],
        "repo_context": {
            "path": "/home/jenny/project",
            "branch": "unknown",
            "head": "unknown",
            "dirty_state": "unknown",
        },
        "lane_lock": {"active_lane": "E1C implementation"},
        "relationships": {"source_thread": "discord://thread/123"},
        "source": "manual_command",
        "raw_user_approval": "Approved to implement E1C backend/store/API only.",
        "metadata": {"reviewer": "Travis"},
    }
    payload.update(overrides)
    return payload


def test_task_control_envelope_routes_require_dashboard_token(_isolate_hermes_home):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import app

    client = TestClient(app)
    assert client.get("/api/mission-control/task-control-envelopes").status_code == 401
    assert client.post("/api/mission-control/task-control-envelopes", json={}).status_code == 401
    assert client.get("/api/mission-control/task-control-envelopes/envelope_demo").status_code == 401
    assert client.post("/api/mission-control/task-control-envelopes/envelope_demo/complete").status_code == 401
    assert client.post("/api/mission-control/task-control-envelopes/envelope_demo/archive").status_code == 401


def test_task_control_envelope_routes_are_not_public_and_expose_only_approved_methods():
    from hermes_cli.web_server import _PUBLIC_API_PATHS, app

    assert "/api/mission-control/task-control-envelopes" not in _PUBLIC_API_PATHS
    methods_by_path = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if str(path).startswith("/api/mission-control/task-control-envelopes"):
            methods_by_path.setdefault(path, set()).update(getattr(route, "methods", set()))
    assert methods_by_path["/api/mission-control/task-control-envelopes"] == {"GET", "POST"}
    assert methods_by_path["/api/mission-control/task-control-envelopes/{envelope_id}"] == {"GET"}
    assert methods_by_path["/api/mission-control/task-control-envelopes/{envelope_id}/complete"] == {"POST"}
    assert methods_by_path["/api/mission-control/task-control-envelopes/{envelope_id}/archive"] == {"POST"}


def test_task_control_envelopes_feature_flag_default_disabled(_isolate_hermes_home, monkeypatch):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli import web_server
    from hermes_cli.config import DEFAULT_CONFIG
    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    assert DEFAULT_CONFIG["dashboard"]["task_control_envelopes_enabled"] is False
    monkeypatch.setattr(web_server, "load_config", lambda: {})
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    resp = client.get("/api/mission-control/task-control-envelopes")

    assert resp.status_code == 404
    assert "disabled" in resp.json()["detail"]


def test_create_list_get_work_under_corrected_state_path(dashboard_client):
    from hermes_constants import get_hermes_home

    resp = dashboard_client.post("/api/mission-control/task-control-envelopes", json=_valid_payload())

    assert resp.status_code == 200
    record = resp.json()["task_control_envelope"]
    assert record["status"] == "active"
    assert record["title"] == "E1C implementation"
    assert record["mode"] == "implement-slice"
    assert record["mode_label"] == "Implement slice"
    assert record["trusted_for_execution"] is False
    assert record["inert_context_only"] is True
    assert record["vocabulary_version"] == "g1"
    assert record["repo_context"] == {
        "path": "/home/jenny/project",
        "branch": None,
        "head": None,
        "dirty_state": "not_probed",
        "source": "unknown",
    }

    list_resp = dashboard_client.get("/api/mission-control/task-control-envelopes")
    assert list_resp.status_code == 200
    assert [item["id"] for item in list_resp.json()["items"]] == [record["id"]]

    get_resp = dashboard_client.get(f"/api/mission-control/task-control-envelopes/{record['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_control_envelope"]["id"] == record["id"]

    state_dir = get_hermes_home() / "state" / "mission-control" / "task-control-envelopes"
    audit_path = get_hermes_home() / "state" / "mission-control" / "task-control-envelopes-audit.jsonl"
    assert state_dir.is_dir()
    assert (state_dir / f"{record['id']}.json").is_file()
    assert "task_control_envelope_created" in audit_path.read_text(encoding="utf-8")


def test_complete_and_archive_set_status_and_timestamps_only(dashboard_client):
    created = dashboard_client.post("/api/mission-control/task-control-envelopes", json=_valid_payload()).json()[
        "task_control_envelope"
    ]

    completed = dashboard_client.post(f"/api/mission-control/task-control-envelopes/{created['id']}/complete")

    assert completed.status_code == 200
    completed_record = completed.json()["task_control_envelope"]
    assert completed_record["status"] == "completed"
    assert completed_record["completed_at"]
    assert completed_record["updated_at"] == completed_record["completed_at"]
    assert completed_record["archived_at"] is None
    assert completed_record["mode"] == created["mode"]
    assert completed_record["allowed_actions"] == created["allowed_actions"]
    assert completed_record["forbidden_actions"] == created["forbidden_actions"]
    assert completed_record["trusted_for_execution"] is False
    assert completed_record["inert_context_only"] is True

    archived = dashboard_client.post(f"/api/mission-control/task-control-envelopes/{created['id']}/archive")

    assert archived.status_code == 200
    archived_record = archived.json()["task_control_envelope"]
    assert archived_record["status"] == "archived"
    assert archived_record["archived_at"]
    assert archived_record["updated_at"] == archived_record["archived_at"]
    assert archived_record["completed_at"] == completed_record["completed_at"]


def test_status_mode_action_and_checkpoint_validation(dashboard_client):
    invalid_cases = [
        ("status", "draft"),
        ("status", "revoked"),
        ("mode", "Implement slice"),
        ("mode", "documentation-only"),
        ("allowed_actions", ["not_g1"]),
        ("forbidden_actions", ["not_g1"]),
        ("checkpoints", ["not_g1"]),
        ("checkpoint_requirements", ["not_g1"]),
    ]
    for field, value in invalid_cases:
        resp = dashboard_client.post(
            "/api/mission-control/task-control-envelopes",
            json=_valid_payload(**{field: value}),
        )
        assert resp.status_code == 400
        assert field in resp.json()["detail"]

    valid = dashboard_client.post(
        "/api/mission-control/task-control-envelopes",
        json=_valid_payload(mode="discussion-only", mode_label="Documentation-only"),
    )
    assert valid.status_code == 200
    record = valid.json()["task_control_envelope"]
    assert record["mode"] == "discussion-only"
    assert record["mode_label"] == "Documentation-only"


def test_path_and_repo_fields_are_opaque_and_do_not_probe_or_normalize(dashboard_client, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("Task Control Envelope paths must not be fetched")

    def fail_command(*args, **kwargs):
        raise AssertionError("Task Control Envelope records must not trigger commands")

    def fail_expanduser(*args, **kwargs):
        raise AssertionError("Task Control Envelope paths must not be expanded")

    original_stat = Path.stat
    watched = {
        "~/not-expanded",
        "../not-normalized/../value",
        "/tmp/does-not-need-to-exist",
    }

    def guarded_stat(self, *args, **kwargs):
        if str(self) in watched:
            raise AssertionError("Task Control Envelope paths must not be statted")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    monkeypatch.setattr(subprocess, "run", fail_command)
    monkeypatch.setattr(subprocess, "Popen", fail_command)
    monkeypatch.setattr(os.path, "expanduser", fail_expanduser)
    monkeypatch.setattr(Path, "expanduser", fail_expanduser)
    monkeypatch.setattr(Path, "stat", guarded_stat)

    payload = _valid_payload(
        repo_context={
            "path": "~/not-expanded",
            "branch": "../not-normalized/../value",
            "head": "/tmp/does-not-need-to-exist",
            "dirty_state": None,
            "source": "discord_thread",
        },
        relationships={"artifact_path": "https://example.invalid/never-fetch"},
    )
    resp = dashboard_client.post("/api/mission-control/task-control-envelopes", json=payload)

    assert resp.status_code == 200
    record = resp.json()["task_control_envelope"]
    assert record["repo_context"] == {
        "path": "~/not-expanded",
        "branch": "../not-normalized/../value",
        "head": "/tmp/does-not-need-to-exist",
        "dirty_state": "not_probed",
        "source": "discord_thread",
    }
    assert record["relationships"] == payload["relationships"]


def test_records_remain_inert_and_do_not_call_runtime_paths(dashboard_client, monkeypatch):
    import gateway.run as gateway_run
    import hermes_cli.goals as runtime_goals
    import model_tools
    import tools.approval as runtime_approval

    def fail(*args, **kwargs):
        raise AssertionError("Task Control Envelope records must remain inert")

    monkeypatch.setattr(runtime_goals, "load_goal", fail)
    monkeypatch.setattr(runtime_goals, "save_goal", fail)
    monkeypatch.setattr(runtime_goals, "GoalManager", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_handle_goal_command", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_handle_approve_command", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_persist_safe_goal_task_contract", fail, raising=False)
    monkeypatch.setattr(model_tools, "handle_function_call", fail)
    monkeypatch.setattr(runtime_approval, "request_approval", fail, raising=False)

    created = dashboard_client.post("/api/mission-control/task-control-envelopes", json=_valid_payload())
    assert created.status_code == 200
    envelope_id = created.json()["task_control_envelope"]["id"]
    assert dashboard_client.post(f"/api/mission-control/task-control-envelopes/{envelope_id}/complete").status_code == 200
    assert dashboard_client.post(f"/api/mission-control/task-control-envelopes/{envelope_id}/archive").status_code == 200


def test_audit_jsonl_redacts_secrets(dashboard_client):
    from hermes_constants import get_hermes_home

    resp = dashboard_client.post(
        "/api/mission-control/task-control-envelopes",
        json=_valid_payload(
            raw_user_approval="Authorization: Bearer ENVELOPESECRET",
            repo_context={"path": "api_key=PATHSECRET"},
            metadata={"token": "METADATASECRET"},
        ),
    )

    assert resp.status_code == 200
    rendered = json.dumps(resp.json())
    assert "ENVELOPESECRET" not in rendered
    assert "PATHSECRET" not in rendered
    assert "METADATASECRET" not in rendered

    record = resp.json()["task_control_envelope"]
    stored = (
        get_hermes_home()
        / "state"
        / "mission-control"
        / "task-control-envelopes"
        / f"{record['id']}.json"
    ).read_text(encoding="utf-8")
    audit = (
        get_hermes_home() / "state" / "mission-control" / "task-control-envelopes-audit.jsonl"
    ).read_text(encoding="utf-8")
    assert "ENVELOPESECRET" not in stored
    assert "PATHSECRET" not in stored
    assert "METADATASECRET" not in stored
    assert "ENVELOPESECRET" not in audit
    assert "PATHSECRET" not in audit
    assert "METADATASECRET" not in audit


def test_active_envelope_empty_state_api_remains_unchanged_and_inert(dashboard_client, monkeypatch):
    from hermes_cli import web_server

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("active-envelope must remain unchanged and inert")

    monkeypatch.setattr(web_server, "load_config", fail_if_called)

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    assert resp.status_code == 200
    assert resp.json() == {
        "exists": False,
        "active_lane": None,
        "active_mode": None,
        "execution_boundary": "no_active_authorization",
        "allowed_actions": [],
        "forbidden_actions": [],
        "checkpoint": None,
        "repo_state": {
            "status": "unknown",
            "source": "not_probed",
        },
        "evidence": {
            "count": 0,
            "links": [],
        },
        "data_source": "no_persisted_envelope",
        "trusted_for_execution": False,
        "inert_context_only": True,
    }
