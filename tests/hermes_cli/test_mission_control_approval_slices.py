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
        lambda: {"dashboard": {"approval_slices_enabled": True}},
    )
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def _valid_payload(**overrides):
    payload = {
        "title": "G3 approval slice",
        "repo_path": "/home/jenny/project",
        "allowed_paths": ["hermes_cli/mission_control_approval_slices.py"],
        "forbidden_paths": ["web/src/lib/api.ts"],
        "expected_locality": "local checkout only",
        "allowed_actions": ["inspect_repo", "read_files", "edit_files", "run_focused_tests"],
        "forbidden_actions": ["deploy", "restart_service", "external_network"],
        "stop_condition": "stop_after_validation_report",
        "checkpoint": "stop_after_validation_report",
        "linked_goal_contract_id": "contract_20260602T000000Z_abcdef123456",
        "created_by": "Travis",
        "created_from": "manual_command",
        "raw_user_approval": "Approved to implement G3 backend/store/API only.",
    }
    payload.update(overrides)
    return payload


def test_approval_slice_routes_require_dashboard_token(_isolate_hermes_home):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import app

    client = TestClient(app)
    assert client.get("/api/mission-control/approval-slices").status_code == 401
    assert client.post("/api/mission-control/approval-slices", json={}).status_code == 401
    assert client.get("/api/mission-control/approval-slices/slice_demo").status_code == 401
    assert client.post("/api/mission-control/approval-slices/slice_demo/revoke").status_code == 401
    assert client.post("/api/mission-control/approval-slices/slice_demo/expire").status_code == 401
    assert client.post("/api/mission-control/approval-slices/slice_demo/complete").status_code == 401


def test_approval_slice_routes_are_not_public():
    from hermes_cli.web_server import _PUBLIC_API_PATHS

    assert "/api/mission-control/approval-slices" not in _PUBLIC_API_PATHS


def test_approval_slices_feature_flag_default_disabled(_isolate_hermes_home, monkeypatch):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli import web_server
    from hermes_cli.config import DEFAULT_CONFIG
    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    assert DEFAULT_CONFIG["dashboard"]["approval_slices_enabled"] is False
    monkeypatch.setattr(web_server, "load_config", lambda: {})
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    resp = client.get("/api/mission-control/approval-slices")

    assert resp.status_code == 404
    assert "disabled" in resp.json()["detail"]


def test_create_sets_active_and_stores_inert_record(dashboard_client):
    from hermes_constants import get_hermes_home

    resp = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload())

    assert resp.status_code == 200
    record = resp.json()["approval_slice"]
    assert record["status"] == "active"
    assert record["title"] == "G3 approval slice"
    assert record["trusted_for_execution"] is False
    assert record["inert_context_only"] is True
    assert record["vocabulary_version"] == "g1"
    assert record["revoked_at"] is None
    assert record["expired_at"] is None
    assert record["completed_at"] is None

    state_dir = get_hermes_home() / "state" / "mission-control" / "approval-slices"
    audit_path = get_hermes_home() / "state" / "mission-control" / "approval-slices-audit.jsonl"
    assert (state_dir / f"{record['id']}.json").is_file()
    assert "approval_slice_created" in audit_path.read_text(encoding="utf-8")


def test_invalid_draft_and_archived_statuses_are_rejected(dashboard_client):
    for status in ("draft", "archived"):
        resp = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload(status=status))
        assert resp.status_code == 400
        assert "status" in resp.json()["detail"]


def test_revoke_expire_complete_set_status_and_timestamps(dashboard_client):
    records = []
    for action, status, timestamp_field in (
        ("revoke", "revoked", "revoked_at"),
        ("expire", "expired", "expired_at"),
        ("complete", "completed", "completed_at"),
    ):
        created = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload(title=action))
        assert created.status_code == 200
        slice_id = created.json()["approval_slice"]["id"]

        transitioned = dashboard_client.post(f"/api/mission-control/approval-slices/{slice_id}/{action}")

        assert transitioned.status_code == 200
        record = transitioned.json()["approval_slice"]
        assert record["status"] == status
        assert record[timestamp_field]
        assert record["updated_at"] == record[timestamp_field]
        records.append(record)

    assert {record["status"] for record in records} == {"revoked", "expired", "completed"}


def test_default_list_returns_active_only_and_include_inactive_includes_all(dashboard_client):
    active = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload(title="active")).json()[
        "approval_slice"
    ]
    inactive_ids = set()
    for action in ("revoke", "expire", "complete"):
        created = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload(title=action)).json()[
            "approval_slice"
        ]
        transitioned = dashboard_client.post(f"/api/mission-control/approval-slices/{created['id']}/{action}").json()[
            "approval_slice"
        ]
        inactive_ids.add(transitioned["id"])

    default_list = dashboard_client.get("/api/mission-control/approval-slices")
    assert default_list.status_code == 200
    assert {item["id"] for item in default_list.json()["items"]} == {active["id"]}

    include_inactive = dashboard_client.get("/api/mission-control/approval-slices?include_inactive=true")
    assert include_inactive.status_code == 200
    all_ids = {item["id"] for item in include_inactive.json()["items"]}
    assert all_ids == {active["id"], *inactive_ids}


def test_direct_read_returns_inactive_records(dashboard_client):
    created = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload()).json()["approval_slice"]
    dashboard_client.post(f"/api/mission-control/approval-slices/{created['id']}/revoke")

    detail = dashboard_client.get(f"/api/mission-control/approval-slices/{created['id']}")

    assert detail.status_code == 200
    assert detail.json()["approval_slice"]["status"] == "revoked"


def test_invalid_actions_checkpoint_stop_condition_and_created_from_are_rejected(dashboard_client):
    cases = [
        ("allowed_actions", ["not_g1"]),
        ("forbidden_actions", ["not_g1"]),
        ("checkpoint", "not_g1"),
        ("stop_condition", "not_g1"),
        ("created_from", "discord_thread"),
    ]
    for field, value in cases:
        resp = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload(**{field: value}))
        assert resp.status_code == 400
        assert field in resp.json()["detail"]


def test_records_remain_inert_and_do_not_call_runtime_paths(dashboard_client, monkeypatch):
    import gateway.run as gateway_run
    import hermes_cli.goals as runtime_goals
    import model_tools
    import tools.approval as runtime_approval

    def fail(*args, **kwargs):
        raise AssertionError("Approval Slice records must remain inert")

    monkeypatch.setattr(runtime_goals, "load_goal", fail)
    monkeypatch.setattr(runtime_goals, "save_goal", fail)
    monkeypatch.setattr(runtime_goals, "GoalManager", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_handle_goal_command", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_handle_approve_command", fail)
    monkeypatch.setattr(gateway_run.GatewayRunner, "_persist_safe_goal_task_contract", fail, raising=False)
    monkeypatch.setattr(model_tools, "handle_function_call", fail)
    monkeypatch.setattr(runtime_approval, "request_approval", fail, raising=False)

    created = dashboard_client.post("/api/mission-control/approval-slices", json=_valid_payload())
    assert created.status_code == 200
    slice_id = created.json()["approval_slice"]["id"]
    assert dashboard_client.post(f"/api/mission-control/approval-slices/{slice_id}/complete").status_code == 200


def test_path_and_locality_fields_are_opaque_and_do_not_stat_fetch_expand_or_normalize(dashboard_client, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("Approval Slice paths/locality must not be fetched")

    def fail_command(*args, **kwargs):
        raise AssertionError("Approval Slice paths/locality must not trigger commands")

    def fail_expanduser(*args, **kwargs):
        raise AssertionError("Approval Slice paths/locality must not be expanded")

    original_stat = Path.stat
    watched = {
        "~/not-expanded",
        "../not-normalized/../value",
        "/tmp/does-not-need-to-exist",
    }

    def guarded_stat(self, *args, **kwargs):
        if str(self) in watched:
            raise AssertionError("Approval Slice paths/locality must not be statted")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    monkeypatch.setattr(subprocess, "run", fail_command)
    monkeypatch.setattr(subprocess, "Popen", fail_command)
    monkeypatch.setattr(os.path, "expanduser", fail_expanduser)
    monkeypatch.setattr(Path, "expanduser", fail_expanduser)
    monkeypatch.setattr(Path, "stat", guarded_stat)

    payload = _valid_payload(
        repo_path="~/not-expanded",
        allowed_paths=["../not-normalized/../value", "/tmp/does-not-need-to-exist"],
        forbidden_paths=["https://example.invalid/never-fetch"],
        expected_locality="literal locality https://example.invalid/no-fetch",
    )
    resp = dashboard_client.post("/api/mission-control/approval-slices", json=payload)

    assert resp.status_code == 200
    record = resp.json()["approval_slice"]
    assert record["repo_path"] == payload["repo_path"]
    assert record["allowed_paths"] == payload["allowed_paths"]
    assert record["forbidden_paths"] == payload["forbidden_paths"]
    assert record["expected_locality"] == payload["expected_locality"]


def test_audit_jsonl_redacts_secrets(dashboard_client):
    from hermes_constants import get_hermes_home

    resp = dashboard_client.post(
        "/api/mission-control/approval-slices",
        json=_valid_payload(
            raw_user_approval="Authorization: Bearer APPROVALSECRET",
            allowed_paths=["api_key=PATHSECRET"],
            metadata={"token": "METADATASECRET"},
        ),
    )

    assert resp.status_code == 200
    rendered = json.dumps(resp.json())
    assert "APPROVALSECRET" not in rendered
    assert "PATHSECRET" not in rendered
    assert "METADATASECRET" not in rendered

    record = resp.json()["approval_slice"]
    stored = (
        get_hermes_home()
        / "state"
        / "mission-control"
        / "approval-slices"
        / f"{record['id']}.json"
    ).read_text(encoding="utf-8")
    audit = (
        get_hermes_home() / "state" / "mission-control" / "approval-slices-audit.jsonl"
    ).read_text(encoding="utf-8")
    assert "APPROVALSECRET" not in stored
    assert "PATHSECRET" not in stored
    assert "METADATASECRET" not in stored
    assert "APPROVALSECRET" not in audit
    assert "PATHSECRET" not in audit
    assert "METADATASECRET" not in audit
