from __future__ import annotations

import json
import subprocess
import urllib.request

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
        lambda: {"dashboard": {"mission_briefs_enabled": True}},
    )
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def test_mission_brief_routes_require_dashboard_token(_isolate_hermes_home):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli.web_server import app

    client = TestClient(app)
    assert client.get("/api/mission-control/mission-briefs").status_code == 401
    assert client.post("/api/mission-control/mission-briefs", json={"title": "x"}).status_code == 401
    assert client.get("/api/mission-control/mission-briefs/brief_demo").status_code == 401
    assert client.put("/api/mission-control/mission-briefs/brief_demo", json={"title": "x"}).status_code == 401
    assert client.delete("/api/mission-control/mission-briefs/brief_demo").status_code == 401


def test_mission_brief_routes_are_not_public():
    from hermes_cli.web_server import _PUBLIC_API_PATHS

    assert "/api/mission-control/mission-briefs" not in _PUBLIC_API_PATHS


def test_mission_briefs_feature_flag_default_disabled(_isolate_hermes_home, monkeypatch):
    try:
        from starlette.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/starlette not installed")

    from hermes_cli import web_server
    from hermes_cli.config import DEFAULT_CONFIG
    from hermes_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

    assert DEFAULT_CONFIG["dashboard"]["mission_briefs_enabled"] is False
    monkeypatch.setattr(web_server, "load_config", lambda: {})
    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    resp = client.get("/api/mission-control/mission-briefs")

    assert resp.status_code == 404
    assert "disabled" in resp.json()["detail"]


def test_create_read_update_archive_mission_brief(dashboard_client):
    from hermes_constants import get_hermes_home

    create = dashboard_client.post(
        "/api/mission-control/mission-briefs",
        json={
            "title": "Phase 1A brief",
            "summary": "Inert local brief.",
            "references": ["discord://thread/123", "/home/jenny/demo path"],
            "author": "Travis",
        },
    )

    assert create.status_code == 200
    brief = create.json()["brief"]
    assert brief["title"] == "Phase 1A brief"
    assert brief["summary"] == "Inert local brief."
    assert brief["references"] == ["discord://thread/123", "/home/jenny/demo path"]
    assert brief["status"] == "active"
    assert brief["trusted_for_execution"] is False
    assert brief["inert_context_only"] is True

    get_resp = dashboard_client.get(f"/api/mission-control/mission-briefs/{brief['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["brief"]["id"] == brief["id"]

    update = dashboard_client.put(
        f"/api/mission-control/mission-briefs/{brief['id']}",
        json={"title": "Updated brief", "references": ["~/literal", "https://example.invalid/a?b=c"]},
    )
    assert update.status_code == 200
    updated = update.json()["brief"]
    assert updated["title"] == "Updated brief"
    assert updated["references"] == ["~/literal", "https://example.invalid/a?b=c"]

    archive = dashboard_client.delete(f"/api/mission-control/mission-briefs/{brief['id']}")
    assert archive.status_code == 200
    assert archive.json()["brief"]["status"] == "archived"

    list_resp = dashboard_client.get("/api/mission-control/mission-briefs")
    assert list_resp.status_code == 200
    assert list_resp.json()["items"][0]["status"] == "archived"

    state_dir = get_hermes_home() / "state" / "mission-control" / "mission-briefs"
    audit_path = get_hermes_home() / "state" / "mission-control" / "mission-briefs-audit.jsonl"
    assert state_dir.is_dir()
    assert (state_dir / f"{brief['id']}.json").is_file()
    assert "brief_archived" in audit_path.read_text(encoding="utf-8")


def test_opaque_reference_storage_keeps_path_and_url_strings_unmodified(dashboard_client, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("URL-like references must not be fetched")

    def fail_command(*args, **kwargs):
        raise AssertionError("Mission Brief references must not trigger commands")

    monkeypatch.setattr(urllib.request, "urlopen", fail_network)
    monkeypatch.setattr(subprocess, "run", fail_command)
    monkeypatch.setattr(subprocess, "Popen", fail_command)

    refs = [
        "~/not-expanded",
        "../not-normalized/../value",
        "/tmp/does-not-need-to-exist",
        "https://example.invalid/never-fetch?token=still-opaque",
    ]

    resp = dashboard_client.post(
        "/api/mission-control/mission-briefs",
        json={"title": "Opaque refs", "references": refs},
    )

    assert resp.status_code == 200
    brief = resp.json()["brief"]
    assert brief["references"] == refs

    detail = dashboard_client.get(f"/api/mission-control/mission-briefs/{brief['id']}")
    assert detail.status_code == 200
    assert detail.json()["brief"]["references"] == refs


def test_mission_brief_store_does_not_use_worker_result_metadata_parser(dashboard_client, monkeypatch):
    import hermes_cli.mission_control as packets

    def fail_parser(*args, **kwargs):
        raise AssertionError("Mission Brief references must not use packet metadata parsing")

    monkeypatch.setattr(packets, "parse_worker_result_metadata", fail_parser)

    resp = dashboard_client.post(
        "/api/mission-control/mission-briefs",
        json={
            "title": "Worker-looking refs",
            "references": [
                "Repo path: /home/jenny/demo",
                "HEAD after: 2222222222222222222222222222222222222222",
            ],
        },
    )

    assert resp.status_code == 200
    assert resp.json()["brief"]["references"] == [
        "Repo path: /home/jenny/demo",
        "HEAD after: 2222222222222222222222222222222222222222",
    ]


def test_mission_brief_persistence_redacts_secrets(dashboard_client):
    from hermes_constants import get_hermes_home

    resp = dashboard_client.post(
        "/api/mission-control/mission-briefs",
        json={
            "title": "Secret brief",
            "summary": "Authorization: Bearer BRIEFSECRET",
            "references": ["api_key=REFSECRET"],
        },
    )

    assert resp.status_code == 200
    rendered = json.dumps(resp.json())
    assert "BRIEFSECRET" not in rendered
    assert "REFSECRET" not in rendered

    brief = resp.json()["brief"]
    stored = (get_hermes_home() / "state" / "mission-control" / "mission-briefs" / f"{brief['id']}.json").read_text(
        encoding="utf-8"
    )
    audit = (get_hermes_home() / "state" / "mission-control" / "mission-briefs-audit.jsonl").read_text(
        encoding="utf-8"
    )
    assert "BRIEFSECRET" not in stored
    assert "REFSECRET" not in stored
    assert "BRIEFSECRET" not in audit
    assert "REFSECRET" not in audit
