from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/MissionControlCompactPage.tsx"
APP = ROOT / "web/src/App.tsx"
PAGE_HEADER_PROVIDER = ROOT / "web/src/contexts/PageHeaderProvider.tsx"


def page_source() -> str:
    return PAGE.read_text(encoding="utf-8")


def function_source(src: str, name: str) -> str:
    async_marker = f"async function {name}"
    function_marker = f"function {name}"
    start = src.find(async_marker)
    if start == -1:
        start = src.index(function_marker)
    next_start = src.find("\n  async function ", start + 1)
    if next_start == -1:
        next_start = src.find("\n  function ", start + 1)
    return src[start:next_start]


def test_mobile_compact_route_is_registered() -> None:
    app = APP.read_text(encoding="utf-8")
    provider = PAGE_HEADER_PROVIDER.read_text(encoding="utf-8")
    assert '"/mission-control-compact": MissionControlCompactPage' in app
    assert 'import MissionControlCompactPage from "@/pages/MissionControlCompactPage"' in app
    assert 'const isCompactChatRoute = normalizedPath === "/mission-control-compact";' in app
    assert "const isChatLikeRoute = isChatRoute || isCompactChatRoute || isJennyMobileRoute;" in app
    assert 'isCompactChatRoute' in app
    assert '"min-h-dvh overflow-x-hidden overflow-y-visible"' in app
    assert '"h-dvh max-h-dvh min-h-0 overflow-hidden"' in app
    assert 'isBodyScrollChatRoute ? "overflow-visible" : "min-h-0 overflow-hidden"' in app
    assert 'const isCompactChatRoute = pathname === "/mission-control-compact" || pathname === "/mission-control-compact/";' in provider
    assert "isChatLikeRoute" in provider
    assert '(isCompactChatRoute || isJennyMobileRoute) && "sr-only"' in provider
    assert 'isBodyScrollChatRoute ? "overflow-visible" : "overflow-hidden"' in provider
    assert '"overflow-visible overflow-x-hidden"' in provider


def test_renders_five_real_projects_in_compact_mode() -> None:
    src = page_source()
    assert "Make Jenny OS native chat the primary workspace" in src
    assert "Make Mission Control the primary Jenny workspace" not in src
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
        "setTitle(\"Jenny\")",
        "w-full min-w-0 max-w-full",
        "[&_*]:box-border",
        "block w-full min-w-0 max-w-full overflow-visible overflow-x-clip sm:flex sm:flex-1 sm:min-h-0 sm:overflow-hidden",
        "Local studio",
        "Projects",
        "IV. — Jenny workspace",
        "Conversation",
        "Jenny chat status",
        "Project paused",
        "Resume this project after Jenny is stable.",
        "Jenny current status",
        "Jenny status",
        "Latest Jenny outcome",
        "latestJennyOutcomeStatus",
        "latestJennyReply",
        "Review before relying",
        "Review the latest Jenny reply in the chat before acting on it.",
        "Do not rely yet",
        "Usable as context",
        "Send one bounded project message, then get one Jenny reply.",
        "Use the reply review buttons: accept only if evidence is clear, otherwise ask for evidence or challenge the plan.",
        "Jenny operator guidance",
        "jennyOperatorGuidance",
        "Jenny needs attention",
        "Review Jenny reply",
        "one reply at a time",
        "evidence required",
        "no hidden execution",
        "Jenny live status",
        "jennyLiveStatusItems",
        "Current phase",
        "Last sent",
        "Reply state",
        "Elapsed",
        "No message sent yet",
        "not running",
        "Jenny work session",
        "Work session",
        "Queued",
        "Jenny working",
        "Reply received",
        "Review next",
        "jennyWorkSessionSteps",
        "Jenny:",
        "jennyConnectionState",
        "isNoPendingBridgeError",
        "hasGitHubBridgeSignal",
        "normalizedBridgeError",
        "Jenny is caught up. Send a new message to start the next reply.",
        "jennyRunStatusToneClass",
        "Jenny is watching",
        "Waiting for Jenny",
        "Jenny needs attention",
        "statusCopy",
        "Bridge error:",
        "Elapsed {jennyRunElapsedSeconds}s",
        "jennyDeliveryStatus",
        "jennyNextStep",
        "Next step",
        "Pending {pendingCount}",
        "Replies {responseCount}",
        "A message is waiting for Jenny; send your next message only after this reply finishes.",
        "Type one bounded project message, then tap Send.",
        "projectRequestPreview",
        "stripHiddenJennyOsContext",
        "Hidden Jenny OS project context:",
        "Visible chat rule:",
        "Project message",
        "cleanChatDisplayMessage",
        "ownerVisibleJennyReply",
        "technicalJennyReply",
        "compact-jenny-raw-reply",
        "user_message",
        "displayBody",
        'chat.speaker === "You" ? chat.displayBody ?? projectRequestPreview(chat.body, 750) : ownerVisibleJennyReply(chat.body)',
        "projectRoomRequestMatch",
        "Project room request:",
        'message.from_agent === "jenny" ? undefined : cleanChatDisplayMessage',
        "inlineRequestMatch",
        "structuredJennyHandoff",
        "Structured handoff:",
        "Challenge: question unclear, unsafe, or wrong-approach requests before implementation.",
        "Report format: preflight, recommendation, work done, validation, risks, safety confirmation.",
        "Evidence contract:",
        "Recommendation: one-sentence next lane.",
        "Evidence: exact files/commands/checks/PR/CI/runtime/links used.",
        "Approval/rollback: approval needed before live action plus rollback path.",
        "Rule: if evidence is missing, say \\\"not proven\\\"; do not present it as done.",
        "Message sent. Use Get reply to run one foreground Jenny answer, or Refresh to check for an existing reply.",
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
        "Advanced",
        "Safety details",
        "Project report archive",
        "Copy phone-safe packet",
        "Save challenge draft",
        "Save read-only lane draft",
        "Send",
        "Jenny is answering one pending message...",
        "Request intake:",
        "assessProjectRequest",
        "Approval check",
        "Contains protected actions; Jenny should challenge scope and identify approvals before work.",
        "cleanup|update|upgrade|install|configure|migrate|worker",
        "Question assumptions, split the request into a bounded lane",
        "Jenny instruction:",
        "jennyReplyContract",
        "Reply quality",
        "Review latest Jenny reply",
        "recommendation",
        "evidence",
        "risks",
        "approval/rollback",
        "buildJennyReplyReviewPrompt",
        "Looks good",
        "Ask for evidence",
        "Challenge",
        "Do not take action. Report evidence only.",
        "Do not implement or trigger live actions.",
        "buildSpecFirstComposerText",
        "buildJennyMailboxMessage",
        "shouldAutoChallengeRequest",
        "jennySendButtonLabel",
        "Jenny challenge checklist",
        "Jenny must challenge first",
        "Question missing facts and unsafe assumptions.",
        "Push back on protected actions or broad scope.",
        "Return the smallest safe lane with evidence and approval needs.",
        "Use spec-first prompt",
        "Request options",
        'hidden>',
        "Use these when Jenny should challenge, narrow, or formalize the request before normal work.",
        "This request is bounded enough for a guarded Jenny reply.",
        "Jenny will challenge this request before planning any implementation.",
        "Spec-first request for Jenny:",
        "Jenny, do not implement yet. First challenge the request like a senior engineer:",
        "Return only the spec/challenge review and the recommended next safe lane.",
        "COMPACT_JENNY_MESSAGE_LIMIT = 1900",
        "MODEL_INFO_URL = \"/api/model/info\"",
        "MODEL_OPTIONS_URL = \"/api/model/options\"",
        "COMPACT_RUN_EFFORTS",
        "compactModelLabel",
        "compactRunSettingsLabel",
        "compactRunSettingsLines",
        "modelLabel={compactModelLabel(modelInfo)}",
        "Compact chat tools",
        "Requested model",
        "Requested effort",
        "Extra high",
        "Get reply",
        "metadata",
        "requested_effort",
        "boundCompactJennyMessage",
        "COMPACT_JENNY_MESSAGE_LIMIT - 3",
        "Queue for Jenny bridge",
        "Refresh replies",
        "min-h-full w-full min-w-0 max-w-full touch-pan-y flex-col overflow-visible overflow-x-clip overscroll-x-none",
        "sr-only",
        "min-w-0 max-w-full overflow-visible sm:flex-1 sm:min-h-0 sm:overflow-hidden",
        "sr-only order-2 min-w-0 max-w-full overflow-hidden",
        "block w-full min-w-0 max-w-full overflow-visible overflow-x-clip",
        "sm:h-full sm:max-h-full sm:min-h-0",
        "rounded-none border-0 border-[#d4a574]/10",
        "grid w-full min-w-0 max-w-xl gap-1",
        "select",
        "sr-only w-full min-w-0 max-w-full gap-1.5",
        "Latest Jenny activity",
        "min-w-0 max-w-full overflow-hidden rounded-md",
        "block max-w-full truncate font-semibold",
        "grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between",
        "min-h-11 rounded-full border border-emerald-500/40",
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
        "Maintenance lanes",
        "These only queue guarded Jenny requests. They do not restart, update, delete files, or switch runtimes.",
        "queueHermesUpdateLane",
        "queueHermesStorageCleanupLane",
        "Hermes update lane request:",
        "Hermes storage cleanup lane request:",
        "No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.",
        "Jenny memory storage",
        "WORKSPACE_PROFILE_MEMORY_STORAGE_URL",
        "WORKSPACE_JENNY_REPLY_REVIEWS_URL",
        "WORKSPACE_JENNY_REPLY_REVIEWS_CREATE_URL",
        "jennyReplyReviews",
        "latestReplyReviewByResponseId",
        "Reviewed: needs evidence",
        "Reviewed: needs safer plan",
        "Reviewed: accepted",
        "Needs evidence",
        "Needs safer plan",
        "Reply accepted",
        "Ask Jenny for exact files, commands, checks, CI/runtime status",
        "Challenge Jenny for unsafe assumptions, missing approvals, rollback concerns",
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
        "operator_decision_packet",
        "execution_lock_blocked_reasons?: string[]",
        "would_dispatch?: boolean",
        "would_session_send?: boolean",
        "orchestration_readiness",
        "worker_node_presence",
        "result_ingestion_contract",
        "report_completion_path",
        "Operator decision",
        "Preview readiness",
        "Worker node",
        "Result ingestion",
        "Report completion",
        "compactOperatorSummary",
        "compactReadinessSummary",
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
        "compact-chat-scroll",
        "compact-chat-composer",
    ]:
        assert expected in src
    assert 'message.from_agent === "jenny" || message.status === "replied"' not in src


def test_compact_chat_strips_hidden_jenny_context_from_user_preview() -> None:
    src = page_source()
    preview_fn = function_source(src, "projectRequestPreview")
    stripper_fn = function_source(src, "stripHiddenJennyOsContext")

    assert "stripHiddenJennyOsContext(value)" in preview_fn
    assert 'return "Project message";' in preview_fn
    assert "visibleValue" in preview_fn
    assert "?? visibleValue" in preview_fn
    assert "Hidden Jenny OS project context:" in stripper_fn
    assert "Visible chat rule:" in stripper_fn
    assert "blankSeparator" in stripper_fn
    assert "visibleRuleIndex" in stripper_fn


def test_compact_chat_summarizes_technical_jenny_reply_in_owner_bubble() -> None:
    src = page_source()
    reply_fn = function_source(src, "ownerVisibleJennyReply")

    for expected in [
        "session_id:",
        "preflight",
        "safety confirmation",
        "stale-runtime confusion",
        "i did not deploy",
        "Jenny replied with a guarded status update.",
        "Open Review reply for evidence, risks, and safety details.",
        "Recommendation:",
    ]:
        assert expected in reply_fn
    assert "ownerVisibleJennyReply(chat.body)" in src
    assert 'data-testid="compact-jenny-raw-reply"' in src
    assert "{chat.body}" in src


def test_compact_jenny_mailbox_payload_is_bounded() -> None:
    src = page_source()
    message_fn = function_source(src, "buildJennyMailboxMessage")
    phone_packet_fn = function_source(src, "buildPhoneSafeProjectPacket")
    queue_fn = function_source(src, "queueJennyBridgeMessage")

    assert "boundCompactJennyMessage(buildSpecFirstComposerText" in message_fn
    assert "boundCompactJennyMessage(buildPhoneSafeProjectPacket" in message_fn
    assert "return boundCompactJennyMessage(packet)" in phone_packet_fn
    assert "message: buildJennyMailboxMessage" in queue_fn
    assert "user_message: boundCompactJennyMessage(chatRequest)" in queue_fn


def test_compact_project_chat_wraps_long_mobile_text() -> None:
    src = page_source()
    for expected in [
        "overflow-x-hidden",
        "min-h-full w-full min-w-0 max-w-full touch-pan-y flex-col overflow-visible overflow-x-clip overscroll-x-none",
        "sm:h-full sm:max-h-full sm:min-h-0 sm:flex-1 sm:overflow-hidden",
        "block w-full min-w-0 max-w-full overflow-visible overflow-x-clip sm:flex sm:flex-1 sm:min-h-0 sm:overflow-hidden",
        "flex min-h-0 min-w-0 max-w-full flex-col overflow-visible overflow-x-clip",
        "sm:min-h-0 sm:flex-1 sm:overflow-hidden",
        "min-[420px]:grid-cols-2",
        "auto-rows-max content-start",
        "overflow-visible overflow-x-hidden overscroll-contain",
        "sm:content-end sm:overflow-y-auto",
        "sm:scroll-pb-6",
        "[-webkit-overflow-scrolling:touch]",
        "pb-[max(env(safe-area-inset-bottom),0.5rem)]",
        "pb-4 pr-1 sm:min-h-0 sm:flex-1",
        "mb-[max(env(safe-area-inset-bottom),1rem)]",
        "aria-label=\"Project chat composer\"",
        "data-testid=\"compact-chat-composer\"",
        "data-testid=\"compact-chat-scroll\"",
        "data-testid={chat.speaker === \"Jenny\" ? \"compact-jenny-reply-body\" : undefined}",
        "max-h-28 min-h-11",
        "order-1 z-10",
        "order-3 mt-2",
        "[overflow-wrap:anywhere]",
        "[word-break:break-word]",
        "min-w-0 max-w-full",
        "w-full max-w-full rounded-lg border px-3 py-2 text-sm",
        "sm:w-fit sm:max-w-[88%]",
        "max-w-full whitespace-pre-wrap break-words",
        "overflow-visible pr-0 sm:max-h-[min(52dvh,32rem)] sm:touch-pan-y sm:overflow-y-auto sm:overscroll-contain",
        "sm:max-h-[min(52dvh,32rem)]",
        "chat.speaker === \"Jenny\"",
        ": \"overflow-visible\"",
        "max-w-full overflow-hidden",
        "whitespace-pre-wrap break-words [overflow-wrap:anywhere]",
        "grid min-w-0 grid-cols-1 gap-2 text-xs sm:grid-cols-2",
    ]:
        assert expected in src
    assert "w-dvw" not in src
    assert "max-w-dvw" not in src
    assert "sticky bottom-0" not in src
    assert "Mission Control compact route should not reserve dashboard chrome" not in src


def test_compact_phone_viewport_avoids_horizontal_document_scroll() -> None:
    src = page_source()
    main_start = src.index('data-testid="mission-control-compact-route"')
    project_room_start = src.index('data-testid="compact-project-room"')
    transcript_start = src.index('aria-label="Project chat transcript"')
    scroll_start = src.index('data-testid="compact-chat-scroll"')
    composer_start = src.index('data-testid="compact-chat-composer"')

    main_src = src[main_start - 600:main_start + 250]
    room_src = src[project_room_start - 500:project_room_start + 250]
    transcript_src = src[transcript_start - 500:transcript_start + 250]
    scroll_src = src[scroll_start - 500:scroll_start + 250]
    composer_src = src[composer_start - 500:composer_start + 250]
    compact_shell = main_src + room_src + transcript_src + scroll_src + composer_src

    for fragment in [main_src, room_src, transcript_src, scroll_src, composer_src]:
        assert "min-w-0" in fragment
        assert "max-w-full" in fragment

    assert "overflow-x-clip" in main_src
    assert "overscroll-x-none" in main_src
    assert "overflow-x-clip" in room_src
    assert "overflow-x-hidden" in scroll_src
    assert "overflow-x-clip" in composer_src

    for forbidden in ["overflow-x-auto", "w-screen", "min-w-screen", "w-dvw", "max-w-dvw"]:
        assert forbidden not in compact_shell


def test_compact_mobile_transcript_uses_page_scroll_not_trapped_panel() -> None:
    src = page_source()
    main_start = src.index('data-testid="mission-control-compact-route"')
    project_room_start = src.index('data-testid="compact-project-room"')
    transcript_start = src.index('aria-label="Project chat transcript"')
    composer_start = src.index('data-testid="compact-chat-composer"')
    main_src = src[main_start - 450:main_start + 150]
    room_src = src[project_room_start - 350:project_room_start + 150]
    transcript_src = src[transcript_start - 300:composer_start]
    composer_src = src[composer_start - 420:composer_start + 150]

    assert "overflow-visible" in main_src
    assert "sm:overflow-hidden" in main_src
    assert "overflow-visible" in room_src
    assert "sm:overflow-hidden" in room_src
    assert "order-3" in transcript_src
    assert "sm:order-none" in transcript_src
    assert "flex-none" in transcript_src
    assert "overflow-visible overflow-x-hidden" in transcript_src
    assert "sm:overflow-y-auto" in transcript_src
    assert "content-start" in transcript_src
    assert "sm:content-end" in transcript_src
    assert "pb-4" in transcript_src
    assert "pb-[calc(env(safe-area-inset-bottom)+10rem)]" not in transcript_src
    assert "order-1" in composer_src
    assert "sm:order-none" in composer_src
    assert "mb-[max(env(safe-area-inset-bottom),1rem)]" in composer_src
    assert "sticky bottom-0" not in composer_src


def test_compact_mobile_does_not_autoscroll_into_old_reply_on_load() -> None:
    src = page_source()
    effect_start = src.index("if (typeof window !== \"undefined\" && !window.matchMedia(\"(min-width: 640px)\").matches)")
    effect_end = src.index("const operatorGuidance", effect_start)
    effect_src = src[effect_start:effect_end]

    assert "return;" in effect_src
    assert "chatEndRef.current?.scrollIntoView?.({ block: \"end\" })" in effect_src


def test_compact_project_chat_keeps_primary_flow_chat_first() -> None:
    src = page_source()
    room = function_source(src, "CompactProjectRoom")
    transcript_start = room.index('aria-label="Project chat transcript"')
    composer_start = room.index('placeholder={paused ? "This project is on hold until Jenny is stable."')
    transcript_src = room[transcript_start:composer_start]
    assert 'className="sr-only"' in transcript_src
    assert 'Conversation' in transcript_src
    assert "rounded-md border border-[#f3ebda]/10 bg-[#120d17] p-2" not in transcript_src
    composer_section_start = room.rindex('className="order-1 z-10 mt-2 mb-[max(env(safe-area-inset-bottom),1rem)] min-w-0 max-w-full shrink-0', 0, composer_start)
    composer_src = room[composer_section_start:composer_start + 500]
    assert "order-1" in composer_src
    assert "sm:order-none" in composer_src
    assert "shrink-0" in composer_src
    assert "rounded-[1.5rem]" in composer_src
    assert "sticky bottom-0" not in composer_src
    assert "max-h-28 min-h-11" in composer_src
    assert "data-testid=\"compact-chat-composer\"" in composer_src
    assert "backdrop-blur" in composer_src
    assert "<summary" in transcript_src
    assert "Review reply" in transcript_src
    assert "Review latest Jenny reply" in transcript_src


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
    assert "WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL" in function_source(src, "runJennyOnce")
    assert "WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL" not in send_fn
    assert 'from_agent: "travis"' in send_fn
    assert 'to_agent: "jenny"' in send_fn
    assert "bridgeRequestId()" in send_fn
    assert "requested_effort" in send_fn
    assert "Message sent. Use Get reply" in send_fn
    assert 'setProjectRequest("")' in send_fn
    assert "void refreshSnapshot().catch" in send_fn
    assert "await runJennyOnce" not in send_fn
    assert "await refreshSnapshot()" not in send_fn


def test_compact_chat_bridge_controls_fail_closed_on_live_flags() -> None:
    src = page_source()
    send_fn = function_source(src, "queueJennyBridgeMessage")
    run_once_fn = function_source(src, "runJennyOnce")
    update_lane_fn = function_source(src, "queueHermesUpdateLane")
    cleanup_lane_fn = function_source(src, "queueHermesStorageCleanupLane")

    for expected in [
        "function compactGitHubBridgeSafety(status: GitHubBridgeStatus | undefined, workspaceStatus?: WorkspaceStatus): CompactBridgeSafety",
        'reasons.push("GitHub bridge status not loaded")',
        'reasons.push("hard_boundary_contract is not loaded")',
        'status.manual_start_only !== true',
        '["dispatch_enabled", "dispatch_enabled must remain false"]',
        '["execution_enabled", "execution_enabled must remain false"]',
        '["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"]',
        '["session_send_enabled", "session_send_enabled must remain false"]',
        '["worker_dispatch_enabled", "worker_dispatch_enabled must remain false"]',
        '["would_execute", "would_execute must remain false"]',
        '["worker_enabled", "worker_enabled must remain false"]',
        '["timer_enabled", "timer_enabled must remain false"]',
        '["daemon_enabled", "daemon_enabled must remain false"]',
        '["discord_automation_enabled", "discord_automation_enabled must remain false"]',
        '["model_routing_enabled", "model_routing_enabled must remain false"]',
        '["execution_ready", "hard_boundary_contract execution_ready must remain false"]',
        '["live_operations_enabled", "hard_boundary_contract live_operations_enabled must remain false"]',
        "function compactLiveFlagEnabled(value: unknown): boolean",
        "if (compactLiveFlagEnabled(status[flag])) reasons.push(reason);",
        "if (compactLiveFlagEnabled(hardBoundary[flag])) reasons.push(reason);",
        "operatorPacket?.execution_lock_blocked_reasons",
        'compactExecutionLockReasons("operator_decision_packet", operatorPacket)',
        'compactExecutionLockReasons("orchestration_readiness", workspaceStatus?.orchestration_readiness)',
        "const uniqueReasons = [...new Set(reasons)];",
        ".filter(([flag]) => compactLiveFlagEnabled(source[flag]))",
        "function compactBridgeBlockedMessage(safety: CompactBridgeSafety): string",
        "const githubBridgeSafety = compactGitHubBridgeSafety(githubBridgeStatus, workspaceStatus);",
        "const bridgeActionDisabled = busy || paused || !githubBridgeSafety.safe;",
        "const canRunForegroundReply = !paused && githubBridgeSafety.safe &&",
        "disabled={bridgeActionDisabled}",
        "disabled={busy || !githubBridgeSafety.safe}",
        'CompactField label="GitHub safety"',
        "Manual Jenny bridge blocked:",
    ]:
        assert expected in src

    for function in [send_fn, run_once_fn, update_lane_fn, cleanup_lane_fn]:
        safety_index = function.index("const bridgeSafety = compactGitHubBridgeSafety(snapshot?.githubBridgeStatus, snapshot?.workspaceStatus);")
        block_index = function.index("if (!bridgeSafety.safe)")
        assert safety_index < block_index
        assert "setRoomMessage(compactBridgeBlockedMessage(bridgeSafety));" in function

    assert send_fn.index("if (!bridgeSafety.safe)") < send_fn.index("WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL")
    assert run_once_fn.index("if (!bridgeSafety.safe)") < run_once_fn.index("WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL")
    assert update_lane_fn.index("if (!bridgeSafety.safe)") < update_lane_fn.index("WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL")
    assert cleanup_lane_fn.index("if (!bridgeSafety.safe)") < cleanup_lane_fn.index("WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL")


def test_compact_health_dashboard_fails_closed_on_execution_locks() -> None:
    src = page_source()

    for expected in [
        "type CompactExecutionLockSource",
        "const COMPACT_EXECUTION_LOCK_FLAGS",
        '["would_execute", "would_execute must remain false"]',
        '["would_dispatch", "would_dispatch must remain false"]',
        '["would_session_send", "would_session_send must remain false"]',
        '["dispatch_enabled", "dispatch_enabled must remain false"]',
        '["execution_enabled", "execution_enabled must remain false"]',
        '["execution_ready", "execution_ready must remain false"]',
        '["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"]',
        '["session_send_enabled", "session_send_enabled must remain false"]',
        '["worker_dispatch_enabled", "worker_dispatch_enabled must remain false"]',
        '["worker_enabled", "worker_enabled must remain false"]',
        "function compactExecutionLockReasons",
        "execution_mode_classification?: CompactExecutionLockSource",
        "execution_packet_preview?: CompactExecutionLockSource",
        "hard_boundary_contract?: CompactExecutionLockSource",
        "worker_node_instruction_preview?: CompactExecutionLockSource",
        'compactExecutionLockReasons("Safe next actions", nextSafeActions)',
        'compactExecutionLockReasons("Execution mode", executionMode)',
        'compactExecutionLockReasons("Execution packet", executionPacket)',
        'compactExecutionLockReasons("Execution packet body", executionPacket?.packet)',
        'compactExecutionLockReasons("Worker contract", executionPacket?.packet?.worker_node_contract)',
        'compactExecutionLockReasons("Hard boundary", hardBoundary)',
        'compactExecutionLockReasons("Operator decision", operatorPacket)',
        "operatorExecutionLockBlockedReasons",
        "Operator execution locks need review",
        'compactExecutionLockReasons("Preview readiness", readiness)',
        'compactExecutionLockReasons("Worker handoff", workerInstruction)',
        'compactExecutionLockReasons("Worker node", workerPresence)',
        'compactExecutionLockReasons("Result ingestion", resultIngestion)',
        'compactExecutionLockReasons("Report completion", reportCompletion)',
        'compactExecutionLockReasons("Report lifecycle", reportLifecycle)',
        'compactExecutionLockReasons("Approval lifecycle", approvalLifecycle)',
        'compactExecutionLockReasons("Run lifecycle", runLifecycle)',
        "Execution preview",
        "Worker handoff",
        "Approval lifecycle",
        "Approval gaps",
        "Run lifecycle",
        "Run gaps",
        "Report lifecycle",
        "Report gaps",
        "Execution preview remains display-only; dispatch, session send, and worker activation stay disabled.",
        "compactLiveFlagEnabled(status.safety?.model_routing_enabled) ? \"Model routing safety is not confirmed off\"",
        "executionPreviewTone",
        "workerInstructionTone",
        "operatorLockReasons.length",
        "readinessLockReasons.length",
        "workerLockReasons.length",
        "approvalLifecycleLockReasons.length",
        "runLifecycleLockReasons.length",
        "approvalMissingRecordCount",
        "approvalUnavailableRunCount",
        "runTerminalMissingLinkedCount",
        "reportLifecycleLockReasons.length",
        "reportOverwriteConflictCount",
        "reportMissingLinkedCount",
        "hardBoundaryLockReasons.length",
        "hardBoundaryViolationCount",
        "Hard boundary",
        "Live operations require separate approval.",
        "ingestionLockReasons.length",
        "completionLockReasons.length",
        "approval_lifecycle?: CompactExecutionLockSource",
        "run_lifecycle?: CompactExecutionLockSource",
        "Approval lifecycle needs review",
        "Run lifecycle needs review",
        "Approval gaps block autonomy",
        "one-active-mutation-lane rule",
        "report_lifecycle?: CompactExecutionLockSource",
        "Report gaps: duplicates",
        "Overwrite conflicts quarantine duplicate report IDs",
        "Report lifecycle needs review",
        'model routing=${compactLiveFlagEnabled(status.safety?.model_routing_enabled) ? "enabled" : "disabled"}',
    ]:
        assert expected in src


def test_compact_chat_uses_plain_language_errors() -> None:
    src = page_source()
    helper = function_source(src, "jennyChatErrorMessage")
    assert "Jenny bridge is offline. Start or reconnect the Hermes gateway, then send the message again." in helper
    assert "That message was too large for the Jenny bridge. Shorten it and send one focused request." in helper
    assert "No message is waiting for Jenny. Send a message first." in helper
    assert "Jenny did not answer before the time limit. The request is still guarded; try again with one smaller task." in helper
    for function_name in [
        "queueJennyBridgeMessage",
        "runJennyOnce",
        "reviewJennyReply",
        "queueHermesUpdateLane",
        "queueHermesStorageCleanupLane",
        "refreshBridge",
        "saveChallengeDraft",
        "saveReadOnlyLaneDraft",
    ]:
        function = function_source(src, function_name)
        assert "jennyChatErrorMessage(err)" in function
        assert "err instanceof Error ? err.message : String(err)" not in function


def test_compact_chat_prefers_current_github_mailbox_errors() -> None:
    src = page_source()
    signal_helper = function_source(src, "hasGitHubBridgeSignal")
    helper = function_source(src, "normalizedBridgeError")
    assert "status.last_error" in signal_helper
    assert "unwrapRecords(status.status_records).length" in signal_helper
    assert "githubBridgeStatus.last_error" in helper
    assert "bridgeStatus.last_error" in helper
    assert "hasGitHubBridgeSignal(githubBridgeStatus) ? \"\" : legacyError" in helper
    assert helper.index("githubBridgeStatus.last_error") < helper.index("bridgeStatus.last_error")
    assert "isNoPendingBridgeError(githubError)" in helper
    assert "isNoPendingBridgeError(legacyError)" in helper


def test_compact_chat_behaves_like_a_normal_thread_after_send() -> None:
    src = page_source()
    assert "useRef" in src
    assert "chatEndRef.current?.scrollIntoView?.({ block: \"end\" })" in src
    assert '<div ref={chatEndRef} />' in src
    chat_start = src.index("const chatMessages: ProjectChatMessage[]")
    chat_end = src.index("const latestReplyReview", chat_start)
    chat_src = src[chat_start:chat_end]
    assert "time: request.created_at" in chat_src
    assert "time: response.created_at" in chat_src


def test_compact_chat_does_not_force_scroll_on_elapsed_timer_ticks() -> None:
    src = page_source()
    effect_start = src.index("chatEndRef.current?.scrollIntoView?.({ block: \"end\" })")
    effect_end = src.index("const operatorGuidance", effect_start)
    effect_src = src[effect_start:effect_end]

    assert "chatMessages.length" in effect_src
    assert "effectiveJennyRunProgress?.phase" in effect_src
    assert "selectedProjectView.project.project_id" in effect_src
    assert "jennyRunElapsedSeconds" not in effect_src


def test_compact_chat_restores_jenny_status_from_bridge_records() -> None:
    src = page_source()
    helper_start = src.index("function recordBackedJennyRunProgress")
    helper_end = src.index("function jennyWorkSessionSteps", helper_start)
    helper = src[helper_start:helper_end]
    assert "statusRecords: GitHubBridgeMailboxStatusRecord[]" in helper
    assert "bridgeMessages: GitHubBridgeMessageRecord[]" in helper
    assert "hermes_answer_started" in helper
    assert "This status is restored from the bridge audit trail." in helper
    assert "hermes_answer_completed" in helper
    assert "response_appended" in helper
    assert "hermes_answer_error" in helper
    room = function_source(src, "CompactProjectRoom")
    assert "const statusRecords = unwrapRecords(githubBridgeStatus.status_records)" in room
    assert "const effectiveJennyRunProgress = jennyRunProgress ?? recordBackedJennyRunProgress" in room
    assert "jennyRunStatusToneClass(effectiveJennyRunProgress, connectionState.tone)" in room


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


def test_compact_run_jenny_once_recovers_late_recorded_reply_before_error() -> None:
    src = page_source()
    helper = function_source(src, "latestGitHubBridgeReplyForRequest")
    assert "status?.response_messages" in helper
    assert "status?.recent_messages" in helper
    assert 'message.request_id === requestId && message.from_agent === "jenny"' in helper

    run_fn = function_source(src, "runJennyOnce")
    assert "latestGitHubBridgeReplyForRequest(nextSnapshot.githubBridgeStatus, pendingRequestId)" in run_fn
    assert "compact chat reply reconciliation failed" in run_fn
    assert run_fn.index("latestGitHubBridgeReplyForRequest(nextSnapshot.githubBridgeStatus, pendingRequestId)") < run_fn.index("jennyChatErrorMessage(err)")
    assert "Jenny replied to the latest pending project message." in run_fn


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
