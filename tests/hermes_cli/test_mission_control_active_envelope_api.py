from __future__ import annotations

import pytest


@pytest.fixture()
def dashboard_client(_isolate_hermes_home):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def _valid_payload(**overrides):
    payload = {
        "title": "E1D implementation",
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
        "lane_lock": {"active_lane": "E1D implementation"},
        "relationships": {"source_thread": "discord://thread/456"},
        "source": "manual_command",
        "raw_user_approval": "Approved to implement E1D backend/API read model only.",
        "metadata": {"reviewer": "Travis"},
    }
    payload.update(overrides)
    return payload


def _create_envelope(**overrides):
    from hermes_cli.mission_control_task_control_envelopes import create_task_control_envelope

    return create_task_control_envelope(_valid_payload(**overrides))


def test_active_envelope_requires_dashboard_token(_isolate_hermes_home):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import app

    client = TestClient(app)

    assert client.get("/api/mission-control/active-envelope").status_code == 401


def test_active_envelope_is_not_public():
    from hermes_cli.web_server import _PUBLIC_API_PATHS

    assert "/api/mission-control/active-envelope" not in _PUBLIC_API_PATHS


def test_active_envelope_returns_exact_empty_state(dashboard_client):
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


def test_active_envelope_returns_single_persisted_active_record(dashboard_client):
    record = _create_envelope()

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    assert resp.status_code == 200
    assert resp.json() == {
        "exists": True,
        "active_lane": "E1D implementation",
        "active_mode": "implement-slice",
        "execution_boundary": "persisted_envelope_inert_non_authorizing",
        "allowed_actions": ["inspect_repo", "read_files", "search_files", "edit_files", "run_focused_tests"],
        "forbidden_actions": ["deploy", "restart_service", "external_network"],
        "checkpoint": "stop_after_validation_report",
        "repo_state": {
            "status": "not_probed",
            "source": "unknown",
        },
        "evidence": {
            "count": 1,
            "links": [],
        },
        "data_source": "persisted_task_control_envelope",
        "task_control_envelope": {
            "id": record["id"],
            "schema": "mission-control.task-control-envelope.v1",
            "status": "active",
            "title": "E1D implementation",
            "mode": "implement-slice",
            "mode_label": "Implement slice",
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "trusted_for_execution": False,
            "inert_context_only": True,
            "vocabulary_version": "g1",
        },
        "selection": {
            "selected_from_count": 1,
            "ambiguous": False,
            "selection_reason": "newest_active_updated_at",
        },
        "trusted_for_execution": False,
        "inert_context_only": True,
    }


def test_active_envelope_selects_newest_updated_at_and_marks_ambiguous(dashboard_client):
    older = _create_envelope(title="Older E1D", lane_lock={"active_lane": "older lane"})
    newer = _create_envelope(title="Newer E1D", lane_lock={"active_lane": "newer lane"})

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    body = resp.json()
    assert resp.status_code == 200
    assert body["task_control_envelope"]["id"] == newer["id"]
    assert body["active_lane"] == "newer lane"
    assert body["selection"] == {
        "selected_from_count": 2,
        "ambiguous": True,
        "selection_reason": "newest_active_updated_at",
    }
    assert body["task_control_envelope"]["updated_at"] >= older["updated_at"]


def test_active_envelope_ignores_completed_archived_and_malformed_records(dashboard_client):
    import json

    from hermes_cli.mission_control_task_control_envelopes import state_dir, transition_task_control_envelope

    active = _create_envelope(title="Active E1D")
    completed = _create_envelope(title="Completed E1D")
    archived = _create_envelope(title="Archived E1D")
    transition_task_control_envelope(completed["id"], "completed")
    transition_task_control_envelope(archived["id"], "archived")
    directory = state_dir()
    (directory / "envelope_20260603T000000Z_badbadbadbad.json").write_text("{not json", encoding="utf-8")
    (directory / "envelope_20260603T000001Z_badbadbadbad.json").write_text(
        json.dumps({"status": "active", "updated_at": "2999-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    body = resp.json()
    assert resp.status_code == 200
    assert body["task_control_envelope"]["id"] == active["id"]
    assert body["selection"]["selected_from_count"] == 1
    assert body["selection"]["ambiguous"] is False


def test_active_envelope_read_does_not_mutate_storage(dashboard_client):
    from hermes_cli.mission_control_task_control_envelopes import state_dir

    record = _create_envelope()
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in state_dir().glob("*")
        if path.is_file()
    }

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    after = {
        path.name: path.read_text(encoding="utf-8")
        for path in state_dir().glob("*")
        if path.is_file()
    }
    assert resp.status_code == 200
    assert resp.json()["task_control_envelope"]["id"] == record["id"]
    assert after == before


def test_active_envelope_does_not_call_probe_or_persistence_helpers(dashboard_client, monkeypatch):
    import hermes_cli.mission_control as mission_control
    from hermes_cli import web_server

    blocked_names = [
        "project_status",
        "open_tasks",
        "latest_worker_results",
        "repo_status",
        "approval_gates",
        "recent_audit_log",
        "list_packets",
        "get_packet",
        "save_next_codex_prompt",
        "import_worker_result",
        "set_block_flag",
        "create_rejection_audit",
    ]

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("active-envelope must not probe repo/state or persist data")

    for name in blocked_names:
        monkeypatch.setattr(mission_control, name, fail_if_called)
    monkeypatch.setattr(web_server, "load_config", fail_if_called)

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    assert resp.status_code == 200


def test_active_envelope_does_not_call_runtime_or_permission_paths(dashboard_client, monkeypatch):
    import subprocess
    from pathlib import Path

    from hermes_cli import web_server

    _create_envelope(
        repo_context={
            "path": "/tmp/active-envelope-must-not-stat",
            "branch": "unknown",
            "head": "unknown",
            "dirty_state": "unknown",
        },
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("active-envelope must not use runtime permission or probing paths")

    original_stat = Path.stat

    def guarded_stat(self, *args, **kwargs):
        if str(self) == "/tmp/active-envelope-must-not-stat":
            raise AssertionError("active-envelope must not stat opaque repo paths")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    monkeypatch.setattr(subprocess, "Popen", fail_if_called)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(web_server, "load_config", fail_if_called)

    resp = dashboard_client.get("/api/mission-control/active-envelope")

    assert resp.status_code == 200


def test_active_envelope_exposes_no_mutation_methods():
    from hermes_cli.web_server import app

    methods = {
        method
        for route in app.routes
        if getattr(route, "path", None) == "/api/mission-control/active-envelope"
        for method in getattr(route, "methods", set())
    }

    assert methods == {"GET"}
