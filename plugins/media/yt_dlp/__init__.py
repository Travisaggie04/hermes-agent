"""yt-dlp adapter skeleton.

This plugin is standalone and opt-in. The initial scope is validation-only
metadata and caption handling; media downloads require a future explicit gate.
"""

from __future__ import annotations

from plugins.media.yt_dlp.tools import (
    YT_DLP_FETCH_CAPTIONS_SCHEMA,
    YT_DLP_LIST_CAPTIONS_SCHEMA,
    YT_DLP_METADATA_SCHEMA,
    YT_DLP_STATUS_SCHEMA,
    check_yt_dlp_available,
    yt_dlp_extract_metadata,
    yt_dlp_fetch_captions,
    yt_dlp_list_captions,
    yt_dlp_status,
)


_TOOLS = (
    ("yt_dlp_status", YT_DLP_STATUS_SCHEMA, yt_dlp_status, ""),
    ("yt_dlp_extract_metadata", YT_DLP_METADATA_SCHEMA, yt_dlp_extract_metadata, ""),
    ("yt_dlp_list_captions", YT_DLP_LIST_CAPTIONS_SCHEMA, yt_dlp_list_captions, ""),
    ("yt_dlp_fetch_captions", YT_DLP_FETCH_CAPTIONS_SCHEMA, yt_dlp_fetch_captions, ""),
)


def register(ctx) -> None:
    """Register disabled yt-dlp stub tools when this opt-in plugin is enabled."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="yt_dlp",
            schema=schema,
            handler=handler,
            check_fn=check_yt_dlp_available,
            description=schema["description"],
            emoji=emoji,
        )
