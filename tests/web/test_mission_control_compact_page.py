from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/MissionControlCompactPage.tsx"
APP = ROOT / "web/src/App.tsx"


def page_source() -> str:
    return PAGE.read_text(encoding="utf-8")


def function_source(src: str, name: str) -> str:
    start = src.index(f"async function {name}")
    next_start = src.find("\n  async function ", start + 1)
    if next_start == -1:
        next_start = src.find("\n  function ", start + 1)
    return src[start:next_start]


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


def test_compact_route_has_project_rooms_and_record_draft_controls() -> None:
    src = page_source()
    for expected in [
        "Project Rooms",
        "Project Room:",
        "Ask Jenny / Propose Work",
        "Copy phone-safe packet",
        "Save challenge draft",
        "Save read-only lane draft",
        "Phone-safe packet",
        "buildPhoneSafeProjectPacket",
        "WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL",
        "WORKSPACE_LANE_REQUESTS_CREATE_URL",
        "Project Sessions",
        "compact-project-room",
    ]:
        assert expected in src


def test_compact_route_has_read_only_project_kanban_lifecycle() -> None:
    src = page_source()
    for expected in [
        "Project Kanban",
        "PROJECT_KANBAN_COLUMNS",
        "projectKanbanColumnFor",
        "Record-backed lifecycle",
        "Dragging disabled",
        "read-only board",
        "Intake",
        "Needs Clarification",
        "Challenge Review",
        "Lane Draft",
        "Awaiting Approval",
        "Active",
        "Evidence Review",
        "Accepted",
        "Blocked / Rollback",
    ]:
        assert expected in src
    for forbidden in [
        "moveKanbanCard",
        "startKanbanWork",
        "kanban/dispatch",
        "POST /kanban",
    ]:
        assert forbidden not in src


def test_compact_lane_draft_requires_latest_clear_challenge_review() -> None:
    src = page_source()
    for expected in [
        "laneDraftBlockMessage",
        "Create a Jenny challenge review before saving a lane request draft.",
        "Latest challenge review is",
        "Resolve that before saving a lane request draft.",
        'review.decision_state !== "clear_and_safe"',
    ]:
        assert expected in src

    challenge_draft = function_source(src, "saveChallengeDraft")
    lane_draft = function_source(src, "saveReadOnlyLaneDraft")
    assert "laneDraftBlockMessage(projectView.challengeReview)" not in challenge_draft
    assert "WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL" in challenge_draft

    gate_index = lane_draft.index("laneDraftBlockMessage(projectView.challengeReview)")
    post_index = lane_draft.index("WORKSPACE_LANE_REQUESTS_CREATE_URL")
    assert gate_index < post_index
    assert "setRoomMessage(blockMessage)" in lane_draft


def test_compact_challenge_draft_is_not_blocked_by_prior_challenge_review() -> None:
    src = page_source()
    challenge_draft = function_source(src, "saveChallengeDraft")
    assert "Write one bounded request before saving a challenge draft." in challenge_draft
    assert "WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL" in challenge_draft
    assert "decision_state: \"needs_spec_first\"" in challenge_draft
    assert "laneDraftBlockMessage" not in challenge_draft


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
