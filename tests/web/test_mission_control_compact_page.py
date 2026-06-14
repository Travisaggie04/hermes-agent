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
        "Project chat workspace",
        "Local studio",
        "Projects",
        "IV. — Jenny workspace",
        "Conversation",
        "Jenny:",
        "jennyConnectionState",
        "Jenny is watching",
        "Waiting for Jenny",
        "Jenny needs attention",
        "jennyDeliveryStatus",
        "jennyNextStep",
        "Next step",
        "Pending {pendingCount}",
        "Replies {responseCount}",
        "Tap Get Jenny reply to ask Jenny for one response to the latest message.",
        "Type one bounded project message, then tap Send to Jenny.",
        "projectRequestPreview",
        "structuredJennyHandoff",
        "Structured handoff:",
        "Challenge: question unclear, unsafe, or wrong-approach requests before implementation.",
        "Report format: preflight, recommendation, work done, validation, risks, safety confirmation.",
        "Sent to Jenny mailbox",
        "Live reply refresh is on and read-only",
        "setInterval",
        "clearInterval",
        "Ask Jenny a bounded question or give her one safe next task below.",
        "Message Jenny",
        "Previous sessions",
        "Open session",
        "useNavigate",
        "compactSessionRoute",
        "/chat?resume=",
        "encodeURIComponent(sessionId)",
        "onOpenSession",
        "onClick={() => onOpenSession(session)}",
        "Safety and maintenance",
        "Safety details and reports",
        "Project report archive",
        "Copy phone-safe packet",
        "Save challenge draft",
        "Save read-only lane draft",
        "Send to Jenny",
        "Get Jenny reply",
        "Request intake:",
        "assessProjectRequest",
        "Approval check",
        "Contains protected actions; Jenny should challenge scope and identify approvals before work.",
        "Question assumptions, split the request into a bounded lane",
        "Jenny instruction:",
        "\\n\\s*\\nRequest intake:",
        "jennyReplyContract",
        "Reply quality",
        "recommendation",
        "evidence",
        "risks",
        "buildJennyReplyReviewPrompt",
        "Jenny reply review actions",
        "Draft acceptance note",
        "Ask for evidence",
        "Challenge plan",
        "Do not take action. Report evidence only.",
        "Do not implement or trigger live actions.",
        "buildSpecFirstComposerText",
        "Use spec-first prompt",
        "Spec-first request for Jenny:",
        "Jenny, do not implement yet. First challenge the request like a senior engineer:",
        "Return only the spec/challenge review and the recommended next safe lane.",
        "Queue for Jenny bridge",
        "Refresh replies",
        "w-[100dvw]",
        "order-1 min-w-0 max-w-full overflow-hidden xl:order-1",
        "order-2 min-w-0 max-w-full overflow-hidden xl:order-2",
        "max-w-[11rem] shrink-0 rounded-full",
        "block truncate font-semibold",
        "projectRoomProjects",
        "canonicalRealProjects",
        "projects={projectRoomProjects}",
        "Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.",
        "This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.",
        "Resume requirements",
        "Jenny challenge review clears the approach",
        "Travis approval is recorded before work resumes",
        "isDiagnosticChatMessage",
        "isOperatorBridgeMessage",
        "fromAgent === \"codex\"",
        "requestId.startsWith(\"codex-\")",
        "bounded dashboard-only deploy check",
        "review pr #",
        "codex app-server startup failed",
        "desktop phone bridge",
        "mission control two process",
        "bridge works",
        "success smoke reached",
        "failure guarded",
        "Hermes update lane",
        "Start Hermes update lane",
        "Start storage cleanup lane",
        "queueHermesUpdateLane",
        "queueHermesStorageCleanupLane",
        "Hermes update lane request:",
        "Hermes storage cleanup lane request:",
        "No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.",
        "Jenny memory storage",
        "WORKSPACE_PROFILE_MEMORY_STORAGE_URL",
        "target of about 50% disk usage",
        "timestamped dry-run manifest",
        "dirty project worktrees",
        "Tool & Tally report-builder data",
        "before and after each pass",
        "gateway update as a separate explicit lane",
        "With explicit cleanup approval",
        "bottom-bar version",
        "separate installed worker-node version",
        "Jenny bridge",
        "Jenny activity",
        "jennyActivityItems",
        "Jenny is thinking",
        "JennyRunProgress",
        "jennyRunProgressCopy",
        "isJennyRunActive",
        "Starting the guarded one-reply Jenny run.",
        "Mission Control sent the latest project message to Jenny and is waiting for one bounded reply.",
        "Waiting for Jenny",
        "Reply received",
        "Elapsed ${elapsedSeconds}s",
        "recent bridge status",
        "refreshing every 2.5s",
        "Record-backed outbox/inbox for Jenny relay",
        "WORKSPACE_JENNY_BRIDGE_OUTBOX_URL",
        "WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL",
        "WORKSPACE_JENNY_BRIDGE_INBOX_URL",
        "WORKSPACE_JENNY_BRIDGE_POLLER_STATUS_URL",
        "WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL",
        "WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL",
        "status_records",
        "githubBridgeMessages",
        "queueJennyBridgeMessage",
        "visible_pending_count",
        "background_pending_count",
        "visible ${githubBridgeStatus.visible_pending_count",
        "visibleCurrentGitHubBridgeMessagesForProject",
        "latestVisiblePendingGitHubBridgeMessageForProject",
        "latestPendingGitHubBridgeMessage",
        "manual-start only",
        "worker/timer",
        "Deploy state",
        "dashboardUpdateNotice",
        "Desktop can be current while phone/web waits for a safe dashboard-only update.",
        "Accepted / deployed",
        "Desktop app",
        "separate worker-node update",
        "deployment_gap",
        "latest report contract",
        "reportContractSummary",
        "Hermes health dashboard",
        "CompactHermesHealthDashboard",
        "Profile storage usage",
        "Profile data",
        "State DB",
        "Sessions",
        "Recall files",
        "Mount max",
        "Mount used",
        "mount {formatPercent",
        "Needs attention",
        "Safe next actions",
        "Kanban parked for later",
        "Phone-safe packet",
        "buildPhoneSafeProjectPacket",
        "WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL",
        "WORKSPACE_LANE_REQUESTS_CREATE_URL",
        "compact-project-room",
    ]:
        assert expected in src


def test_compact_project_chat_wraps_long_mobile_text() -> None:
    src = page_source()
    for expected in [
        "overflow-x-hidden",
        "overflow-y-auto overflow-x-hidden",
        "[overflow-wrap:anywhere]",
        "min-w-0 max-w-full",
        "max-w-full overflow-hidden",
        "whitespace-pre-wrap break-words [overflow-wrap:anywhere]",
        "grid min-w-0 grid-cols-1 gap-2 text-xs sm:grid-cols-2",
    ]:
        assert expected in src


def test_compact_route_parks_kanban_until_real_task_board_is_reliable() -> None:
    src = page_source()
    for expected in [
        "Kanban parked for later",
        "The task board is hidden until it can show real tasks and reliable controls.",
        "CompactKanbanParkedCard",
    ]:
        assert expected in src
    for forbidden in [
        "Memory cap",
        "Memory used %",
        "Total memory files",
        "profileMemoryPercent",
        "profileMemoryLimit",
    ]:
        assert forbidden not in src
    for forbidden in [
        "moveKanbanCard",
        "startKanbanWork",
        "kanban/dispatch",
        "POST /kanban",
    ]:
        assert forbidden not in src


def test_compact_route_has_display_only_tonight_active_lanes() -> None:
    src = page_source()
    for expected in [
        "Active Jenny OS Lane",
        "Active Jenny OS lane compact",
        "Mission Control/Jenny stability lane only",
        "Display-only; no dispatch, queue mutation, worker, or timer",
        "ACTIVE_OS_PROJECT_IDS",
        "PAUSED_PROJECT_IDS",
        "Projects on hold",
        "compactActiveLaneStage",
        "next safe lane",
        "latest evidence",
        "report contract",
    ]:
        assert expected in src

    section_start = src.index("function CompactActiveLanes")
    section_end = src.index("function CompactProjectRoom", section_start)
    active_lanes_src = src[section_start:section_end]
    for forbidden in [
        "fetchJSON(",
        "method: \"POST\"",
        "setInterval",
        "setTimeout",
        "Worker(",
        "dispatch",
    ]:
        if forbidden == "dispatch":
            assert "no dispatch" in active_lanes_src
        else:
            assert forbidden not in active_lanes_src


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
    assert 'blocking_verdicts: ["requires_spec_update", "blocks_lane_draft"]' in challenge_draft
    assert 'challenge_categories: ["questions_required", "missing_context"]' in challenge_draft
    assert "decision_state: \"needs_spec_first\"" in challenge_draft
    assert "laneDraftBlockMessage" not in challenge_draft


def test_compact_chat_send_uses_github_mailbox_not_local_only_outbox() -> None:
    src = page_source()
    send_fn = function_source(src, "queueJennyBridgeMessage")
    assert "WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL" in send_fn
    assert "WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL" not in send_fn
    assert 'from_agent: "travis"' in send_fn
    assert 'to_agent: "jenny"' in send_fn
    assert "bridgeRequestId()" in send_fn
    assert "Sent to Jenny mailbox" in send_fn


def test_compact_run_jenny_once_targets_visible_current_project_message() -> None:
    src = page_source()
    run_fn = function_source(src, "runJennyOnce")
    assert "latestVisiblePendingGitHubBridgeMessageForProject" in run_fn
    assert "projectView.project.project_id" in run_fn
    helper_start = src.index("function visibleCurrentGitHubBridgeMessagesForProject")
    helper_end = src.index("function latestVisiblePendingGitHubBridgeMessageForProject", helper_start)
    helper = src[helper_start:helper_end]
    assert "isDiagnosticChatMessage" in helper
    assert "isOperatorBridgeMessage" in helper
    assert "latestJennyReplyTimestamp([], visibleMessages)" in helper
    assert "isCurrentAfterReply" in helper


def test_compact_jenny_activity_uses_github_bridge_status_records() -> None:
    src = page_source()
    start = src.index("function jennyActivityItems")
    activity_src = src[start : src.index("\n}", start) + 2]
    assert "status.status_records" in activity_src
    assert ".slice(-4).reverse()" in activity_src
    assert "function jennyActivityLabel" in src
    assert "hermes_answer_started" in src
    assert "Jenny is thinking" in src
    assert "hermes_answer_completed" in src
    assert "Jenny replied" in src
    assert "aria-label=\"Jenny activity\"" in src

    interval_effect = src[src.index("const timer = window.setInterval") : src.index("return () => window.clearInterval(timer)", src.index("const timer = window.setInterval"))]
    assert "roomBusy ? 2500 : 15000" in interval_effect


def test_compact_admin_buttons_use_github_mailbox_not_local_only_outbox() -> None:
    src = page_source()
    for function_name, expected in [
        ("queueHermesUpdateLane", "Sent safe Hermes update lane to Jenny mailbox"),
        ("queueHermesStorageCleanupLane", "Sent safe Hermes storage cleanup lane to Jenny mailbox"),
    ]:
        function = function_source(src, function_name)
        assert "WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL" in function
        assert "WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL" not in function
        assert 'from_agent: "travis"' in function
        assert 'to_agent: "jenny"' in function
        assert "bridgeRequestId()" in function
        assert expected in function


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
        "report_contract",
        "reportContractSummaryForState",
        "latest_activity_at",
        "artifact_links",
    ]:
        assert expected in src


def test_send_dispatch_disabled_and_no_post_session_wiring() -> None:
    src = page_source()
    assert "Manual record repair" in src
    assert "Save a missing Jenny report" in src
    assert "Not needed for normal chat." in src
    assert "WORKSPACE_REPORTS_CREATE_URL" in src
    assert "method: \"POST\"" in src
    assert "Forbidden actions: no POST, session-send, dispatch" in src
    forbidden_runtime_fragments = [
        'fetchJSON<unknown>("/api/plugins/mission-control-governance/workspace/projects/create"',
        "session-send",
        "sendToJenny(",
        "dispatchMissionControl",
        "localStorage",
        "sessionStorage",
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
