from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load_json(result: str) -> dict:
    return json.loads(result)


def test_status_without_base_url_is_disabled_and_does_not_call_network(monkeypatch):
    from plugins.presentation.presenton import tools

    monkeypatch.delenv("PRESENTON_BASE_URL", raising=False)

    def fail_network(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("network should not be called")

    monkeypatch.setattr(tools, "_http_request", fail_network)

    result = _load_json(tools.presenton_status())

    assert result["ok"] is False
    assert result["configured"] is False
    assert result["code"] == "presenton_not_configured"


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://localhost:5000",
        "file:///tmp/presenton",
        "localhost:5000",
        "https://user:pass@example.com",
    ],
)
def test_base_url_validation_rejects_unsafe_urls(base_url):
    from plugins.presentation.presenton.tools import validate_base_url

    with pytest.raises(ValueError):
        validate_base_url(base_url)


def test_generate_deck_validates_slide_count_and_request_size():
    from plugins.presentation.presenton import tools

    too_many_slides = [{"title": f"Slide {i}", "body": "x"} for i in range(tools.MAX_SLIDES + 1)]
    too_large_markdown = "x" * (tools.MAX_REQUEST_CHARS + 1)

    slide_result = _load_json(
        tools.presenton_generate_deck(base_url="http://localhost:5000", outline=too_many_slides)
    )
    markdown_result = _load_json(
        tools.presenton_generate_deck(base_url="http://localhost:5000", outline=too_large_markdown)
    )

    assert slide_result["ok"] is False
    assert slide_result["code"] == "too_many_slides"
    assert markdown_result["ok"] is False
    assert markdown_result["code"] == "request_too_large"


def test_export_path_validation_prevents_path_traversal(tmp_path: Path):
    from plugins.presentation.presenton.tools import resolve_output_path

    with pytest.raises(ValueError):
        resolve_output_path(tmp_path, "../escape", "pptx")


def test_register_wires_disabled_stub_tools_only():
    import plugins.presentation.presenton as plugin

    calls = []

    class _Ctx:
        def register_tool(self, **kw):
            calls.append(kw)

    plugin.register(_Ctx())

    assert [call["name"] for call in calls] == [
        "presenton_status",
        "presenton_generate_deck",
        "presenton_export_deck",
    ]
    assert {call["toolset"] for call in calls} == {"presenton"}
    assert all(call["check_fn"]() is False for call in calls)


def test_plugin_contains_no_service_lifecycle_commands():
    plugin_root = Path("plugins/presentation/presenton")
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in plugin_root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yaml"}
    ).lower()

    forbidden = ["docker", "compose", "subprocess", "systemctl", "service start", "serve --mcp"]
    assert not any(term in combined for term in forbidden)
