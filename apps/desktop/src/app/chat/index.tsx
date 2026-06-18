import {
  type AppendMessage,
  AssistantRuntimeProvider,
  ExportedMessageRepository,
  type ThreadMessage
} from '@assistant-ui/react'
import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import type * as React from 'react'
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { Thread } from '@/components/assistant-ui/thread'
import { Backdrop } from '@/components/Backdrop'
import { PromptOverlays } from '@/components/prompt-overlays'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  createMissionControlProject,
  createMissionControlProjectBrief,
  getGlobalModelOptions,
  getMissionControlAsyncAgentStatus,
  getMissionControlGitHubBridgeStatus,
  getMissionControlProjects,
  getMissionControlProjectSessions,
  type HermesGateway,
  type MissionControlAsyncAgentStatusResponse,
  type MissionControlProjectRecord,
  type MissionControlProjectSessionGroup
} from '@/hermes'
import { type ChatMessage, chatMessageText } from '@/lib/chat-messages'
import { quickModelOptions, sessionTitle, toRuntimeMessage } from '@/lib/chat-runtime'
import { useIncrementalExternalStoreRuntime } from '@/lib/incremental-external-store-runtime'
import { JENNY_ACTION_POLICY_RULES } from '@/lib/jenny-action-policy'
import {
  JENNY_GOAL_LOOP_BLOCKED_AUDIT,
  JENNY_GOAL_LOOP_CHECKPOINTS,
  JENNY_GOAL_LOOP_COMPLETION_AUDIT,
  JENNY_GOAL_LOOP_PROGRESS_REPORT,
  JENNY_GOAL_LOOP_STOP_RULES
} from '@/lib/jenny-goal-loop'
import {
  MISSION_CONTROL_PROJECT_CREATED,
  MISSION_CONTROL_PROJECT_LINK_CREATED,
  notifyMissionControlProjectCreated
} from '@/lib/mission-control-events'
import {
  buildNativeProjectBriefCreatePayload,
  buildNativeProjectCreatePayload,
  emptyNativeProjectIntake,
  type NativeProjectIntakeValue,
  parseNativeProjectIntake
} from '@/lib/native-project-intake'
import { cn } from '@/lib/utils'
import type { ComposerAttachment } from '@/store/composer'
import { $pinnedSessionIds } from '@/store/layout'
import { notify, notifyError } from '@/store/notifications'
import { $gatewaySwapTarget } from '@/store/profile'
import {
  $activeSessionId,
  $awaitingResponse,
  $busy,
  $contextSuggestions,
  $currentCwd,
  $currentModel,
  $currentProvider,
  $freshDraftReady,
  $gatewayState,
  $introPersonality,
  $introSeed,
  $messages,
  $selectedMissionControlProjectId,
  $selectedMissionControlProjectName,
  $selectedStoredSessionId,
  $sessions,
  sessionPinId,
  setSelectedMissionControlProject
} from '@/store/session'
import { $subagentsBySession, activeSubagentCount, type SubagentProgress } from '@/store/subagents'
import type { ModelOptionsResponse } from '@/types/hermes'

import { routeSessionId } from '../routes'
import { titlebarHeaderBaseClass, titlebarHeaderShadowClass } from '../shell/titlebar'

import { ChatDropOverlay } from './chat-drop-overlay'
import { ChatSwapOverlay } from './chat-swap-overlay'
import { ChatBar, ChatBarFallback } from './composer'
import { requestComposerInsert, requestComposerInsertRefs } from './composer/focus'
import { droppedFileInlineRef, type SessionDragPayload, sessionInlineRef } from './composer/inline-refs'
import type { ChatBarState } from './composer/types'
import type { DroppedFile } from './hooks/use-composer-actions'
import { useFileDropZone } from './hooks/use-file-drop-zone'
import { nativeJennyStatus, type NativeJennyStatusTone } from './native-jenny-status'
import { nativeChatProjects } from './native-projects'
import { SessionActionsMenu } from './sidebar/session-actions-menu'
import { lastVisibleMessageIsUser, threadLoadingState } from './thread-loading'

interface ChatViewProps extends Omit<React.ComponentProps<'div'>, 'onSubmit'> {
  gateway: HermesGateway | null
  onToggleSelectedPin: () => void
  onDeleteSelectedSession: () => void
  onCancel: () => Promise<void> | void
  onAddContextRef: (refText: string, label?: string, detail?: string) => void
  onAddUrl: (url: string) => void
  onBranchInNewChat: (messageId: string) => void
  maxVoiceRecordingSeconds?: number
  onAttachImageBlob: (blob: Blob) => Promise<boolean | void> | boolean | void
  onAttachDroppedItems: (candidates: DroppedFile[]) => Promise<boolean | void> | boolean | void
  onPasteClipboardImage: () => void
  onPickFiles: () => void
  onPickFolders: () => void
  onPickImages: () => void
  onRemoveAttachment: (id: string) => void
  onOpenProjectSession: (sessionId: string, projectId: string, projectName: string) => void
  onSubmit: (
    text: string,
    options?: { attachments?: ComposerAttachment[]; fromQueue?: boolean }
  ) => Promise<boolean> | boolean
  onThreadMessagesChange: (messages: readonly ThreadMessage[]) => void
  onEdit: (message: AppendMessage) => Promise<void>
  onReload: (parentId: string | null) => Promise<void>
  onStartProjectChat: (projectId: string, projectName: string) => void
  onTranscribeAudio?: (audio: Blob) => Promise<string>
}

interface ChatHeaderProps {
  activeSessionId: null | string
  activeTurnRunning: boolean
  awaitingResponse: boolean
  gatewayOpen: boolean
  isRoutedSessionView: boolean
  messages: ChatMessage[]
  onDeleteSelectedSession: () => void
  onStartProjectChat: (projectId: string, projectName: string) => void
  onToggleSelectedPin: () => void
  selectedSessionId: null | string
}

type NativeProjectChatOption = {
  id: string
  lastSessionId: string
  lastSessionTitle: string
  name: string
  sessionCount: number
}

function ChatHeader({
  activeSessionId,
  activeTurnRunning,
  awaitingResponse,
  gatewayOpen,
  isRoutedSessionView,
  messages,
  onDeleteSelectedSession,
  onStartProjectChat,
  onToggleSelectedPin,
  selectedSessionId
}: ChatHeaderProps) {
  const sessions = useStore($sessions)
  const pinnedSessionIds = useStore($pinnedSessionIds)
  const selectedProjectId = useStore($selectedMissionControlProjectId)
  const selectedProjectName = useStore($selectedMissionControlProjectName)
  const subagentsBySession = useStore($subagentsBySession)
  const [activityOpen, setActivityOpen] = useState(false)
  const [projectIntakeOpen, setProjectIntakeOpen] = useState(false)
  const projectsQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjects,
    queryKey: ['mission-control-projects-native-chat'],
    staleTime: 30_000
  })
  const projectSessionsQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjectSessions,
    queryKey: ['mission-control-project-sessions-native-chat'],
    staleTime: 30_000
  })
  const bridgeStatusQuery = useQuery({
    enabled: gatewayOpen && Boolean(selectedProjectId.trim()),
    queryFn: () => getMissionControlGitHubBridgeStatus(selectedProjectId),
    queryKey: ['mission-control-github-bridge-status', selectedProjectId],
    refetchInterval: 3_000,
    staleTime: 10_000
  })
  const asyncAgentStatusQuery = useQuery({
    enabled: gatewayOpen && Boolean(selectedProjectId.trim()),
    queryFn: getMissionControlAsyncAgentStatus,
    queryKey: ['mission-control-async-agent-status'],
    refetchInterval: 60_000,
    staleTime: 60_000
  })
  const refetchHeaderProjects = projectsQuery.refetch
  const refetchHeaderProjectSessions = projectSessionsQuery.refetch

  useEffect(() => {
    const onProjectRecordsChanged = () => {
      void refetchHeaderProjects()
      void refetchHeaderProjectSessions()
    }

    window.addEventListener(MISSION_CONTROL_PROJECT_CREATED, onProjectRecordsChanged)
    window.addEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectRecordsChanged)

    return () => {
      window.removeEventListener(MISSION_CONTROL_PROJECT_CREATED, onProjectRecordsChanged)
      window.removeEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectRecordsChanged)
    }
  }, [refetchHeaderProjectSessions, refetchHeaderProjects])

  const activeStoredSession =
    sessions.find(session => session.id === selectedSessionId || session._lineage_root_id === selectedSessionId) || null

  const selectedProjectTitle = selectedProjectName.trim()
  const projects = useMemo(
    () => projectChatOptions(projectsQuery.data?.projects.map(item => item.record) ?? [], projectSessionsQuery.data?.groups ?? []),
    [projectSessionsQuery.data, projectsQuery.data]
  )
  const projectPickerAvailable = projectsQuery.isLoading || projects.length > 0 || Boolean(selectedProjectTitle)
  const title = activeStoredSession ? sessionTitle(activeStoredSession) : selectedProjectTitle ? 'New project chat' : 'New session'
  const sessionSubagents = activeSessionId ? (subagentsBySession[activeSessionId] ?? []) : []
  const runningSubagents = activeSubagentCount(sessionSubagents)
  const asyncAgentActivityAvailable = Boolean(
    asyncAgentStatusQuery.data?.async_agent_controls_available || asyncAgentStatusQuery.data?.sync_delegate_task_available
  )
  const showActivity = sessionSubagents.length > 0 || asyncAgentActivityAvailable

  // Pins live on the durable lineage-root id, but selectedSessionId is the live
  // (tip) id — resolve through the loaded row so the menu reflects the pin
  // state after auto-compression rotates the id.
  const selectedIsPinned = activeStoredSession
    ? pinnedSessionIds.includes(sessionPinId(activeStoredSession))
    : selectedSessionId
      ? pinnedSessionIds.includes(selectedSessionId)
      : false
  const jennyStatus = nativeJennyStatus({
    activeTurnRunning,
    awaitingResponse,
    bridgeStatus: bridgeStatusQuery.data,
    gatewayOpen,
    latestChatError: latestVisibleAssistantError(messages),
    latestChatReplied: latestVisibleAssistantReply(messages),
    liveSubagentCount: runningSubagents,
    loading: bridgeStatusQuery.isLoading,
    projectId: selectedProjectId,
    queryError: bridgeStatusQuery.error
  })
  const jennyStatusDetail = [jennyStatus.detail, nativeAsyncAgentDetail(asyncAgentStatusQuery.data)]
    .filter(Boolean)
    .join(' ')

  // A brand-new generic session has no session actions yet. Keep the header
  // visible once project records are available so the native chat home can act
  // like a project picker instead of forcing Travis into Mission Control.
  if (!selectedSessionId && !activeSessionId && !isRoutedSessionView && !projectPickerAvailable) {
    return null
  }

  return (
    <header className={cn(titlebarHeaderBaseClass, isRoutedSessionView && titlebarHeaderShadowClass)}>
      <div className="min-w-0 flex-1">
        {selectedSessionId || activeSessionId ? (
          <SessionActionsMenu
            align="start"
            onDelete={selectedSessionId ? onDeleteSelectedSession : undefined}
            onPin={selectedSessionId ? onToggleSelectedPin : undefined}
            pinned={selectedIsPinned}
            sessionId={selectedSessionId || activeSessionId || ''}
            sideOffset={8}
            title={title}
          >
            <Button
              className="pointer-events-auto h-6 min-w-0 gap-1 border border-transparent bg-transparent px-2 py-0 text-(--ui-text-secondary) hover:border-(--ui-stroke-tertiary) hover:bg-(--ui-control-hover-background) hover:text-foreground data-[state=open]:border-(--ui-stroke-tertiary) data-[state=open]:bg-(--ui-control-active-background) [-webkit-app-region:no-drag]"
              type="button"
              variant="ghost"
            >
              <h2 className="max-w-[52vw] truncate text-[0.75rem] font-medium leading-none">{title}</h2>
              <Codicon className="shrink-0 text-(--ui-text-tertiary)" name="chevron-down" size="0.8125rem" />
            </Button>
          </SessionActionsMenu>
        ) : (
          <div className="flex h-6 min-w-0 items-center px-2 [-webkit-app-region:no-drag]">
            <h2 className="max-w-[52vw] truncate text-[0.75rem] font-medium leading-none text-(--ui-text-secondary)">
              {title}
            </h2>
          </div>
        )}
      </div>
      <div className="ml-auto flex min-w-0 max-w-[52vw] items-center gap-1.5 [-webkit-app-region:no-drag]">
        <ProjectHeaderSelect
          loading={projectsQuery.isLoading || projectSessionsQuery.isLoading}
          onClearProject={() => setSelectedMissionControlProject(null)}
          onNewProject={() => setProjectIntakeOpen(true)}
          onSelectProject={onStartProjectChat}
          projects={projects}
          selectedProjectId={selectedProjectId}
          selectedProjectTitle={selectedProjectTitle}
        />
        <HeaderPill
          className="hidden min-[46rem]:inline-flex"
          label={jennyStatus.label}
          title={jennyStatusDetail}
          tone={jennyStatus.tone}
        />
        {showActivity && (
          <Button
            className="h-6 shrink-0 px-2 text-[0.6875rem]"
            onClick={() => setActivityOpen(true)}
            title="Open Jenny activity"
            type="button"
            variant="outline"
          >
            <span className="hidden min-[46rem]:inline">
              {runningSubagents > 0 ? `Activity ${runningSubagents}` : 'Activity'}
            </span>
            <span className="min-[46rem]:hidden">{runningSubagents > 0 ? runningSubagents : 'Activity'}</span>
          </Button>
        )}
      </div>
      <NativeJennyActivityDialog
        asyncStatus={asyncAgentStatusQuery.data}
        onOpenChange={setActivityOpen}
        open={activityOpen}
        projectName={selectedProjectTitle}
        subagents={sessionSubagents}
      />
      <NativeProjectIntakeDialog
        onCreated={(projectId, projectName) => {
          onStartProjectChat(projectId, projectName)
          void projectsQuery.refetch()
        }}
        onOpenChange={setProjectIntakeOpen}
        open={projectIntakeOpen}
      />
    </header>
  )
}

function NativeJennyActivityDialog({
  asyncStatus,
  onOpenChange,
  open,
  projectName,
  subagents
}: {
  asyncStatus?: MissionControlAsyncAgentStatusResponse | null
  onOpenChange: (open: boolean) => void
  open: boolean
  projectName: string
  subagents: readonly SubagentProgress[]
}) {
  const running = activeSubagentCount(subagents)
  const rows = subagents.slice(-8).reverse()
  const readiness = nativeAsyncAgentDetail(asyncStatus) || 'Checking Jenny activity support.'
  const flags = [
    ['Execution', asyncStatus?.execution_enabled === true ? 'on' : 'off'],
    ['Dispatch', asyncStatus?.dispatch_enabled === true ? 'on' : 'off'],
    ['Worker', asyncStatus?.worker_enabled === true ? 'on' : 'off'],
    ['Timer', asyncStatus?.timer_enabled === true ? 'on' : 'off']
  ]

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-xl gap-4">
        <DialogHeader>
          <DialogTitle>Jenny activity</DialogTitle>
          <DialogDescription>
            Read-only status for {projectName || 'this chat'}. Jenny starts, steering, and approvals remain guarded.
          </DialogDescription>
        </DialogHeader>
        <section className="grid gap-3 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background)/40 p-3">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">{running > 0 ? `Jenny working (${running})` : 'No active Jenny work'}</p>
              <p className="mt-1 text-xs leading-relaxed text-(--ui-text-secondary)">{readiness}</p>
            </div>
            <span className="shrink-0 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2 py-1 text-[0.6875rem] font-medium text-emerald-100">
              read-only
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {flags.map(([label, value]) => (
              <div className="rounded border border-(--ui-stroke-tertiary) bg-background/35 px-2 py-1.5" key={label}>
                <p className="text-[0.62rem] font-medium uppercase tracking-wider text-(--ui-text-tertiary)">{label}</p>
                <p className="mt-0.5 text-xs font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </div>
        </section>
        <details className="rounded-md border border-(--ui-stroke-tertiary) bg-background/30 p-3 text-sm">
          <summary className="cursor-pointer font-medium text-(--ui-text-secondary)">Policy guardrails</summary>
          <div className="mt-3 grid gap-2">
            {JENNY_ACTION_POLICY_RULES.map(rule => (
              <div className="rounded border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background)/35 p-2" key={rule.decision}>
                <div className="flex min-w-0 items-center gap-2">
                  <span className="shrink-0 rounded-full border border-(--ui-stroke-tertiary) px-2 py-0.5 text-[0.6875rem] font-semibold">
                    {rule.decision}
                  </span>
                  <span className="min-w-0 text-xs font-medium text-foreground">{rule.summary}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-(--ui-text-tertiary)">
                  {rule.examples.slice(0, 3).join('; ')}
                </p>
              </div>
            ))}
          </div>
        </details>
        <details className="rounded-md border border-(--ui-stroke-tertiary) bg-background/30 p-3 text-sm">
          <summary className="cursor-pointer font-medium text-(--ui-text-secondary)">Goal loop</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {[
              ['Checkpoints', JENNY_GOAL_LOOP_CHECKPOINTS],
              ['Progress reports', JENNY_GOAL_LOOP_PROGRESS_REPORT],
              ['Completion audit', JENNY_GOAL_LOOP_COMPLETION_AUDIT],
              ['Blocked audit', JENNY_GOAL_LOOP_BLOCKED_AUDIT],
              ['Stop rules', JENNY_GOAL_LOOP_STOP_RULES]
            ].map(([label, items]) => (
              <div className="rounded border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background)/35 p-2" key={label as string}>
                <p className="text-xs font-semibold text-foreground">{label as string}</p>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-relaxed text-(--ui-text-tertiary)">
                  {(items as readonly string[]).slice(0, 3).map(item => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </details>
        <section className="grid max-h-[45vh] gap-2 overflow-y-auto pr-1">
          {rows.length ? (
            rows.map(item => <NativeJennyActivityRow item={item} key={item.id} />)
          ) : (
            <div className="rounded-md border border-dashed border-(--ui-stroke-tertiary) p-4 text-sm text-(--ui-text-secondary)">
              No live subagent activity for this chat yet.
            </div>
          )}
        </section>
      </DialogContent>
    </Dialog>
  )
}

function NativeJennyActivityRow({ item }: { item: SubagentProgress }) {
  const latestStream = item.stream[item.stream.length - 1]
  const detail = item.currentTool || item.summary || latestStream?.text || ''
  const statusClass =
    item.status === 'failed' || item.status === 'interrupted'
      ? 'text-red-200'
      : item.status === 'completed'
        ? 'text-emerald-100'
        : 'text-blue-100'

  return (
    <article className="rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background)/35 p-3">
      <div className="flex min-w-0 items-center gap-2">
        <span className={cn('shrink-0 text-xs font-semibold capitalize', statusClass)}>{item.status}</span>
        <span className="min-w-0 truncate text-sm font-medium text-foreground" title={item.goal}>
          {item.goal}
        </span>
      </div>
      {detail && (
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-(--ui-text-secondary)" title={detail}>
          {detail}
        </p>
      )}
      <div className="mt-2 flex flex-wrap gap-2 text-[0.6875rem] text-(--ui-text-tertiary)">
        <span>step {Math.max(1, item.taskIndex + 1)} of {Math.max(1, item.taskCount)}</span>
        {item.toolCount ? <span>{item.toolCount} tools</span> : null}
        {item.filesWritten.length ? <span>{item.filesWritten.length} files changed</span> : null}
      </div>
    </article>
  )
}

function nativeAsyncAgentDetail(status?: MissionControlAsyncAgentStatusResponse | null): string {
  if (!status) {
    return ''
  }

  if (status.async_agent_controls_available) {
    return 'Async agent controls are available but starts and steering remain approval-gated.'
  }

  if (status.sync_delegate_task_available) {
    return 'Current runtime has synchronous delegation; native async agents are not active yet.'
  }

  return 'Native async agent capability has not been detected in this runtime.'
}

function latestVisibleAssistantError(messages: readonly ChatMessage[]): string {
  return latestVisibleAssistantErrorMessage(messages)?.error ?? ''
}

function latestVisibleAssistantReply(messages: readonly ChatMessage[]): boolean {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]

    if (message.hidden) {
      continue
    }

    if (message.role === 'user') {
      return false
    }

    if (message.role === 'assistant') {
      return !message.error && chatMessageText(message).trim().length > 0
    }
  }

  return false
}

function latestVisibleAssistantErrorMessage(messages: readonly ChatMessage[]): ChatMessage | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]

    if (message.hidden) {
      continue
    }

    if (message.role === 'user') {
      return null
    }

    if (message.role === 'assistant' && typeof message.error === 'string' && message.error.trim()) {
      return message
    }
  }

  return null
}

function latestProjectSession(group?: MissionControlProjectSessionGroup): MissionControlProjectSessionGroup['sessions'][number] | null {
  return (group?.sessions ?? []).reduce<MissionControlProjectSessionGroup['sessions'][number] | null>(
    (latest, session) => {
      const sessionTs = session.last_active || session.started_at || 0
      const latestTs = latest?.last_active || latest?.started_at || 0

      return sessionTs > latestTs ? session : latest
    },
    null
  )
}

function latestProjectSessionTitle(group?: MissionControlProjectSessionGroup): string {
  const latestSession = latestProjectSession(group)

  return latestSession?.title?.trim() || latestSession?.preview?.trim() || ''
}

function projectChatOptions(
  projects: MissionControlProjectRecord[] = [],
  groups: MissionControlProjectSessionGroup[] = []
): NativeProjectChatOption[] {
  const sessionGroupsByProject = new Map(groups.map(group => [group.project_id, group]))

  return nativeChatProjects(projects).map(project => {
    const sessionGroup = sessionGroupsByProject.get(project.project_id)
    const sessionCount = sessionGroup?.linked_session_count ?? sessionGroup?.sessions.length ?? 0
    const latestSession = latestProjectSession(sessionGroup)

    return {
      id: project.project_id,
      lastSessionId: latestSession?.session_id?.trim() || '',
      lastSessionTitle: latestProjectSessionTitle(sessionGroup),
      name: project.name,
      sessionCount
    }
  })
}

function ProjectHeaderSelect({
  loading,
  onClearProject,
  onNewProject,
  onSelectProject,
  projects,
  selectedProjectId,
  selectedProjectTitle
}: {
  loading: boolean
  onClearProject: () => void
  onNewProject: () => void
  onSelectProject: (projectId: string, projectName: string) => void
  projects: NativeProjectChatOption[]
  selectedProjectId: string
  selectedProjectTitle: string
}) {
  if (!projects.length && !selectedProjectTitle && !loading) {
    return null
  }

  const value = selectedProjectId.trim()
  const selectedProjectKnown = projects.some(project => project.id === value)
  const showSelectedProjectFallback = Boolean(value && selectedProjectTitle && !selectedProjectKnown)

  return (
    <div className="flex min-w-0 items-center gap-1">
      <label className="flex min-w-0 items-center gap-1 text-[0.6875rem] text-(--ui-text-tertiary)" title="Project">
        <span className="sr-only">Project</span>
        <select
          aria-label="Project"
          className="h-6 min-w-0 max-w-[38vw] rounded-full border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) px-2 py-0 text-[0.6875rem] font-medium text-(--ui-text-secondary) outline-none hover:text-foreground focus:border-blue-400/60 min-[46rem]:max-w-56"
          disabled={loading && !projects.length}
          onChange={event => {
            const nextValue = event.currentTarget.value

            if (!nextValue) {
              onClearProject()
              return
            }

            const project = projects.find(item => item.id === nextValue)
            if (project) {
              onSelectProject(project.id, project.name)
            }
          }}
          value={selectedProjectKnown || showSelectedProjectFallback ? value : ''}
        >
          <option value="">{loading ? 'Loading projects...' : 'Other chats'}</option>
          {showSelectedProjectFallback && <option value={value}>{selectedProjectTitle}</option>}
          {projects.map(project => (
            <option key={project.id} value={project.id}>
              {project.name}
              {project.sessionCount > 0 ? ` (${project.sessionCount})` : ''}
            </option>
          ))}
        </select>
      </label>
      <Button
        aria-label="Create project"
        className="size-6 rounded-full border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) text-(--ui-text-secondary) hover:text-foreground [&_svg]:size-3.5!"
        onClick={onNewProject}
        title="Create project"
        type="button"
        variant="ghost"
      >
        <Codicon name="add" size="0.875rem" />
      </Button>
    </div>
  )
}

function NativeProjectIntakeDialog({
  onCreated,
  onOpenChange,
  open
}: {
  onCreated: (projectId: string, projectName: string) => void
  onOpenChange: (open: boolean) => void
  open: boolean
}) {
  const [value, setValue] = useState<NativeProjectIntakeValue>(emptyNativeProjectIntake)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const update = (key: keyof NativeProjectIntakeValue) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setValue(current => ({ ...current, [key]: event.currentTarget.value }))

  const submit = async () => {
    const parsed = parseNativeProjectIntake(value)

    if (!parsed.name || !parsed.goal) {
      setError('Project name and goal are required.')

      return
    }

    setSaving(true)
    setError('')

    try {
      const project = await createMissionControlProject(buildNativeProjectCreatePayload(parsed))
      const createdProjectId = project.project.project_id || parsed.projectId
      const createdProjectName = project.project.name || parsed.name

      await createMissionControlProjectBrief(
        buildNativeProjectBriefCreatePayload(parsed, createdProjectId, createdProjectName)
      )

      notifyMissionControlProjectCreated({ projectId: createdProjectId, projectName: createdProjectName })
      onCreated(createdProjectId, createdProjectName)
      notify({ durationMs: 2_000, kind: 'success', message: `Created ${createdProjectName}` })
      setValue(emptyNativeProjectIntake())
      onOpenChange(false)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message)
      notifyError(err, 'Could not create project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create project</DialogTitle>
          <DialogDescription>
            Name the work, give Jenny the goal, and keep detailed guardrails optional.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-2"
          onSubmit={event => {
            event.preventDefault()
            void submit()
          }}
        >
          <Input disabled={saving} onChange={update('name')} placeholder="Project name" value={value.name} />
          <textarea
            className="min-h-20 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
            disabled={saving}
            onChange={update('goal')}
            placeholder="What should Jenny help you accomplish?"
            value={value.goal}
          />
          <Input
            disabled={saving}
            onChange={update('source')}
            placeholder="Source of truth, repo, folder, or notes"
            value={value.source}
          />
          <textarea
            className="min-h-16 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
            disabled={saving}
            onChange={update('success')}
            placeholder="Wins / success criteria, one per line"
            value={value.success}
          />
          <details className="grid gap-2 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background)/40 p-2 text-sm">
            <summary className="cursor-pointer text-(--ui-text-secondary)">Advanced setup</summary>
            <div className="mt-2 grid gap-2">
              <textarea
                className="min-h-16 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
                disabled={saving}
                onChange={update('evidence')}
                placeholder="Evidence Jenny must return, one per line"
                value={value.evidence}
              />
              <textarea
                className="min-h-16 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
                disabled={saving}
                onChange={update('approval')}
                placeholder="Approval or stop rules, one per line"
                value={value.approval}
              />
              <textarea
                className="min-h-16 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
                disabled={saving}
                onChange={update('forbidden')}
                placeholder="Forbidden actions or risks, one per line"
                value={value.forbidden}
              />
            </div>
          </details>
          {error && <div className="text-sm text-red-300">{error}</div>}
          <DialogFooter>
            <Button disabled={saving} onClick={() => onOpenChange(false)} type="button" variant="ghost">
              Cancel
            </Button>
            <Button disabled={saving} type="submit">
              {saving ? 'Creating...' : 'Create project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function HeaderPill({
  className,
  label,
  title,
  tone
}: {
  className?: string
  label: string
  title: string
  tone: NativeJennyStatusTone
}) {
  const toneClass =
    tone === 'warn'
      ? 'border-red-500/35 bg-red-500/10 text-red-200'
      : tone === 'pending'
        ? 'border-amber-500/35 bg-amber-500/10 text-amber-100'
        : tone === 'working'
          ? 'border-blue-400/35 bg-blue-400/10 text-blue-100'
          : tone === 'ok'
            ? 'border-emerald-400/35 bg-emerald-400/10 text-emerald-100'
            : 'border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) text-(--ui-text-secondary)'

  return (
    <span
      className={cn(
        'max-w-56 truncate rounded-full border px-2 py-0.5 text-[0.6875rem] font-medium leading-none',
        toneClass,
        className
      )}
      title={title}
    >
      {label}
    </span>
  )
}

function ProjectJennyStatusStrip({
  activeTurnRunning,
  awaitingResponse,
  gatewayOpen,
  messages,
  onRetry,
  subagents
}: {
  activeTurnRunning: boolean
  awaitingResponse: boolean
  gatewayOpen: boolean
  messages: ChatMessage[]
  onRetry: (messageId: string) => void
  subagents: readonly SubagentProgress[]
}) {
  const selectedProjectId = useStore($selectedMissionControlProjectId)
  const selectedProjectName = useStore($selectedMissionControlProjectName)
  const projectName = selectedProjectName.trim()
  const bridgeStatusQuery = useQuery({
    enabled: gatewayOpen && Boolean(selectedProjectId.trim()),
    queryFn: () => getMissionControlGitHubBridgeStatus(selectedProjectId),
    queryKey: ['mission-control-github-bridge-status', selectedProjectId],
    refetchInterval: 3_000,
    staleTime: 10_000
  })

  if (!projectName) {
    return null
  }

  const latestChatReplied = latestVisibleAssistantReply(messages)
  const runningSubagents = activeSubagentCount(subagents)
  const jennyStatus = nativeJennyStatus({
    activeTurnRunning,
    awaitingResponse,
    bridgeStatus: bridgeStatusQuery.data,
    gatewayOpen,
    latestChatError: latestVisibleAssistantError(messages),
    latestChatReplied,
    liveSubagentCount: runningSubagents,
    loading: bridgeStatusQuery.isLoading,
    projectId: selectedProjectId,
    queryError: bridgeStatusQuery.error
  })
  const latestErrorMessage = latestVisibleAssistantErrorMessage(messages)
  const visibleStatusTones = new Set<NativeJennyStatusTone>([
    'pending',
    'working',
    'warn',
    ...(latestChatReplied ? (['ok'] as const) : [])
  ])

  if (!visibleStatusTones.has(jennyStatus.tone)) {
    return null
  }

  const summaryClass =
    jennyStatus.tone === 'warn'
      ? 'text-red-200'
      : jennyStatus.tone === 'pending'
        ? 'text-amber-100'
        : 'text-blue-100'

  return (
    <div
      aria-label="Project chat status"
      aria-live="polite"
      className="relative z-10 flex min-h-8 shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background)/95 px-4 text-[0.75rem] text-(--ui-text-secondary)"
      role="status"
    >
      <span className="shrink-0 font-medium text-foreground">Jenny</span>
      <span className={cn('min-w-0 truncate font-medium', summaryClass)} title={jennyStatus.detail}>
        {jennyStatus.summary}
      </span>
      <span className="hidden min-w-0 truncate text-(--ui-text-tertiary) min-[42rem]:inline" title={projectName}>
        in {projectName}
      </span>
      <span className="ml-auto hidden shrink-0 text-(--ui-text-tertiary) min-[52rem]:inline" title={jennyStatus.detail}>
        {jennyStatus.label}
      </span>
      {latestErrorMessage && (
        <Button
          className="ml-auto h-6 shrink-0 px-2 text-[0.6875rem] min-[52rem]:ml-0"
          onClick={() => onRetry(latestErrorMessage.id)}
          size="sm"
          type="button"
          variant="outline"
        >
          Retry
        </Button>
      )}
    </div>
  )
}

export function ChatView({
  className,
  gateway,
  onToggleSelectedPin,
  onDeleteSelectedSession,
  onCancel,
  onAddContextRef,
  onAddUrl,
  onAttachImageBlob,
  onAttachDroppedItems,
  onBranchInNewChat,
  maxVoiceRecordingSeconds,
  onPasteClipboardImage,
  onPickFiles,
  onPickFolders,
  onPickImages,
  onRemoveAttachment,
  onOpenProjectSession,
  onSubmit,
  onThreadMessagesChange,
  onEdit,
  onReload,
  onStartProjectChat,
  onTranscribeAudio
}: ChatViewProps) {
  const location = useLocation()
  const activeSessionId = useStore($activeSessionId)
  const awaitingResponse = useStore($awaitingResponse)
  const busy = useStore($busy)
  const contextSuggestions = useStore($contextSuggestions)
  const currentCwd = useStore($currentCwd)
  const currentModel = useStore($currentModel)
  const currentProvider = useStore($currentProvider)
  const freshDraftReady = useStore($freshDraftReady)
  const gatewayState = useStore($gatewayState)
  const gatewaySwapTarget = useStore($gatewaySwapTarget)
  const gatewayOpen = gatewayState === 'open'
  const introPersonality = useStore($introPersonality)
  const introSeed = useStore($introSeed)
  const messages = useStore($messages)
  const selectedProjectName = useStore($selectedMissionControlProjectName)
  const selectedSessionId = useStore($selectedStoredSessionId)
  const subagentsBySession = useStore($subagentsBySession)
  const [projectIntakeOpen, setProjectIntakeOpen] = useState(false)
  const selectedProjectTitle = selectedProjectName.trim()
  const runtimeMessageCacheRef = useRef(new WeakMap<ChatMessage, ThreadMessage>())
  const isRoutedSessionView = Boolean(routeSessionId(location.pathname))
  const projectHomeQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjects,
    queryKey: ['mission-control-projects-native-chat-home'],
    staleTime: 30_000
  })
  const projectHomeSessionsQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjectSessions,
    queryKey: ['mission-control-project-sessions-native-chat-home'],
    staleTime: 30_000
  })
  const refetchProjectHome = projectHomeQuery.refetch
  const refetchProjectHomeSessions = projectHomeSessionsQuery.refetch
  useEffect(() => {
    const onProjectRecordsChanged = () => {
      void refetchProjectHome()
      void refetchProjectHomeSessions()
    }

    window.addEventListener(MISSION_CONTROL_PROJECT_CREATED, onProjectRecordsChanged)
    window.addEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectRecordsChanged)

    return () => {
      window.removeEventListener(MISSION_CONTROL_PROJECT_CREATED, onProjectRecordsChanged)
      window.removeEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectRecordsChanged)
    }
  }, [refetchProjectHome, refetchProjectHomeSessions])
  const projectHomeOptions = useMemo(
    () => projectChatOptions(projectHomeQuery.data?.projects.map(item => item.record) ?? [], projectHomeSessionsQuery.data?.groups ?? []),
    [projectHomeQuery.data, projectHomeSessionsQuery.data]
  )

  const blankNativeChat = !isRoutedSessionView && !selectedSessionId && !activeSessionId && messages.length === 0
  const showProjectHomeIntro =
    blankNativeChat &&
    (projectHomeQuery.isLoading || projectHomeSessionsQuery.isLoading || projectHomeOptions.length > 0 || Boolean(selectedProjectTitle))
  const showIntro = blankNativeChat && (freshDraftReady || showProjectHomeIntro)

  // Session is still loading if the route references a session we haven't
  // resumed yet. Once `activeSessionId` is set (runtime has resumed), the
  // session exists — even if it has zero messages (a brand-new routed
  // session). The flicker where `busy` flips true briefly during hydrate
  // is handled by `threadLoadingState`'s last-visible-user gate.
  const loadingSession = isRoutedSessionView && messages.length === 0 && !activeSessionId
  const threadLoading = threadLoadingState(loadingSession, busy, awaitingResponse, lastVisibleMessageIsUser(messages))
  const showChatBar = !loadingSession
  const threadKey = selectedSessionId || activeSessionId || (isRoutedSessionView ? location.pathname : 'new')

  const modelOptionsQuery = useQuery<ModelOptionsResponse>({
    queryKey: ['model-options', activeSessionId || 'global'],
    queryFn: () => {
      if (!activeSessionId) {
        return getGlobalModelOptions()
      }

      if (!gateway) {
        throw new Error('Hermes gateway unavailable')
      }

      return gateway.request<ModelOptionsResponse>('model.options', { session_id: activeSessionId })
    },
    enabled: gatewayOpen
  })

  const quickModels = useMemo(
    () => quickModelOptions(modelOptionsQuery.data, currentProvider, currentModel),
    [currentModel, currentProvider, modelOptionsQuery.data]
  )

  const chatBarState = useMemo<ChatBarState>(
    () => ({
      model: {
        model: currentModel,
        provider: currentProvider,
        canSwitch: gatewayOpen,
        loading: !gatewayOpen || (!currentModel && !currentProvider),
        quickModels
      },
      tools: {
        enabled: true,
        label: 'Add context',
        suggestions: contextSuggestions
      },
      voice: {
        enabled: true,
        active: false
      }
    }),
    [contextSuggestions, currentModel, currentProvider, gatewayOpen, quickModels]
  )

  const runtimeMessageRepository = useMemo(() => {
    const items: { message: ThreadMessage; parentId: string | null }[] = []
    const branchParentByGroup = new Map<string, string | null>()
    let visibleParentId: string | null = null
    let headId: string | null = null

    for (const message of messages) {
      let parentId = visibleParentId

      if (message.role === 'assistant' && message.branchGroupId) {
        if (!branchParentByGroup.has(message.branchGroupId)) {
          branchParentByGroup.set(message.branchGroupId, visibleParentId)
        }

        parentId = branchParentByGroup.get(message.branchGroupId) ?? null
      }

      const cachedMessage = runtimeMessageCacheRef.current.get(message)
      const runtimeMessage = cachedMessage ?? toRuntimeMessage(message)

      if (!cachedMessage) {
        runtimeMessageCacheRef.current.set(message, runtimeMessage)
      }

      items.push({ message: runtimeMessage, parentId })

      if (!message.hidden) {
        visibleParentId = message.id
        headId = message.id
      }
    }

    return ExportedMessageRepository.fromBranchableArray(items, { headId })
  }, [messages])

  const runtime = useIncrementalExternalStoreRuntime<ThreadMessage>({
    messageRepository: runtimeMessageRepository,
    isRunning: busy,
    setMessages: onThreadMessagesChange,
    onNew: async () => {
      // Submission is handled explicitly by ChatBar.
      // Keeping this no-op avoids duplicate prompt.submit calls.
    },
    onEdit,
    onCancel: async () => onCancel(),
    onReload
  })

  // Drop files anywhere in the conversation area, not just on the composer
  // input — appending the same inline `@file:` ref chips the composer drop
  // produces (vs. attachment cards) so both surfaces behave identically.
  const onDropFiles = useCallback(
    (candidates: DroppedFile[]) => {
      const refs = candidates
        .map(candidate => droppedFileInlineRef(candidate, currentCwd))
        .filter((ref): ref is string => Boolean(ref))

      if (refs.length) {
        requestComposerInsert(refs.join(' '), { mode: 'inline', target: 'main' })
      }
    },
    [currentCwd]
  )

  // Dropping a sidebar session inserts an @session link the agent can resolve
  // via session_search (carries the source profile, so cross-profile works).
  const onDropSession = useCallback((session: SessionDragPayload) => {
    requestComposerInsertRefs([sessionInlineRef(session)], { target: 'main' })
  }, [])

  const { dragKind, dropHandlers } = useFileDropZone({ enabled: showChatBar, onDropFiles, onDropSession })

  return (
    <div
      className={cn(
        'relative isolate flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)',
        className
      )}
    >
      <Backdrop />
      <ChatHeader
        activeSessionId={activeSessionId}
        activeTurnRunning={busy}
        awaitingResponse={awaitingResponse}
        gatewayOpen={gatewayOpen}
        isRoutedSessionView={isRoutedSessionView}
        messages={messages}
        onDeleteSelectedSession={onDeleteSelectedSession}
        onStartProjectChat={onStartProjectChat}
        onToggleSelectedPin={onToggleSelectedPin}
        selectedSessionId={selectedSessionId}
      />
      <ProjectJennyStatusStrip
        activeTurnRunning={busy}
        awaitingResponse={awaitingResponse}
        gatewayOpen={gatewayOpen}
        messages={messages}
        onRetry={messageId => void onReload(messageId)}
        subagents={activeSessionId ? (subagentsBySession[activeSessionId] ?? []) : []}
      />

      <PromptOverlays />

      <div
        className="relative min-h-0 max-w-full flex-1 overflow-hidden bg-(--ui-chat-surface-background) contain-[layout_paint]"
        {...dropHandlers}
      >
        <AssistantRuntimeProvider runtime={runtime}>
          <Thread
            clampToComposer={showChatBar}
            cwd={currentCwd}
            gateway={gateway}
            intro={
              showIntro
                ? {
                    onCreateProject: () => setProjectIntakeOpen(true),
                    onResumeProjectSession: onOpenProjectSession,
                    onSelectProject: onStartProjectChat,
                    personality: introPersonality,
                    projectName: selectedProjectName.trim(),
                    projectOptions: projectHomeOptions,
                    projectsLoading: projectHomeQuery.isLoading || projectHomeSessionsQuery.isLoading,
                    seed: introSeed
                  }
                : undefined
            }
            loading={threadLoading}
            loadingLabel={selectedProjectTitle ? (awaitingResponse ? 'Waiting for Jenny' : 'Jenny is working') : undefined}
            onBranchInNewChat={onBranchInNewChat}
            onCancel={onCancel}
            sessionId={activeSessionId}
            sessionKey={threadKey}
          />
          {showChatBar && (
            <Suspense fallback={<ChatBarFallback />}>
              <ChatBar
                busy={busy}
                cwd={currentCwd}
                disabled={!gatewayOpen}
                disabledPlaceholderOverride={
                  selectedProjectTitle ? `Jenny is offline; reconnect gateway to message ${selectedProjectTitle}` : undefined
                }
                focusKey={activeSessionId}
                gateway={gateway}
                maxRecordingSeconds={maxVoiceRecordingSeconds}
                onAddContextRef={onAddContextRef}
                onAddUrl={onAddUrl}
                onAttachDroppedItems={onAttachDroppedItems}
                onAttachImageBlob={onAttachImageBlob}
                onCancel={onCancel}
                onPasteClipboardImage={onPasteClipboardImage}
                onPickFiles={onPickFiles}
                onPickFolders={onPickFolders}
                onPickImages={onPickImages}
                onRemoveAttachment={onRemoveAttachment}
                onSubmit={onSubmit}
                onTranscribeAudio={onTranscribeAudio}
                placeholderOverride={
                  selectedProjectTitle ? `Message Jenny in ${selectedProjectTitle}; she replies here` : undefined
                }
                queueSessionKey={selectedSessionId || activeSessionId}
                sessionId={activeSessionId}
                state={chatBarState}
              />
            </Suspense>
          )}
        </AssistantRuntimeProvider>
        <NativeProjectIntakeDialog
          onCreated={(projectId, projectName) => {
            onStartProjectChat(projectId, projectName)
            void projectHomeQuery.refetch()
            void projectHomeSessionsQuery.refetch()
          }}
          onOpenChange={setProjectIntakeOpen}
          open={projectIntakeOpen}
        />
        <ChatDropOverlay kind={dragKind} />
        <ChatSwapOverlay profile={gatewaySwapTarget} />
      </div>
    </div>
  )
}
