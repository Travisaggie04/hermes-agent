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
        'WORKSPACE_STATUS_URL = "/api/plugins/mission-control-governance/workspace-status"',
        'WORKSPACE_GITHUB_BRIDGE_STATUS_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/status"',
        'WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/outbox/create"',
        'WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once"',
        'MODEL_INFO_URL = "/api/model/info"',
        'MODEL_OPTIONS_URL = "/api/model/options"',
    ]:
        assert expected in src

    for forbidden in [
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
        "Report lifecycle",
        "Report gaps",
        "Report lifecycle needs Jenny review",
        "Readiness",
        "Laptop Codex",
        "Worker objective",
        "Worker handoff",
        "Laptop Codex needs review",
        "dup {reportLifecycle?.duplicate_report_ids?.length ?? 0} / overwrite",
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
    send_start = src.index("async function sendMessage()")
    send_end = src.index("  return (", send_start)
    send_fn = src[send_start:send_end]

    assert "appendMessage(project.project_id" in src
    assert "optimistic: true" in src
    assert "status: \"queued\"" in src
    assert "void refreshMessages(project.project_id)" in send_fn
    assert "await refreshMessages(project.project_id)" not in send_fn
    assert "void runJennyOnce(project.project_id, requestId)" in src
    assert "await runJennyOnce(project.project_id, requestId)" not in src
    assert "const sendDisabled = sending || loading || !composer.trim() || !mobileSafety.safe;" in src
    assert 'const ANSWER_ONCE_TIMEOUT_MS = 45_000;' in src
    assert "fetchJSONWithTimeout<AnswerOnceResponse>" in src
    assert "confirm_manual_hermes_answer: true" in src
    assert "manual foreground reply only" in src
    assert "no hidden worker, timer, daemon, gateway restart, deploy, Waha/social/payment/outreach" in src
    assert "Visible request from Travis:" in src
    assert "Reply as Jenny" in src
    assert "setSelectedModelChoice" in src
    assert "setSelectedEffort" in src
    assert "createMissionControl" not in src


def test_jenny_mobile_bridge_controls_fail_closed_on_live_flags() -> None:
    src = page_source()

    for expected in [
        "function mobileBridgeSafety(status: GitHubBridgeStatus | undefined): MobileBridgeSafety",
        "function mobileLiveFlagEnabled(value: unknown): boolean",
        'reasons.push("bridge status not loaded")',
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
        "if (mobileLiveFlagEnabled(status[flag])) reasons.push(reason);",
        'return ["1", "true", "yes", "y", "on", "enabled"].includes(value.trim().toLowerCase());',
        "function mobileWorkspaceSafety(status: MobileWorkspaceStatus | null): MobileBridgeSafety",
        'reasons.push("workspace status not loaded")',
        'reasons.push("hard_boundary_contract is not loaded")',
        'hardBoundary.blocked_reasons?.[0] ?? "hard_boundary_contract is blocked"',
        "hardBoundary.live_flag_violations",
        '["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"]',
        'mobileExecutionLockReasons("hard_boundary_contract", hardBoundary)',
        "operatorPacket?.execution_lock_blocked_reasons",
        'mobileExecutionLockReasons("operator_decision_packet", operatorPacket)',
        'mobileExecutionLockReasons("orchestration_readiness", status?.orchestration_readiness)',
        'mobileExecutionLockReasons("report_lifecycle", status?.report_lifecycle)',
        'mobileExecutionLockReasons("worker_node_presence", status?.worker_node_presence)',
        'mobileExecutionLockReasons("worker_node_orchestration", status?.worker_node_orchestration)',
        'mobileExecutionLockReasons("worker_node_instruction_preview", status?.worker_node_instruction_preview)',
        "interface MobileReportLifecycle extends MobileExecutionLockSource",
        "interface MobileWorkerNodePresence extends MobileExecutionLockSource",
        "interface MobileWorkerNodeInstructionPreview extends MobileExecutionLockSource",
        "interface MobileWorkerNodeOrchestration extends MobileExecutionLockSource",
        "report_lifecycle?: MobileReportLifecycle",
        "worker_node_presence?: MobileWorkerNodePresence",
        "worker_node_instruction_preview?: MobileWorkerNodeInstructionPreview",
        "worker_node_orchestration?: MobileWorkerNodeOrchestration",
        "mobileRecordText",
        "workerBlockedReasons",
        "function combineMobileSafety(...checks: MobileBridgeSafety[]): MobileBridgeSafety",
        "fetchJSON<MobileWorkspaceStatus>(WORKSPACE_STATUS_URL)",
        "const bridgeSafety = useMemo(() => mobileBridgeSafety(bridgeStatus), [bridgeStatus]);",
        "const workspaceSafety = useMemo(() => mobileWorkspaceSafety(workspaceStatus), [workspaceStatus]);",
        "const mobileSafety = useMemo(() => combineMobileSafety(bridgeSafety, workspaceSafety), [bridgeSafety, workspaceSafety]);",
        "const visibleRunState: RunState = mobileSafety.safe",
        "Manual chat blocked:",
        "const sendDisabled = sending || loading || !composer.trim() || !mobileSafety.safe;",
        'disabled={replyingRequestId !== "" || sending || !mobileSafety.safe}',
        'mobileSafety.safe ? "manual foreground only" : "blocked"',
    ]:
        assert expected in src

    run_once_start = src.index("const runJennyOnce = useCallback")
    run_once_end = src.index("replyingRequestIdRef.current = requestId;", run_once_start)
    run_once_guard = src[run_once_start:run_once_end]
    assert "if (!mobileSafety.safe)" in run_once_guard
    assert "setRunByProject" in run_once_guard
    assert "fetchJSONWithTimeout<AnswerOnceResponse>" not in run_once_guard


def test_jenny_mobile_has_no_hidden_runtime_status_or_dispatch_wiring() -> None:
    src = page_source()

    for forbidden in [
        "/api/status",
        "9121",
        "dispatchMissionControl",
        "session-send",
        "kanban/dispatch",
        "new Worker",
        "window.setInterval",
        "setInterval(",
        "/api/model/set",
    ]:
        assert forbidden not in src

    assert src.count('method: "POST"') == 2

    timeout_start = src.index("async function fetchJSONWithTimeout")
    timeout_end = src.index("function stripHiddenJennyContext", timeout_start)
    timeout_fn = src[timeout_start:timeout_end]
    assert "window.setTimeout(() => controller.abort(), timeoutMs)" in timeout_fn
    assert "window.clearTimeout(timeoutId)" in timeout_fn

    send_start = src.index("async function sendMessage()")
    send_end = src.index("  return (", send_start)
    send_fn = src[send_start:send_end]
    run_once_start = src.index("const runJennyOnce = useCallback")
    run_once_end = src.index("async function sendMessage()", run_once_start)
    run_once_fn = src[run_once_start:run_once_end]
    assert "WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL" in send_fn
    assert "WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL" in run_once_fn
    assert "confirm_manual_hermes_answer: true" in run_once_fn
