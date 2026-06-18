"""Tests for foreground /codex-handoff handling in tui_gateway."""

from __future__ import annotations

import importlib
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


@pytest.fixture()
def server(hermes_home: Path):
    with patch.dict(
        "sys.modules",
        {
            "hermes_cli.env_loader": MagicMock(),
            "hermes_cli.banner": MagicMock(),
        },
    ):
        mod = importlib.import_module("tui_gateway.server")
        yield mod
        mod._sessions.clear()
        mod._pending.clear()
        mod._answers.clear()


@pytest.fixture()
def session(server):
    sid = "sid-codex-handoff"
    session_key = "tui-codex-handoff-session-1"
    server._sessions[sid] = {
        "session_key": session_key,
        "history": [],
        "history_lock": threading.Lock(),
        "history_version": 0,
        "running": False,
        "attached_images": [],
        "cols": 120,
    }
    return sid, session_key


def _call(server, method: str, **params):
    return server._methods[method](1, params)


def test_codex_handoff_dispatch_lifecycle_uses_foreground_review_gate(server, session, hermes_home: Path):
    sid, session_key = session

    created = _call(
        server,
        "command.dispatch",
        name="codex-handoff",
        arg="create Re-run phone compact validation and return evidence.",
        session_id=sid,
    )

    assert "error" not in created
    assert created["result"]["type"] == "exec"
    output = created["result"]["output"]
    assert "Queued Codex handoff codex-" in output
    packet_id = output.split("Queued Codex handoff ", 1)[1].split(".", 1)[0]

    store_path = hermes_home / "codex_handoffs.json"
    assert store_path.exists()
    stored = store_path.read_text(encoding="utf-8")
    assert session_key in stored
    assert "Re-run phone compact validation" in stored

    claimed = _call(
        server,
        "command.dispatch",
        name="codex",
        arg=f"claim {packet_id}",
        session_id=sid,
    )
    claim_output = claimed["result"]["output"]
    assert "Codex foreground work packet" in claim_output
    assert "Manual/foreground only" in claim_output
    assert "never starts a daemon" in claim_output

    returned = _call(
        server,
        "command.dispatch",
        name="codex-handoff",
        arg=(
            f"return {packet_id} "
            "Changed files: tests/web/test_mission_control_compact_page.py "
            "Tests: focused tests passed "
            "PR: none "
            "Blockers: none "
            "Evidence: phone compact validation covered"
        ),
        session_id=sid,
    )
    assert returned["result"]["type"] == "exec"
    assert "for Jenny review" in returned["result"]["output"]

    reviewed = _call(
        server,
        "command.dispatch",
        name="codex-handoff",
        arg=f"review {packet_id} approve Evidence reviewed against the returned files and tests.",
        session_id=sid,
    )
    assert reviewed["result"]["type"] == "exec"
    assert "Jenny may report done" in reviewed["result"]["output"]


def test_slash_exec_rejects_codex_handoff_for_command_dispatch(server, session):
    sid, _ = session

    response = _call(server, "slash.exec", command="codex-handoff list", session_id=sid)

    assert "error" in response
    assert response["error"]["code"] == 4018
    assert "pending-input command" in response["error"]["message"]
    assert "command.dispatch" in response["error"]["message"]


def test_pending_input_commands_includes_codex_handoff_aliases(server):
    assert "codex-handoff" in server._PENDING_INPUT_COMMANDS
    assert "codex" in server._PENDING_INPUT_COMMANDS
