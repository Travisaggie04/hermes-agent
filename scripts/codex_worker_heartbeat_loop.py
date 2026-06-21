#!/usr/bin/env python3
"""Operator-started Codex worker-node heartbeat loop for Mission Control.

This script is intentionally manual. It does not install a daemon, cron job,
startup task, or worker dispatcher. It records append-only WorkerNodeRunRecord
heartbeats only when an operator starts it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

PLUGIN_PATH = "/api/plugins/mission-control-governance/workspace/worker-node-runs/create"
DEFAULT_WORKER_RUN_ID = "laptop-codex-manual-readiness-main-laptop"
DEFAULT_PARENT_RUN_ID = "mission-control-codex-worker-readiness"
DEFAULT_PACKET_ID = "codex-worker-lite-wrapper-2026-06-21"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _endpoint(base_url: str) -> str:
    stripped = base_url.strip()
    if not stripped:
        raise ValueError("mission control URL is required")
    if stripped.endswith(PLUGIN_PATH):
        return stripped
    return urljoin(stripped.rstrip("/") + "/", PLUGIN_PATH.lstrip("/"))


def _heartbeat_payload(args: argparse.Namespace) -> dict[str, Any]:
    now = _utc_now()
    return {
        "worker_run_id": args.worker_run_id,
        "parent_run_id": args.parent_run_id,
        "project_id": args.project_id,
        "worker_id": args.worker_id,
        "worker_type": "codex",
        "display_name": "Main Laptop Codex worker-node",
        "worker_identity": "codex",
        "worker_host_label": args.worker_host_label,
        "worker_kind": "laptop_codex",
        "objective": args.objective,
        "assigned_packet_id": args.assigned_packet_id,
        "assigned_packet_summary": "Manual Codex worker readiness heartbeat; dispatch remains disabled.",
        "allowed_actions": [
            "manual handoff preview",
            "read-only repo inspection when separately instructed by operator",
            "focused tests when separately instructed by operator",
        ],
        "forbidden_actions": [
            "automatic worker dispatch",
            "session send",
            "queue mutation",
            "Waha",
            "social posting",
            "payments",
            "model routing changes",
            "timers",
            "daemon/autostart installation",
            "live runtime restart/switch/deploy",
            "secrets inspection or output",
        ],
        "status": "running",
        "presence_status": "online",
        "smoke_status": args.smoke_status,
        "last_heartbeat_at": now,
        "last_seen_at": now,
        "worker_version": args.worker_version,
        "capability_summary": "operator-started laptop Codex worker; manual handoff only; heartbeat proves presence only",
        "capabilities_advertised": ["manual handoff preview", "read-only repo inspection"],
        "capabilities_allowed": ["status display", "manual handoff preview"],
        "capabilities_blocked": [
            "worker dispatch",
            "session-send",
            "mutation worker execution",
            "live operations",
            "scoped PR creation",
        ],
        "project_scope": [args.project_id] if args.project_id else [],
        "lane_scope": ["manual_codex_handoff", "read_only_status"],
        "max_concurrent_read_only_lanes": 1,
        "max_concurrent_mutation_lanes": 0,
        "source_of_truth": "WorkerNodeRunRecord",
        "safety_notes": [
            "heartbeat proves laptop worker availability only",
            "worker_dispatch_enabled remains false",
            "session_send_enabled remains false",
            "operator must copy any handoff packet manually",
            "no daemon, cron, autostart, or automatic execution is installed by this script",
        ],
        "worker_dispatch_enabled": False,
        "metadata": {
            "heartbeat_loop": True,
            "operator_started": True,
            "manual_handoff_only": True,
            "smoke_status": args.smoke_status,
            "no_secrets_printed": True,
        },
    }


def _post_json(url: str, payload: dict[str, Any], *, token_env: str, header_name: str, timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get(token_env, "")
    if token:
        headers[header_name] = token
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-supplied Mission Control URL.
        response_body = response.read().decode("utf-8", errors="replace")
        if not response_body:
            return {"status": response.status}
        parsed = json.loads(response_body)
        if isinstance(parsed, dict):
            return parsed
        return {"status": response.status, "response_type": type(parsed).__name__}


def _redacted_payload(payload: dict[str, Any]) -> dict[str, Any]:
    # Payload intentionally contains no secret material; keep this function to
    # make dry-run output explicit and future-proof.
    return dict(payload)


def run_once(args: argparse.Namespace, url: str) -> int:
    payload = _heartbeat_payload(args)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "endpoint": url, "payload": _redacted_payload(payload)}, indent=2, sort_keys=True))
        return 0
    try:
        result = _post_json(
            url,
            payload,
            token_env=args.token_env,
            header_name=args.auth_header_name,
            timeout=args.timeout,
        )
    except urllib.error.HTTPError as exc:
        print(f"heartbeat_failed http_status={exc.code}", file=sys.stderr)
        return 1
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"heartbeat_failed error={exc.__class__.__name__}", file=sys.stderr)
        return 1
    record = result.get("worker_node_run") if isinstance(result, dict) else None
    record_index = result.get("record_index") if isinstance(result, dict) else None
    heartbeat = payload["last_heartbeat_at"]
    print(
        "heartbeat_recorded "
        f"worker_run_id={payload['worker_run_id']} "
        f"presence_status=online "
        f"last_heartbeat_at={heartbeat} "
        f"record_index={record_index if record_index is not None else 'unknown'} "
        f"stored={bool(result.get('stored')) if isinstance(result, dict) else 'unknown'}"
    )
    if isinstance(record, dict) and record.get("worker_dispatch_enabled") is not False:
        print("heartbeat_rejected unsafe worker_dispatch_enabled echoed true", file=sys.stderr)
        return 1
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record manual Codex worker-node online heartbeats.")
    parser.add_argument("--mission-control-url", default=os.environ.get("HERMES_MISSION_CONTROL_URL", ""))
    parser.add_argument("--token-env", default="HERMES_MISSION_CONTROL_TOKEN")
    parser.add_argument("--auth-header-name", default="X-Hermes-Session-Token")
    parser.add_argument("--worker-run-id", default=os.environ.get("CODEX_WORKER_RUN_ID", DEFAULT_WORKER_RUN_ID))
    parser.add_argument("--parent-run-id", default=os.environ.get("CODEX_WORKER_PARENT_RUN_ID", DEFAULT_PARENT_RUN_ID))
    parser.add_argument("--worker-id", default=os.environ.get("CODEX_WORKER_ID", "codex-worker-main-laptop"))
    parser.add_argument("--worker-host-label", default=os.environ.get("CODEX_WORKER_HOST_LABEL", "main-laptop"))
    parser.add_argument("--assigned-packet-id", default=os.environ.get("CODEX_WORKER_PACKET_ID", DEFAULT_PACKET_ID))
    parser.add_argument("--project-id", default=os.environ.get("CODEX_WORKER_PROJECT_ID", "project-hermes-mission-control"))
    parser.add_argument("--objective", default="Keep laptop Codex available for operator-approved manual handoff packets.")
    parser.add_argument("--smoke-status", default="heartbeat_loop_ok")
    parser.add_argument("--worker-version", default=os.environ.get("CODEX_WORKER_VERSION", "codex-worker-lite"))
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--duration-seconds", type=int, default=0, help="0 means run until Ctrl+C unless --once is set.")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        url = _endpoint(args.mission_control_url)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.interval_seconds <= 0:
        print("interval-seconds must be positive", file=sys.stderr)
        return 2
    deadline = time.monotonic() + args.duration_seconds if args.duration_seconds > 0 else None
    while True:
        rc = run_once(args, url)
        if rc != 0 or args.once:
            return rc
        if deadline is not None and time.monotonic() >= deadline:
            return 0
        sleep_for = args.interval_seconds
        if deadline is not None:
            sleep_for = max(0, min(sleep_for, int(deadline - time.monotonic())))
            if sleep_for == 0:
                return 0
        try:
            time.sleep(sleep_for)
        except KeyboardInterrupt:
            print("heartbeat_loop_stopped_by_operator")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
