"""Regression specs for active-task/workspace restart recovery."""

import json
import logging
import subprocess
import time
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from gateway.active_task import (
    ActiveTaskStore,
    build_active_task_recovery_note,
    render_safe_task_contract_for_prompt,
)
from gateway.run import GatewayRunner
from tools.process_registry import ProcessRegistry, ProcessSession


def _init_git_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)
    (path / "README.md").write_text("# Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_active_task_store_roundtrips_workspace_snapshot(tmp_path):
    store_path = tmp_path / "session_active_tasks.json"
    repo_path = tmp_path / "project"
    repo_path.mkdir()

    store = ActiveTaskStore(store_path)
    store.upsert(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        session_id="sid",
        platform="discord",
        chat_id="thread-parent",
        thread_id="thread-1",
        repo_path=str(repo_path),
        branch="main",
        head="abc123",
        command="python tools/refill.py",
        task_summary="Signal Room refill batch",
        status="active",
        process_session_id="proc_active",
        pid=12345,
        latest_log_path=str(repo_path / "runtime/refill.log"),
        latest_summary_path=str(repo_path / "runtime/refill.json"),
        resume_reason="restart_timeout",
    )

    reloaded = ActiveTaskStore(store_path).get(
        "agent:main:discord:thread:thread-parent:thread-1"
    )

    assert reloaded is not None
    assert reloaded.session_id == "sid"
    assert reloaded.platform == "discord"
    assert reloaded.chat_id == "thread-parent"
    assert reloaded.thread_id == "thread-1"
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.branch == "main"
    assert reloaded.command == "python tools/refill.py"
    assert reloaded.task_summary == "Signal Room refill batch"
    assert reloaded.status == "active"
    assert reloaded.process_session_id == "proc_active"
    assert reloaded.pid == 12345
    assert reloaded.latest_log_path.endswith("runtime/refill.log")
    assert reloaded.latest_summary_path.endswith("runtime/refill.json")
    assert reloaded.resume_reason == "restart_timeout"


def test_gateway_workspace_resolver_prefers_active_task_cwd(tmp_path, monkeypatch):
    active_repo = tmp_path / "active-project"
    systemd_cwd = tmp_path / "gateway-checkout"
    terminal_cwd = tmp_path / "terminal-cwd"
    _init_git_repo(active_repo)
    systemd_cwd.mkdir()
    terminal_cwd.mkdir()

    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    runner.active_task_store.upsert(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(active_repo),
        branch="main",
        command="python tools/refill.py",
        status="active",
    )
    monkeypatch.setenv("TERMINAL_CWD", str(terminal_cwd))

    resolved = runner._resolve_agent_working_directory(
        "agent:main:discord:thread:thread-parent:thread-1",
        fallback_cwd=str(systemd_cwd),
    )

    assert resolved == str(active_repo)
    reloaded = runner.active_task_store.get(
        "agent:main:discord:thread:thread-parent:thread-1"
    )
    assert reloaded.command == "python tools/refill.py"
    assert reloaded.process_session_id is None


def test_gateway_workspace_resolver_falls_back_to_terminal_cwd(tmp_path, monkeypatch):
    systemd_cwd = tmp_path / "gateway-checkout"
    terminal_cwd = tmp_path / "terminal-cwd"
    systemd_cwd.mkdir()
    _init_git_repo(terminal_cwd)

    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    monkeypatch.setenv("TERMINAL_CWD", str(terminal_cwd))

    resolved = runner._resolve_agent_working_directory(
        "agent:main:discord:thread:thread-parent:thread-1",
        fallback_cwd=str(systemd_cwd),
    )

    assert resolved == str(terminal_cwd)


def test_gateway_workspace_resolver_skips_placeholder_terminal_cwd_and_home_fallback(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    home.mkdir()
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    monkeypatch.setenv("TERMINAL_CWD", ".")
    monkeypatch.setattr("gateway.run.Path.home", lambda: home)

    resolved = runner._resolve_agent_working_directory(
        "agent:main:discord:thread:thread-parent:thread-1",
        fallback_cwd=str(home),
    )

    assert resolved == str(home)
    assert not store_path.exists()


def test_gateway_workspace_resolver_uses_explicit_agent_cwd_before_placeholder(
    tmp_path, monkeypatch
):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    home = tmp_path / "home"
    home.mkdir()
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    monkeypatch.setenv("TERMINAL_CWD", ".")
    monkeypatch.setattr("gateway.run.Path.home", lambda: home)

    resolved = runner._resolve_agent_working_directory(
        session_key,
        explicit_cwds=[str(repo_path)],
        fallback_cwd=str(home),
    )

    reloaded = runner.active_task_store.get(session_key)
    assert resolved == str(repo_path)
    assert reloaded is not None
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.head == expected_head


def test_gateway_workspace_resolver_skips_non_git_terminal_cwd(tmp_path, monkeypatch):
    systemd_cwd = tmp_path / "gateway-checkout"
    terminal_cwd = tmp_path / "terminal-cwd"
    systemd_cwd.mkdir()
    terminal_cwd.mkdir()
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    monkeypatch.setenv("TERMINAL_CWD", str(terminal_cwd))

    resolved = runner._resolve_agent_working_directory(
        "agent:main:discord:thread:thread-parent:thread-1",
        fallback_cwd=str(systemd_cwd),
    )

    assert resolved == str(systemd_cwd)
    assert not store_path.exists()


def test_gateway_workspace_resolver_records_foreground_session_snapshot(tmp_path, monkeypatch):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)

    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    resolved = runner._resolve_agent_working_directory(
        "agent:main:discord:thread:thread-parent:thread-1",
        fallback_cwd=str(repo_path),
    )

    reloaded = runner.active_task_store.get(
        "agent:main:discord:thread:thread-parent:thread-1"
    )
    assert resolved == str(repo_path)
    assert reloaded is not None
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.branch
    assert reloaded.head == expected_head
    assert reloaded.mode == "foreground_session"
    assert reloaded.command is None
    assert reloaded.pid is None
    assert reloaded.process_session_id is None
    assert "SENSITIVE_SENTINEL_DO_NOT_PERSIST" not in json.dumps(reloaded.to_dict())


def test_foreground_session_snapshot_replaces_stale_same_session_metadata(tmp_path):
    repo_path = tmp_path / "project"
    _init_git_repo(repo_path)
    store_path = tmp_path / "active_tasks.json"
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    runner.active_task_store.upsert(
        session_key=session_key,
        session_id="old-session-id",
        platform="discord",
        chat_id="thread-parent",
        thread_id="thread-1",
        repo_path=str(tmp_path / "old-project"),
        branch="old-branch",
        head="old-head",
        command="python stale_task.py",
        task_summary="old user task text",
        status="active",
        process_session_id="proc_old",
        pid=9876,
        latest_log_path=str(tmp_path / "old.log"),
        latest_summary_path=str(tmp_path / "old.json"),
        resume_reason="shutdown_timeout",
    )

    runner._record_foreground_session_workspace(session_key, str(repo_path))

    raw = json.loads(store_path.read_text(encoding="utf-8"))[session_key]
    forbidden_fields = {
        "session_id",
        "platform",
        "chat_id",
        "thread_id",
        "command",
        "task_summary",
        "pid",
        "process_session_id",
        "latest_log_path",
        "latest_summary_path",
        "resume_reason",
    }
    assert set(raw) == {
        "session_key_hash",
        "repo_path",
        "branch",
        "head",
        "mode",
        "status",
        "updated_at",
    }
    assert forbidden_fields.isdisjoint(raw)
    assert raw["session_key_hash"].startswith("sha256:")
    assert session_key not in json.dumps(raw)
    assert raw["repo_path"] == str(repo_path)
    assert raw["mode"] == "foreground_session"
    assert raw["status"] == "active"
    assert "old user task text" not in json.dumps(raw)


def test_foreground_session_record_with_non_git_repo_path_is_not_usable(tmp_path):
    repo_path = tmp_path / "non-git"
    repo_path.mkdir()
    record = ActiveTaskStore(tmp_path / "active_tasks.json").upsert(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        mode="foreground_session",
        status="active",
    )

    assert not record.has_usable_workspace()


def test_gateway_workspace_resolver_ignores_non_git_foreground_record(tmp_path, monkeypatch, caplog):
    bad_cwd = tmp_path / "non-git"
    fallback_cwd = tmp_path / "fallback"
    bad_cwd.mkdir()
    fallback_cwd.mkdir()
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    runner.active_task_store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(bad_cwd),
    )
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        resolved = runner._resolve_agent_working_directory(
            session_key,
            fallback_cwd=str(fallback_cwd),
        )

    assert resolved == str(fallback_cwd)
    assert "foreground active-task recovery record ignored" in caplog.text
    assert "repo_path_git_valid=False" in caplog.text


def test_foreground_persistence_skips_non_git_fallback_cwd(tmp_path, monkeypatch, caplog):
    fallback_cwd = tmp_path / "fallback"
    fallback_cwd.mkdir()
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        resolved = runner._resolve_agent_working_directory(
            "agent:main:discord:thread:thread-parent:thread-1",
            fallback_cwd=str(fallback_cwd),
        )

    assert resolved == str(fallback_cwd)
    assert not store_path.exists()
    assert "foreground workspace source skipped" in caplog.text
    assert "reason=non_git" in caplog.text


def test_foreground_persistence_does_not_overwrite_valid_repo_with_non_git_fallback(
    tmp_path, monkeypatch, caplog
):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    fallback_cwd = tmp_path / "fallback"
    fallback_cwd.mkdir()
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    runner.active_task_store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        runner._record_foreground_session_workspace(session_key, str(fallback_cwd))

    reloaded = runner.active_task_store.get(session_key)
    assert reloaded is not None
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.head == expected_head
    assert "foreground active-task record skipped" in caplog.text
    assert "cwd_git_valid=False" in caplog.text


def test_gateway_workspace_resolver_does_not_overwrite_valid_repo_with_home_fallback(
    tmp_path, monkeypatch, caplog
):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    home = tmp_path / "home"
    home.mkdir()
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    runner.active_task_store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )
    monkeypatch.setenv("TERMINAL_CWD", ".")
    monkeypatch.setattr("gateway.run.Path.home", lambda: home)

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        resolved = runner._resolve_agent_working_directory(
            session_key,
            fallback_cwd=str(home),
        )

    reloaded = runner.active_task_store.get(session_key)
    assert resolved == str(repo_path)
    assert reloaded is not None
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.head == expected_head
    assert "foreground active-task recovery record used" in caplog.text


def test_gateway_workspace_resolver_ignores_stale_foreground_record(
    tmp_path, monkeypatch, caplog
):
    stale_repo = tmp_path / "stale-project"
    fallback_repo = tmp_path / "runtime-checkout"
    _init_git_repo(stale_repo)
    _init_git_repo(fallback_repo)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(stale_repo),
        branch="main",
        head="stale-head",
    )
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    raw[session_key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=8)
    ).isoformat()
    store.path.write_text(json.dumps(raw), encoding="utf-8")
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = store
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        resolved = runner._resolve_agent_working_directory(
            session_key,
            fallback_cwd=str(fallback_repo),
        )

    assert resolved == str(fallback_repo)
    assert "active-task recovery record stale" in caplog.text


def test_foreground_persistence_normalizes_nested_git_cwd(tmp_path, monkeypatch):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    nested = repo_path / "nested" / "dir"
    nested.mkdir(parents=True)
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    runner._record_foreground_session_workspace(
        "agent:main:discord:thread:thread-parent:thread-1",
        str(nested),
    )

    reloaded = runner.active_task_store.get(
        "agent:main:discord:thread:thread-parent:thread-1"
    )
    assert reloaded is not None
    assert reloaded.repo_path == str(repo_path)
    assert reloaded.branch
    assert reloaded.head == expected_head


def test_legacy_foreground_session_record_is_sanitized_on_read(tmp_path):
    repo_path = tmp_path / "project"
    repo_path.mkdir()
    store_path = tmp_path / "active_tasks.json"
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store_path.write_text(
        json.dumps(
            {
                session_key: {
                    "session_key": session_key,
                    "session_id": "stale-session",
                    "platform": "discord",
                    "chat_id": "thread-parent",
                    "thread_id": "thread-1",
                    "repo_path": str(repo_path),
                    "branch": "main",
                    "head": "abc123",
                    "mode": "foreground_session",
                    "command": "SECRET_COMMAND_SHOULD_NOT_LEAK",
                    "task_summary": "SECRET_TASK_SHOULD_NOT_LEAK",
                    "status": "active",
                    "pid": 123,
                    "process_session_id": "proc-stale",
                    "latest_log_path": "/tmp/secret.log",
                    "latest_summary_path": "/tmp/secret.json",
                    "resume_reason": "shutdown_timeout",
                    "updated_at": "2026-05-31T07:41:14.889016+00:00",
                    "extra_legacy_field": "SECRET_EXTRA_SHOULD_NOT_LEAK",
                }
            }
        ),
        encoding="utf-8",
    )

    record = ActiveTaskStore(store_path).get(session_key)
    note = build_active_task_recovery_note(record, "restart_timeout")

    assert record is not None
    assert record.mode == "foreground_session"
    assert record.repo_path == str(repo_path)
    assert record.branch == "main"
    assert record.head == "abc123"
    assert record.command is None
    assert record.task_summary is None
    assert record.pid is None
    assert record.process_session_id is None
    assert record.session_id is None
    assert record.platform is None
    assert record.chat_id is None
    assert record.thread_id is None
    assert record.latest_log_path is None
    assert record.latest_summary_path is None
    assert record.resume_reason is None
    raw = record.to_dict()
    assert set(raw) == {
        "repo_path",
        "branch",
        "head",
        "mode",
        "status",
        "updated_at",
    }
    assert "SECRET_" not in json.dumps(raw)
    assert "SECRET_" not in note


def test_background_process_record_keeps_process_fields_on_read(tmp_path):
    repo_path = tmp_path / "project"
    repo_path.mkdir()
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    record = store.upsert(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head="abc123",
        mode="background_process",
        command="python tools/refill.py",
        task_summary="Signal Room refill batch",
        status="active",
        process_session_id="proc_active",
        pid=12345,
    )

    reloaded = ActiveTaskStore(store.path).get(record.session_key)

    assert reloaded is not None
    assert reloaded.mode == "background_process"
    assert reloaded.command == "python tools/refill.py"
    assert reloaded.task_summary == "Signal Room refill batch"
    assert reloaded.process_session_id == "proc_active"
    assert reloaded.pid == 12345


def test_gateway_workspace_resolver_does_not_use_non_git_background_record_as_cwd(
    tmp_path, monkeypatch
):
    repo_path = tmp_path / "non-git"
    fallback_cwd = tmp_path / "gateway"
    repo_path.mkdir()
    fallback_cwd.mkdir()
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.upsert(
        session_key=session_key,
        repo_path=str(repo_path),
        mode="background_process",
        status="active",
        process_session_id="proc_active",
        pid=12345,
    )
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = store
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    resolved = runner._resolve_agent_working_directory(
        session_key,
        fallback_cwd=str(fallback_cwd),
    )

    reloaded = store.get(session_key)
    assert reloaded is not None
    assert reloaded.has_usable_workspace()
    assert resolved == str(fallback_cwd)
    assert reloaded.mode == "background_process"
    assert reloaded.process_session_id == "proc_active"


def test_gateway_workspace_resolver_does_not_record_foreground_without_session_key(tmp_path, monkeypatch):
    repo_path = tmp_path / "project"
    repo_path.mkdir()
    store_path = tmp_path / "active_tasks.json"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)
    monkeypatch.delenv("TERMINAL_CWD", raising=False)

    resolved = runner._resolve_agent_working_directory("", fallback_cwd=str(repo_path))

    assert resolved == str(repo_path)
    assert not store_path.exists()


def test_resume_recovery_logs_when_active_task_store_file_is_absent(tmp_path, caplog):
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "missing_active_tasks.json")

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        note = runner._build_resume_recovery_note(
            "agent:main:discord:thread:thread-parent:thread-1",
            "restart_timeout",
        )

    assert "Active workspace/process state: unknown" in note
    assert "active-task store file is absent" in caplog.text
    assert "session_key=agent:ma..." in caplog.text


def test_resume_recovery_logs_when_active_task_store_file_is_malformed(tmp_path, caplog):
    store_path = tmp_path / "active_tasks.json"
    store_path.write_text("{not json", encoding="utf-8")
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(store_path)

    with caplog.at_level(logging.INFO):
        note = runner._build_resume_recovery_note(
            "agent:main:discord:thread:thread-parent:thread-1",
            "restart_timeout",
        )

    assert "Active workspace/process state: unknown" in note
    assert "failed to parse active-task store" in caplog.text
    assert any(
        "active-task recovery lookup failed: store_parse_ok=False" in record.getMessage()
        for record in caplog.records
    )


def test_resume_recovery_logs_session_key_miss_with_existing_records(tmp_path, caplog):
    repo_path = tmp_path / "project"
    repo_path.mkdir()
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key="agent:main:discord:thread:other-parent:other-thread",
        repo_path=str(repo_path),
        branch="main",
        head="abc123",
    )
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = store

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        note = runner._build_resume_recovery_note(
            "agent:main:discord:thread:thread-parent:thread-1",
            "restart_timeout",
        )

    assert "Active workspace/process state: unknown" in note
    assert "record_found=False" in caplog.text
    assert "record_count=1" in caplog.text
    assert "foreground_count=1" in caplog.text
    assert "thread-parent" not in caplog.text
    assert "thread-1" not in caplog.text


def test_resume_recovery_logs_session_key_hit_with_foreground_record(tmp_path, caplog):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = store

    with caplog.at_level(logging.INFO, logger="gateway.run"):
        note = runner._build_resume_recovery_note(session_key, "restart_timeout")

    assert f"Previous repo path: {repo_path}" in note
    assert "record_found=True" in caplog.text
    assert "mode=foreground_session" in caplog.text
    assert "has_repo_path=True" in caplog.text
    assert "has_branch=True" in caplog.text
    assert "has_head=True" in caplog.text
    assert "used=True" in caplog.text
    assert "thread-parent" not in caplog.text
    assert "thread-1" not in caplog.text


def test_resume_recovery_note_for_foreground_record_refuses_task_inference(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )

    note = build_active_task_recovery_note(store.get(session_key), "restart_interrupted")

    assert "Previous active task: unknown" in note
    assert "Exact interrupted session record: found" in note
    assert "workspace-only foreground record" in note
    assert "Do not infer the task from unrelated logs, dirty checkout files" in note
    assert "ask the user" in note


def test_foreground_turn_persists_safe_task_summary(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")

    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
        task_summary="Implement durable safe task-summary recovery; do not restart.",
        task_type="foreground_turn",
        risk_level="high",
        source="foreground_turn",
        forbidden_operations=["restart", "push"],
        validation_required=True,
    )

    record = ActiveTaskStore(store.path).get(session_key)
    assert record is not None
    assert record.task_summary_safe == "Implement durable safe task-summary recovery; do not restart."
    assert record.task_contract is not None
    assert record.task_contract["intended_repo"] == str(repo_path)
    assert record.task_contract["risk_level"] == "high"
    assert record.task_contract["forbidden_operations"] == ["restart", "push"]
    assert record.task_contract["validation_required"] is True
    assert "thread-parent" not in json.dumps(record.to_dict())


def test_recovery_uses_safe_task_summary_after_restart(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    record = store.replace_foreground_session(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
        task_summary="Recover safe foreground task summary.",
        source="foreground_turn",
    )

    note = build_active_task_recovery_note(record, "restart_timeout")

    assert "Recovered safe task summary: Recover safe foreground task summary." in note
    assert "Previous active task: Recover safe foreground task summary." in note
    assert "Recovery task body: unknown" not in note
    assert "Do not infer the task from unrelated logs" in note


def test_recovery_without_summary_does_not_infer(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    record = ActiveTaskStore(tmp_path / "active_tasks.json").replace_foreground_session(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )

    note = build_active_task_recovery_note(record, "restart_timeout")

    assert "Previous active task: unknown" in note
    assert "Recovery task body: unknown" in note
    assert "Do not infer the task from unrelated logs" in note


def test_task_summary_redacts_secrets_and_session_ids(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    record = store.replace_foreground_session(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
        task_summary=(
            "Use token=sk-testSECRET123456 and discord message id "
            "123456789012345678 in session_id abcdef1234567890abcdef1234567890."
        ),
    )

    rendered = json.dumps(record.to_dict())
    assert "sk-testSECRET123456" not in rendered
    assert "123456789012345678" not in rendered
    assert "abcdef1234567890abcdef1234567890" not in rendered
    assert "[redacted" in rendered


def test_task_contract_invalidates_cached_prompt_when_updated(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
        task_summary="First safe task summary.",
    )
    first = render_safe_task_contract_for_prompt(store.get(session_key))

    store.update_task_contract(
        session_key=session_key,
        task_summary="Second safe task summary.",
        source="recovery",
    )
    second = render_safe_task_contract_for_prompt(store.get(session_key))

    assert "First safe task summary." in first
    assert "Second safe task summary." in second
    assert first != second


def test_goal_summary_can_seed_task_contract(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    store = ActiveTaskStore(tmp_path / "active_tasks.json")
    store.replace_foreground_session(
        session_key=session_key,
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
    )

    store.update_task_contract(
        session_key=session_key,
        task_summary="Standing goal: finish recovery safely.",
        source="goal",
        status="paused",
    )

    record = store.get(session_key)
    assert record is not None
    assert record.task_summary_safe == "Standing goal: finish recovery safely."
    assert record.task_contract["source"] == "goal"
    assert record.task_contract["status"] == "paused"


def test_gateway_goal_summary_seeds_task_contract(tmp_path, monkeypatch):
    session_key = "agent:main:discord:thread:thread-parent:thread-1"
    runner = object.__new__(GatewayRunner)
    runner.active_task_store = ActiveTaskStore(tmp_path / "active_tasks.json")
    monkeypatch.setattr(
        "hermes_cli.goals.load_goal",
        lambda session_id: SimpleNamespace(
            status="active",
            goal="Continue safe recovery without restart.",
        ),
    )

    runner._persist_safe_goal_task_contract(session_key, "session-1")

    record = runner.active_task_store.get(session_key)
    assert record is not None
    assert record.task_summary_safe == "Continue safe recovery without restart."
    assert record.task_contract["source"] == "goal"
    assert record.task_contract["status"] == "active"


def test_completed_or_superseded_contract_not_recovered(tmp_path):
    repo_path = tmp_path / "project"
    expected_head = _init_git_repo(repo_path)
    record = ActiveTaskStore(tmp_path / "active_tasks.json").replace_foreground_session(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head=expected_head,
        task_summary="Completed safe task.",
        status="completed",
    )

    note = build_active_task_recovery_note(record, "restart_timeout")

    assert "Completed safe task." not in note
    assert "Previous active task: unknown" in note
    assert "Recovery task body: unknown" in note


def test_resume_pending_note_includes_active_task_facts(tmp_path):
    repo_path = tmp_path / "project"
    repo_path.mkdir()
    record = ActiveTaskStore(tmp_path / "active_tasks.json").upsert(
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        repo_path=str(repo_path),
        branch="main",
        head="abc123",
        command="python tools/refill.py",
        task_summary="Signal Room refill batch",
        status="detached",
        process_session_id="proc_active",
        latest_summary_path=str(repo_path / "runtime/refill.json"),
        resume_reason="restart_timeout",
    )

    note = build_active_task_recovery_note(record, "restart_timeout")

    assert "Previous active task: Signal Room refill batch" in note
    assert f"Previous repo path: {repo_path}" in note
    assert "Previous branch: main" in note
    assert "Previous HEAD: abc123" in note
    assert "Previous command: python tools/refill.py" in note
    assert "Process status: detached" in note
    assert "Process/session id: proc_active" in note
    assert "Latest summary path:" in note
    assert "Next safe recovery check:" in note


def test_resume_pending_note_without_active_task_reports_unknown():
    note = build_active_task_recovery_note(None, "restart_timeout")

    assert "Active workspace/process state: unknown" in note
    assert "Do not silently default to the gateway working directory" in note
    assert "Next safe recovery check:" in note


def test_process_checkpoint_flushes_after_notification_metadata_changes(tmp_path):
    registry = ProcessRegistry()
    session = ProcessSession(
        id="proc_active",
        command="python tools/refill.py",
        task_id="agent:main:discord:thread:thread-parent:thread-1",
        session_key="agent:main:discord:thread:thread-parent:thread-1",
        pid=12345,
        pid_scope="host",
        cwd="/tmp/project",
        started_at=time.time(),
    )
    registry._running[session.id] = session
    checkpoint = tmp_path / "processes.json"

    with patch("tools.process_registry.CHECKPOINT_PATH", checkpoint):
        registry._write_checkpoint()
        registry.update_session_metadata(
            session.id,
            notify_on_complete=True,
            watcher_platform="discord",
            watcher_chat_id="thread-parent",
            watcher_thread_id="thread-1",
            watcher_interval=5,
        )

        data = json.loads(checkpoint.read_text())

    assert data[0]["notify_on_complete"] is True
    assert data[0]["watcher_platform"] == "discord"
    assert data[0]["watcher_interval"] == 5
