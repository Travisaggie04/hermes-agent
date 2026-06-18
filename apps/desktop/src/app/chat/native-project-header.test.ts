import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('native project chat header', () => {
  it('keeps the header visible for a selected project draft before a session exists', () => {
    expect(source).toContain("const selectedProjectTitle = selectedProjectName.trim()")
    expect(source).toContain("selectedProjectTitle ? 'New project chat' : 'New session'")
    expect(source).toContain('!isRoutedSessionView && !projectPickerAvailable')
  })

  it('does not attach session actions to a project draft with no backend session yet', () => {
    expect(source).toContain('selectedSessionId || activeSessionId ? (')
    expect(source).toContain('<SessionActionsMenu')
    expect(source).toContain('<div className="flex h-6 min-w-0 items-center px-2 [-webkit-app-region:no-drag]">')
  })

  it('shows a slim Jenny status strip for selected project chats', () => {
    expect(source).toContain('function ProjectJennyStatusStrip')
    expect(source).toContain('aria-label="Project chat status"')
    expect(source).toContain('aria-live="polite"')
    expect(source).toContain('role="status"')
    expect(source).toContain('queryFn: () => getMissionControlGitHubBridgeStatus(selectedProjectId)')
    expect(source).toContain('<span className="shrink-0 font-medium text-foreground">Jenny</span>')
    expect(source).toContain('in {projectName}')
    expect(source).toContain('{jennyStatus.summary}')
    expect(source).toContain('<ProjectJennyStatusStrip')
    expect(source).toContain('onRetry={messageId => void onReload(messageId)}')
    expect(source).toContain('subagents={activeSessionId ? (subagentsBySession[activeSessionId] ?? []) : []}')
  })

  it('shows the extra Jenny status strip while Jenny is queued, working, failed, or freshly replied', () => {
    expect(source).toContain('const latestChatReplied = latestVisibleAssistantReply(messages)')
    expect(source).toContain('...(latestChatReplied ? ([\'ok\'] as const) : [])')
    expect(source).toContain('if (!visibleStatusTones.has(jennyStatus.tone)) {')
    expect(source).toContain('return null')
    expect(source).toContain("jennyStatus.tone === 'warn'")
    expect(source).toContain("jennyStatus.tone === 'pending'")
  })

  it('makes the native composer feel project-scoped when a project is selected', () => {
    expect(source).toContain('const selectedProjectTitle = selectedProjectName.trim()')
    expect(source).toContain('placeholderOverride={')
    expect(source).toContain('Message Jenny in ${selectedProjectTitle}; she replies here')
    expect(source).toContain('disabledPlaceholderOverride={')
    expect(source).toContain('Jenny is offline; reconnect gateway to message ${selectedProjectTitle}')
  })

  it('lets the native chat header switch Jenny projects without opening Mission Control', () => {
    expect(source).toContain('getMissionControlProjects')
    expect(source).toContain("queryKey: ['mission-control-projects-native-chat']")
    expect(source).toContain('function ProjectHeaderSelect')
    expect(source).toContain('aria-label="Project"')
    expect(source).toContain('onSelectProject(project.project_id, project.name)')
    expect(source).toContain('onSelectProject={onStartProjectChat}')
  })

  it('keeps the native project picker available on narrow chat widths', () => {
    expect(source).toContain('ml-auto flex min-w-0 max-w-[52vw]')
    expect(source).not.toContain('ml-auto hidden min-w-0 max-w-[44vw]')
    expect(source).toContain('max-w-[38vw]')
    expect(source).toContain('min-[46rem]:max-w-56')
    expect(source).toContain('className="hidden min-[46rem]:inline-flex"')
    expect(source).toContain('className="h-6 shrink-0 px-2 text-[0.6875rem]"')
    expect(source).toContain('className="min-[46rem]:hidden"')
    expect(source).not.toContain("className=\"hidden h-6 shrink-0 px-2 text-[0.6875rem] min-[46rem]:inline-flex\"")
  })

  it('lets Travis leave project mode from the native project picker', () => {
    expect(source).toContain('setSelectedMissionControlProject')
    expect(source).toContain('onClearProject={() => setSelectedMissionControlProject(null)}')
    expect(source).toContain('onClearProject: () => void')
    expect(source).toContain('if (!nextValue) {')
    expect(source).toContain('onClearProject()')
    expect(source).toContain('<option value="">{loading ? \'Loading projects...\' : \'Other chats\'}</option>')
  })

  it('keeps the project picker visible on the blank native chat home', () => {
    expect(source).toContain('const projectPickerAvailable = projectsQuery.isLoading || projects.length > 0 || Boolean(selectedProjectTitle)')
    expect(source).toContain('!projectPickerAvailable')
    expect(source).toContain('native chat home can act')
  })

  it('keeps the native project picker scoped to existing project records', () => {
    expect(source).toContain("import { nativeChatProjects } from './native-projects'")
    expect(source).toContain('nativeChatProjects(projectsQuery.data?.projects.map(item => item.record) ?? [])')
  })

  it('uses the blank native chat home as a project picker before a session exists', () => {
    expect(source).toContain("queryKey: ['mission-control-projects-native-chat-home']")
    expect(source).toContain('const projectHomeOptions = useMemo')
    expect(source).toContain('const blankNativeChat = !isRoutedSessionView && !selectedSessionId && !activeSessionId && messages.length === 0')
    expect(source).toContain('const showProjectHomeIntro =')
    expect(source).toContain('projectHomeQuery.isLoading || projectHomeOptions.length > 0 || Boolean(selectedProjectTitle)')
    expect(source).toContain('const showIntro = blankNativeChat && (freshDraftReady || showProjectHomeIntro)')
    expect(source).toContain('onCreateProject: () => setProjectIntakeOpen(true)')
    expect(source).toContain('projectOptions: projectHomeOptions.map(project => ({')
    expect(source).toContain('onSelectProject: onStartProjectChat')
  })

  it('lets the native chat header create a structured Jenny project brief', () => {
    expect(source).toContain("from '@/lib/native-project-intake'")
    expect(source).toContain('function NativeProjectIntakeDialog')
    expect(source).toContain('Create project')
    expect(source).toContain('Name the work, give Jenny the goal, and keep detailed guardrails optional.')
    expect(source).toContain('parseNativeProjectIntake(value)')
    expect(source).toContain('createMissionControlProject(buildNativeProjectCreatePayload(parsed))')
    expect(source).toContain('createMissionControlProjectBrief(')
    expect(source).toContain('buildNativeProjectBriefCreatePayload(parsed, createdProjectId, createdProjectName)')
    expect(source).toContain('Advanced setup')
    expect(source).toContain('Evidence Jenny must return, one per line')
    expect(source).toContain('Approval or stop rules, one per line')
    expect(source).toContain('notifyMissionControlProjectCreated({ projectId: createdProjectId, projectName: createdProjectName })')
    expect(source).toContain('onStartProjectChat(projectId, projectName)')
  })

  it('refreshes native project pickers when any surface creates a project', () => {
    expect(source).toContain('MISSION_CONTROL_PROJECT_CREATED')
    expect(source).toContain('const refetchHeaderProjects = projectsQuery.refetch')
    expect(source).toContain('void refetchHeaderProjects()')
    expect(source).toContain('const refetchProjectHome = projectHomeQuery.refetch')
    expect(source).toContain('void refetchProjectHome()')
    expect(source).toContain('window.addEventListener(MISSION_CONTROL_PROJECT_CREATED')
    expect(source).toContain('window.removeEventListener(MISSION_CONTROL_PROJECT_CREATED')
  })

  it('uses the same clean project chat action for header, home, and newly created projects', () => {
    expect(source).toContain('onStartProjectChat: (projectId: string, projectName: string) => void')
    expect(source).toContain('onStartProjectChat={onStartProjectChat}')
    expect(source).toContain('onSelectProject={onStartProjectChat}')
    expect(source).toContain('onSelectProject: onStartProjectChat')
    expect(source).toContain('onStartProjectChat(projectId, projectName)')
  })

  it('shows Jenny as queued before the first reply update and working after that', () => {
    expect(source).toContain('activeTurnRunning={busy}')
    expect(source).not.toContain('activeTurnRunning={busy && awaitingResponse}')
    expect(source).toContain('awaitingResponse={awaitingResponse}')
    expect(source).toContain("awaitingResponse ? 'Waiting for Jenny' : 'Jenny is working'")
  })

  it('lets native chat failures drive Jenny status before stale background records', () => {
    expect(source).toContain('function latestVisibleAssistantError')
    expect(source).toContain('function latestVisibleAssistantErrorMessage')
    expect(source).toContain('latestChatError: latestVisibleAssistantError(messages)')
    expect(source).toContain("if (message.role === 'user') {")
  })

  it('lets native assistant replies drive Jenny replied status before stale background records', () => {
    expect(source).toContain('function latestVisibleAssistantReply')
    expect(source).toContain('chatMessageText(message).trim().length > 0')
    expect(source).toContain('latestChatReplied: latestVisibleAssistantReply(messages)')
  })

  it('offers retry only for the latest failed native Jenny reply', () => {
    expect(source).toContain('const latestErrorMessage = latestVisibleAssistantErrorMessage(messages)')
    expect(source).toContain('{latestErrorMessage && (')
    expect(source).toContain('onClick={() => onRetry(latestErrorMessage.id)}')
    expect(source).toContain('Retry')
  })

  it('uses the normal thread loading row while a project reply is pending', () => {
    expect(source).toContain('loading={threadLoading}')
    expect(source).toContain(
      "loadingLabel={selectedProjectTitle ? (awaitingResponse ? 'Waiting for Jenny' : 'Jenny is working') : undefined}"
    )
    expect(source).not.toContain('Jenny is working in {selectedProjectTitle}')
  })

  it('keeps the Jenny status strip hidden until a project is selected', () => {
    expect(source).toContain('if (!projectName) {')
    expect(source).toContain('return null')
  })

  it('reads async-agent readiness as hidden status detail without adding an execution control', () => {
    expect(source).toContain('getMissionControlAsyncAgentStatus')
    expect(source).toContain("queryKey: ['mission-control-async-agent-status']")
    expect(source).toContain('function nativeAsyncAgentDetail')
    expect(source).toContain('starts and steering remain approval-gated')
    expect(source).toContain('native async agents are not active yet')
    expect(source).not.toContain('Run async agent')
    expect(source).not.toContain('Start async agent')
  })

  it('keeps detailed Jenny activity behind an in-chat read-only activity panel', () => {
    expect(source).toContain("import { routeSessionId } from '../routes'")
    expect(source).toContain('const sessionSubagents = activeSessionId ? (subagentsBySession[activeSessionId] ?? []) : []')
    expect(source).toContain('const asyncAgentActivityAvailable = Boolean(')
    expect(source).toContain('asyncAgentStatusQuery.data?.async_agent_controls_available')
    expect(source).toContain('asyncAgentStatusQuery.data?.sync_delegate_task_available')
    expect(source).toContain('const showActivity = sessionSubagents.length > 0 || asyncAgentActivityAvailable')
    expect(source).toContain('const [activityOpen, setActivityOpen] = useState(false)')
    expect(source).toContain('onClick={() => setActivityOpen(true)}')
    expect(source).toContain('function NativeJennyActivityDialog')
    expect(source).toContain('Read-only status for {projectName || \'this chat\'}')
    expect(source).toContain('No live subagent activity for this chat yet.')
    expect(source).toContain("runningSubagents > 0 ? `Activity ${runningSubagents}` : 'Activity'")
    expect(source).toContain('className="h-6 shrink-0 px-2 text-[0.6875rem]"')
    expect(source).toContain('className="min-[46rem]:hidden"')
    expect(source).not.toContain('navigate(AGENTS_ROUTE)')
    expect(source).not.toContain('Run async agent')
    expect(source).not.toContain('Start async agent')
    expect(source).not.toContain('className="hidden h-6 shrink-0 px-2 text-[0.6875rem] min-[46rem]:inline-flex"')
  })

  it('shows central Jenny action policy only inside the read-only activity details', () => {
    expect(source).toContain("import { JENNY_ACTION_POLICY_RULES } from '@/lib/jenny-action-policy'")
    expect(source).toContain('Policy guardrails')
    expect(source).toContain('JENNY_ACTION_POLICY_RULES.map(rule => (')
    expect(source).toContain('{rule.decision}')
    expect(source).toContain('{rule.summary}')
    expect(source).toContain('rule.examples.slice(0, 3).join')
    expect(source).not.toContain('setPolicy')
    expect(source).not.toContain('updatePolicy')
  })

  it('lets live subagent activity drive the visible native Jenny status', () => {
    expect(source).toContain('liveSubagentCount: runningSubagents')
    expect(source).toContain('const runningSubagents = activeSubagentCount(subagents)')
    expect(source).toContain('subagents: readonly SubagentProgress[]')
  })
})
