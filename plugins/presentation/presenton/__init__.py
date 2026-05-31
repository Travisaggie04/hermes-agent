"""Presenton adapter skeleton.

This plugin is intentionally standalone and opt-in. Hermes does not start,
stop, install, or supervise Presenton; future live calls must target a
user-configured, already-running service.
"""

from __future__ import annotations

from plugins.presentation.presenton.tools import (
    PRESENTON_EXPORT_SCHEMA,
    PRESENTON_GENERATE_SCHEMA,
    PRESENTON_STATUS_SCHEMA,
    check_presenton_available,
    presenton_export_deck,
    presenton_generate_deck,
    presenton_status,
)


_TOOLS = (
    ("presenton_status", PRESENTON_STATUS_SCHEMA, presenton_status, ""),
    ("presenton_generate_deck", PRESENTON_GENERATE_SCHEMA, presenton_generate_deck, ""),
    ("presenton_export_deck", PRESENTON_EXPORT_SCHEMA, presenton_export_deck, ""),
)


def register(ctx) -> None:
    """Register disabled Presenton stub tools when this opt-in plugin is enabled."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="presenton",
            schema=schema,
            handler=handler,
            check_fn=check_presenton_available,
            description=schema["description"],
            emoji=emoji,
        )
