from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "or1_start_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("or1_start_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["or1_start_gate"] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def make_repo(tmp_path: Path, branch: str = "mission-control-os-stateful-foundation") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    (repo / "README.md").write_text("initial\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "initial")
    git(repo, "checkout", "-b", branch)
    return repo


def run_gate(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def assert_blocked(result: subprocess.CompletedProcess[str], reason: str | None = None) -> None:
    assert result.returncode == 2
    assert result.stdout.startswith("START GATE BLOCKED")
    assert "blocked reason:" in result.stdout
    if reason:
        assert reason in result.stdout


def assert_passed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0
    assert result.stdout.startswith("START GATE PASS")
    assert "blocked reason:" not in result.stdout


def test_passes_in_expected_repo_path_and_branch_when_clean(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_passed(result)
    assert f"expected path: {repo}" in result.stdout
    assert f"actual cwd: {repo}" in result.stdout
    assert f"git root: {repo}" in result.stdout
    assert "expected branch: mission-control-os-stateful-foundation" in result.stdout
    assert "actual branch: mission-control-os-stateful-foundation" in result.stdout
    assert "actual HEAD:" in result.stdout
    assert "dirty files: none" in result.stdout


def test_blocks_on_wrong_cwd_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    wrong_path = tmp_path / "other"

    result = run_gate(
        repo,
        "--expected-path",
        str(wrong_path),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_blocked(result, "actual cwd does not match expected path")


def test_blocks_on_wrong_git_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    subdir = repo / "subdir"
    subdir.mkdir()

    result = run_gate(
        subdir,
        "--expected-path",
        str(subdir),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_blocked(result, "git root does not match expected path")


def test_blocks_outside_git_repo(tmp_path: Path) -> None:
    outside = tmp_path / "not-a-repo"
    outside.mkdir()

    result = run_gate(
        outside,
        "--expected-path",
        str(outside),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_blocked(result, "not inside a git repository")


def test_blocks_on_wrong_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, branch="other-branch")

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_blocked(result, "actual branch does not match expected branch")


def test_blocks_on_detached_head_unless_explicitly_allowed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "--detach", head)

    blocked = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )
    allowed = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
        "--allow-detached-head",
    )

    assert_blocked(blocked, "detached HEAD is not allowed")
    assert_passed(allowed)
    assert "actual branch: DETACHED" in allowed.stdout


def test_blocks_on_expected_head_mismatch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    wrong_head = "0" * 40

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
        "--expected-head",
        wrong_head,
    )

    assert_blocked(result, "actual HEAD does not match expected HEAD")
    assert f"expected HEAD: {wrong_head}" in result.stdout


def test_blocks_when_dirty_files_exist_by_default(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    assert_blocked(result, "dirty files are not allowed")
    assert "dirty.txt" in result.stdout


def test_allows_dirty_files_only_under_allow_dirty_pattern(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    allowed_dir = repo / "tests" / "scripts"
    allowed_dir.mkdir(parents=True)
    (allowed_dir / "test_or1_start_gate.py").write_text("dirty\n", encoding="utf-8")

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
        "--allow-dirty",
        "tests/scripts/*",
    )

    assert_passed(result)
    assert "tests/scripts/test_or1_start_gate.py" in result.stdout


def test_blocks_dirty_files_outside_allow_dirty_pattern(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "other.txt").write_text("dirty\n", encoding="utf-8")

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
        "--allow-dirty",
        "tests/scripts/*",
    )

    assert_blocked(result, "dirty files are not allowed")


def test_forbid_dirty_pattern_blocks_even_when_allowed(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    target = repo / "tests" / "scripts"
    target.mkdir(parents=True)
    (target / "test_or1_start_gate.py").write_text("dirty\n", encoding="utf-8")

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
        "--allow-dirty",
        "tests/scripts/*",
        "--forbid-dirty",
        "tests/scripts/test_or1_start_gate.py",
    )

    assert_blocked(result, "dirty files match forbidden patterns")


def test_internal_error_returns_exit_code_1(monkeypatch, capsys) -> None:
    module = load_module()

    def fail(_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "evaluate_gate", fail)

    assert module.main([]) == 1
    output = capsys.readouterr().out
    assert output.startswith("START GATE ERROR")
    assert "boom" in output


def test_helper_does_not_modify_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    before = {
        path.relative_to(repo): path.stat().st_mtime_ns
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    result = run_gate(
        repo,
        "--expected-path",
        str(repo),
        "--expected-branch",
        "mission-control-os-stateful-foundation",
    )

    after = {
        path.relative_to(repo): path.stat().st_mtime_ns
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert_passed(result)
    assert after == before
    assert git(repo, "status", "--short", "--branch").splitlines() == [
        "## mission-control-os-stateful-foundation"
    ]
