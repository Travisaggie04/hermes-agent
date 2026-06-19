"""Pure Mission Control runtime provenance and autonomy eligibility checks.

The evaluators in this module are intentionally inert. They only inspect
caller-supplied dictionaries and append-only record projections. They do not
read files, call Git, inspect services, mutate records, dispatch work, start
workers, or send sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PROVENANCE_CLEAN = "CLEAN_AND_ALIGNED"
PROVENANCE_BLOCKED = "BLOCKED_UNSAFE_FOR_AUTONOMY"

_STATUS_PRIORITY = (
    "BROKEN_GIT_METADATA",
    "GATEWAY_UNTRUSTED",
    "MISSING_RUNTIME_PATH",
    "DIRTY_RUNTIME",
    "SOURCE_DEFAULT_DRIFT",
    "DASHBOARD_GATEWAY_DRIFT",
    "SOURCE_CURRENT_BUT_BASELINE_STALE",
    "ROLLBACK_STALE",
)

_BROAD_APPROVAL_VALUES = {"*", "all", "any", "global", "everything", "unlimited", "blanket"}

_ACTIVE_RUN_STATUSES = {"requested", "preflight_passed", "running", "stopping"}
_READ_ONLY_LANE_TYPES = {"read_only_lane", "read_only_design", "read_only_inspection"}
_APPROVED_ACTION_CLASSES = _READ_ONLY_LANE_TYPES

_MUTATION_FORBIDDEN_CLASSES = (
    ("write", "file write", "file-write"),
    ("commit",),
    ("pr", "pull request", "pr creation"),
    ("merge",),
    ("deploy",),
    ("restart",),
    ("runtime switch", "switch runtime", "runtime-switch"),
    ("waha", "whatsapp"),
    ("social",),
    ("payment",),
    ("model routing", "model-routing"),
    ("queue",),
    ("worker",),
    ("timer",),
    ("daemon",),
    ("dispatch",),
    ("session-send", "session send", "session_send"),
)

_PR_FORBIDDEN_CLASSES = (
    ("merge",),
    ("deploy",),
    ("restart",),
    ("runtime switch", "switch runtime", "runtime-switch"),
    ("waha", "whatsapp"),
    ("social",),
    ("payment",),
    ("model routing", "model-routing"),
    ("queue",),
    ("worker",),
    ("timer",),
    ("daemon",),
    ("dispatch",),
    ("session-send", "session send", "session_send"),
)

_CAPABILITY_KEYS = (
    "write_capable_tools",
    "file_write",
    "commit",
    "pr_create",
    "merge",
    "deploy",
    "restart",
    "runtime_switch",
    "waha",
    "waha_enabled",
    "social",
    "social_enabled",
    "payment",
    "payment_enabled",
    "model_routing",
    "model_routing_enabled",
    "queue_mutation",
    "queue_mutation_enabled",
    "worker",
    "worker_dispatch_enabled",
    "workers_enabled",
    "timer",
    "timer_enabled",
    "daemon",
    "daemon_enabled",
    "dispatch",
    "session_send",
)

_PR_BLOCKED_CAPABILITY_KEYS = (
    "merge",
    "deploy",
    "restart",
    "runtime_switch",
    "waha",
    "waha_enabled",
    "social",
    "social_enabled",
    "payment",
    "payment_enabled",
    "model_routing",
    "model_routing_enabled",
    "queue_mutation",
    "queue_mutation_enabled",
    "worker",
    "worker_dispatch_enabled",
    "workers_enabled",
    "timer",
    "timer_enabled",
    "daemon",
    "daemon_enabled",
    "dispatch",
    "session_send",
)

_ACTIVE_PR_STATUSES = {"requested", "preflight_passed", "running", "stopping"}

_PROTECTED_EXECUTION_MARKERS = {
    "deploy": "deploy",
    "deployment": "deploy",
    "restart": "restart",
    "runtime switch": "runtime_switch",
    "runtime_switch": "runtime_switch",
    "runtime-switch": "runtime_switch",
    "merge": "merge",
    "payment": "payment",
    "checkout": "payment",
    "waha": "waha",
    "whatsapp": "waha",
    "social": "social",
    "post": "social",
    "publish": "social",
    "model routing": "model_routing",
    "model_routing": "model_routing",
    "queue": "queue_mutation",
    "timer": "worker_timer_enablement",
    "daemon": "worker_timer_enablement",
    "cron": "worker_timer_enablement",
    "dispatch": "dispatch",
    "session-send": "session_send",
    "session_send": "session_send",
    "session send": "session_send",
}

_PROTECTED_CAPABILITY_KEYS = {
    "merge",
    "deploy",
    "restart",
    "runtime_switch",
    "waha",
    "social",
    "payment",
    "model_routing",
    "queue_mutation",
    "worker",
    "timer",
    "daemon",
    "dispatch",
    "session_send",
    "worker_dispatch_enabled",
}

_PREVIEW_DISABLED_FLAG_REASONS = {
    "would_execute": "would_execute must remain false in previews",
    "would_dispatch": "would_dispatch must remain false in previews",
    "would_session_send": "would_session_send must remain false in previews",
    "execution_enabled": "execution_enabled must remain false",
    "dispatch_enabled": "dispatch_enabled must remain false",
    "session_send_enabled": "session_send_enabled must remain false",
    "worker_dispatch_enabled": "worker_dispatch_enabled must remain false",
}

INERT_PREVIEW_FLAGS = {
    "display_only": True,
    "trusted_for_execution": False,
    "inert_context_only": True,
    "would_execute": False,
    "would_dispatch": False,
    "would_session_send": False,
    "execution_enabled": False,
    "dispatch_enabled": False,
    "session_send_enabled": False,
    "worker_dispatch_enabled": False,
    "stored": False,
    "dry_run_only": True,
}

_BRIDGE_DISABLED_FLAG_REASONS = {
    **_PREVIEW_DISABLED_FLAG_REASONS,
    "worker_enabled": "worker_enabled must remain false",
    "timer_enabled": "timer_enabled must remain false",
    "daemon_enabled": "daemon_enabled must remain false",
    "discord_automation_enabled": "discord_automation_enabled must remain false",
    "model_routing_enabled": "model_routing_enabled must remain false",
}

_PATH_WRITE_CAPABILITY_KEYS = (
    "write_capable",
    "write_capable_tools",
    "file_write",
    "write_file",
    "patch",
    "shell",
    "terminal",
    "execute_code",
    "commit",
    "pr_create",
    "merge",
    "deploy",
    "restart",
    "runtime_switch",
    "waha",
    "social",
    "payment",
    "model_routing",
    "queue_mutation",
    "worker",
    "worker_node_path",
    "delegate",
    "delegate_task",
    "delegation",
    "async_delegation",
    "async_agent",
    "subagent",
    "child_agent",
    "child_agent_capability_inheritance",
    "process_registry",
    "timer",
    "daemon",
    "dispatch",
    "session_send",
    "send_message",
    "post_message",
    "send_to_jenny_enabled",
    "external_response",
    "external_github_response",
    "external_jenny_response",
    "manual_hermes_answer_enabled",
    "post_github_comment",
    "worker_dispatch_enabled",
)

_PATH_WRITE_TOOL_TERMS = (
    "write",
    "patch",
    "shell",
    "terminal",
    "execute",
    "commit",
    "pull request",
    "pr create",
    "merge",
    "deploy",
    "restart",
    "runtime switch",
    "waha",
    "whatsapp",
    "social",
    "payment",
    "model routing",
    "queue",
    "worker",
    "worker node",
    "worker_node",
    "delegate",
    "delegate_task",
    "delegation",
    "async delegation",
    "async_delegation",
    "async agent",
    "async_agent",
    "subagent",
    "child agent",
    "child_agent",
    "process registry",
    "process_registry",
    "timer",
    "daemon",
    "dispatch",
    "session-send",
    "session_send",
    "send message",
    "send_message",
    "post message",
    "post_message",
    "file_operations",
    "file operations",
    "file_tools",
    "file tools",
    "write_file",
    "write file",
    "edit_file",
    "edit file",
    "modify_file",
    "modify file",
    "delete_file",
    "delete file",
    "move_file",
    "move file",
    "apply_patch",
)

_PATH_WRITE_TOOLSET_NAMES = {
    "browser",
    "code_execution",
    "debugging",
    "delegation",
    "file",
    "kanban",
    "messaging",
    "terminal",
}

_DEFAULT_PERMISSION_PATHS: tuple[dict[str, Any], ...] = (
    {
        "path_id": "github_bridge_outbox",
        "label": "GitHub bridge outbox",
        "send_to_jenny_enabled": True,
        "external_response": True,
    },
    {
        "path_id": "github_bridge_answer_once",
        "label": "GitHub bridge answer-once",
        "manual_hermes_answer_enabled": True,
        "external_github_response": True,
    },
    {
        "path_id": "jenny_bridge_relay",
        "label": "Jenny bridge relay",
        "manual_start_only": True,
        "append_records": True,
    },
    {
        "path_id": "hermes_responder_toolsets",
        "label": "Hermes responder toolsets",
        "enabled_toolsets": ["file", "skills"],
    },
    {
        "path_id": "delegate_tool",
        "label": "delegate tool",
        "capability_inheritance": "unknown",
    },
    {
        "path_id": "async_delegation",
        "label": "async delegation",
        "worker": True,
    },
    {
        "path_id": "process_registry",
        "label": "process registry",
        "capability_inheritance": "unknown",
    },
    {
        "path_id": "file_write_shell_patch",
        "label": "file/write/shell/patch capabilities",
        "file_write": True,
        "shell": True,
        "patch": True,
    },
    {
        "path_id": "laptop_codex_worker_node",
        "label": "laptop Codex worker-node path",
        "worker_node_path": True,
        "write_capable_tools": True,
    },
    {
        "path_id": "child_agent_capability_inheritance",
        "label": "child-agent capability inheritance",
        "capability_inheritance": "unknown",
    },
)


def evaluate_runtime_provenance(observed_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate caller-supplied runtime/source provenance and fail closed.

    Expected input keys are intentionally simple dictionaries:
    source, accepted_baseline, dashboard_runtime, gateway_runtime,
    rollback_runtime, dispatch_state, and active_lane_count.
    """

    state = dict(observed_state or {})
    source = _section(state, "source")
    baseline = _section(state, "accepted_baseline")
    dashboard = _section(state, "dashboard_runtime")
    gateway = _section(state, "gateway_runtime")
    rollback = _section(state, "rollback_runtime")

    source_head = _safe_text(source.get("head") or state.get("source_head"))
    baseline_head = _safe_text(baseline.get("head"))
    dashboard_head = _safe_text(dashboard.get("head"))
    gateway_head = _safe_text(gateway.get("head"))
    rollback_head = _safe_text(rollback.get("head"))
    default_branch_head = _safe_text(source.get("default_branch_head") or state.get("default_branch_head"))
    latest_merged_pr = _safe_text(source.get("latest_merged_pr") or state.get("latest_merged_pr"))
    merged_prs_after_baseline = [
        _safe_text(item, max_chars=80)
        for item in _as_list(
            source.get("merged_prs_after_accepted_baseline")
            or state.get("merged_prs_after_accepted_baseline")
        )
        if _safe_text(item, max_chars=80)
    ]

    statuses: list[str] = []
    reasons: list[str] = []
    blocked_reasons: list[str] = []
    runtimes: dict[str, dict[str, Any]] = {}

    for name, runtime in (
        ("accepted_baseline", baseline),
        ("dashboard", dashboard),
        ("gateway", gateway),
        ("rollback", rollback),
    ):
        summary = _runtime_summary(name, runtime)
        runtimes[name] = summary
        if summary["missing_path"]:
            _add(statuses, "MISSING_RUNTIME_PATH")
            _add(blocked_reasons, f"{name} runtime path is missing or absent")
        if summary["broken_git_metadata"]:
            _add(statuses, "BROKEN_GIT_METADATA")
            if name == "gateway":
                _add(statuses, "GATEWAY_UNTRUSTED")
            _add(blocked_reasons, f"{name} git metadata is broken")
        if summary["dirty"]:
            _add(statuses, "DIRTY_RUNTIME")
            _add(blocked_reasons, f"{name} runtime has dirty or untracked files")

    if not source_head:
        _add(blocked_reasons, "source HEAD is missing")
    if source_head and default_branch_head and source_head != default_branch_head:
        _add(statuses, "SOURCE_DEFAULT_DRIFT")
        _add(blocked_reasons, "source HEAD does not match default branch HEAD")
    if not baseline_head:
        _add(blocked_reasons, "accepted baseline HEAD is missing")
    if source_head and baseline_head and source_head != baseline_head:
        _add(statuses, "SOURCE_CURRENT_BUT_BASELINE_STALE")
        _add(blocked_reasons, "accepted baseline HEAD does not match source HEAD")
        if latest_merged_pr:
            _add(blocked_reasons, f"latest merged PR #{latest_merged_pr} is after the accepted baseline")
    if merged_prs_after_baseline:
        _add(statuses, "SOURCE_CURRENT_BUT_BASELINE_STALE")
        _add(
            blocked_reasons,
            "merged PRs after accepted baseline: "
            + ", ".join(_format_pr_label(item) for item in merged_prs_after_baseline[:8]),
        )
    if dashboard_head and baseline_head and dashboard_head != baseline_head:
        _add(statuses, "SOURCE_CURRENT_BUT_BASELINE_STALE")
        _add(blocked_reasons, "dashboard runtime HEAD does not match accepted baseline HEAD")
    if dashboard_head and gateway_head and dashboard_head != gateway_head:
        _add(statuses, "DASHBOARD_GATEWAY_DRIFT")
        _add(blocked_reasons, "dashboard and gateway runtime HEADs do not match")
    if source_head and gateway_head and source_head != gateway_head:
        _add(statuses, "DASHBOARD_GATEWAY_DRIFT")
        _add(blocked_reasons, "gateway runtime HEAD does not match source HEAD")
    if source_head and rollback_head and source_head != rollback_head:
        _add(statuses, "ROLLBACK_STALE")
        _add(reasons, "rollback runtime HEAD is stale relative to source HEAD")
        _add(blocked_reasons, "rollback runtime is stale relative to source HEAD")

    if _flag_enabled(state.get("dispatch_state")) or _flag_enabled(state.get("dispatch_in_gateway")):
        _add(blocked_reasons, "dispatch is enabled")
    if _safe_int(state.get("active_lane_count")) > _safe_int(state.get("max_active_lane"), default=1):
        _add(blocked_reasons, "active lane count exceeds configured maximum")

    if not statuses and not blocked_reasons:
        statuses = [PROVENANCE_CLEAN]

    autonomy_blocked = bool(blocked_reasons) or statuses != [PROVENANCE_CLEAN]
    return {
        **INERT_PREVIEW_FLAGS,
        "status": PROVENANCE_BLOCKED if autonomy_blocked else PROVENANCE_CLEAN,
        "primary_status": _primary_status(statuses),
        "statuses": statuses,
        "autonomy_blocked": autonomy_blocked,
        "autonomy_blocked_reasons": blocked_reasons,
        "warnings": reasons,
        "source_head": source_head,
        "accepted_baseline_head": baseline_head,
        "dashboard_head": dashboard_head,
        "gateway_head": gateway_head,
        "rollback_head": rollback_head,
        "default_branch_head": default_branch_head,
        "latest_merged_pr": latest_merged_pr,
        "merged_prs_after_accepted_baseline": merged_prs_after_baseline,
        "runtimes": runtimes,
        "dry_run_only": True,
        "enforces_runtime": False,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "send_to_jenny_enabled": False,
        "worker_dispatch_enabled": False,
    }


def classify_bridge_permissions(bridge_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify whether a bridge path may be treated as read-only autonomy."""

    state = dict(bridge_state or {})
    reasons: list[str] = []
    disabled_flag_reasons = [
        reason
        for key, reason in _BRIDGE_DISABLED_FLAG_REASONS.items()
        if _flag_enabled(state.get(key))
    ]

    if disabled_flag_reasons:
        return _bridge_result(
            "write_capable_not_safe_for_autonomy",
            False,
            ["bridge live execution flags must be disabled: " + "; ".join(disabled_flag_reasons[:8])],
        )

    if any(
        _flag_enabled(state.get(key))
        for key in (
            "execution_enabled",
            "send_to_jenny_enabled",
            "manual_hermes_answer_enabled",
            "external_response",
            "external_github_response",
            "external_jenny_response",
            "writes_external_response",
            "post_github_comment",
        )
    ):
        return _bridge_result("write_capable_not_safe_for_autonomy", False, ["bridge can execute or write an external/response record"])

    if _safe_bool(state.get("append_records")) or _safe_bool(state.get("stored")):
        _add(reasons, "bridge appends records and is manual-only, not a read-only executor")
        return _bridge_result("manual_only", False, reasons)

    if _safe_bool(state.get("manual_start_only")) or _safe_bool(state.get("manual_copy_only")):
        _add(reasons, "bridge is manual-only")
        return _bridge_result("manual_only", False, reasons)

    if _safe_bool(state.get("read_only_safe")):
        return _bridge_result("read_only_safe", True, [])

    return _bridge_result("unknown_blocked", False, ["bridge safety is not proven; defaulting to blocked"])


def classify_control_path_permissions(observed_state: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    """Classify Mission Control bridge/tool/worker paths without enabling them."""

    paths = [_classify_control_path(path) for path in _permission_path_inputs(observed_state)]
    write_capable = [path for path in paths if path["permission_classification"] == "write_capable_not_safe_for_autonomy"]
    unknown = [path for path in paths if path["permission_classification"] == "unknown_blocked"]
    manual = [path for path in paths if path["permission_classification"] == "manual_only"]
    read_only = [path for path in paths if path["permission_classification"] == "read_only_safe"]
    if write_capable:
        classification = "write_capable_not_safe_for_autonomy"
    elif unknown:
        classification = "unknown_blocked"
    elif paths and len(read_only) == len(paths):
        classification = "read_only_safe"
    elif manual:
        classification = "manual_only"
    else:
        classification = "unknown_blocked"
    blocked_reasons = [
        f"{path['path_id']}: {reason}"
        for path in paths
        if path["permission_classification"] != "read_only_safe"
        for reason in path.get("reasons", ())
    ]
    return {
        **INERT_PREVIEW_FLAGS,
        "source": "mission_control_control_path_permission_preview_v1",
        "permission_classification": classification,
        "read_only_safe": classification == "read_only_safe",
        "stored": False,
        "dry_run_only": True,
        "display_only": True,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "path_count": len(paths),
        "read_only_safe_path_count": len(read_only),
        "manual_only_path_count": len(manual),
        "write_capable_path_count": len(write_capable),
        "unknown_blocked_path_count": len(unknown),
        "write_capable_path_ids": [path["path_id"] for path in write_capable],
        "unknown_path_ids": [path["path_id"] for path in unknown],
        "blocked_path_count": len(write_capable) + len(unknown),
        "blocked_reasons": blocked_reasons,
        "paths": paths,
    }


def classify_execution_mode(observed_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify a requested orchestration mode without enabling execution."""

    state = dict(observed_state or {})
    run = _section(state, "run")
    lane = _section(state, "lane")
    approval = _section(state, "approval")
    worker_node = _section(state, "worker_node")
    capabilities = _section(state, "capabilities")
    requested_mode = _safe_text(
        state.get("mode")
        or state.get("execution_mode")
        or run.get("execution_mode")
        or lane.get("mode")
    )
    lane_type = _safe_text(
        state.get("lane_type")
        or run.get("lane_type")
        or lane.get("lane_type")
    )
    action_class = _safe_text(
        state.get("action_class")
        or approval.get("action_class")
        or lane.get("action_class")
    )
    mode_terms = tuple(
        text.lower()
        for text in (
            requested_mode,
            lane_type,
            action_class,
            _safe_text(run.get("title")),
            _safe_text(run.get("objective")),
            _safe_text(lane.get("objective")),
        )
        if text
    )
    protected_markers = _execution_protected_markers(
        mode_terms=mode_terms,
        state=state,
        lane=lane,
        run=run,
        capabilities=capabilities,
    )
    blocked_reasons: list[str] = []
    warnings: list[str] = []

    mode_family = "unknown_blocked"
    if _worker_node_requested(state, worker_node, requested_mode, lane_type, action_class):
        mode_family = "worker_node_preview"
        _add(warnings, "worker-node mode is manual-handoff only and not an executor")
    elif lane_type in {"pr_creation", "scoped_pr"} or action_class == "pr_creation" or requested_mode == "scoped_pr":
        mode_family = "scoped_pr_preview"
    elif (
        lane_type in _READ_ONLY_LANE_TYPES
        or lane_type.startswith("read_only")
        or action_class in _APPROVED_ACTION_CLASSES
        or requested_mode == "read_only"
        or requested_mode.startswith("read_only")
    ):
        mode_family = "read_only_preview"
    elif requested_mode or lane_type or action_class:
        mode_family = "higher_risk_blocked"

    if mode_family == "unknown_blocked":
        _add(blocked_reasons, "execution mode is not recognized")
    if protected_markers:
        if mode_family in {"read_only_preview", "scoped_pr_preview", "worker_node_preview"}:
            _add(blocked_reasons, f"requested mode includes protected actions: {', '.join(protected_markers[:8])}")
        else:
            mode_family = "higher_risk_blocked"
            _add(blocked_reasons, f"higher-risk mode requires separate approval: {', '.join(protected_markers[:8])}")
    if action_class in {"implementation", "deploy", "runtime_switch", "payment", "waha", "social_post", "model_routing", "queue_mutation", "worker_timer_enablement"}:
        mode_family = "higher_risk_blocked"
        _add(blocked_reasons, f"action_class {action_class} is not eligible for autonomous execution")
    if _flag_enabled(state.get("execution_enabled")) or _flag_enabled(run.get("execution_enabled")):
        _add(blocked_reasons, "execution_enabled must remain false")
    if _flag_enabled(state.get("dispatch_enabled")) or _flag_enabled(run.get("dispatch_enabled")):
        _add(blocked_reasons, "dispatch_enabled must remain false")
    if _flag_enabled(state.get("session_send_enabled")) or _flag_enabled(run.get("session_send_enabled")):
        _add(blocked_reasons, "session_send_enabled must remain false")
    if _flag_enabled(state.get("worker_dispatch_enabled")) or _flag_enabled(worker_node.get("worker_dispatch_enabled")):
        _add(blocked_reasons, "worker_dispatch_enabled must remain false")

    preview_ready = mode_family in {"read_only_preview", "scoped_pr_preview", "worker_node_preview"} and not blocked_reasons
    return {
        **INERT_PREVIEW_FLAGS,
        "source": "mission_control_execution_mode_classification_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "stored": False,
        "dry_run_only": True,
        "requested_mode": requested_mode,
        "lane_type": lane_type,
        "action_class": action_class,
        "mode_family": mode_family,
        "preview_ready": preview_ready,
        "higher_risk": mode_family == "higher_risk_blocked",
        "separate_approval_required": mode_family == "higher_risk_blocked" or bool(protected_markers),
        "manual_handoff_only": mode_family == "worker_node_preview",
        "read_only_preview_allowed": mode_family == "read_only_preview" and not blocked_reasons,
        "scoped_pr_preview_allowed": mode_family == "scoped_pr_preview" and not blocked_reasons,
        "worker_node_preview_allowed": mode_family == "worker_node_preview" and not blocked_reasons,
        "protected_action_markers": protected_markers,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
    }


def evaluate_read_only_autonomy_eligibility(observed_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Preview whether a read-only Jenny lane is eligible without executing it."""

    state = dict(observed_state or {})
    provenance = state.get("runtime_provenance")
    if not isinstance(provenance, dict):
        provenance = evaluate_runtime_provenance(_section(state, "runtime"))

    bridge = classify_bridge_permissions(_section(state, "bridge"))
    approval = _section(state, "approval")
    run = _section(state, "run")
    report = _section(state, "report")
    lane = _section(state, "lane")
    capabilities = _section(state, "capabilities")
    tool_permissions = _optional_tool_permissions(state)

    blocked: list[str] = []
    warnings: list[str] = []

    if provenance.get("autonomy_blocked") is not False or provenance.get("primary_status") != PROVENANCE_CLEAN:
        _add(blocked, "runtime provenance is not clean")
        for reason in provenance.get("autonomy_blocked_reasons", ()):
            _add(blocked, str(reason))

    _check_approval(approval, blocked, now=_safe_text(state.get("now")))
    _check_run(run, approval, blocked)
    _check_report_inbox(report, state, blocked)
    _check_lane(run, lane, blocked)
    _check_forbidden_actions(run, lane, blocked)
    _check_capabilities(capabilities, blocked)
    _check_preview_disabled_flags(blocked, state, run, lane)

    if _safe_int(state.get("active_mutation_lane_count")) > 0:
        _add(blocked, "active mutation lane count must be 0")
    if bridge["permission_classification"] in {"write_capable", "unsafe_for_autonomy", "write_capable_not_safe_for_autonomy", "unknown_blocked"}:
        _add(blocked, "bridge path is not read-only safe")
    elif bridge["permission_classification"] == "manual_only":
        _add(warnings, "bridge path is manual-only; preview must not execute")
    if tool_permissions:
        _check_tool_permissions_for_read_only(tool_permissions, blocked, warnings)

    return {
        **INERT_PREVIEW_FLAGS,
        "eligible": not blocked,
        "blocked_reasons": blocked,
        "warnings": warnings,
        "runtime_provenance": provenance,
        "bridge_permissions": bridge,
        "tool_permissions": tool_permissions or {},
        "would_execute": False,
        "stored": False,
        "dry_run_only": True,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "send_to_jenny_enabled": False,
        "worker_dispatch_enabled": False,
    }


def evaluate_scoped_pr_lane_eligibility(observed_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Preview whether a scoped PR-creation lane is eligible without running it."""

    state = dict(observed_state or {})
    provenance = state.get("runtime_provenance")
    if not isinstance(provenance, dict):
        provenance = evaluate_runtime_provenance(_section(state, "runtime"))

    approval = _section(state, "approval")
    run = _section(state, "run")
    lane = _section(state, "lane")
    capabilities = _section(state, "capabilities")
    report_contract = _section(state, "report_contract")
    bridge = classify_bridge_permissions(_section(state, "bridge"))
    tool_permissions = _optional_tool_permissions(state)

    blocked: list[str] = []
    warnings: list[str] = []

    if provenance.get("autonomy_blocked") is not False or provenance.get("primary_status") != PROVENANCE_CLEAN:
        _add(blocked, "runtime provenance is not clean")
        for reason in provenance.get("autonomy_blocked_reasons", ()):
            _add(blocked, str(reason))

    _check_pr_approval(approval, blocked, now=_safe_text(state.get("now")))
    _check_pr_run(run, approval, blocked)
    _check_pr_scope(approval, lane, blocked)
    _check_pr_forbidden_actions(run, lane, blocked)
    _check_pr_capabilities(capabilities, blocked)
    _check_preview_disabled_flags(blocked, state, run, lane)

    active_mutation_lane_count = _safe_int(state.get("active_mutation_lane_count"))
    if active_mutation_lane_count > 1:
        _add(blocked, "scoped PR lane requires at most one active mutation lane")
    if active_mutation_lane_count == 1 and _safe_text(run.get("lane_type")) != "pr_creation":
        _add(blocked, "the only active mutation lane must be this scoped PR lane")
    if _flag_enabled(state.get("merge_allowed")) or _flag_enabled(lane.get("merge_allowed")):
        _add(blocked, "merge is not allowed in scoped PR lanes")
    if _flag_enabled(state.get("deploy_allowed")) or _flag_enabled(lane.get("deploy_allowed")):
        _add(blocked, "deploy is not allowed in scoped PR lanes")
    if _flag_enabled(state.get("runtime_switch_allowed")) or _flag_enabled(lane.get("runtime_switch_allowed")):
        _add(blocked, "runtime switch is not allowed in scoped PR lanes")
    if _safe_bool(report_contract.get("required")) is not True:
        _add(blocked, "report/result contract is required")
    if _safe_bool(report_contract.get("tests_required")) is not True and _safe_bool(lane.get("tests_required")) is not True:
        _add(blocked, "tests are required for scoped PR lanes")
    if _safe_bool(report_contract.get("review_required")) is not True and _safe_bool(lane.get("review_required")) is not True:
        _add(blocked, "human review is required before merge")
    if bridge["permission_classification"] in {"write_capable", "unsafe_for_autonomy", "write_capable_not_safe_for_autonomy"}:
        _add(blocked, "write-capable bridge path cannot be used for scoped PR lane execution")
    elif bridge["permission_classification"] in {"manual_only", "unknown_blocked"}:
        _add(warnings, "bridge path is not an executor; PR lane preview remains inert")
    if tool_permissions:
        _check_tool_permissions_for_scoped_pr(tool_permissions, blocked, warnings)

    scope = _explicit_scope(approval, lane)
    return {
        **INERT_PREVIEW_FLAGS,
        "eligible": not blocked,
        "blocked_reasons": blocked,
        "warnings": warnings,
        "runtime_provenance": provenance,
        "bridge_permissions": bridge,
        "tool_permissions": tool_permissions or {},
        "scope": scope,
        "would_execute": False,
        "would_create_pr": False,
        "would_commit": False,
        "stored": False,
        "dry_run_only": True,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
        "merge_enabled": False,
        "deploy_enabled": False,
        "runtime_switch_enabled": False,
    }


def build_execution_packet_preview(observed_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a future work-packet preview while keeping execution disabled."""

    state = dict(observed_state or {})
    mode = _safe_text(state.get("mode") or state.get("execution_mode"))
    if mode not in {"read_only", "scoped_pr", "worker_node"}:
        mode = "blocked"
    eligibility = (
        evaluate_read_only_autonomy_eligibility(state)
        if mode == "read_only"
        else evaluate_scoped_pr_lane_eligibility(state)
        if mode == "scoped_pr"
        else _evaluate_worker_node_packet_preview(state)
        if mode == "worker_node"
        else {
            "eligible": False,
            "blocked_reasons": ["execution mode is not recognized"],
            "warnings": [],
        }
    )
    blocked_reasons = list(eligibility.get("blocked_reasons") or ())
    _check_preview_disabled_flags(
        blocked_reasons,
        state,
        _section(state, "run"),
        _section(state, "lane"),
        _section(state, "worker_node"),
    )
    packet = {
        **INERT_PREVIEW_FLAGS,
        "packet_version": "mission_control_execution_packet_preview_v1",
        "mode": mode,
        "run_id": _safe_text(_section(state, "run").get("run_id")),
        "approval_id": _safe_text(_section(state, "approval").get("approval_id")),
        "project_id": _safe_text(_section(state, "run").get("project_id") or _section(state, "approval").get("project_id")),
        "objective": _safe_text(_section(state, "run").get("objective") or _section(state, "lane").get("objective"), max_chars=800),
        "allowed_actions": _bounded_texts(_as_list(_section(state, "run").get("allowed_actions")) + _as_list(_section(state, "lane").get("allowed_actions"))),
        "forbidden_actions": _bounded_texts(_as_list(_section(state, "run").get("forbidden_actions")) + _as_list(_section(state, "lane").get("forbidden_actions"))),
        "scope": _explicit_scope(_section(state, "approval"), _section(state, "lane")),
        "report_contract": _section(state, "report_contract"),
        "child_run_contract": _section(state, "child_run_contract"),
        "worker_node_contract": _worker_node_contract(state),
    }
    return {
        **INERT_PREVIEW_FLAGS,
        "source": "mission_control_execution_packet_preview_v1",
        "eligible": bool(eligibility.get("eligible")) and not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "warnings": list(eligibility.get("warnings") or ()),
        "packet": packet,
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "stored": False,
        "dry_run_only": True,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _evaluate_worker_node_packet_preview(state: dict[str, Any]) -> dict[str, Any]:
    worker_node = _section(state, "worker_node")
    report_contract = _section(state, "report_contract")
    lane = _section(state, "lane")
    run = _section(state, "run")
    requested_mode = _safe_text(
        worker_node.get("lane_mode")
        or worker_node.get("mode")
        or state.get("worker_node_mode")
        or state.get("worker_mode")
        or lane.get("lane_type")
        or lane.get("mode")
        or run.get("lane_type")
    )
    if requested_mode in {"pr_creation", "scoped_pr"}:
        base = evaluate_scoped_pr_lane_eligibility(state)
    elif requested_mode in _READ_ONLY_LANE_TYPES or requested_mode.startswith("read_only"):
        base = evaluate_read_only_autonomy_eligibility(state)
    else:
        base = {
            "eligible": False,
            "blocked_reasons": ["worker-node packet requires read_only or scoped_pr lane mode"],
            "warnings": [],
        }

    blocked = list(base.get("blocked_reasons") or ())
    warnings = list(base.get("warnings") or ())
    if _flag_enabled(worker_node.get("worker_dispatch_enabled")) or _flag_enabled(state.get("worker_dispatch_enabled")):
        _add(blocked, "worker dispatch must stay disabled")
    if _flag_enabled(worker_node.get("execution_enabled")) or _flag_enabled(state.get("execution_enabled")):
        _add(blocked, "worker execution must stay disabled")
    if _flag_enabled(worker_node.get("session_send_enabled")) or _flag_enabled(state.get("session_send_enabled")):
        _add(blocked, "session sending must stay disabled")
    _check_preview_disabled_flags(
        blocked,
        state,
        run,
        lane,
        worker_node,
        keys=("dispatch_enabled", "would_execute", "would_dispatch", "would_session_send"),
    )
    if _safe_bool(report_contract.get("required")) is not True:
        _add(blocked, "worker-node report contract is required")
    if _safe_bool(report_contract.get("tests_required")) is not True:
        _add(blocked, "worker-node tests/checks are required")
    if _safe_bool(report_contract.get("review_required")) is not True:
        _add(blocked, "worker-node report review is required")
    if not _safe_text(worker_node.get("objective") or run.get("objective") or lane.get("objective")):
        _add(blocked, "worker-node objective is required")
    if not _safe_text(worker_node.get("parent_run_id") or run.get("run_id")):
        _add(blocked, "worker-node parent run is required")
    presence_status = _safe_text(worker_node.get("presence_status") or worker_node.get("presence_state"))
    if presence_status != "online" and _safe_bool(worker_node.get("online")) is not True:
        _add(blocked, "worker-node presence is not confirmed online")

    _add(warnings, "worker-node packet is a manual handoff preview; no worker dispatch is enabled")
    return {
        **INERT_PREVIEW_FLAGS,
        "eligible": not blocked,
        "blocked_reasons": blocked,
        "warnings": warnings,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "stored": False,
        "dry_run_only": True,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _worker_node_contract(state: dict[str, Any]) -> dict[str, Any]:
    worker_node = _section(state, "worker_node")
    run = _section(state, "run")
    lane = _section(state, "lane")
    worker_safety_hardness = [
        "Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.",
        "A Jenny packet is not permission to bypass Codex safety checks.",
    ]
    return {
        **INERT_PREVIEW_FLAGS,
        "worker_identity": _safe_text(worker_node.get("worker_identity")) or "codex",
        "worker_host_label": _safe_text(worker_node.get("worker_host_label")) or "laptop-codex",
        "worker_kind": _safe_text(worker_node.get("worker_kind")) or "laptop_codex",
        "parent_run_id": _safe_text(worker_node.get("parent_run_id") or run.get("run_id")),
        "assigned_packet_id": _safe_text(worker_node.get("assigned_packet_id")),
        "assigned_packet_summary": _safe_text(worker_node.get("assigned_packet_summary"), max_chars=800),
        "objective": _safe_text(worker_node.get("objective") or run.get("objective") or lane.get("objective"), max_chars=800),
        "report_contract_status": _safe_text(worker_node.get("report_contract_status") or "required"),
        "report_review_status": _safe_text(worker_node.get("report_review_status") or "required"),
        "manual_handoff_only": True,
        "codex_safety_hardness_required": True,
        "worker_safety_hardness": worker_safety_hardness,
        "trusted_for_execution": False,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _worker_node_requested(
    state: dict[str, Any],
    worker_node: dict[str, Any],
    requested_mode: str,
    lane_type: str,
    action_class: str,
) -> bool:
    return bool(worker_node) or requested_mode == "worker_node" or lane_type == "worker_node" or action_class == "worker_node"


def _execution_protected_markers(
    *,
    mode_terms: tuple[str, ...],
    state: dict[str, Any],
    lane: dict[str, Any],
    run: dict[str, Any],
    capabilities: dict[str, Any],
) -> list[str]:
    markers: list[str] = []
    for term in mode_terms:
        if term in {"worker_node", "laptop_codex_worker_node"}:
            continue
        for pattern, marker in _PROTECTED_EXECUTION_MARKERS.items():
            if pattern in term:
                _add(markers, marker)
    for key in _PROTECTED_CAPABILITY_KEYS:
        if _flag_enabled(state.get(key)) or _flag_enabled(lane.get(key)) or _flag_enabled(run.get(key)) or _flag_enabled(capabilities.get(key)):
            _add(markers, _permission_marker_label(key))
    for key in ("allowed_actions", "requested_actions", "tools", "tool_names"):
        for item in _as_list(state.get(key)) + _as_list(lane.get(key)) + _as_list(run.get(key)):
            lowered = _safe_text(item).lower()
            for pattern, marker in _PROTECTED_EXECUTION_MARKERS.items():
                if pattern in lowered:
                    _add(markers, marker)
                    break
    return markers


def _optional_tool_permissions(state: dict[str, Any]) -> dict[str, Any]:
    value = state.get("tool_permissions")
    if isinstance(value, dict) or isinstance(value, list):
        return classify_control_path_permissions(value)
    return {}


def _check_tool_permissions_for_read_only(tool_permissions: dict[str, Any], blocked: list[str], warnings: list[str]) -> None:
    classification = _safe_text(tool_permissions.get("permission_classification"))
    if classification in {"write_capable_not_safe_for_autonomy", "unknown_blocked"}:
        _add(blocked, "tool permission paths are not read-only safe")
        for reason in tool_permissions.get("blocked_reasons", ())[:8]:
            _add(blocked, str(reason))
    elif classification == "manual_only":
        _add(warnings, "tool permission paths are manual-only; preview must not execute")


def _check_tool_permissions_for_scoped_pr(tool_permissions: dict[str, Any], blocked: list[str], warnings: list[str]) -> None:
    classification = _safe_text(tool_permissions.get("permission_classification"))
    if classification == "write_capable_not_safe_for_autonomy":
        _add(blocked, "write-capable tool paths cannot be used for scoped PR lane execution")
        for reason in tool_permissions.get("blocked_reasons", ())[:8]:
            _add(blocked, str(reason))
    elif classification in {"manual_only", "unknown_blocked"}:
        _add(warnings, "tool permission paths are not executors; PR lane preview remains inert")


def _permission_path_inputs(observed_state: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
    if observed_state is None:
        return [dict(path) for path in _DEFAULT_PERMISSION_PATHS]
    if isinstance(observed_state, list):
        return [dict(item) for item in observed_state if isinstance(item, dict)] or [dict(path) for path in _DEFAULT_PERMISSION_PATHS]
    if not isinstance(observed_state, dict):
        return [dict(path) for path in _DEFAULT_PERMISSION_PATHS]
    paths = observed_state.get("paths")
    if isinstance(paths, list):
        return [dict(item) for item in paths if isinstance(item, dict)] or [dict(path) for path in _DEFAULT_PERMISSION_PATHS]
    if isinstance(paths, dict):
        output: list[dict[str, Any]] = []
        for path_id, value in paths.items():
            if isinstance(value, dict):
                output.append({"path_id": str(path_id), **value})
        return output or [dict(path) for path in _DEFAULT_PERMISSION_PATHS]
    if any(key in observed_state for key in ("path_id", "id", "label", "read_only_safe", "manual_only")):
        return [dict(observed_state)]
    return [dict(path) for path in _DEFAULT_PERMISSION_PATHS]


def _classify_control_path(path: dict[str, Any]) -> dict[str, Any]:
    path_id = _safe_text(path.get("path_id") or path.get("id") or path.get("name")) or "unknown_path"
    label = _safe_text(path.get("label") or path.get("name")) or path_id
    reasons: list[str] = []
    write_markers = _write_capability_markers(path)
    if write_markers:
        _add(reasons, f"path exposes write or execution capabilities: {', '.join(write_markers[:8])}")
        classification = "write_capable_not_safe_for_autonomy"
        read_only_safe = False
    elif _capability_inheritance_unknown(path):
        _add(reasons, "path capability inheritance is unknown")
        classification = "unknown_blocked"
        read_only_safe = False
    elif _safe_bool(path.get("read_only_safe")):
        classification = "read_only_safe"
        read_only_safe = True
    elif _manual_only_path(path):
        _add(reasons, "path is manual-only or append-only")
        classification = "manual_only"
        read_only_safe = False
    else:
        _add(reasons, "path safety is not proven; defaulting to blocked")
        classification = "unknown_blocked"
        read_only_safe = False
    return {
        **INERT_PREVIEW_FLAGS,
        "path_id": path_id,
        "label": label,
        "permission_classification": classification,
        "read_only_safe": read_only_safe,
        "reasons": reasons,
        "write_capability_markers": write_markers,
        "manual_only": classification == "manual_only",
        "stored": False,
        "dry_run_only": True,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "session_send_enabled": False,
        "worker_dispatch_enabled": False,
    }


def _write_capability_markers(path: dict[str, Any]) -> list[str]:
    markers: list[str] = []
    capability_dict = _section(path, "capabilities")
    for key in _PATH_WRITE_CAPABILITY_KEYS:
        if _flag_enabled(path.get(key)) or _flag_enabled(capability_dict.get(key)):
            _add(markers, _permission_marker_label(key))
    for toolset in _path_toolset_texts(path):
        if toolset in _PATH_WRITE_TOOLSET_NAMES:
            _add(markers, f"{toolset} toolset")
    for text_value in _path_tool_texts(path):
        lowered = text_value.lower()
        for term in _PATH_WRITE_TOOL_TERMS:
            if term in lowered:
                _add(markers, term)
                break
    return markers


def _permission_marker_label(value: str) -> str:
    return value.replace("_", " ")


def _format_pr_label(value: str) -> str:
    text = _safe_text(value, max_chars=80).lstrip("#")
    return f"PR #{text}" if text else "unknown PR"


def _path_tool_texts(path: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("tools", "tool_names", "allowed_tools", "capability_names"):
        for item in _as_list(path.get(key)):
            text = _safe_text(item)
            if text:
                texts.append(text)
    capabilities = path.get("capabilities")
    if isinstance(capabilities, dict):
        texts.extend(str(key) for key, value in capabilities.items() if _flag_enabled(value))
    return texts


def _path_toolset_texts(path: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("toolsets", "enabled_toolsets", "responder_toolsets"):
        for item in _as_list(path.get(key)):
            text = _safe_text(item).lower().replace(",", " ")
            for part in text.split():
                if part:
                    texts.append(part)
    return texts


def _capability_inheritance_unknown(path: dict[str, Any]) -> bool:
    inheritance = _safe_text(path.get("capability_inheritance")).lower()
    if inheritance in {"unknown", "parent", "inherits_parent", "unbounded"}:
        return True
    if _flag_enabled(path.get("unknown_capabilities")):
        return True
    if _flag_enabled(path.get("inherits_parent_capabilities")) and not _safe_bool(path.get("inherited_capabilities_read_only")):
        return True
    return False


def _manual_only_path(path: dict[str, Any]) -> bool:
    return any(
        _safe_bool(path.get(key))
        for key in (
            "manual_only",
            "manual_start_only",
            "manual_copy_only",
            "manual_handoff_only",
            "append_records",
            "record_append_only",
        )
    )


def _check_approval(approval: dict[str, Any], blocked: list[str], *, now: str = "") -> None:
    if not approval:
        _add(blocked, "exact approved ApprovalRecord is required")
        return
    if _safe_text(approval.get("status")) != "approved":
        _add(blocked, "approval status must be approved")
    if _safe_text(approval.get("approval_mode") or "one_time") != "one_time":
        _add(blocked, "approval_mode must be one_time")
    if _safe_text(approval.get("consumed_at")) or _safe_text(approval.get("status")) == "consumed":
        _add(blocked, "approval is consumed")
    if _is_expired(_safe_text(approval.get("expires_at")), now=now):
        _add(blocked, "approval is expired")
    if _scope_is_missing_or_broad(_safe_text(approval.get("approval_scope"))):
        _add(blocked, "approval scope must be exact and bounded")
    if _safe_text(approval.get("action_class")) not in _APPROVED_ACTION_CLASSES:
        _add(blocked, "approval action_class must be read-only")


def _check_pr_approval(approval: dict[str, Any], blocked: list[str], *, now: str = "") -> None:
    if not approval:
        _add(blocked, "exact approved ApprovalRecord is required")
        return
    if _safe_text(approval.get("status")) != "approved":
        _add(blocked, "approval status must be approved")
    if _safe_text(approval.get("approval_mode") or "one_time") != "one_time":
        _add(blocked, "approval_mode must be one_time")
    if _safe_text(approval.get("consumed_at")) or _safe_text(approval.get("status")) == "consumed":
        _add(blocked, "approval is consumed")
    if _is_expired(_safe_text(approval.get("expires_at")), now=now):
        _add(blocked, "approval is expired")
    if _scope_is_missing_or_broad(_safe_text(approval.get("approval_scope"))):
        _add(blocked, "approval scope must be exact and bounded")
    if _safe_text(approval.get("action_class")) != "pr_creation":
        _add(blocked, "approval action_class must be pr_creation")


def _check_run(run: dict[str, Any], approval: dict[str, Any], blocked: list[str]) -> None:
    if not run:
        _add(blocked, "valid RunRecord is required")
        return
    if _safe_text(run.get("status")) not in _ACTIVE_RUN_STATUSES:
        _add(blocked, "run status must be an active pre-execution/read-only state")
    if _safe_text(run.get("approval_id")) != _safe_text(approval.get("approval_id")):
        _add(blocked, "run approval_id must match the exact ApprovalRecord")
    if _flag_enabled(run.get("dispatch_state")):
        _add(blocked, "run dispatch_state must be false")


def _check_pr_run(run: dict[str, Any], approval: dict[str, Any], blocked: list[str]) -> None:
    if not run:
        _add(blocked, "valid RunRecord is required")
        return
    if _safe_text(run.get("status")) not in _ACTIVE_PR_STATUSES:
        _add(blocked, "run status must be an active pre-execution/PR state")
    if _safe_text(run.get("approval_id")) != _safe_text(approval.get("approval_id")):
        _add(blocked, "run approval_id must match the exact ApprovalRecord")
    if _safe_text(run.get("lane_type")) != "pr_creation":
        _add(blocked, "run lane_type must be pr_creation")
    if _flag_enabled(run.get("dispatch_state")):
        _add(blocked, "run dispatch_state must be false")


def _check_report_inbox(report: dict[str, Any], state: dict[str, Any], blocked: list[str]) -> None:
    inbox_ready = state.get("report_inbox_ready")
    if inbox_ready is None:
        inbox_ready = bool(report) or _safe_bool(state.get("report_record_ready"))
    if inbox_ready is not True:
        _add(blocked, "report inbox must be ready")


def _check_lane(run: dict[str, Any], lane: dict[str, Any], blocked: list[str]) -> None:
    lane_types = [
        _safe_text(item.get("lane_type") or item.get("mode"))
        for item in (run, lane)
        if item
    ]
    if not lane_types or any(
        lane_type not in _READ_ONLY_LANE_TYPES and not lane_type.startswith("read_only")
        for lane_type in lane_types
    ):
        _add(blocked, "lane type must be read-only")


def _check_forbidden_actions(run: dict[str, Any], lane: dict[str, Any], blocked: list[str]) -> None:
    forbidden = tuple(_safe_text(item).lower() for item in _as_list(run.get("forbidden_actions")) + _as_list(lane.get("forbidden_actions")))
    missing = [
        aliases[0]
        for aliases in _MUTATION_FORBIDDEN_CLASSES
        if not any(alias in item for item in forbidden for alias in aliases)
    ]
    if missing:
        _add(blocked, f"forbidden actions missing mutation classes: {', '.join(missing[:8])}")


def _check_pr_forbidden_actions(run: dict[str, Any], lane: dict[str, Any], blocked: list[str]) -> None:
    forbidden = tuple(_safe_text(item).lower() for item in _as_list(run.get("forbidden_actions")) + _as_list(lane.get("forbidden_actions")))
    missing = [
        aliases[0]
        for aliases in _PR_FORBIDDEN_CLASSES
        if not any(alias in item for item in forbidden for alias in aliases)
    ]
    if missing:
        _add(blocked, f"forbidden actions missing protected classes: {', '.join(missing[:8])}")


def _check_capabilities(capabilities: dict[str, Any], blocked: list[str]) -> None:
    for key in _CAPABILITY_KEYS:
        if _flag_enabled(capabilities.get(key)):
            _add(blocked, f"capability {key} must be disabled")


def _check_pr_capabilities(capabilities: dict[str, Any], blocked: list[str]) -> None:
    for key in _PR_BLOCKED_CAPABILITY_KEYS:
        if _flag_enabled(capabilities.get(key)):
            _add(blocked, f"capability {key} must be disabled")


def _check_preview_disabled_flags(
    blocked: list[str],
    *sections: dict[str, Any],
    keys: tuple[str, ...] | None = None,
) -> None:
    flag_keys = keys or tuple(_PREVIEW_DISABLED_FLAG_REASONS)
    for key in flag_keys:
        if any(_flag_enabled(section.get(key)) for section in sections if isinstance(section, dict)):
            _add(blocked, _PREVIEW_DISABLED_FLAG_REASONS[key])


def _check_pr_scope(approval: dict[str, Any], lane: dict[str, Any], blocked: list[str]) -> None:
    scope = _explicit_scope(approval, lane)
    if not scope["files"] and not scope["directories"]:
        _add(blocked, "explicit files or directories are required")
    if scope["has_wildcard"]:
        _add(blocked, "scoped PR lane cannot use wildcard paths")


def _runtime_summary(name: str, runtime: dict[str, Any]) -> dict[str, Any]:
    path = _safe_text(runtime.get("path") or runtime.get("runtime_path"))
    exists = runtime.get("exists")
    git_healthy = runtime.get("git_healthy")
    dirty_files = tuple(_safe_text(item) for item in _as_list(runtime.get("dirty_files")) if _safe_text(item))
    untracked_files = tuple(_safe_text(item) for item in _as_list(runtime.get("untracked_files")) if _safe_text(item))
    status_short = tuple(_safe_text(item) for item in _as_list(runtime.get("status_short")) if _safe_text(item))
    error = _safe_text(runtime.get("error"), max_chars=300)
    dirty = bool(dirty_files or untracked_files)
    broken = git_healthy is False or bool(error)
    missing_path = not path or exists is False
    return {
        "name": name,
        "path": path,
        "exists": exists if isinstance(exists, bool) else None,
        "git_healthy": git_healthy if isinstance(git_healthy, bool) else None,
        "head": _safe_text(runtime.get("head")),
        "status_short": list(status_short),
        "dirty_files": list(dirty_files),
        "untracked_files": list(untracked_files),
        "error": error,
        "dirty": dirty,
        "broken_git_metadata": broken,
        "missing_path": missing_path,
    }


def _bridge_result(classification: str, read_only_safe: bool, reasons: list[str]) -> dict[str, Any]:
    return {
        **INERT_PREVIEW_FLAGS,
        "permission_classification": classification,
        "legacy_permission_classification": "write_capable" if classification == "write_capable_not_safe_for_autonomy" else classification,
        "read_only_safe": read_only_safe,
        "reasons": reasons,
        "would_execute": False,
        "would_dispatch": False,
        "would_session_send": False,
        "execution_enabled": False,
        "dispatch_enabled": False,
        "timer_enabled": False,
        "daemon_enabled": False,
        "discord_automation_enabled": False,
        "model_routing_enabled": False,
        "session_send_enabled": False,
        "send_to_jenny_enabled": False,
        "worker_dispatch_enabled": False,
        "worker_enabled": False,
    }


def _is_expired(expires_at: str, *, now: str = "") -> bool:
    if not expires_at:
        return False
    parsed = _parse_datetime(expires_at)
    if parsed is None:
        return True
    current = _parse_datetime(now) if now else datetime.now(timezone.utc)
    return current is None or parsed <= current


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _looks_broad(value: str) -> bool:
    lowered = value.lower().strip()
    return lowered in _BROAD_APPROVAL_VALUES or any(term in lowered for term in ("approve all", "anything", "everything", "unlimited", "blanket approval"))


def _scope_is_missing_or_broad(value: str) -> bool:
    lowered = value.lower().strip()
    return not lowered or "*" in lowered or _looks_broad(lowered)


def _primary_status(statuses: list[str]) -> str:
    if not statuses:
        return PROVENANCE_BLOCKED
    if statuses == [PROVENANCE_CLEAN]:
        return PROVENANCE_CLEAN
    for status in _STATUS_PRIORITY:
        if status in statuses:
            return status
    return statuses[0]


def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _safe_text(value: Any, *, max_chars: int = 240) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\x00", "")
    return text[:max_chars]


def _safe_bool(value: Any) -> bool:
    return value is True


def _flag_enabled(value: Any) -> bool:
    """Fail closed on API-shaped truthy values for dangerous live-action flags."""

    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}
    return False


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _bounded_texts(values: list[Any], *, max_items: int = 40) -> list[str]:
    output: list[str] = []
    for item in values:
        text = _safe_text(item)
        if text and text not in output:
            output.append(text)
        if len(output) >= max_items:
            break
    return output


def _explicit_scope(approval: dict[str, Any], lane: dict[str, Any]) -> dict[str, Any]:
    files = _bounded_texts(
        _as_list(approval.get("approved_files"))
        + _as_list(approval.get("files"))
        + _as_list(lane.get("allowed_files"))
        + _as_list(lane.get("files"))
    )
    directories = _bounded_texts(
        _as_list(approval.get("approved_directories"))
        + _as_list(approval.get("directories"))
        + _as_list(lane.get("allowed_directories"))
        + _as_list(lane.get("directories"))
    )
    all_paths = files + directories
    return {
        "files": files,
        "directories": directories,
        "has_wildcard": any(path in {"*", ".", "/"} or path.endswith("/*") for path in all_paths),
        "explicit": bool(files or directories),
    }


def _add(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
