from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_control.scoped_pr_draft_runner import (
    CommandResult,
    ScopedPrDraftRunnerError,
    _append_docs_note,
    run_scoped_pr_draft,
)


DOC_PATH = "docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md"


def _packet(**overrides):
    packet = {
        "packet_version": "mission_control_scoped_pr_execution_packet_v1",
        "mode": "scoped_pr_draft",
        "runner_id": "mission_control_scoped_pr_draft_runner",
        "run_id": "run-scoped-pr-exec-1",
        "approval_id": "approval-scoped-pr-exec-1",
        "branch_name": "codex/scoped-pr-docs-smoke-test",
        "base_branch": "accepted-live/approval-safety-5ad8906",
        "draft_pr_title": "docs: record scoped PR creation smoke test",
        "edit_instruction": "Append a bounded scoped PR smoke-test note.",
        "scope": {"files": [DOC_PATH], "directories": [], "has_wildcard": False, "explicit": True},
        "draft_pr_required": True,
        "max_files": 1,
        "max_commits": 1,
        "max_prs": 1,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "merge_enabled": False,
        "deploy_enabled": False,
        "restart_enabled": False,
        "runtime_switch_enabled": False,
    }
    packet.update(overrides)
    return packet


class FakeCommands:
    def __init__(self, *, remote_branch_exists: bool = False, pr_state: dict | None = None):
        self.remote_branch_exists = remote_branch_exists
        self.pr_state = pr_state or {
            "url": "https://github.com/Travisaggie04/hermes-agent/pull/412",
            "isDraft": True,
            "state": "OPEN",
            "headRefName": "codex/scoped-pr-docs-smoke-test",
            "baseRefName": "accepted-live/approval-safety-5ad8906",
            "files": [{"path": DOC_PATH}],
            "commits": [{"oid": "a" * 40}],
        }
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, args: list[str], *, cwd: Path | None = None, check: bool = True) -> CommandResult:
        self.commands.append(tuple(args))
        if args[:4] == ["gh", "pr", "list", "--repo"]:
            return CommandResult(0, "[]", "")
        if args[:3] == ["git", "ls-remote", "--heads"]:
            if self.remote_branch_exists:
                return CommandResult(0, "a" * 40 + "\trefs/heads/codex/scoped-pr-docs-smoke-test\n", "")
            return CommandResult(2, "", "")
        if args[:2] == ["git", "clone"]:
            worktree = Path(args[-1])
            target = worktree / DOC_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Runbook\n", encoding="utf-8")
            return CommandResult(0, "", "")
        if args[:3] == ["git", "checkout", "-b"]:
            return CommandResult(0, "", "")
        if args[:3] == ["git", "status", "--short"]:
            return CommandResult(0, f" M {DOC_PATH}\n", "")
        if args[:3] == ["git", "diff", "--check"]:
            return CommandResult(0, "", "")
        if args[:2] == ["git", "add"]:
            return CommandResult(0, "", "")
        if args[:2] == ["git", "commit"]:
            return CommandResult(0, "[branch abc] docs\n", "")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return CommandResult(0, "b" * 40 + "\n", "")
        if args[:3] == ["git", "diff", "--name-only"]:
            return CommandResult(0, DOC_PATH + "\n", "")
        if args[:2] == ["git", "push"]:
            return CommandResult(0, "", "")
        if args[:3] == ["gh", "pr", "create"]:
            return CommandResult(0, "https://github.com/Travisaggie04/hermes-agent/pull/412\n", "")
        if args[:3] == ["gh", "pr", "view"]:
            return CommandResult(0, json.dumps(self.pr_state), "")
        if check:
            raise AssertionError(f"unexpected command: {args}")
        return CommandResult(1, "", "unexpected command")


def test_scoped_pr_draft_runner_creates_one_draft_pr_for_approved_file(tmp_path):
    fake = FakeCommands()

    result = run_scoped_pr_draft(_packet(), worktree_root=tmp_path, command_runner=fake)

    assert result.branch_name == "codex/scoped-pr-docs-smoke-test"
    assert result.base_branch == "accepted-live/approval-safety-5ad8906"
    assert result.pr_url == "https://github.com/Travisaggie04/hermes-agent/pull/412"
    assert result.changed_files == (DOC_PATH,)
    assert result.tests == ("git diff --check",)
    assert result.draft is True
    assert ("git", "push", "origin", "HEAD:refs/heads/codex/scoped-pr-docs-smoke-test") in fake.commands
    assert any(command[:3] == ("gh", "pr", "create") and "--draft" in command for command in fake.commands)


def test_scoped_pr_draft_runner_refuses_existing_remote_branch(tmp_path):
    with pytest.raises(ScopedPrDraftRunnerError, match="remote branch already exists"):
        run_scoped_pr_draft(
            _packet(),
            worktree_root=tmp_path,
            command_runner=FakeCommands(remote_branch_exists=True),
        )


def test_scoped_pr_draft_runner_refuses_non_draft_created_pr(tmp_path):
    fake = FakeCommands(pr_state={
        "url": "https://github.com/Travisaggie04/hermes-agent/pull/412",
        "isDraft": False,
        "state": "OPEN",
        "headRefName": "codex/scoped-pr-docs-smoke-test",
        "baseRefName": "accepted-live/approval-safety-5ad8906",
        "files": [{"path": DOC_PATH}],
        "commits": [{"oid": "a" * 40}],
    })

    with pytest.raises(ScopedPrDraftRunnerError, match="not draft"):
        run_scoped_pr_draft(_packet(), worktree_root=tmp_path, command_runner=fake)


def test_scoped_pr_draft_runner_refuses_unsafe_packet_scope(tmp_path):
    with pytest.raises(ScopedPrDraftRunnerError, match="safe docs markdown path"):
        run_scoped_pr_draft(
            _packet(scope={"files": ["mission_control/autonomy_eligibility.py"], "directories": []}),
            worktree_root=tmp_path,
            command_runner=FakeCommands(),
        )


def test_append_docs_note_leaves_exactly_one_trailing_newline(tmp_path):
    target = tmp_path / DOC_PATH
    target.parent.mkdir(parents=True)
    target.write_text("# Runbook\n\n", encoding="utf-8")

    _append_docs_note(
        target,
        run_id="run-scoped-pr-exec-1",
        approval_id="approval-scoped-pr-exec-1",
        edit_instruction="Append a bounded note.",
    )

    content = target.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert not content.endswith("\n\n")
    assert "<!-- scoped-pr-draft-runner:run-scoped-pr-exec-1 -->" in content
