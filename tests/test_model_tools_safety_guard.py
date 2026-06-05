"""Focused Tool Guard tests for model_tools dispatch."""

import json

from model_tools import handle_function_call


def test_tool_guard_blocks_edit_tool_in_docs_only_lane(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "documentation-only hardening")
    called = False

    def fake_dispatch(*args, **kwargs):
        nonlocal called
        called = True
        return json.dumps({"ok": True})

    monkeypatch.setattr("model_tools.registry.dispatch", fake_dispatch)

    result = json.loads(handle_function_call("write_file", {"path": "AGENTS.md", "content": "x"}))

    assert called is False
    assert "STOP:" in result["error"]
    assert "write/edit" in result["error"]


def test_tool_guard_blocks_broad_tests_when_focused_tests_required(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "code implementation")
    monkeypatch.setenv("HERMES_FOCUSED_TESTS_REQUIRED", "1")
    monkeypatch.setattr(
        "model_tools.registry.dispatch",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dispatch should not run")),
    )

    result = json.loads(handle_function_call("terminal", {"command": "pytest"}))

    assert "broad test" in result["error"]


def test_tool_guard_blocks_quarantined_path_before_dispatch(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "read-only inventory")
    monkeypatch.setenv("HERMES_QUARANTINED_PATHS", "/tmp/quarantine")
    monkeypatch.setattr(
        "model_tools.registry.dispatch",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dispatch should not run")),
    )

    result = json.loads(handle_function_call("read_file", {"path": "/tmp/quarantine/file.txt"}))

    assert "quarantined path" in result["error"]
