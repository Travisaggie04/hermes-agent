import {
  type AppendMessage,
  AssistantRuntimeProvider,
  ExportedMessageRepository,
  type ThreadMessage
} from '@assistant-ui/react'
import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import type * as React from 'react'
import { Suspense, useCallback, useMemo, useRef, useState } from 'react'
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
  getMissionControlGitHubBridgeStatus,
  getMissionControlProjects,
  type HermesGateway,
  type MissionControlProjectRecord
} from '@/hermes'
import type { ChatMessage } from '@/lib/chat-messages'
import { quickModelOptions, sessionTitle, toRuntimeMessage } from '@/lib/chat-runtime'
import { useIncrementalExternalStoreRuntime } from '@/lib/incremental-external-store-runtime'
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
  onSubmit: (
    text: string,
    options?: { attachments?: ComposerAttachment[]; fromQueue?: boolean }
  ) => Promise<boolean> | boolean
  onThreadMessagesChange: (messages: readonly ThreadMessage[]) => void
  onEdit: (message: AppendMessage) => Promise<void>
  onReload: (parentId: string | null) => Promise<void>
  onTranscribeAudio?: (audio: Blob) => Promise<string>
}

interface ChatHeaderProps {
  activeSessionId: null | string
  activeTurnRunning: boolean
  gatewayOpen: boolean
  isRoutedSessionView: boolean
  onDeleteSelectedSession: () => void
  onToggleSelectedPin: () => void
  selectedSessionId: null | string
}

function ChatHeader({
  activeSessionId,
  activeTurnRunning,
  gatewayOpen,
  isRoutedSessionView,
  onDeleteSelectedSession,
  onToggleSelectedPin,
  selectedSessionId
}: ChatHeaderProps) {
  const sessions = useStore($sessions)
  const pinnedSessionIds = useStore($pinnedSessionIds)
  const selectedProjectId = useStore($selectedMissionControlProjectId)
  const selectedProjectName = useStore($selectedMissionControlProjectName)
  const [projectIntakeOpen, setProjectIntakeOpen] = useState(false)
  const projectsQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjects,
    queryKey: ['mission-control-projects-native-chat'],
    staleTime: 30_000
  })
  const bridgeStatusQuery = useQuery({
    enabled: gatewayOpen && Boolean(selectedProjectId.trim()),
    queryFn: getMissionControlGitHubBridgeStatus,
    queryKey: ['mission-control-github-bridge-status', selectedProjectId],
    refetchInterval: 3_000,
    staleTime: 10_000
  })

  const activeStoredSession =
    sessions.find(session => session.id === selectedSessionId || session._lineage_root_id === selectedSessionId) || null

  const selectedProjectTitle = selectedProjectName.trim()
  const projects = useMemo(() => nativeChatProjects(projectsQuery.data?.projects.map(item => item.record) ?? []), [projectsQuery.data])
  const projectPickerAvailable = projectsQuery.isLoading || projects.length > 0 || Boolean(selectedProjectTitle)
  const title = activeStoredSession ? sessionTitle(activeStoredSession) : selectedProjectTitle ? 'New project chat' : 'New session'

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
    bridgeStatus: bridgeStatusQuery.data,
    gatewayOpen,
    loading: bridgeStatusQuery.isLoading,
    projectId: selectedProjectId,
    queryError: bridgeStatusQuery.error
  })

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
      <div className="ml-auto hidden min-w-0 max-w-[44vw] items-center gap-1.5 [-webkit-app-region:no-drag] min-[46rem]:flex">
        <ProjectHeaderSelect
          loading={projectsQuery.isLoading}
          onNewProject={() => setProjectIntakeOpen(true)}
          projects={projects}
          selectedProjectId={selectedProjectId}
          selectedProjectTitle={selectedProjectTitle}
        />
        <HeaderPill label={jennyStatus.label} title={jennyStatus.detail} tone={jennyStatus.tone} />
      </div>
      <NativeProjectIntakeDialog
        onCreated={(projectId, projectName) => {
          setSelectedMissionControlProject(projectId, projectName)
          void projectsQuery.refetch()
        }}
        onOpenChange={setProjectIntakeOpen}
        open={projectIntakeOpen}
      />
    </header>
  )
}

function ProjectHeaderSelect({
  loading,
  onNewProject,
  projects,
  selectedProjectId,
  selectedProjectTitle
}: {
  loading: boolean
  onNewProject: () => void
  projects: MissionControlProjectRecord[]
  selectedProjectId: string
  selectedProjectTitle: string
}) {
  if (!projects.length && !selectedProjectTitle && !loading) {
    return null
  }

  const value = selectedProjectId.trim()

  return (
    <div className="flex min-w-0 items-center gap-1">
      <label className="flex min-w-0 items-center gap-1 text-[0.6875rem] text-(--ui-text-tertiary)" title="Jenny project">
        <span className="sr-only">Jenny project</span>
        <select
          aria-label="Jenny project"
          className="h-6 max-w-56 rounded-full border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) px-2 py-0 text-[0.6875rem] font-medium text-(--ui-text-secondary) outline-none hover:text-foreground focus:border-blue-400/60"
          disabled={loading && !projects.length}
          onChange={event => {
            const project = projects.find(item => item.project_id === event.currentTarget.value)
            setSelectedMissionControlProject(project?.project_id ?? null, project?.name ?? null)
          }}
          value={projects.some(project => project.project_id === value) ? value : ''}
        >
          <option value="">{loading ? 'Loading projects...' : 'Pick project'}</option>
          {projects.map(project => (
            <option key={project.project_id} value={project.project_id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
      <Button
        aria-label="Create Jenny project"
        className="size-6 rounded-full border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) text-(--ui-text-secondary) hover:text-foreground [&_svg]:size-3.5!"
        onClick={onNewProject}
        title="Create Jenny project"
        type="button"
        variant="ghost"
      >
        <Codicon name="add" size="0.875rem" />
      </Button>
    </div>
  )
}

interface NativeProjectIntakeValue {
  forbidden: string
  goal: string
  name: string
  source: string
  success: string
}

function projectSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'project'
}

function listFromTextarea(value: string): string[] {
  return value.split(/\r?\n|,/).map(item => item.trim()).filter(Boolean)
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
  const [value, setValue] = useState<NativeProjectIntakeValue>({
    forbidden: '',
    goal: '',
    name: '',
    source: '',
    success: ''
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const update = (key: keyof NativeProjectIntakeValue) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setValue(current => ({ ...current, [key]: event.currentTarget.value }))

  const submit = async () => {
    const name = value.name.trim()
    const goal = value.goal.trim()
    const source = value.source.trim()
    const success = listFromTextarea(value.success)
    const forbidden = listFromTextarea(value.forbidden)

    if (!name || !goal) {
      setError('Project name and goal are required.')

      return
    }

    setSaving(true)
    setError('')

    try {
      const projectId = `project-${projectSlug(name)}`
      const project = await createMissionControlProject({
        current_goal: goal,
        mistakes_guards: forbidden.join('; '),
        name,
        next_recommended_lane: 'Start with a spec-first project setup review.',
        project_id: projectId,
        source_of_truth: source,
        status: 'active'
      })
      const createdProjectId = project.project.project_id || projectId
      const createdProjectName = project.project.name || name

      await createMissionControlProjectBrief({
        approval_rules: ['Jenny must challenge vague, risky, or wrong-approach requests before implementation.'],
        constraints: forbidden,
        forbidden_actions: forbidden,
        name: `${createdProjectName} initial brief`,
        outcome: goal,
        project_id: createdProjectId,
        source_of_truth: source,
        status: 'active',
        success_criteria: success
      })

      onCreated(createdProjectId, createdProjectName)
      notify({ durationMs: 2_000, kind: 'success', message: `Created ${createdProjectName}` })
      setValue({ forbidden: '', goal: '', name: '', source: '', success: '' })
      onOpenChange(false)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message)
      notifyError(err, 'Could not create Jenny project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Jenny project</DialogTitle>
          <DialogDescription>
            Set up the project brief before Jenny starts work. Guardrails stay in the background.
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
          <textarea
            className="min-h-16 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
            disabled={saving}
            onChange={update('forbidden')}
            placeholder="Forbidden actions or risks, one per line"
            value={value.forbidden}
          />
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

function HeaderPill({ label, title, tone }: { label: string; title: string; tone: NativeJennyStatusTone }) {
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
      className={cn('max-w-56 truncate rounded-full border px-2 py-0.5 text-[0.6875rem] font-medium leading-none', toneClass)}
      title={title}
    >
      {label}
    </span>
  )
}

function ProjectJennyStatusStrip({
  activeTurnRunning,
  gatewayOpen
}: {
  activeTurnRunning: boolean
  gatewayOpen: boolean
}) {
  const selectedProjectId = useStore($selectedMissionControlProjectId)
  const selectedProjectName = useStore($selectedMissionControlProjectName)
  const projectName = selectedProjectName.trim()
  const bridgeStatusQuery = useQuery({
    enabled: gatewayOpen && Boolean(selectedProjectId.trim()),
    queryFn: getMissionControlGitHubBridgeStatus,
    queryKey: ['mission-control-github-bridge-status', selectedProjectId],
    refetchInterval: 3_000,
    staleTime: 10_000
  })

  if (!projectName) {
    return null
  }

  const jennyStatus = nativeJennyStatus({
    activeTurnRunning,
    bridgeStatus: bridgeStatusQuery.data,
    gatewayOpen,
    loading: bridgeStatusQuery.isLoading,
    projectId: selectedProjectId,
    queryError: bridgeStatusQuery.error
  })

  const toneClass =
    jennyStatus.tone === 'warn'
      ? 'text-red-200'
      : jennyStatus.tone === 'pending'
        ? 'text-amber-100'
        : jennyStatus.tone === 'working'
          ? 'text-blue-100'
          : jennyStatus.tone === 'ok'
            ? 'text-emerald-100'
            : 'text-(--ui-text-secondary)'

  return (
    <div
      aria-label="Jenny project status"
      className="relative z-10 flex min-h-8 shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background)/95 px-4 text-[0.75rem] text-(--ui-text-secondary)"
    >
      <span className="min-w-0 truncate">
        Project: <span className="font-medium text-foreground">{projectName}</span>
      </span>
      <span aria-hidden="true" className="text-(--ui-text-tertiary)">
        /
      </span>
      <span className={cn('min-w-0 truncate font-medium', toneClass)} title={jennyStatus.detail}>
        {jennyStatus.label}
      </span>
      <span className="hidden min-w-0 truncate text-(--ui-text-tertiary) min-[42rem]:inline" title={jennyStatus.detail}>
        {jennyStatus.summary}
      </span>
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
  onSubmit,
  onThreadMessagesChange,
  onEdit,
  onReload,
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
  const selectedProjectTitle = selectedProjectName.trim()
  const runtimeMessageCacheRef = useRef(new WeakMap<ChatMessage, ThreadMessage>())
  const isRoutedSessionView = Boolean(routeSessionId(location.pathname))
  const projectHomeQuery = useQuery({
    enabled: gatewayOpen,
    queryFn: getMissionControlProjects,
    queryKey: ['mission-control-projects-native-chat-home'],
    staleTime: 30_000
  })
  const projectHomeOptions = useMemo(
    () => nativeChatProjects(projectHomeQuery.data?.projects.map(item => item.record) ?? []),
    [projectHomeQuery.data]
  )

  const showIntro =
    freshDraftReady && !isRoutedSessionView && !selectedSessionId && !activeSessionId && messages.length === 0

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
        gatewayOpen={gatewayOpen}
        isRoutedSessionView={isRoutedSessionView}
        onDeleteSelectedSession={onDeleteSelectedSession}
        onToggleSelectedPin={onToggleSelectedPin}
        selectedSessionId={selectedSessionId}
      />
      <ProjectJennyStatusStrip activeTurnRunning={busy} gatewayOpen={gatewayOpen} />

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
                    onSelectProject: (projectId, projectName) => setSelectedMissionControlProject(projectId, projectName),
                    personality: introPersonality,
                    projectName: selectedProjectName.trim(),
                    projectOptions: projectHomeOptions.map(project => ({
                      id: project.project_id,
                      name: project.name
                    })),
                    projectsLoading: projectHomeQuery.isLoading,
                    seed: introSeed
                  }
                : undefined
            }
            loading={threadLoading}
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
        <ChatDropOverlay kind={dragKind} />
        <ChatSwapOverlay profile={gatewaySwapTarget} />
      </div>
    </div>
  )
}
