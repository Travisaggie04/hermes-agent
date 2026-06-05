"""Focused tests for Safety Start Gate and Tool Guard helpers."""

import subprocess
from pathlib import Path

import pytest

from hermes_cli.safety_guard import (
    SafetyGuardConfig,
    evaluate_start_gate,
    evaluate_tool_guard,
    format_stop_report,
)


EXPECTED_REMOTE = "https://github.com/Travisaggie04/hermes-agent.git"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "remote", "add", "origin", EXPECTED_REMOTE)
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "checkout", "-b", "pr-safety-start-gate-tool-guard")
    return repo


class TestStartGate:
    def test_blocks_dirty_worktree_and_reports_counts_separately(self, git_repo: Path) -> None:
        (git_repo / "staged.txt").write_text("staged\n", encoding="utf-8")
        _git(git_repo, "add", "staged.txt")
        (git_repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (git_repo / "new.txt").write_text("new\n", encoding="utf-8")

        decision = evaluate_start_gate(git_repo, SafetyGuardConfig())

        assert decision.blocked is True
        assert decision.counts.staged == 1
        assert decision.counts.unstaged == 1
        assert decision.counts.untracked == 1
        assert "dirty worktree" in decision.summary.lower()

    def test_blocks_staged_file_explosion(self, git_repo: Path) -> None:
        for index in range(3):
            (git_repo / f"staged_{index}.txt").write_text("x\n", encoding="utf-8")
        _git(git_repo, "add", ".")

        decision = evaluate_start_gate(
            git_repo,
            SafetyGuardConfig(max_staged_entries=2),
        )

        assert decision.blocked is True
        assert "staged-file explosion" in decision.summary.lower()
        assert decision.counts.staged == 3

    def test_blocks_wrong_target_remote(self, git_repo: Path) -> None:
        _git(git_repo, "remote", "set-url", "origin", "https://github.com/NousResearch/hermes-agent.git")

        decision = evaluate_start_gate(git_repo, SafetyGuardConfig())

        assert decision.blocked is True
        assert "remote mismatch" in decision.summary.lower()
        assert "NousResearch" in decision.details[0]

    def test_remote_mismatch_redacts_credential_userinfo(self, git_repo: Path) -> None:
        userinfo = "credential-userinfo"
        _git(git_repo, "remote", "set-url", "origin", f"https://{userinfo}@github.com/NousResearch/hermes-agent.git")

        decision = evaluate_start_gate(git_repo, SafetyGuardConfig())
        report = format_stop_report(decision)

        assert decision.blocked is True
        assert userinfo not in report
        assert f"https://{userinfo}@" not in report
        assert "github.com/NousResearch/hermes-agent.git" in report

    def test_blocks_wrong_branch_unless_allowed(self, git_repo: Path) -> None:
        _git(git_repo, "checkout", "-b", "wrong-branch")

        blocked = evaluate_start_gate(git_repo, SafetyGuardConfig())
        allowed = evaluate_start_gate(git_repo, SafetyGuardConfig(allow_wrong_branch=True))

        assert blocked.blocked is True
        assert "branch mismatch" in blocked.summary.lower()
        assert allowed.blocked is False

    def test_blocks_detached_head_unless_allowed(self, git_repo: Path) -> None:
        head = _git(git_repo, "rev-parse", "HEAD").stdout.strip()
        _git(git_repo, "checkout", "--detach", head)

        blocked = evaluate_start_gate(git_repo, SafetyGuardConfig())
        allowed = evaluate_start_gate(git_repo, SafetyGuardConfig(allow_detached_head=True))

        assert blocked.blocked is True
        assert "detached head" in blocked.summary.lower()
        assert allowed.blocked is False

    def test_blocks_merge_rebase_or_conflict_state(self, git_repo: Path) -> None:
        git_dir = Path(_git(git_repo, "rev-parse", "--git-dir").stdout.strip())
        if not git_dir.is_absolute():
            git_dir = git_repo / git_dir
        (git_dir / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")

        decision = evaluate_start_gate(git_repo, SafetyGuardConfig())

        assert decision.blocked is True
        assert "merge/rebase/conflict" in decision.summary.lower()


class TestToolGuard:
    def test_blocks_edit_tools_in_read_only_docs_only_and_stop_state_lanes(self) -> None:
        for lane in ["read-only inventory", "documentation-only hardening", "stop-state only"]:
            decision = evaluate_tool_guard(
                "write_file",
                {"path": "notes.txt", "content": "x"},
                SafetyGuardConfig(active_lane=lane),
            )
            assert decision.blocked is True
            assert "write/edit" in decision.summary.lower()

    def test_blocks_broad_tests_when_focused_tests_required(self) -> None:
        decision = evaluate_tool_guard(
            "terminal",
            {"command": "pytest"},
            SafetyGuardConfig(active_lane="code implementation", focused_tests_required=True),
        )

        assert decision.blocked is True
        assert "broad test" in decision.summary.lower()

    def test_blocks_cleanup_commands_without_named_cleanup_lane_target(self) -> None:
        blocked = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build"},
            SafetyGuardConfig(active_lane="code implementation"),
        )
        unnamed = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build"},
            SafetyGuardConfig(active_lane="cleanup/revert"),
        )
        cleanup_only_unnamed = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build"},
            SafetyGuardConfig(active_lane="cleanup-only"),
        )
        non_exact_target = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build-cache"},
            SafetyGuardConfig(active_lane="cleanup-only", cleanup_target="build"),
        )
        broad_cleanup = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build dist"},
            SafetyGuardConfig(active_lane="cleanup-only", cleanup_target="build"),
        )
        allowed = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build"},
            SafetyGuardConfig(active_lane="cleanup/revert", cleanup_target="build"),
        )

        assert blocked.blocked is True
        assert unnamed.blocked is True
        assert cleanup_only_unnamed.blocked is True
        assert non_exact_target.blocked is True
        assert broad_cleanup.blocked is True
        assert allowed.blocked is False

    def test_allows_cleanup_only_lane_with_exact_cleanup_target(self) -> None:
        decision = evaluate_tool_guard(
            "terminal",
            {"command": "rm -rf build"},
            SafetyGuardConfig(active_lane="cleanup-only", cleanup_target="build"),
        )

        assert decision.blocked is False

    def test_blocks_parent_directory_scans(self) -> None:
        decision = evaluate_tool_guard(
            "terminal",
            {"command": "rg secret .."},
            SafetyGuardConfig(active_lane="read-only inventory"),
        )

        assert decision.blocked is True
        assert "parent-directory scan" in decision.summary.lower()

    def test_blocks_quarantined_path_access(self) -> None:
        decision = evaluate_tool_guard(
            "read_file",
            {"path": "/tmp/quarantine/notes.txt"},
            SafetyGuardConfig(
                active_lane="read-only inventory",
                quarantined_paths=("/tmp/quarantine",),
            ),
        )

        assert decision.blocked is True
        assert "quarantined path" in decision.summary.lower()

    def test_guard_output_redacts_secret_values(self) -> None:
        secret = "sk-test-secret-value"
        decision = evaluate_tool_guard(
            "terminal",
            {"command": f"echo {secret} > ../outside.txt"},
            SafetyGuardConfig(active_lane="code implementation", secret_values=(secret,)),
        )
        report = format_stop_report(decision)

        assert decision.blocked is True
        assert secret not in report
        assert "target-root containment" in report
