from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/JennyMobilePage.tsx"
APP = ROOT / "web/src/App.tsx"
PAGE_HEADER_PROVIDER = ROOT / "web/src/contexts/PageHeaderProvider.tsx"


def page_source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_jenny_mobile_route_is_registered_as_shell_light_phone_route() -> None:
    app = APP.read_text(encoding="utf-8")
    provider = PAGE_HEADER_PROVIDER.read_text(encoding="utf-8")

    assert 'import JennyMobilePage from "@/pages/JennyMobilePage"' in app
    assert '"/jenny-mobile": JennyMobilePage' in app
    assert 'const isJennyMobileRoute = normalizedPath === "/jenny-mobile";' in app
    assert "const isBodyScrollChatRoute = isCompactChatRoute || isJennyMobileRoute;" in app
    assert "const isChatLikeRoute = isChatRoute || isCompactChatRoute || isJennyMobileRoute;" in app
    assert "{!isJennyMobileRoute && <header" in app
    assert "{!isJennyMobileRoute && <aside" in app
    assert 'isJennyMobileRoute ? "pt-0" : "pt-14 lg:pt-0"' in app
    assert 'isJennyMobileRoute ? "px-0" : "px-3 sm:px-6"' in app

    assert 'const isJennyMobileRoute = pathname === "/jenny-mobile" || pathname === "/jenny-mobile/";' in provider
    assert 'isBodyScrollChatRoute ? "overflow-visible" : "overflow-hidden"' in provider
    assert '(isCompactChatRoute || isJennyMobileRoute) && "sr-only"' in provider


def test_jenny_mobile_uses_lightweight_project_chat_endpoints() -> None:
    src = page_source()

    for expected in [
        'WORKSPACE_PROJECTS_URL = "/api/plugins/mission-control-governance/workspace/projects"',
        'WORKSPACE_GITHUB_BRIDGE_STATUS_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/status"',
        'WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/outbox/create"',
        'WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once"',
        'MODEL_INFO_URL = "/api/model/info"',
        'MODEL_OPTIONS_URL = "/api/model/options"',
    ]:
        assert expected in src

    for forbidden in [
        "workspace-status",
        "project-briefs",
        "challenge-reviews",
        "lane-requests",
        "profile-memory-storage",
        "Project report archive",
        "Kanban",
        "Safety details",
        "/api/model/set",
        "setInterval",
    ]:
        assert forbidden not in src


def test_jenny_mobile_renders_codex_like_mobile_chat_controls() -> None:
    src = page_source()

    for expected in [
        'data-testid="jenny-mobile-route"',
        'data-testid="jenny-mobile-project-select"',
        'data-testid="jenny-mobile-chat-timeline"',
        'data-testid="jenny-mobile-composer"',
        'data-testid="jenny-mobile-model-select"',
        'data-testid="jenny-mobile-effort-select"',
        'data-testid="jenny-mobile-input"',
        "fixed inset-x-0 top-0",
        "fixed inset-x-0 bottom-0",
        "pt-[calc(4.75rem+env(safe-area-inset-top,0px))]",
        "Ask Jenny",
        "Send Jenny message",
        "Open activity",
        "Extra high",
    ]:
        assert expected in src

    for project in [
        "Hermes / Mission Control",
        "Long-form Video",
        "Shorts Video",
        "Tool & Tally",
        "Waha Work",
        "Other chats",
    ]:
        assert project in src


def test_jenny_mobile_send_is_optimistic_and_foreground_only() -> None:
    src = page_source()

    assert "appendMessage(project.project_id" in src
    assert "optimistic: true" in src
    assert "status: \"queued\"" in src
    assert "await refreshMessages(project.project_id)" in src
    assert "await runJennyOnce(project.project_id, requestId)" in src
    assert "confirm_manual_hermes_answer: true" in src
    assert "manual foreground reply only" in src
    assert "no hidden worker, timer, daemon, gateway restart, deploy, Waha/social/payment/outreach" in src
    assert "setSelectedModelChoice" in src
    assert "setSelectedEffort" in src
    assert "createMissionControl" not in src
