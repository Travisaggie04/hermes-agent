"""Shared fail-closed flags for inert Mission Control policy surfaces."""

from __future__ import annotations

from typing import Any


INERT_LIVE_OPERATION_FLAGS: dict[str, Any] = {
    "trusted_for_execution": False,
    "inert_context_only": True,
    "would_execute": False,
    "would_dispatch": False,
    "would_session_send": False,
    "execution_enabled": False,
    "execution_ready": False,
    "live_operations_enabled": False,
    "dispatch_enabled": False,
    "dispatch_in_gateway": False,
    "dispatch_state": False,
    "session_send_enabled": False,
    "send_to_jenny_enabled": False,
    "worker_dispatch_enabled": False,
    "worker_enabled": False,
    "workers_enabled": False,
    "timer_enabled": False,
    "daemon_enabled": False,
    "waha_enabled": False,
    "social_enabled": False,
    "payment_enabled": False,
    "queue_mutation_enabled": False,
    "model_routing_enabled": False,
}


def inert_live_operation_flags(**extra: Any) -> dict[str, Any]:
    """Return a copy of the common inert hard-boundary flag contract."""

    return {**INERT_LIVE_OPERATION_FLAGS, **extra}
