from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from mission_control.records import AcceptedBaselineRecord, JsonlRecordStore


ACCEPTED_HEAD = "2" * 40
ROLLBACK_HEAD = "3" * 40


def _write_baseline(home: Path, accepted: Path, rollback: Path) -> None:
    JsonlRecordStore(home / "mission-control" / "records.jsonl").append(
        AcceptedBaselineRecord(
            baseline_id="update-surface-test",
            recorded_at="2026-06-11T00:00:00Z",
            source="test",
            runtime_path=str(accepted),
            head=ACCEPTED_HEAD,
            rollback_runtime_path=str(rollback),
            rollback_head=ROLLBACK_HEAD,
        )
    )


@pytest.fixture
def accepted_runtime_home(tmp_path):
    home = tmp_path / "hermes-home"
    accepted = tmp_path / "accepted-runtime"
    rollback = tmp_path / "rollback-runtime"
    accepted.mkdir()
    rollback.mkdir()
    _write_baseline(home, accepted, rollback)
    token = set_hermes_home_override(home)
    try:
        yield SimpleNamespace(home=home, accepted=accepted, rollback=rollback)
    finally:
        reset_hermes_home_override(token)


def test_cli_update_blocks_before_checkout_in_accepted_runtime(
    accepted_runtime_home,
    monkeypatch,
    capsys,
):
    import hermes_cli.config as config
    import hermes_cli.main as hermes_main

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        raise AssertionError("hermes update must block before git subprocesses")

    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", accepted_runtime_home.accepted)
    monkeypatch.setattr(config, "is_managed", lambda: False)
    monkeypatch.setattr(config, "detect_install_method", lambda _root: "git")
    monkeypatch.setattr(hermes_main.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as excinfo:
        hermes_main.cmd_update(SimpleNamespace(check=False, gateway=False, yes=False, force=False))

    assert excinfo.value.code == 2
    assert all("checkout" not in cmd and "switch" not in cmd and "reset" not in cmd and "pull" not in cmd for cmd in calls)
    assert "live_runtime_update_blocked" in capsys.readouterr().out


def test_dashboard_update_route_blocks_without_spawning(
    accepted_runtime_home,
    monkeypatch,
):
    import hermes_cli.web_server as web_server

    spawned = False

    def fail_spawn(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("dashboard update must not spawn from accepted runtime")

    monkeypatch.setattr(web_server, "PROJECT_ROOT", accepted_runtime_home.accepted)
    monkeypatch.setattr(web_server, "detect_install_method", lambda _root: "git")
    monkeypatch.setattr(web_server, "_spawn_hermes_action", fail_spawn)
    web_server._ACTION_PROCS.pop("hermes-update", None)
    web_server._ACTION_RESULTS.pop("hermes-update", None)

    from fastapi.testclient import TestClient

    client = TestClient(web_server.app)
    client.headers[web_server._SESSION_HEADER_NAME] = web_server._SESSION_TOKEN

    resp = client.post("/api/hermes/update")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["pid"] is None
    assert data["error"] == "live_runtime_update_blocked"
    assert spawned is False


def test_gateway_update_blocks_without_spawning(
    accepted_runtime_home,
    monkeypatch,
):
    import gateway.run as gateway_run

    monkeypatch.setattr(gateway_run, "__file__", str(accepted_runtime_home.accepted / "gateway" / "run.py"))
    monkeypatch.setattr(gateway_run, "_resolve_hermes_bin", lambda: ["hermes"])

    source = SimpleNamespace(
        platform=gateway_run.Platform.LOCAL,
        chat_id="local",
        chat_type="direct",
        user_id="user",
        thread_id=None,
    )
    event = SimpleNamespace(source=source, message_id=None)
    gateway = SimpleNamespace(_UPDATE_ALLOWED_PLATFORMS={gateway_run.Platform.LOCAL})

    import asyncio

    result = asyncio.run(gateway_run.GatewayRunner._handle_update_command(gateway, event))

    assert "live_runtime_update_blocked" in result
