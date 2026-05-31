"""Safe yt-dlp adapter skeleton tools.

The skeleton only validates requests and constructs fixed future argv values.
It does not install yt-dlp, call live URLs, read browser credentials, write
artifacts, or retrieve media.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tools.registry import tool_error, tool_result


DEFAULT_TIMEOUT_SECONDS = 30
MAX_STDIO_CAPTURE_BYTES = 2 * 1024 * 1024
MAX_METADATA_JSON_BYTES = 5 * 1024 * 1024
MAX_CAPTION_FILE_BYTES = 2 * 1024 * 1024
MAX_FILENAME_CHARS = 120
ALLOWED_URL_SCHEMES = {"http", "https"}
ALLOWED_CAPTION_FORMATS = {"srt", "vtt", "ttml", "json3"}
DEFAULT_CAPTION_FORMATS = ("vtt",)
DEFAULT_CAPTION_LANGUAGES = ("en",)
FORBIDDEN_YT_DLP_FLAGS = {
    "--username",
    "--password",
    "--netrc",
    "--netrc-location",
    "--video-password",
}


YT_DLP_STATUS_SCHEMA = {
    "description": "Check yt-dlp adapter configuration without installing or executing yt-dlp.",
    "input_schema": {
        "type": "object",
        "properties": {
            "runtime_path": {"type": "string", "description": "Explicit yt-dlp executable path/name."},
        },
    },
}

YT_DLP_METADATA_SCHEMA = {
    "description": "Validate a future metadata-only yt-dlp extraction request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "runtime_path": {"type": "string"},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": DEFAULT_TIMEOUT_SECONDS},
            "domain_allowlist": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["url"],
    },
}

YT_DLP_LIST_CAPTIONS_SCHEMA = {
    "description": "Validate a future caption/subtitle listing request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "runtime_path": {"type": "string"},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": DEFAULT_TIMEOUT_SECONDS},
            "domain_allowlist": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["url"],
    },
}

YT_DLP_FETCH_CAPTIONS_SCHEMA = {
    "description": "Validate a future controlled caption retrieval request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "output_root": {"type": "string"},
            "filename": {"type": "string"},
            "languages": {"type": "array", "items": {"type": "string"}},
            "formats": {"type": "array", "items": {"type": "string", "enum": sorted(ALLOWED_CAPTION_FORMATS)}},
            "runtime_path": {"type": "string"},
            "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": DEFAULT_TIMEOUT_SECONDS},
            "domain_allowlist": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["url", "output_root", "filename"],
    },
}


def _json_error(code: str, message: str, **extra: Any) -> str:
    return tool_error(message, ok=False, code=code, **extra)


def _configured_runtime_path(explicit_runtime_path: str | None = None) -> str | None:
    return explicit_runtime_path or os.environ.get("HERMES_YT_DLP_PATH")


def check_yt_dlp_available() -> bool:
    """Keep skeleton tools unavailable until a live implementation is approved."""
    return False


def validate_media_url(url: str, domain_allowlist: list[str] | tuple[str, ...] | None = None) -> str:
    raw = str(url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise ValueError("url must be an http(s) URL with a host")
    if parsed.username or parsed.password:
        raise ValueError("url must not contain credentials")
    if domain_allowlist:
        allowed = {domain.lower().strip() for domain in domain_allowlist if domain.strip()}
        hostname = (parsed.hostname or "").lower()
        if hostname not in allowed:
            raise ValueError("url host is not in the configured domain allowlist")
    return raw


def _validate_timeout(timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> int:
    if not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")
    return min(timeout_seconds, DEFAULT_TIMEOUT_SECONDS)


def _validate_runtime_path(runtime_path: str) -> str:
    value = str(runtime_path or "").strip()
    if not value:
        raise ValueError("runtime_path is required for future live execution")
    if any(ch in value for ch in "\n\r\x00"):
        raise ValueError("runtime_path contains unsafe characters")
    return value


def sanitize_filename(filename: str) -> str:
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("filename must not contain path separators")
    stem = Path(filename).stem or filename
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")
    if not safe:
        raise ValueError("filename must contain at least one safe character")
    return safe[:MAX_FILENAME_CHARS]


def _normalize_caption_languages(languages: list[str] | tuple[str, ...] | None = None) -> list[str]:
    raw_languages = languages or DEFAULT_CAPTION_LANGUAGES
    normalized: list[str] = []
    for language in raw_languages:
        value = str(language).strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,12}", value):
            raise ValueError("caption language must be a short language tag")
        normalized.append(value)
    return normalized


def _normalize_caption_formats(formats: list[str] | tuple[str, ...] | None = None) -> list[str]:
    raw_formats = formats or DEFAULT_CAPTION_FORMATS
    normalized = [str(item).strip().lower().lstrip(".") for item in raw_formats]
    if not normalized or any(item not in ALLOWED_CAPTION_FORMATS for item in normalized):
        raise ValueError("unsupported caption format")
    return normalized


def resolve_caption_output_path(
    output_root: str | Path,
    filename: str,
    language: str,
    caption_format: str,
) -> Path:
    language_value = _normalize_caption_languages([language])[0]
    format_value = _normalize_caption_formats([caption_format])[0]
    root = Path(output_root).expanduser().resolve()
    target = (root / f"{sanitize_filename(filename)}.{language_value}.{format_value}").resolve()
    if root != target and root not in target.parents:
        raise ValueError("output path must stay inside output_root")
    return target


def _base_argv(url: str, *, timeout_seconds: int, domain_allowlist: list[str] | None = None) -> list[str]:
    safe_url = validate_media_url(url, domain_allowlist)
    timeout = _validate_timeout(timeout_seconds)
    return [
        "yt-dlp",
        safe_url,
        "--no-playlist",
        "--skip-download",
        "--socket-timeout",
        str(timeout),
    ]


def _assert_no_forbidden_flags(argv: list[str]) -> None:
    lower_argv = {item.lower() for item in argv}
    if lower_argv & FORBIDDEN_YT_DLP_FLAGS:
        raise ValueError("credential and login flags are not allowed")
    if any("cookie" in item.lower() for item in argv):
        raise ValueError("cookie flags are not allowed")


def build_metadata_argv(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> list[str]:
    argv = _base_argv(url, timeout_seconds=timeout_seconds, domain_allowlist=domain_allowlist)
    argv.extend(["--dump-json"])
    _assert_no_forbidden_flags(argv)
    return argv


def build_list_captions_argv(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> list[str]:
    argv = _base_argv(url, timeout_seconds=timeout_seconds, domain_allowlist=domain_allowlist)
    argv.extend(["--list-subs"])
    _assert_no_forbidden_flags(argv)
    return argv


def build_caption_argv(
    url: str,
    *,
    output_root: str | Path,
    filename: str,
    languages: list[str] | tuple[str, ...] | None = None,
    formats: list[str] | tuple[str, ...] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> list[str]:
    safe_languages = _normalize_caption_languages(languages)
    safe_formats = _normalize_caption_formats(formats)
    resolve_caption_output_path(output_root, filename, safe_languages[0], safe_formats[0])
    argv = _base_argv(url, timeout_seconds=timeout_seconds, domain_allowlist=domain_allowlist)
    argv.extend(
        [
            "--write-subs",
            "--sub-langs",
            ",".join(safe_languages),
            "--sub-format",
            ",".join(safe_formats),
            "--paths",
            str(Path(output_root).expanduser().resolve()),
            "--output",
            f"{sanitize_filename(filename)}.%(ext)s",
        ]
    )
    _assert_no_forbidden_flags(argv)
    return argv


def build_media_download_argv(url: str, *, approve_media_download: bool = False) -> list[str]:
    raise NotImplementedError("Audio/video downloads are not implemented in this metadata/captions skeleton")


def _run_yt_dlp(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError("Live yt-dlp execution is not implemented in this skeleton")


def yt_dlp_status(runtime_path: str | None = None) -> str:
    configured_runtime = _configured_runtime_path(runtime_path)
    if not configured_runtime:
        return tool_result(
            ok=False,
            configured=False,
            code="yt_dlp_not_configured",
            message="yt-dlp is disabled/not configured; provide runtime_path for future live execution.",
        )
    try:
        safe_runtime = _validate_runtime_path(configured_runtime)
    except ValueError as exc:
        return _json_error("invalid_config", str(exc))
    return tool_result(
        ok=False,
        configured=True,
        code="yt_dlp_skeleton_only",
        runtime_path=safe_runtime,
        message="yt-dlp adapter skeleton is registered, but live execution is not implemented.",
    )


def yt_dlp_extract_metadata(
    url: str,
    runtime_path: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> str:
    configured_runtime = _configured_runtime_path(runtime_path)
    if not configured_runtime:
        return _json_error(
            "yt_dlp_not_configured",
            "yt-dlp is disabled/not configured; provide runtime_path for future live execution.",
        )
    try:
        safe_runtime = _validate_runtime_path(configured_runtime)
        argv = build_metadata_argv(url, timeout_seconds=timeout_seconds, domain_allowlist=domain_allowlist)
        argv[0] = safe_runtime
    except ValueError as exc:
        return _json_error("invalid_request", str(exc))
    return tool_result(
        ok=False,
        configured=True,
        code="yt_dlp_skeleton_only",
        argv=argv,
        max_stdout_bytes=MAX_STDIO_CAPTURE_BYTES,
        max_stderr_bytes=MAX_STDIO_CAPTURE_BYTES,
        max_metadata_json_bytes=MAX_METADATA_JSON_BYTES,
        message="Metadata extraction is validation-only in this skeleton; yt-dlp was not executed.",
    )


def yt_dlp_list_captions(
    url: str,
    runtime_path: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> str:
    configured_runtime = _configured_runtime_path(runtime_path)
    if not configured_runtime:
        return _json_error(
            "yt_dlp_not_configured",
            "yt-dlp is disabled/not configured; provide runtime_path for future live execution.",
        )
    try:
        safe_runtime = _validate_runtime_path(configured_runtime)
        argv = build_list_captions_argv(url, timeout_seconds=timeout_seconds, domain_allowlist=domain_allowlist)
        argv[0] = safe_runtime
    except ValueError as exc:
        return _json_error("invalid_request", str(exc))
    return tool_result(
        ok=False,
        configured=True,
        code="yt_dlp_skeleton_only",
        argv=argv,
        max_stdout_bytes=MAX_STDIO_CAPTURE_BYTES,
        max_stderr_bytes=MAX_STDIO_CAPTURE_BYTES,
        message="Caption listing is validation-only in this skeleton; yt-dlp was not executed.",
    )


def yt_dlp_fetch_captions(
    url: str,
    output_root: str,
    filename: str,
    languages: list[str] | None = None,
    formats: list[str] | None = None,
    runtime_path: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    domain_allowlist: list[str] | None = None,
) -> str:
    configured_runtime = _configured_runtime_path(runtime_path)
    if not configured_runtime:
        return _json_error(
            "yt_dlp_not_configured",
            "yt-dlp is disabled/not configured; provide runtime_path for future live execution.",
        )
    try:
        safe_runtime = _validate_runtime_path(configured_runtime)
        argv = build_caption_argv(
            url,
            output_root=output_root,
            filename=filename,
            languages=languages,
            formats=formats,
            timeout_seconds=timeout_seconds,
            domain_allowlist=domain_allowlist,
        )
        argv[0] = safe_runtime
    except ValueError as exc:
        return _json_error("invalid_request", str(exc))
    return tool_result(
        ok=False,
        configured=True,
        code="yt_dlp_skeleton_only",
        argv=argv,
        max_caption_file_bytes=MAX_CAPTION_FILE_BYTES,
        message="Caption retrieval is validation-only in this skeleton; no file was written and yt-dlp was not executed.",
    )
