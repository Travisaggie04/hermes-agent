from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load_json(result: str) -> dict:
    return json.loads(result)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/video.mp4",
        "ftp://example.com/video",
        "ssh://example.com/video",
        "data:text/plain,hello",
        "javascript:alert(1)",
    ],
)
def test_url_validation_rejects_unsafe_schemes(url: str):
    from plugins.media.yt_dlp.tools import validate_media_url

    with pytest.raises(ValueError):
        validate_media_url(url)


@pytest.mark.parametrize("url", ["/tmp/video.mp4", "./video.mp4", "video.mp4", "~/video.mp4"])
def test_url_validation_rejects_local_paths(url: str):
    from plugins.media.yt_dlp.tools import validate_media_url

    with pytest.raises(ValueError):
        validate_media_url(url)


def test_output_root_validation_prevents_path_traversal(tmp_path: Path):
    from plugins.media.yt_dlp.tools import resolve_caption_output_path

    with pytest.raises(ValueError):
        resolve_caption_output_path(tmp_path, "../escape", "en", "vtt")


def test_safe_metadata_argv_is_metadata_only_and_no_playlist():
    from plugins.media.yt_dlp.tools import build_metadata_argv

    argv = build_metadata_argv("https://example.com/watch?v=abc123", timeout_seconds=99)

    assert argv[:2] == ["yt-dlp", "https://example.com/watch?v=abc123"]
    assert "--dump-json" in argv
    assert "--skip-download" in argv
    assert "--no-playlist" in argv
    assert "--socket-timeout" in argv
    assert "30" in argv
    assert not any("cookie" in item.lower() for item in argv)
    assert not any(item in {"--username", "--password", "--netrc"} for item in argv)
    assert not any(item.startswith("-o") or item == "--output" for item in argv)


def test_caption_argv_is_fixed_and_has_no_cookie_or_login_flags(tmp_path: Path):
    from plugins.media.yt_dlp.tools import build_caption_argv

    argv = build_caption_argv(
        "https://example.com/watch?v=abc123",
        output_root=tmp_path,
        filename="safe title",
        languages=["en", "es"],
        formats=["vtt"],
    )

    assert "--skip-download" in argv
    assert "--no-playlist" in argv
    assert "--write-subs" in argv
    assert "--write-auto-subs" not in argv
    assert "--sub-langs" in argv
    assert "en,es" in argv
    assert "--sub-format" in argv
    assert "vtt" in argv
    assert "--paths" in argv
    assert not any("cookie" in item.lower() for item in argv)
    assert not any(item in {"--username", "--password", "--netrc"} for item in argv)


def test_status_without_runtime_is_disabled_and_does_not_execute(monkeypatch):
    from plugins.media.yt_dlp import tools

    monkeypatch.delenv("HERMES_YT_DLP_PATH", raising=False)

    def fail_execute(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr(tools, "_run_yt_dlp", fail_execute)

    result = _load_json(tools.yt_dlp_status())

    assert result["ok"] is False
    assert result["configured"] is False
    assert result["code"] == "yt_dlp_not_configured"


def test_extract_metadata_without_runtime_does_not_execute(monkeypatch):
    from plugins.media.yt_dlp import tools

    monkeypatch.delenv("HERMES_YT_DLP_PATH", raising=False)

    def fail_execute(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr(tools, "_run_yt_dlp", fail_execute)

    result = _load_json(tools.yt_dlp_extract_metadata("https://example.com/watch?v=abc123"))

    assert result["ok"] is False
    assert result["code"] == "yt_dlp_not_configured"


def test_media_download_mode_is_rejected():
    from plugins.media.yt_dlp.tools import build_media_download_argv

    with pytest.raises(NotImplementedError):
        build_media_download_argv("https://example.com/watch?v=abc123", approve_media_download=False)


def test_register_wires_disabled_stub_tools_only():
    import plugins.media.yt_dlp as plugin

    calls = []

    class _Ctx:
        def register_tool(self, **kw):
            calls.append(kw)

    plugin.register(_Ctx())

    assert [call["name"] for call in calls] == [
        "yt_dlp_status",
        "yt_dlp_extract_metadata",
        "yt_dlp_list_captions",
        "yt_dlp_fetch_captions",
    ]
    assert {call["toolset"] for call in calls} == {"yt_dlp"}
    assert all(call["check_fn"]() is False for call in calls)


def test_plugin_contains_no_install_docker_service_or_shell_passthrough_commands():
    plugin_root = Path("plugins/media/yt_dlp")
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in plugin_root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yaml"}
    ).lower()

    forbidden = [
        "pip install",
        "npm install",
        "apt-get",
        "docker",
        "compose",
        "systemctl",
        "service start",
        "shell=true",
        "serve --mcp",
        "--cookies",
        "--cookies-from-browser",
    ]
    assert not any(term in combined for term in forbidden)
