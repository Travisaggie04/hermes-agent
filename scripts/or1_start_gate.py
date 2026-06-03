#!/usr/bin/env python3
"""Read-only OR1 Start Gate helper."""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXPECTED_PATH = Path("/home/jenny/.hermes/hermes-context-routing-e1d-integration")
DEFAULT_EXPECTED_BRANCH = "mission-control-os-stateful-foundation"


@dataclass(frozen=True)
class GitResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class GateResult:
    passed: bool
    expected_path: Path
    actual_cwd: Path
    git_root: str
    expected_branch: str
    actual_branch: str
    expected_head: str | None
    actual_head: str
    status_lines: list[str]
    dirty_files: list[str]
    blocked_reasons: list[str]


def run_git(args: list[str], cwd: Path) -> GitResult:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return GitResult(
        ok=result.returncode == 0,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )


def normalize_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def parse_dirty_files(status_output: str) -> list[str]:
    dirty_files: list[str] = []
    for line in status_output.splitlines():
        if not line or line.startswith("## "):
            continue
        path_text = line[3:] if len(line) > 3 else line
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[1]
        path_text = path_text.strip()
        if path_text:
            dirty_files.append(path_text)
    return dirty_files


def matches_any(path_text: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path_text, pattern) for pattern in patterns)


def dirty_block_reasons(
    dirty_files: list[str],
    allow_patterns: list[str],
    forbid_patterns: list[str],
) -> list[str]:
    reasons: list[str] = []
    forbidden = [path for path in dirty_files if matches_any(path, forbid_patterns)]
    if forbidden:
        reasons.append("dirty files match forbidden patterns")

    unallowed = [
        path
        for path in dirty_files
        if not allow_patterns or not matches_any(path, allow_patterns)
    ]
    if unallowed:
        reasons.append("dirty files are not allowed")
    return reasons


def evaluate_gate(args: argparse.Namespace) -> GateResult:
    expected_path = normalize_path(args.expected_path)
    actual_cwd = Path.cwd().resolve()
    expected_branch = args.expected_branch
    blocked_reasons: list[str] = []

    if actual_cwd != expected_path:
        blocked_reasons.append("actual cwd does not match expected path")

    root_result = run_git(["rev-parse", "--show-toplevel"], actual_cwd)
    if root_result.ok:
        git_root = str(normalize_path(Path(root_result.stdout)))
        if Path(git_root) != expected_path:
            blocked_reasons.append("git root does not match expected path")
    else:
        git_root = "UNKNOWN"
        blocked_reasons.append("not inside a git repository")

    branch_result = run_git(["branch", "--show-current"], actual_cwd)
    branch_name = branch_result.stdout.strip() if branch_result.ok else ""
    detached = branch_result.ok and branch_name == ""
    actual_branch = "DETACHED" if detached else branch_name or "UNKNOWN"
    if detached:
        if not args.allow_detached_head:
            blocked_reasons.append("detached HEAD is not allowed")
    elif actual_branch != expected_branch:
        blocked_reasons.append("actual branch does not match expected branch")

    head_result = run_git(["rev-parse", "HEAD"], actual_cwd)
    actual_head = head_result.stdout.strip() if head_result.ok else "UNKNOWN"
    if args.expected_head and actual_head != args.expected_head:
        blocked_reasons.append("actual HEAD does not match expected HEAD")

    status_result = run_git(
        ["status", "--short", "--branch", "--untracked-files=all"],
        actual_cwd,
    )
    status_lines = status_result.stdout.splitlines() if status_result.ok else []
    dirty_files = parse_dirty_files(status_result.stdout) if status_result.ok else []
    blocked_reasons.extend(
        dirty_block_reasons(dirty_files, args.allow_dirty, args.forbid_dirty)
    )

    return GateResult(
        passed=not blocked_reasons,
        expected_path=expected_path,
        actual_cwd=actual_cwd,
        git_root=git_root,
        expected_branch=expected_branch,
        actual_branch=actual_branch,
        expected_head=args.expected_head,
        actual_head=actual_head,
        status_lines=status_lines,
        dirty_files=dirty_files,
        blocked_reasons=blocked_reasons,
    )


def render_result(result: GateResult) -> str:
    lines = ["START GATE PASS" if result.passed else "START GATE BLOCKED"]
    lines.extend(
        [
            f"expected path: {result.expected_path}",
            f"actual cwd: {result.actual_cwd}",
            f"git root: {result.git_root}",
            f"expected branch: {result.expected_branch}",
            f"actual branch: {result.actual_branch}",
        ]
    )
    if result.expected_head:
        lines.append(f"expected HEAD: {result.expected_head}")
    lines.append(f"actual HEAD: {result.actual_head}")
    lines.append("git status --short --branch:")
    if result.status_lines:
        lines.extend(f"  {line}" for line in result.status_lines)
    else:
        lines.append("  unavailable")
    if result.dirty_files:
        lines.append("dirty files:")
        lines.extend(f"  {path}" for path in result.dirty_files)
    else:
        lines.append("dirty files: none")
    if result.blocked_reasons:
        lines.append("blocked reason:")
        lines.extend(f"  - {reason}" for reason in result.blocked_reasons)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-path", type=Path, default=DEFAULT_EXPECTED_PATH)
    parser.add_argument("--expected-branch", default=DEFAULT_EXPECTED_BRANCH)
    parser.add_argument("--expected-head")
    parser.add_argument("--allow-dirty", action="append", default=[])
    parser.add_argument("--forbid-dirty", action="append", default=[])
    parser.add_argument(
        "--allow-detached-head",
        action="store_true",
        help="allow detached HEAD while still reporting actual branch as DETACHED",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = evaluate_gate(args)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print("START GATE ERROR")
        print(f"error: {exc}")
        return 1
    print(render_result(result))
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
