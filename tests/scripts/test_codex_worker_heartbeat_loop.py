from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "codex_worker_heartbeat_loop.py"


def test_codex_worker_heartbeat_loop_dry_run_emits_online_worker_record_without_secrets(monkeypatch):
    monkeypatch.setenv("HERMES_MISSION_CONTROL_TOKEN", "super-secret-token")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mission-control-url",
            "http://127.0.0.1:9119",
            "--once",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "super-secret-token" not in result.stdout
    data = json.loads(result.stdout)
    payload = data["payload"]
    assert data["dry_run"] is True
    assert data["endpoint"].endswith("/api/plugins/mission-control-governance/workspace/worker-node-runs/create")
    assert payload["presence_status"] == "online"
    assert payload["smoke_status"] == "heartbeat_loop_ok"
    assert payload["worker_dispatch_enabled"] is False
    assert payload["max_concurrent_read_only_lanes"] == 1
    assert payload["max_concurrent_mutation_lanes"] == 0
    assert "automatic worker dispatch" in payload["forbidden_actions"]
    assert payload["metadata"]["manual_handoff_only"] is True
    assert payload["metadata"]["no_secrets_printed"] is True
