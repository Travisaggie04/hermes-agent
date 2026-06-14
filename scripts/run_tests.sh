#!/usr/bin/env bash
# Canonical test runner for hermes-agent. Run this instead of calling
# `pytest` directly to guarantee your local run matches CI behavior.
#
# What this script enforces:
#   * Per-file isolation via scripts/run_tests_parallel.py — each test
#     file runs in its own freshly-spawned `python -m pytest <file>`
#     subprocess. No xdist, no shared workers, no module-level leakage
#     between files.
#   * TZ=UTC, LANG=C.UTF-8, PYTHONHASHSEED=0 (deterministic)
#   * Env vars blanked (conftest.py also does this, but this
#     is belt-and-suspenders for anyone running pytest outside our
#     conftest path — e.g. on a single file)
#   * Proper venv activation (probes .venv, venv, then ~/.hermes/...)
#
# Usage:
#   scripts/run_tests.sh                            # full suite
#   scripts/run_tests.sh -j 4                       # cap parallelism
#   scripts/run_tests.sh tests/agent/               # discover only here
#   scripts/run_tests.sh tests/agent/ tests/acp/    # multiple roots
#   scripts/run_tests.sh tests/foo.py               # single file
#   scripts/run_tests.sh tests/foo.py -- --tb=long  # path + pytest args
#   scripts/run_tests.sh -- -v --tb=long            # pytest args only
#
# Native Windows contributors should use scripts/run_tests.ps1. This
# Bash wrapper supports POSIX/Git-Bash venv layouts; WSL with only a
# Windows .venv cannot safely bridge Python path semantics.
#
# Everything after a literal '--' is passed through to each per-file
# pytest invocation. Positional path arguments before '--' override
# the default discovery root (tests/).

set -euo pipefail

# ── Locate repo root ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Activate venv ───────────────────────────────────────────────────────────
PYTHON=""
for candidate in "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/venv/bin/python" "$HOME/.hermes/hermes-agent/venv/bin/python"; do
  if [ -x "$candidate" ]; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  if [ -f "$REPO_ROOT/.venv/Scripts/python.exe" ] || [ -f "$REPO_ROOT/venv/Scripts/python.exe" ]; then
    echo "error: found a Windows virtualenv but no POSIX Python for this Bash shell." >&2
    echo "       Run native Windows tests with: powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1" >&2
    exit 1
  fi
  echo "error: no virtualenv found in $REPO_ROOT/.venv or $REPO_ROOT/venv" >&2
  exit 1
fi


# ── Live-gateway plugin (computed before we drop env) ───────────────────────
EXTRA_PYTHONPATH=""
EXTRA_PYTEST_PLUGINS=""
if [ -f "$HOME/.hermes/pytest_live_guard.py" ]; then
  EXTRA_PYTHONPATH="$HOME/.hermes"
  EXTRA_PYTEST_PLUGINS="pytest_live_guard"
fi


# ── Run in hermetic env ──────────────────────────────────────────────────────
# env -i: start with empty environment, opt-in only what we need.
# No credential var can leak — you'd have to explicitly add it here.
echo "▶ running per-file parallel test suite via run_tests_parallel.py"
echo "  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; clean env)"

cd "$REPO_ROOT"
TEST_TMP="$REPO_ROOT/.codex-tmp/pytest"
mkdir -p "$TEST_TMP"

exec env -i \
  PATH="$PATH" \
  HOME="$HOME" \
  TMPDIR="$TEST_TMP" \
  TMP="$TEST_TMP" \
  TEMP="$TEST_TMP" \
  TZ=UTC \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  PYTHONUTF8=1 \
  PYTHONIOENCODING=utf-8 \
  PYTHONHASHSEED=0 \
  ${EXTRA_PYTHONPATH:+PYTHONPATH="$EXTRA_PYTHONPATH"} \
  ${EXTRA_PYTEST_PLUGINS:+PYTEST_PLUGINS="$EXTRA_PYTEST_PLUGINS"} \
  "$PYTHON" "$SCRIPT_DIR/run_tests_parallel.py" "$@"
