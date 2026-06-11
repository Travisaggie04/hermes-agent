from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/MissionControlCompactPage.tsx"
APP = ROOT / "web/src/App.tsx"


def page_source() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_mobile_compact_route_is_registered() -> None:
    app = APP.read_text(encoding="utf-8")
    assert '"/mission-control-compact": MissionControlCompactPage' in app
    assert 'import MissionControlCompactPage from "@/pages/MissionControlCompactPage"' in app


def test_renders_five_real_projects_in_compact_mode() -> None:
    src = page_source()
    for expected in [
        "Hermes / Mission Control",
        "Long-form Video",
        "Shorts Video",
        "Tool & Tally",
        "Waha Work",
    ]:
        assert expected in src
    for expected_id in [
        "project-hermes-mission-control",
        "project-long-form-video",
        "project-shorts-video",
        "project-tool-tally",
        "project-waha-work",
    ]:
        assert expected_id in src
    assert 'data-testid="mission-control-compact-route"' in src


def test_prompt_copy_text_is_project_specific() -> None:
    src = page_source()
    assert "PROJECT_LANE_GUIDANCE" in src
    assert "Mission Control workspace validation" in src
    assert "Long-form video toolchain/status proof" in src
    assert "Shorts video topic/research/review packet" in src
    assert "Tool & Tally read-only launch/hardening packet" in src
    assert "Waha owner-side inspection handoff" in src
    assert "Copy next lane prompt" in src


def test_compact_cards_show_project_state_freshness_and_artifacts() -> None:
    src = page_source()
    for expected in [
        "Live report available",
        "Seed only — needs first report",
        "latestActivity",
        "latestLane",
        "artifact/report links",
        "missing state",
        "has_real_report",
        "missing_state_fields",
        "latest_activity_at",
        "artifact_links",
    ]:
        assert expected in src


def test_send_dispatch_disabled_and_no_post_session_wiring() -> None:
    src = page_source()
    assert "Save Jenny report manually" in src
    assert "WORKSPACE_REPORTS_CREATE_URL" in src
    assert "method: \"POST\"" in src
    assert "Send to Jenny disabled" in src
    assert "Forbidden actions: no POST, session-send, dispatch" in src
    forbidden_runtime_fragments = [
        'fetchJSON<unknown>("/api/plugins/mission-control-governance/workspace/projects/create"',
        "session-send",
        "sendToJenny(",
        "dispatchMissionControl",
        "localStorage",
        "sessionStorage",
        "setInterval",
        "setTimeout",
        "new Worker",
    ]
    for fragment in forbidden_runtime_fragments:
        if fragment == "session-send":
            assert src.count(fragment) == 1  # only appears in forbidden-action copy
        else:
            assert fragment not in src


def test_smoke_support_project_deemphasized() -> None:
    src = page_source()
    assert "Smoke/support records de-emphasized" in src
    assert "support only" in src
    assert "isSmokeProject" in src
