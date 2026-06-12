"""v0.16 sandbox upgrade safety locks for Travis's Mission Control authority model."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

from fastapi.routing import APIRoute

from hermes_cli.config import DEFAULT_CONFIG
from mission_control.workspace_status import build_workspace_status


REPO_ROOT = Path(__file__).resolve().parents[2]
MISSION_CONTROL_PLUGIN_API = REPO_ROOT / "plugins" / "mission-control-governance" / "api.py"


def _load_mission_control_plugin_api():
    spec = importlib.util.spec_from_file_location(
        "mission_control_governance_v016_safety_lock_test",
        MISSION_CONTROL_PLUGIN_API,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _route_table(module) -> list[tuple[str, tuple[str, ...]]]:
    routes = []
    for route in module.router.routes:
        if isinstance(route, APIRoute):
            routes.append((route.path, tuple(sorted(route.methods or ()))))
    return routes


def test_v016_sandbox_keeps_embedded_kanban_dispatch_default_false():
    """Upstream v0.16 defaulted this true; Travis's Mission Control lane must not."""
    kanban = DEFAULT_CONFIG["kanban"]

    assert kanban["dispatch_in_gateway"] is False


def test_record_sourced_workspace_status_defaults_to_idle_and_dispatch_false():
    status = build_workspace_status(
        {
            "accepted_baseline_record": {
                "baseline_id": "baseline-v016-sandbox",
                "recorded_at": "2026-06-09T00:00:00Z",
                "source": "unit-test",
                "runtime_path": "/home/jenny/.hermes/hermes-runtime-wsreconcile-ef917d4",
                "head": "ef917d48559b2a816d8d1fb15fa40becf8bc5f2d",
                "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
                "rollback_head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
                "dispatch_in_gateway": False,
                "active_kanban": 0,
                "max_active_lane": 1,
                "issue": "none",
            }
        }
    )

    assert status["accepted_baseline_source"] == "record"
    assert status["display_only"] is True
    assert status["trusted_for_execution"] is False
    assert status["execution_enabled"] is False
    assert status["enforcement_enabled"] is False
    assert status["dry_run_only"] is True
    assert status["enforces_runtime"] is False
    assert status["safety"]["dispatch_in_gateway"] is False
    assert status["safety"]["workers_enabled"] is False
    assert status["safety"]["queue_mutation_enabled"] is False
    assert status["safety"]["model_routing_enabled"] is False
    assert status["lane"]["active_lane_count"] == 0
    assert status["lane"]["max_active_lane"] == 1
    assert status["lane"]["active_lane"] == ""
    assert status["activity"]["active_workers"] == 0
    assert status["activity"]["active_tasks"] == 0
    assert status["activity"]["active_runs"] == 0
    assert status["stale_context"]["warnings"] == []


def test_gateway_kanban_watchers_fail_closed_when_dispatch_flag_missing():
    source = (REPO_ROOT / "gateway" / "run.py").read_text(encoding="utf-8")

    assert 'kanban_cfg.get("dispatch_in_gateway", True)' not in source
    assert 'kanban_cfg.get("dispatch_in_gateway", False)' in source
    assert "dispatch_in_gateway` (default True)" not in source
    assert "dispatch_in_gateway` in config.yaml (default True)" not in source


def test_mission_control_governance_router_exposes_no_execution_or_mutation_control_routes():
    module = _load_mission_control_plugin_api()
    routes = _route_table(module)

    forbidden_fragments = (
        "execute",
        "run",
        "deploy",
        "restart",
        "start-worker",
        "worker-start",
        "queue",
        "enqueue",
        "model-route",
        "route-model",
        "enable-enforcement",
        "waha",
    )
    allowed_append_only_record_routes = {
        "/workspace/projects/create",
        "/workspace/projects/seed-defaults",
        "/workspace/project-briefs",
        "/workspace/project-briefs/create",
        "/workspace/challenge-reviews",
        "/workspace/challenge-reviews/create",
        "/workspace/lane-requests/create",
        "/workspace/reports/create",
        "/workspace/jenny-bridge/outbox",
        "/workspace/jenny-bridge/outbox/create",
        "/workspace/jenny-bridge/inbox",
        "/workspace/jenny-bridge/inbox/create",
        "/workspace/session-project-links/create",
        "/workspace/approvals",
        "/workspace/approvals/create",
        "/workspace/runs",
        "/workspace/runs/create",
        "/workspace/report-inbox",
        "/workspace/reports/ingest",
    }
    for path, methods in routes:
        if path in allowed_append_only_record_routes:
            continue
        lowered = path.lower()
        assert not any(fragment in lowered for fragment in forbidden_fragments), (path, methods)

    mutating_routes = {
        path
        for path, methods in routes
        if set(methods) & {"POST", "PUT", "PATCH", "DELETE"}
    }
    assert mutating_routes <= {
        "/global-resource-guard/evaluate",
        "/storage-guard/evaluate",
        "/workspace-status/preview",
        "/pr-merge-verifier-gate/evaluate",
        "/pr-merge-verifier-gate/visibility",
        "/verifier-workflow/evaluate",
        "/start-gate/evaluate",
        "/lane-preflight/evaluate",
        "/workspace/projects/create",
        "/workspace/projects/seed-defaults",
        "/workspace/project-briefs/create",
        "/workspace/challenge-reviews/create",
        "/workspace/lane-requests/create",
        "/workspace/reports/create",
        "/workspace/jenny-bridge/outbox/create",
        "/workspace/jenny-bridge/inbox/create",
        "/workspace/session-project-links/create",
        "/workspace/approvals/create",
        "/workspace/runs/create",
        "/workspace/reports/ingest",
    }


def test_mission_control_governance_api_does_not_spawn_processes_or_call_live_control_primitives():
    tree = ast.parse(MISSION_CONTROL_PLUGIN_API.read_text(encoding="utf-8"))
    forbidden_calls = {
        ("os", "system"),
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
    }
    observed: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name):
                candidate = (owner.id, node.func.attr)
                if candidate in forbidden_calls:
                    observed.append(candidate)

    assert observed == []


def test_mission_control_preview_routes_remain_non_persistent_and_inert(client=None):
    """Structural lock: preview/evaluate routes may report decisions, not runtime authority."""
    module = _load_mission_control_plugin_api()
    routes = _route_table(module)
    preview_or_evaluate = [
        path for path, methods in routes
        if set(methods) & {"POST", "PUT", "PATCH", "DELETE"}
    ]

    assert preview_or_evaluate
    allowed_append_only_record_routes = {
        "/workspace/projects/create",
        "/workspace/projects/seed-defaults",
        "/workspace/project-briefs/create",
        "/workspace/challenge-reviews/create",
        "/workspace/lane-requests/create",
        "/workspace/reports/create",
        "/workspace/jenny-bridge/outbox/create",
        "/workspace/jenny-bridge/inbox/create",
        "/workspace/session-project-links/create",
        "/workspace/approvals/create",
        "/workspace/runs/create",
        "/workspace/reports/ingest",
    }
    assert all(
        path.endswith(("/evaluate", "/preview", "/visibility")) or path in allowed_append_only_record_routes
        for path in preview_or_evaluate
    )
