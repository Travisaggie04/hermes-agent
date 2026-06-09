"""Display-only Mission Control operating workspace status builder.

This module is intentionally pure and inert. It normalizes caller-supplied
status snippets into a bounded display payload and computes warnings. It does
not read files, query GitHub, inspect services, mutate queues, write records,
or enable enforcement.
"""

from __future__ import annotations

import re
from typing import Any

MAX_TEXT_CHARS = 160
MAX_WARNINGS = 20
_PACKET_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PR_LANE_RE = re.compile(r"\b(pr|pull request|merge|verify|deploy)\b", re.IGNORECASE)

INERT_WORKSPACE_FLAGS: dict[str, bool] = {
    "display_only": True,
    "trusted_for_execution": False,
    "inert_context_only": True,
    "execution_enabled": False,
    "enforcement_enabled": False,
    "dry_run_only": True,
    "enforces_runtime": False,
}

_FORBIDDEN_KEYS = {
    "raw_log",
    "raw_logs",
    "transcript",
    "transcripts",
    "discord_messages",
    "discord_history",
    "comments",
    "pr_body",
    "local_path",
    "path",
    "token",
    "api_key",
    "secret",
    "github_response",
    "api_response",
    "service_status",
    "full_observed_state",
    "canonical_packet_json",
}

_DEFAULT_STATUS: dict[str, Any] = {
    "accepted_baseline": {
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-approvalhash-775f493",
        "head": "775f49352189fdec3169f59e3378b6744da2bdda",
        "status": "accepted",
    },
    "rollback_baseline": {
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-evidencehash-cb42bbc",
        "head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
        "clean": True,
    },
    "lane": {
        "active_lane": "Mission Control Operating Workspace",
        "mode": "display-only status",
        "declared_baseline_head": "775f49352189fdec3169f59e3378b6744da2bdda",
        "max_active_lane": 1,
        "active_lane_count": 1,
    },
    "safety": {
        "dispatch_in_gateway": False,
        "workers_enabled": False,
        "queue_mutation_enabled": False,
        "model_routing_enabled": False,
        "enforcement_enabled": False,
    },
    "activity": {
        "active_workers": 0,
        "active_tasks": 0,
        "active_runs": 0,
        "appserver_pairs": None,
    },
    "pr_gate": {
        "latest_pr": "",
        "packet_hash": "",
        "verifier_evidence_record_id": "",
        "verifier_evidence_match": None,
        "approval_record_id": "",
        "approval_record_match": None,
        "guard_enabled": False,
        "guard_advisory_only": True,
    },
    "deployment": {
        "status": "accepted",
        "target_runtime": "/home/jenny/.hermes/hermes-runtime-approvalhash-775f493",
        "target_head": "775f49352189fdec3169f59e3378b6744da2bdda",
        "rollback_used": False,
        "blocking_errors": (),
    },
}


def default_workspace_status_input() -> dict[str, Any]:
    """Return a bounded static display snapshot for the current accepted slice."""
    return _merge_dicts({}, _DEFAULT_STATUS)


def build_workspace_status(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a display-only operating workspace status payload.

    Caller input is allowlisted by section. Unknown top-level data, raw logs,
    transcripts, API responses, token-like fields, and local paths are ignored.
    """
    source = payload if isinstance(payload, dict) else {}
    latest_handoff = _latest_handoff_section(_section(source, "latest_handoff"))
    accepted_record = _accepted_baseline_record_section(_section(source, "accepted_baseline_record"))
    accepted_source = "static_fallback"
    if accepted_record.get("present") is True:
        accepted_source = "record"
        accepted_defaults = {
            "runtime_path": accepted_record.get("runtime_path", ""),
            "head": accepted_record.get("head", ""),
            "status": "accepted" if not accepted_record.get("issue") or accepted_record.get("issue") == "none" else accepted_record.get("issue", "accepted"),
        }
        rollback_defaults = {
            "runtime_path": accepted_record.get("rollback_runtime_path", ""),
            "head": accepted_record.get("rollback_head", ""),
            "clean": True,
        }
    elif _handoff_has_baseline(latest_handoff):
        accepted_source = "handoff"
        accepted_defaults = {
            "runtime_path": latest_handoff.get("accepted_runtime_path", ""),
            "head": latest_handoff.get("accepted_head", ""),
            "status": "accepted",
        }
        rollback_defaults = {
            "runtime_path": latest_handoff.get("rollback_runtime_path", ""),
            "head": latest_handoff.get("rollback_head", ""),
            "clean": True,
        }
    else:
        accepted_defaults = _DEFAULT_STATUS["accepted_baseline"]
        rollback_defaults = _DEFAULT_STATUS["rollback_baseline"]
    baseline_override = _section(source, "accepted_baseline") if accepted_source == "static_fallback" else {}
    rollback_override = _section(source, "rollback_baseline") if accepted_source == "static_fallback" else {}
    accepted = _baseline_section(baseline_override, defaults=accepted_defaults)
    rollback = _rollback_section(rollback_override, defaults=rollback_defaults)
    lane_input = _section(source, "lane")
    lane_defaults = _DEFAULT_STATUS["lane"]
    if accepted_record.get("present") is True:
        lane_defaults = {
            "active_lane": "",
            "mode": "",
            "declared_baseline_head": accepted_record.get("head", ""),
            "max_active_lane": accepted_record.get("max_active_lane", 1),
            "active_lane_count": 0,
        }
        lane_input = _record_authoritative_lane_input(lane_input)
    lane = _lane_section(lane_input, defaults=lane_defaults)
    safety = _safety_section(_section(source, "safety"), defaults=_DEFAULT_STATUS["safety"])
    activity = _activity_section(_section(source, "activity"), defaults=_DEFAULT_STATUS["activity"])
    if accepted_record.get("present") is True:
        safety = {**safety, "dispatch_in_gateway": accepted_record.get("dispatch_in_gateway")}
        activity = {**activity, "active_workers": 0, "active_tasks": 0, "active_runs": accepted_record.get("active_kanban", 0)}
        lane = {**lane, "max_active_lane": accepted_record.get("max_active_lane", lane.get("max_active_lane", 1))}
    pr_gate = _pr_gate_section(_section(source, "pr_gate"), defaults=_DEFAULT_STATUS["pr_gate"])
    deployment = _deployment_section(_section(source, "deployment"), defaults=_DEFAULT_STATUS["deployment"])

    warnings: list[str] = []
    if accepted_source == "static_fallback":
        warnings.append("accepted_baseline_source_missing")
    accepted_head = accepted.get("head") or ""
    declared_head = lane.get("declared_baseline_head") or ""
    if not declared_head:
        warnings.append("missing_lane_baseline")
    elif accepted_head and declared_head != accepted_head:
        warnings.append("baseline_mismatch")
    if safety.get("dispatch_in_gateway") is not False:
        warnings.append("dispatch_not_false")
    if lane["active_lane_count"] > lane["max_active_lane"]:
        warnings.append("active_lane_count_exceeds_max")
    if activity["active_workers"] > 0 or activity["active_tasks"] > 0 or activity["active_runs"] > 0:
        warnings.append("active_workers_tasks_or_runs_present")
    active_lane = str(lane.get("active_lane") or "")
    if _PR_LANE_RE.search(active_lane):
        if not pr_gate.get("packet_hash"):
            warnings.append("missing_pr_packet_hash")
        if not pr_gate.get("verifier_evidence_record_id"):
            warnings.append("missing_verifier_evidence")
        if not pr_gate.get("approval_record_id"):
            warnings.append("missing_approval_record")
    if latest_handoff.get("present") is True:
        handoff_head = latest_handoff.get("accepted_head") or ""
        if handoff_head and accepted_head and handoff_head != accepted_head:
            warnings.append("handoff_baseline_mismatch")
        if latest_handoff.get("accepted_runtime_path") and accepted.get("runtime_path") and latest_handoff.get("accepted_runtime_path") != accepted.get("runtime_path"):
            warnings.append("handoff_baseline_mismatch")
        if latest_handoff.get("rollback_head") and rollback.get("head") and latest_handoff.get("rollback_head") != rollback.get("head"):
            warnings.append("handoff_rollback_baseline_mismatch")
        if latest_handoff.get("rollback_runtime_path") and rollback.get("runtime_path") and latest_handoff.get("rollback_runtime_path") != rollback.get("runtime_path"):
            warnings.append("handoff_rollback_baseline_mismatch")
        if latest_handoff.get("dispatch_in_gateway") is not False:
            warnings.append("handoff_dispatch_not_false")
        if latest_handoff.get("active_lane_count", 0) > latest_handoff.get("max_active_lane", 1):
            warnings.append("handoff_active_lane_count_exceeds_max")
        if latest_handoff.get("target_type") and latest_handoff.get("target_id") and not latest_handoff.get("target_head"):
            warnings.append("handoff_missing_target_head")
    if source.get("stale_discord_context") is True:
        warnings.append("stale_discord_context")

    warnings = _dedupe_bounded(warnings)
    return {
        "workspace_id": "mission_control_operating_workspace_v1",
        **INERT_WORKSPACE_FLAGS,
        "source": "caller_supplied_or_static_display_status",
        "stored": False,
        "accepted_baseline_source": accepted_source,
        "accepted_baseline_record": accepted_record,
        "accepted_baseline": accepted,
        "rollback_baseline": rollback,
        "lane": lane,
        "safety": safety,
        "activity": activity,
        "pr_gate": pr_gate,
        "deployment": deployment,
        "latest_handoff": latest_handoff,
        "stale_context": {
            "baseline_mismatch": "baseline_mismatch" in warnings,
            "thread_mismatch": "stale_discord_context" in warnings,
            "warnings": warnings,
        },
    }




def _accepted_baseline_record_section(section: dict[str, Any]) -> dict[str, Any]:
    if not section:
        return {"present": False}
    return {
        "present": True,
        "baseline_id": _safe_text(section.get("baseline_id")),
        "recorded_at": _safe_text(section.get("recorded_at")),
        "source": _safe_text(section.get("source")),
        "runtime_path": _safe_text(section.get("runtime_path"), max_chars=240),
        "head": _safe_sha(section.get("head")),
        "rollback_runtime_path": _safe_text(section.get("rollback_runtime_path"), max_chars=240),
        "rollback_head": _safe_sha(section.get("rollback_head")),
        "dispatch_in_gateway": _safe_bool(section.get("dispatch_in_gateway"), default=False),
        "active_kanban": _safe_int(section.get("active_kanban"), default=0),
        "max_active_lane": _safe_int(section.get("max_active_lane"), default=1) or 1,
        "issue": _safe_text(section.get("issue")),
        "display_only": True,
        "dry_run_only": True,
        "enforces_runtime": False,
    }


def _record_authoritative_lane_input(section: dict[str, Any]) -> dict[str, Any]:
    """Drop stale static lane defaults when a baseline record is authoritative."""
    if not section:
        return {}
    lane = dict(section)
    default_lane = _DEFAULT_STATUS["lane"]
    active_lane = _safe_text(lane.get("active_lane"))
    has_caller_lane = bool(active_lane) and active_lane != default_lane["active_lane"]
    for key in ("active_lane", "mode", "active_lane_count"):
        if not has_caller_lane and lane.get(key) == default_lane.get(key):
            lane.pop(key, None)
    if lane.get("declared_baseline_head") == default_lane.get("declared_baseline_head"):
        lane.pop("declared_baseline_head", None)
    if lane.get("max_active_lane") == default_lane.get("max_active_lane"):
        lane.pop("max_active_lane", None)
    return lane


def _handoff_has_baseline(handoff: dict[str, Any]) -> bool:
    return (
        handoff.get("present") is True
        and bool(handoff.get("accepted_runtime_path"))
        and bool(handoff.get("accepted_head"))
        and bool(handoff.get("rollback_runtime_path"))
        and bool(handoff.get("rollback_head"))
    )

def _latest_handoff_section(section: dict[str, Any]) -> dict[str, Any]:
    if not section:
        return {"present": False}
    max_lane = _safe_int(section.get("max_active_lane"), default=1) or 1
    active_count = _safe_int(section.get("active_lane_count"), default=0)
    return {
        "present": True,
        "handoff_id": _safe_text(section.get("handoff_id")),
        "created_at": _safe_text(section.get("created_at")),
        "source": _safe_text(section.get("source")),
        "active_lane": _safe_text(section.get("active_lane")),
        "lane_mode": _safe_text(section.get("lane_mode")),
        "accepted_runtime_path": _safe_text(section.get("accepted_runtime_path"), max_chars=240),
        "accepted_head": _safe_sha(section.get("accepted_head")),
        "rollback_runtime_path": _safe_text(section.get("rollback_runtime_path"), max_chars=240),
        "rollback_head": _safe_sha(section.get("rollback_head")),
        "dispatch_in_gateway": _safe_bool(section.get("dispatch_in_gateway"), default=False),
        "max_active_lane": max_lane,
        "active_lane_count": active_count,
        "target_type": _safe_text(section.get("target_type")),
        "target_id": _safe_text(section.get("target_id")),
        "target_head": _safe_sha(section.get("target_head")),
        "status": _safe_text(section.get("status")),
        "last_result": _safe_text(section.get("last_result")),
        "next_action": _safe_text(section.get("next_action")),
        "warnings": _dedupe_bounded(section.get("warnings") if isinstance(section.get("warnings"), list | tuple) else ()),
        "dry_run_only": True,
        "enforces_runtime": False,
        "display_only": True,
    }

def _section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _merge_dicts(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict):
            merged[key] = _merge_dicts(merged.get(key, {}) if isinstance(merged.get(key), dict) else {}, value)
        else:
            merged[key] = value
    return merged


def _safe_text(value: Any, *, max_chars: int = MAX_TEXT_CHARS) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\x00", "")
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(number, 999))


def _safe_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return _safe_int(value)


def _safe_sha(value: Any) -> str:
    text = _safe_text(value, max_chars=64).lower()
    return text if _SHA_RE.fullmatch(text) else ""


def _safe_packet_hash(value: Any) -> str:
    text = _safe_text(value, max_chars=80).lower()
    return text if _PACKET_HASH_RE.fullmatch(text) else ""


def _baseline_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    return {
        "runtime_path": _safe_text(merged.get("runtime_path"), max_chars=240),
        "head": _safe_sha(merged.get("head")),
        "status": _safe_text(merged.get("status") or "accepted"),
    }


def _rollback_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    return {
        "runtime_path": _safe_text(merged.get("runtime_path"), max_chars=240),
        "head": _safe_sha(merged.get("head")),
        "clean": _safe_bool(merged.get("clean"), default=False),
    }


def _lane_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    max_lane = _safe_int(merged.get("max_active_lane"), default=1) or 1
    active_count = _safe_int(merged.get("active_lane_count"), default=0)
    return {
        "active_lane": _safe_text(merged.get("active_lane")),
        "mode": _safe_text(merged.get("mode")),
        "declared_baseline_head": _safe_sha(merged.get("declared_baseline_head")),
        "max_active_lane": max_lane,
        "active_lane_count": active_count,
        "lane_status": "within_limit" if active_count <= max_lane else "exceeds_limit",
    }


def _safety_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    return {
        "dispatch_in_gateway": _safe_bool(merged.get("dispatch_in_gateway"), default=False),
        "workers_enabled": _safe_bool(merged.get("workers_enabled"), default=False),
        "queue_mutation_enabled": _safe_bool(merged.get("queue_mutation_enabled"), default=False),
        "model_routing_enabled": _safe_bool(merged.get("model_routing_enabled"), default=False),
        "enforcement_enabled": False,
    }


def _activity_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    return {
        "active_workers": _safe_int(merged.get("active_workers")),
        "active_tasks": _safe_int(merged.get("active_tasks")),
        "active_runs": _safe_int(merged.get("active_runs")),
        "appserver_pairs": _safe_optional_int(merged.get("appserver_pairs")),
    }


def _pr_gate_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    packet_hash = _safe_packet_hash(merged.get("packet_hash"))
    return {
        "latest_pr": _safe_text(merged.get("latest_pr"), max_chars=20),
        "packet_hash": packet_hash,
        "packet_hash_valid": bool(packet_hash) if merged.get("packet_hash") else None,
        "verifier_evidence_record_id": _safe_text(merged.get("verifier_evidence_record_id")),
        "verifier_evidence_match": _safe_optional_bool(merged.get("verifier_evidence_match")),
        "approval_record_id": _safe_text(merged.get("approval_record_id")),
        "approval_record_match": _safe_optional_bool(merged.get("approval_record_match")),
        "guard_enabled": False,
        "guard_advisory_only": True,
    }


def _safe_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _deployment_section(section: dict[str, Any], *, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = _merge_dicts(defaults, section)
    errors = merged.get("blocking_errors")
    return {
        "status": _safe_text(merged.get("status")),
        "target_runtime": _safe_text(merged.get("target_runtime"), max_chars=240),
        "target_head": _safe_sha(merged.get("target_head")),
        "rollback_used": _safe_bool(merged.get("rollback_used"), default=False),
        "blocking_errors": _dedupe_bounded(errors if isinstance(errors, list | tuple) else ()),
    }


def _dedupe_bounded(values: Any) -> list[str]:
    output: list[str] = []
    for value in values or ():
        text = _safe_text(value)
        if text and text not in output:
            output.append(text)
        if len(output) >= MAX_WARNINGS:
            break
    return output
