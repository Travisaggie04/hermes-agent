"""Focused Tool Guard tests for terminal command approval checks."""

from tools.approval import check_all_command_guards


def test_command_guard_blocks_cleanup_without_cleanup_lane(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "code implementation")

    result = check_all_command_guards("rm -rf build", "local")

    assert result["approved"] is False
    assert "cleanup command" in result["message"]


def test_command_guard_blocks_parent_directory_scan(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "read-only inventory")

    result = check_all_command_guards("rg password ..", "local")

    assert result["approved"] is False
    assert "parent-directory scan" in result["message"]


def test_command_guard_blocks_quarantined_path(monkeypatch):
    monkeypatch.setenv("HERMES_ACTIVE_LANE", "read-only inventory")
    monkeypatch.setenv("HERMES_QUARANTINED_PATHS", "/tmp/quarantine")

    result = check_all_command_guards("cat /tmp/quarantine/file.txt", "local")

    assert result["approved"] is False
    assert "quarantined path" in result["message"]
