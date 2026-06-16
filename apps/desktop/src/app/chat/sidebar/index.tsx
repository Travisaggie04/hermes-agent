import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useStore } from '@nanostores/react'
import type * as React from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { DisclosureCaret } from '@/components/ui/disclosure-caret'
import { KbdGroup } from '@/components/ui/kbd'
import { SearchField } from '@/components/ui/search-field'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem
} from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import { Tip } from '@/components/ui/tooltip'
import {
  createMissionControlProject,
  createMissionControlProjectBrief,
  createMissionControlSessionProjectLink,
  getMissionControlProjects,
  getMissionControlProjectSessions,
  type MissionControlProjectSession,
  type MissionControlProjectSessionGroup,
  searchSessions,
  type SessionInfo,
  type SessionSearchResult
} from '@/hermes'
import { useI18n } from '@/i18n'
import { sessionTitle } from '@/lib/chat-runtime'
import { MISSION_CONTROL_PROJECT_LINK_CREATED } from '@/lib/mission-control-events'
import { profileColor } from '@/lib/profile-color'
import { sessionMatchesSearch } from '@/lib/session-search'
import { cn } from '@/lib/utils'
import {
  $panesFlipped,
  $pinnedSessionIds,
  $sidebarAgentsGrouped,
  $sidebarOpen,
  $sidebarPinsOpen,
  $sidebarRecentsOpen,
  pinSession,
  reorderPinnedSession,
  setSidebarAgentsGrouped,
  setSidebarPinsOpen,
  setSidebarRecentsOpen,
  SIDEBAR_SESSIONS_PAGE_SIZE,
  unpinSession
} from '@/store/layout'
import { notify, notifyError } from '@/store/notifications'
import {
  $newChatProfile,
  $profiles,
  $profileScope,
  ALL_PROFILES,
  newSessionInProfile,
  normalizeProfileKey
} from '@/store/profile'
import {
  $selectedMissionControlProjectId,
  $selectedMissionControlProjectName,
  $selectedStoredSessionId,
  $sessionProfileTotals,
  $sessions,
  $sessionsLoading,
  $sessionsTotal,
  $workingSessionIds,
  sessionPinId
} from '@/store/session'
import { setSelectedMissionControlProject } from '@/store/session'

import { type AppView, ARTIFACTS_ROUTE, MESSAGING_ROUTE, SKILLS_ROUTE } from '../../routes'
import { SidebarPanelLabel } from '../../shell/sidebar-label'
import type { SidebarNavItem } from '../../types'
import { fallbackProjectGroups, nativeChatProjects } from '../native-projects'

import { ProfileRail } from './profile-switcher'
import type { ProjectMoveTarget } from './session-actions-menu'
import { SidebarSessionRow } from './session-row'
import { VirtualSessionList } from './virtual-session-list'

const VIRTUALIZE_THRESHOLD = 25

// Render the modifier key the user actually presses on this platform. The
// global accelerator is bound to both Cmd+N (macOS) and Ctrl+N (everywhere
// else) in desktop-controller.tsx, but the hint should match muscle memory.
const NEW_SESSION_KBD: readonly string[] =
  typeof navigator !== 'undefined' && navigator.platform.toLowerCase().includes('mac') ? ['⌘', 'N'] : ['Ctrl', 'N']

const SIDEBAR_NAV: SidebarNavItem[] = [
  {
    id: 'new-session',
    label: 'New session',
    icon: props => <Codicon name="robot" {...props} />,
    action: 'new-session'
  },
  {
    id: 'skills',
    label: 'Skills & Tools',
    icon: props => <Codicon name="symbol-misc" {...props} />,
    route: SKILLS_ROUTE
  },
  { id: 'messaging', label: 'Messaging', icon: props => <Codicon name="comment" {...props} />, route: MESSAGING_ROUTE },
  { id: 'artifacts', label: 'Artifacts', icon: props => <Codicon name="files" {...props} />, route: ARTIFACTS_ROUTE },
  {
    id: 'mission-control',
    label: 'Jenny OS',
    icon: props => <Codicon name="dashboard" {...props} />,
    action: 'jenny-os'
  }
]

const WORKSPACE_PAGE = 5
// ALL-profiles view: show only the latest N per profile up front to keep the
// unified list scannable, then reveal/fetch more in N-sized steps on demand.
const PROFILE_INITIAL_PAGE = 5
const WS_ID_PREFIX = 'workspace:'
const HERMES_PROJECT_NAME = 'Hermes / Mission Control'

const wsId = (id: string) => `${WS_ID_PREFIX}${id}`
const parseWsId = (id: string) => (id.startsWith(WS_ID_PREFIX) ? id.slice(WS_ID_PREFIX.length) : null)
const countLabel = (loaded: number, total: number) => (total > loaded ? `${loaded}/${total}` : String(loaded))
const sessionTime = (s: SessionInfo) => s.last_active || s.started_at || 0

function orderByIds<T>(items: T[], getId: (item: T) => string, orderIds: string[]): T[] {
  if (!orderIds.length) {
    return items
  }

  const byId = new Map(items.map(item => [getId(item), item]))
  const seen = new Set<string>()
  const out: T[] = []

  for (const id of orderIds) {
    const item = byId.get(id)

    if (item) {
      out.push(item)
      seen.add(id)
    }
  }

  for (const item of items) {
    if (!seen.has(getId(item))) {
      out.push(item)
    }
  }

  return out
}

const baseName = (path: string) =>
  path
    .replace(/[/\\]+$/, '')
    .split(/[/\\]/)
    .filter(Boolean)
    .pop()

// FTS results cover sessions that aren't in the loaded page; synthesize a
// minimal SessionInfo so they render in the same row component (resume works
// by id; the snippet stands in for the preview).
function searchResultToSession(result: SessionSearchResult): SessionInfo {
  const ts = result.session_started ?? Date.now() / 1000

  return {
    archived: false,
    cwd: null,
    ended_at: null,
    id: result.session_id,
    _lineage_root_id: result.lineage_root ?? null,
    input_tokens: 0,
    is_active: false,
    last_active: ts,
    message_count: 0,
    model: result.model ?? null,
    output_tokens: 0,
    preview: result.snippet?.trim() || null,
    source: result.source ?? null,
    started_at: ts,
    title: null,
    tool_call_count: 0
  }
}

function workspaceGroupsFor(sessions: SessionInfo[], noWorkspaceLabel: string): SidebarSessionGroup[] {
  const groups = new Map<string, SidebarSessionGroup>()

  for (const session of sessions) {
    const path = session.cwd?.trim() || ''
    const id = path || '__no_workspace__'
    const label = baseName(path) || path || noWorkspaceLabel

    const group = groups.get(id) ?? { id, label, path: path || null, sessions: [] }
    group.sessions.push(session)
    groups.set(id, group)
  }

  // Groups keep recency order (Map insertion = first-seen in the recency-sorted
  // input, so an active project floats up), but rows *within* a group sort by
  // creation time so they don't reshuffle every time a message lands — keeps
  // muscle memory intact.
  for (const group of groups.values()) {
    group.sessions.sort((a, b) => b.started_at - a.started_at)
  }

  return [...groups.values()]
}

function projectSessionToSessionInfo(session: MissionControlProjectSession): SessionInfo {
  const ts = session.last_active || session.started_at || Date.now() / 1000

  return {
    archived: false,
    cwd: session.cwd ?? null,
    ended_at: null,
    id: session.durable_session_id || session.session_id,
    _lineage_root_id: session.lineage_root_id ?? null,
    input_tokens: 0,
    is_active: false,
    is_default_profile: session.is_default_profile,
    last_active: ts,
    message_count: session.message_count ?? 0,
    model: null,
    output_tokens: 0,
    preview: session.preview ?? null,
    profile: session.profile,
    source: session.source ?? null,
    started_at: session.started_at || ts,
    title: session.title ?? null,
    tool_call_count: session.tool_call_count ?? 0
  }
}

function projectGroupsFor(groups: MissionControlProjectSessionGroup[]): SidebarSessionGroup[] {
  return groups.map(group => ({
    id: group.project_id,
    label: group.name,
    mode: 'project' as const,
    path: null,
    sessions: group.sessions.map(projectSessionToSessionInfo),
    totalCount: group.sessions.length
  }))
}

function projectSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'project'
}

function listFromTextarea(value: string): string[] {
  return value.split(/\r?\n|,/).map(item => item.trim()).filter(Boolean)
}

function useSortableBindings(id: string) {
  const { attributes, isDragging, listeners, setNodeRef, transform, transition } = useSortable({ id })

  return {
    dragging: isDragging,
    dragHandleProps: { ...attributes, ...listeners },
    ref: setNodeRef,
    reorderable: true as const,
    style: { transform: CSS.Transform.toString(transform), transition }
  }
}

interface ChatSidebarProps extends React.ComponentProps<typeof Sidebar> {
  currentView: AppView
  onNavigate: (item: SidebarNavItem) => void
  onLoadMoreSessions: () => void
  onLoadMoreProfileSessions?: (profile: string) => Promise<void> | void
  onResumeSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onArchiveSession: (sessionId: string) => void
  onNewSessionInWorkspace: (path: null | string) => void
  onNewSessionInProject: (projectId: string, projectName: string) => void
}

export function ChatSidebar({
  currentView,
  onNavigate,
  onLoadMoreSessions,
  onLoadMoreProfileSessions,
  onResumeSession,
  onDeleteSession,
  onArchiveSession,
  onNewSessionInWorkspace,
  onNewSessionInProject
}: ChatSidebarProps) {
  const { t } = useI18n()
  const s = t.sidebar
  const sidebarOpen = useStore($sidebarOpen)
  const panesFlipped = useStore($panesFlipped)
  const agentsGrouped = useStore($sidebarAgentsGrouped)
  const pinnedSessionIds = useStore($pinnedSessionIds)
  const pinsOpen = useStore($sidebarPinsOpen)
  const agentsOpen = useStore($sidebarRecentsOpen)
  const selectedSessionId = useStore($selectedStoredSessionId)
  const selectedMissionControlProjectId = useStore($selectedMissionControlProjectId)
  const selectedMissionControlProjectName = useStore($selectedMissionControlProjectName)
  const sessions = useStore($sessions)
  const sessionsLoading = useStore($sessionsLoading)
  const sessionsTotal = useStore($sessionsTotal)
  const sessionProfileTotals = useStore($sessionProfileTotals)
  const workingSessionIds = useStore($workingSessionIds)
  const profiles = useStore($profiles)
  const profileScope = useStore($profileScope)
  // Only surface the profile switcher when more than one profile exists, so
  // single-profile users see the unchanged sidebar.
  const multiProfile = profiles.length > 1
  // Gate ALL-profiles grouping on multiProfile too: if a user drops back to one
  // profile while scope is still ALL (persisted), the rail is hidden and they'd
  // otherwise be stuck in the grouped view with no way out.
  const showAllProfiles = multiProfile && profileScope === ALL_PROFILES
  const [agentOrderIds, setAgentOrderIds] = useState<string[]>([])
  const [workspaceOrderIds, setWorkspaceOrderIds] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [serverMatches, setServerMatches] = useState<SessionSearchResult[]>([])
  const [newSessionKbdFlash, setNewSessionKbdFlash] = useState(false)
  const [projectGroups, setProjectGroups] = useState<SidebarSessionGroup[]>([])
  const [projectGroupsLoading, setProjectGroupsLoading] = useState(false)
  const [projectIntakeOpen, setProjectIntakeOpen] = useState(false)
  const [projectIntakeError, setProjectIntakeError] = useState('')
  const [projectIntakeSaving, setProjectIntakeSaving] = useState(false)
  const [projectIntake, setProjectIntake] = useState<ProjectIntakeValue>({
    approval: '',
    evidence: '',
    forbidden: '',
    goal: '',
    name: '',
    source: '',
    success: ''
  })
  const [profileLoadMorePending, setProfileLoadMorePending] = useState<Record<string, boolean>>({})
  const trimmedQuery = searchQuery.trim()

  // Flash the ⌘N hint full-opacity (no transition) for the press, so hitting
  // the shortcut visibly pings its affordance in the sidebar.
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | undefined

    const onShortcut = () => {
      setNewSessionKbdFlash(true)
      clearTimeout(timeout)
      timeout = setTimeout(() => setNewSessionKbdFlash(false), 140)
    }

    window.addEventListener('hermes:new-session-shortcut', onShortcut)

    return () => {
      window.removeEventListener('hermes:new-session-shortcut', onShortcut)
      clearTimeout(timeout)
    }
  }, [])

  const activeSidebarSessionId = currentView === 'chat' ? selectedSessionId : null

  const dndSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // Profile scope = the "workspace switcher" context. Concrete scope shows only
  // that profile's sessions (clean rows, no per-row tags); ALL fans every
  // profile in, grouped by profile below. Single-profile users land here with
  // scope === their only profile, so nothing is filtered out.
  const visibleSessions = useMemo(
    () => (showAllProfiles ? sessions : sessions.filter(s => normalizeProfileKey(s.profile) === profileScope)),
    [sessions, showAllProfiles, profileScope]
  )

  const sortedSessions = useMemo(
    () => [...visibleSessions].sort((a, b) => sessionTime(b) - sessionTime(a)),
    [visibleSessions]
  )

  const workingSessionIdSet = useMemo(() => new Set(workingSessionIds), [workingSessionIds])

  const refreshProjectGroups = useCallback(() => {
    let cancelled = false

    setProjectGroupsLoading(true)
    Promise.allSettled([getMissionControlProjects(), getMissionControlProjectSessions()])
      .then(results => {
        if (cancelled) {
          return
        }

        const [projectsResult, sessionsResult] = results
        const projectRecords =
          projectsResult.status === 'fulfilled' ? nativeChatProjects(projectsResult.value.projects.map(item => item.record)) : nativeChatProjects()
        const sessionGroups = sessionsResult.status === 'fulfilled' ? sessionsResult.value.groups || [] : []
        const byId = new Map(projectGroupsFor(sessionGroups).map(group => [group.id, group]))

        for (const project of projectRecords) {
          const projectId = project.project_id || project.name

          if (!projectId || byId.has(projectId)) {
            continue
          }

          byId.set(projectId, {
            id: projectId,
            label: project.name || projectId,
            mode: 'project',
            path: null,
            sessions: [],
            totalCount: 0
          })
        }

        const next = byId.size ? [...byId.values()].sort((a, b) => a.label.localeCompare(b.label)) : projectGroupsFor(fallbackProjectGroups())
        setProjectGroups(next)

        if (!$selectedMissionControlProjectId.get().trim() && next.length) {
          setSelectedMissionControlProject(next[0].id, next[0].label)
          setSidebarRecentsOpen(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProjectGroups([])
        }
      })
      .finally(() => {
        if (!cancelled) {
          setProjectGroupsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => refreshProjectGroups(), [refreshProjectGroups])

  useEffect(() => {
    const onProjectLinkCreated = () => {
      refreshProjectGroups()
    }

    window.addEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectLinkCreated)

    return () => {
      window.removeEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED, onProjectLinkCreated)
    }
  }, [refreshProjectGroups])

  const createProjectFromIntake = useCallback(async () => {
    const name = projectIntake.name.trim()
    const goal = projectIntake.goal.trim()
    const source = projectIntake.source.trim()
    const success = listFromTextarea(projectIntake.success)
    const forbidden = listFromTextarea(projectIntake.forbidden)
    const evidence = listFromTextarea(projectIntake.evidence)
    const approval = listFromTextarea(projectIntake.approval)
    const approvalRules = [
      'Jenny must challenge vague, risky, or wrong-approach requests before implementation.',
      'Jenny must define evidence, tests, rollback/stop conditions, and approval needs before broad work.',
      ...approval
    ]
    const constraints = [
      ...evidence.map(item => `Evidence required: ${item}`),
      ...approval.map(item => `Approval/stop rule: ${item}`)
    ]

    if (!name || !goal) {
      setProjectIntakeError('Project name and goal are required.')

      return
    }

    setProjectIntakeSaving(true)
    setProjectIntakeError('')

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

      await createMissionControlProjectBrief({
        approval_rules: approvalRules,
        constraints,
        forbidden_actions: forbidden,
        name: `${name} initial brief`,
        outcome: goal,
        project_id: createdProjectId,
        source_of_truth: source,
        status: 'active',
        success_criteria: success
      })

      setSelectedMissionControlProject(createdProjectId, project.project.name || name)
      setSidebarRecentsOpen(false)
      setProjectIntake({ approval: '', evidence: '', forbidden: '', goal: '', name: '', source: '', success: '' })
      setProjectIntakeOpen(false)
      refreshProjectGroups()
      onNewSessionInProject(createdProjectId, project.project.name || name)
    } catch (err) {
      setProjectIntakeError(err instanceof Error ? err.message : String(err))
    } finally {
      setProjectIntakeSaving(false)
    }
  }, [onNewSessionInProject, projectIntake, refreshProjectGroups])

  const projectMoveTargets = useMemo<ProjectMoveTarget[]>(
    () => projectGroups.map(group => ({ name: group.label, project_id: group.id })),
    [projectGroups]
  )

  const visibleProjectGroups = useMemo(() => {
    const activeProjectId = selectedMissionControlProjectId.trim()

    if (!activeProjectId) {
      return projectGroups
    }

    return [...projectGroups].sort((a, b) => {
      if (a.id === activeProjectId) {
        return -1
      }

      if (b.id === activeProjectId) {
        return 1
      }

      return a.label.localeCompare(b.label)
    })
  }, [projectGroups, selectedMissionControlProjectId])

  const projectMode = Boolean(selectedMissionControlProjectId.trim())
  const recentsLabel = projectMode ? 'Unfiled chats' : s.sessions
  const recentsRootClassName = projectMode ? 'shrink-0 p-0 pb-1 opacity-90' : 'min-h-0 flex-1 p-0'
  const recentsContentClassName = cn(
    projectMode
      ? 'flex max-h-52 shrink-0 flex-col overflow-y-auto overscroll-contain rounded-lg pb-1.75'
      : 'flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain pb-1.75',
    // Separate profile sections clearly in the ALL view; rows inside
    // each group keep their own tight gap-px rhythm.
    showAllProfiles ? 'gap-3' : 'gap-px'
  )

  const moveSessionToProject = useCallback(
    async (session: SessionInfo, projectId: string, projectName: string) => {
      try {
        await createMissionControlSessionProjectLink({
          cwd_snapshot: session.cwd || undefined,
          lineage_root_id: session._lineage_root_id || undefined,
          link_method: 'manual',
          linked_by: 'desktop',
          profile: session.profile || undefined,
          project_id: projectId,
          session_id: session.id,
          source: 'desktop-native-chat',
          status: 'active',
          title_snapshot: sessionTitle(session)
        })
        notify({ durationMs: 2_000, kind: 'success', message: `Moved to ${projectName}` })
        refreshProjectGroups()
      } catch (err) {
        notifyError(err, `Could not move session to ${projectName}`)
      }
    },
    [refreshProjectGroups]
  )

  const selectProjectGroup = useCallback((projectId: string, projectName: string) => {
    setSelectedMissionControlProject(projectId, projectName)
    setSidebarRecentsOpen(false)
  }, [])

  const startProjectChat = useCallback(
    (projectId: string, projectName: string) => {
      setSidebarRecentsOpen(false)
      onNewSessionInProject(projectId, projectName)
    },
    [onNewSessionInProject]
  )

  // Index sessions by both their live id and their lineage-root id so a pin
  // stored as the pre-compression root resolves to the live continuation tip.
  const sessionByAnyId = useMemo(() => {
    const map = new Map<string, SessionInfo>()

    for (const s of visibleSessions) {
      map.set(s.id, s)

      if (s._lineage_root_id && !map.has(s._lineage_root_id)) {
        map.set(s._lineage_root_id, s)
      }
    }

    return map
  }, [visibleSessions])

  const pinnedSessions = useMemo(() => {
    const seen = new Set<string>()
    const out: SessionInfo[] = []

    for (const pinId of pinnedSessionIds) {
      const session = sessionByAnyId.get(pinId)

      if (session && !seen.has(session.id)) {
        seen.add(session.id)
        out.push(session)
      }
    }

    return out
  }, [pinnedSessionIds, sessionByAnyId])

  const pinnedRealIdSet = useMemo(() => new Set(pinnedSessions.map(s => s.id)), [pinnedSessions])

  // Full-text search across *all* sessions (not just the loaded page) so 699
  // sessions stay findable. Debounced; loaded sessions are matched instantly
  // client-side and merged ahead of the server hits.
  useEffect(() => {
    if (!trimmedQuery) {
      setServerMatches([])

      return
    }

    let cancelled = false

    const id = window.setTimeout(() => {
      void searchSessions(trimmedQuery)
        .then(res => {
          if (!cancelled) {
            setServerMatches(res.results)
          }
        })
        .catch(() => undefined)
    }, 200)

    return () => {
      cancelled = true
      window.clearTimeout(id)
    }
  }, [trimmedQuery])

  const searchResults = useMemo(() => {
    if (!trimmedQuery) {
      return []
    }

    const out = new Map<string, SessionInfo>()

    for (const s of sortedSessions) {
      if (sessionMatchesSearch(s, trimmedQuery)) {
        out.set(s.id, s)
      }
    }

    for (const match of serverMatches) {
      if (out.has(match.session_id)) {
        continue
      }

      const loaded = sessionByAnyId.get(match.session_id)
      out.set(match.session_id, loaded ?? searchResultToSession(match))
    }

    return [...out.values()]
  }, [trimmedQuery, sortedSessions, serverMatches, sessionByAnyId])

  const unpinnedAgentSessions = useMemo(
    () => sortedSessions.filter(s => !pinnedRealIdSet.has(s.id)),
    [sortedSessions, pinnedRealIdSet]
  )

  const agentSessions = useMemo(
    () => orderByIds(unpinnedAgentSessions, s => s.id, agentOrderIds),
    [unpinnedAgentSessions, agentOrderIds]
  )

  const agentGroups = useMemo(
    () => orderByIds(workspaceGroupsFor(agentSessions, s.noWorkspace), g => g.id, workspaceOrderIds),
    [agentSessions, s.noWorkspace, workspaceOrderIds]
  )

  const loadMoreForProfileGroup = useCallback(
    (profile: string) => {
      if (!onLoadMoreProfileSessions) {
        return
      }

      setProfileLoadMorePending(prev => ({ ...prev, [profile]: true }))

      void Promise.resolve(onLoadMoreProfileSessions(profile))
        .catch(() => undefined)
        .finally(() =>
          setProfileLoadMorePending(({ [profile]: _done, ...rest }) => rest)
        )
    },
    [onLoadMoreProfileSessions]
  )

  // ALL-profiles view: one collapsible group per profile, color on the header
  // (not on every row). Default profile floats to the top, the rest alpha.
  const profileGroups = useMemo<SidebarSessionGroup[] | undefined>(() => {
    if (!showAllProfiles) {
      return undefined
    }

    const groups = new Map<string, SidebarSessionGroup>()

    for (const session of agentSessions) {
      const key = normalizeProfileKey(session.profile)

      const group = groups.get(key) ?? {
        color: profileColor(key),
        id: key,
        label: key,
        mode: 'profile',
        path: null,
        sessions: []
      }

      group.sessions.push(session)

      groups.set(key, group)
    }

    return [...groups.values()]
      .map(group => ({
        ...group,
        loadingMore: Boolean(profileLoadMorePending[group.id]),
        onLoadMore: onLoadMoreProfileSessions ? () => loadMoreForProfileGroup(group.id) : undefined,
        totalCount: Math.max(group.sessions.length, sessionProfileTotals[group.id] ?? 0)
      }))
      // default (root) first, then the rest alphabetically.
      .sort((a, b) => (a.id === 'default' ? -1 : b.id === 'default' ? 1 : a.label.localeCompare(b.label)))
  }, [
    showAllProfiles,
    agentSessions,
    loadMoreForProfileGroup,
    onLoadMoreProfileSessions,
    profileLoadMorePending,
    sessionProfileTotals
  ])

  const showSessionSkeletons = sessionsLoading && sortedSessions.length === 0
  const showSessionSections = showSessionSkeletons || sortedSessions.length > 0
  // Pagination is scope-aware. In "All profiles" mode it tracks the global
  // unified set. When scoped to one profile it must compare that profile's own
  // loaded rows against that profile's total — otherwise a huge default profile
  // keeps "Load more" stuck on while you browse a small one (the aggregator's
  // total sums every profile). Per-profile totals come from the aggregator
  // (children excluded); fall back to the global total / loaded count.
  const loadedSessionCount = showAllProfiles ? sessions.length : visibleSessions.length
  const scopedProfileTotal = showAllProfiles ? undefined : sessionProfileTotals[profileScope]

  const knownSessionTotal = Math.max(
    showAllProfiles ? sessionsTotal : (scopedProfileTotal ?? loadedSessionCount),
    loadedSessionCount
  )

  const hasMoreSessions = knownSessionTotal > loadedSessionCount
  const remainingSessionCount = Math.max(0, knownSessionTotal - loadedSessionCount)

  const recentsMeta = countLabel(agentSessions.length, knownSessionTotal)

  const handlePinnedDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) {
      return
    }

    const newIndex = pinnedSessions.findIndex(s => s.id === String(over.id))

    if (newIndex < 0) {
      return
    }

    // Sortable ids are live session ids; the pinned store is keyed by durable
    // (lineage-root) ids, so translate before reordering.
    const dragged = sessionByAnyId.get(String(active.id))
    reorderPinnedSession(dragged ? sessionPinId(dragged) : String(active.id), newIndex)
  }

  const handleAgentDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) {
      return
    }

    const activeId = String(active.id)
    const overId = String(over.id)
    const activeWs = parseWsId(activeId)
    const overWs = parseWsId(overId)

    if (activeWs && overWs) {
      const oldIdx = agentGroups.findIndex(g => g.id === activeWs)
      const newIdx = agentGroups.findIndex(g => g.id === overWs)

      if (oldIdx < 0 || newIdx < 0) {
        return
      }

      setWorkspaceOrderIds(arrayMove(agentGroups, oldIdx, newIdx).map(g => g.id))

      return
    }

    if (activeWs || overWs) {
      return
    }

    const oldIdx = agentSessions.findIndex(s => s.id === activeId)
    const newIdx = agentSessions.findIndex(s => s.id === overId)

    if (oldIdx < 0 || newIdx < 0) {
      return
    }

    setAgentOrderIds(arrayMove(agentSessions, oldIdx, newIdx).map(s => s.id))
  }

  return (
    <Sidebar
      className={cn(
        'relative h-full min-w-0 overflow-hidden border-t-0 border-b-0 text-foreground transition-none',
        panesFlipped ? 'border-l border-r-0' : 'border-r border-l-0',
        sidebarOpen
          ? 'border-(--sidebar-edge-border) bg-(--ui-sidebar-surface-background) opacity-100'
          : 'pointer-events-none border-transparent bg-transparent opacity-0'
      )}
      collapsible="none"
    >
      <SidebarContent className="gap-0 overflow-hidden bg-transparent px-2.5">
        <SidebarGroup className="shrink-0 p-0 pb-2 pt-[calc(var(--titlebar-height)+0.375rem)]">
          <SidebarGroupContent>
            <SidebarMenu className="gap-px">
              {SIDEBAR_NAV.map(item => {
                const isInteractive = Boolean(item.action) || Boolean(item.route)

                const active =
                  (item.id === 'skills' && currentView === 'skills') ||
                  (item.id === 'messaging' && currentView === 'messaging') ||
                  (item.id === 'artifacts' && currentView === 'artifacts') ||
                  (item.action === 'jenny-os' && currentView === 'chat' && Boolean(selectedMissionControlProjectId.trim()))

                const isNewSession = item.id === 'new-session'
                const isJennyOs = item.action === 'jenny-os'
                const navLabel =
                  isNewSession && selectedMissionControlProjectId
                    ? 'New project chat'
                    : (s.nav[item.id] ?? item.label)
                const navTooltip =
                  isNewSession && selectedMissionControlProjectId
                    ? `New chat in ${selectedMissionControlProjectName || selectedMissionControlProjectId}`
                    : isJennyOs
                      ? `Open Jenny chat in ${HERMES_PROJECT_NAME}`
                    : (s.nav[item.id] ?? item.label)

                return (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      aria-disabled={!isInteractive}
                      className={cn(
                        'flex h-7 w-full justify-start gap-2 rounded-md border border-transparent px-2 text-left text-[0.8125rem] font-medium text-(--ui-text-secondary) transition-colors duration-100 ease-out hover:bg-(--ui-control-hover-background) hover:text-foreground hover:transition-none',
                        active &&
                          'border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) text-foreground shadow-none hover:border-(--ui-stroke-tertiary)!',
                        !isInteractive &&
                          'cursor-default hover:border-transparent hover:bg-transparent hover:text-inherit'
                      )}
                      onClick={() => {
                        // A plain new session lands in whatever profile the live
                        // gateway is on (= the active switcher context). null →
                        // no swap. The switcher header is the single place to
                        // change which profile that is.
                        if (isNewSession) {
                          $newChatProfile.set(null)
                        }

                        onNavigate(item)
                      }}
                      tooltip={navTooltip}
                      type="button"
                    >
                      <item.icon className="size-4 shrink-0 text-[color-mix(in_srgb,currentColor_72%,transparent)]" />
                      {sidebarOpen && (
                        <>
                          <span className="min-w-0 flex-1 truncate max-[46.25rem]:hidden">
                            {navLabel}
                          </span>
                          {isNewSession && (
                            <KbdGroup
                              className={cn('ml-auto max-[46.25rem]:hidden', newSessionKbdFlash && 'opacity-100!')}
                              keys={[...NEW_SESSION_KBD]}
                            />
                          )}
                        </>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {sidebarOpen && showSessionSections && (
          <div className="shrink-0 px-2 pb-1 pt-1">
            <SearchField
              aria-label={s.searchAria}
              onChange={setSearchQuery}
              placeholder={s.searchPlaceholder}
              value={searchQuery}
            />
          </div>
        )}

        {sidebarOpen && showSessionSections && trimmedQuery && (
          <SidebarSessionsSection
            activeSessionId={activeSidebarSessionId}
            contentClassName="flex min-h-0 flex-1 flex-col gap-px overflow-y-auto overscroll-contain pb-1.75"
            emptyState={
              <div className="grid min-h-24 place-items-center rounded-lg px-2 text-center text-xs text-(--ui-text-tertiary)">
                {s.noMatch(trimmedQuery)}
              </div>
            }
            label={s.results}
            labelMeta={String(searchResults.length)}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
            onMoveSessionToProject={moveSessionToProject}
            onResumeSession={onResumeSession}
            onToggle={() => undefined}
            onTogglePin={pinSession}
            open
            pinned={false}
            projectMoveTargets={projectMoveTargets}
            rootClassName="min-h-0 flex-1 p-0"
            sessions={searchResults}
            workingSessionIdSet={workingSessionIdSet}
          />
        )}

        {sidebarOpen && !trimmedQuery && (
          <SidebarSessionsSection
            activeGroupId={selectedMissionControlProjectId}
            activeSessionId={activeSidebarSessionId}
            contentClassName="flex min-h-10 shrink-0 flex-col gap-2 rounded-lg pb-2 pt-1"
            emptyState={
              projectGroupsLoading ? (
                <SidebarSessionSkeletons />
              ) : (
                <div className="grid min-h-10 place-items-center rounded-lg px-2 text-center text-xs text-(--ui-text-tertiary)">
                  No projects yet.
                </div>
              )
            }
            footer={
              projectIntakeOpen ? (
                <ProjectIntakeForm
                  error={projectIntakeError}
                  onCancel={() => {
                    setProjectIntakeOpen(false)
                    setProjectIntakeError('')
                  }}
                  onChange={setProjectIntake}
                  onSubmit={() => void createProjectFromIntake()}
                  saving={projectIntakeSaving}
                  value={projectIntake}
                />
              ) : null
            }
            forceEmptyState={projectGroupsLoading || projectGroups.length === 0}
            groups={visibleProjectGroups}
            headerAction={
              <Tip label="Create project">
                <Button
                  aria-label="Create project"
                  className="h-6 gap-1 px-1.5 text-[0.6875rem] text-(--ui-text-tertiary) opacity-90 hover:bg-(--ui-control-hover-background) hover:text-foreground hover:opacity-100"
                  onClick={event => {
                    event.stopPropagation()
                    setProjectIntakeOpen(open => !open)
                  }}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  <Codicon name="add" size="0.75rem" />
                  <span className="max-[46.25rem]:hidden">New project</span>
                </Button>
              </Tip>
            }
            label="Projects"
            labelMeta={String(visibleProjectGroups.length)}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
            onMoveSessionToProject={moveSessionToProject}
            onNewSessionInProject={startProjectChat}
            onResumeSession={onResumeSession}
            onSelectProject={selectProjectGroup}
            onToggle={() => undefined}
            onTogglePin={pinSession}
            open
            pinned={false}
            projectMoveTargets={projectMoveTargets}
            rootClassName="shrink-0 p-0 pb-1"
            sessions={visibleProjectGroups.flatMap(group => group.sessions)}
            workingSessionIdSet={workingSessionIdSet}
          />
        )}

        {sidebarOpen && showSessionSections && !trimmedQuery && (
          <SidebarSessionsSection
            activeSessionId={activeSidebarSessionId}
            contentClassName="flex min-h-10 shrink-0 flex-col gap-px rounded-lg pb-2 pt-1"
            dndSensors={dndSensors}
            emptyState={<SidebarPinnedEmptyState />}
            label={s.pinned}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
            onMoveSessionToProject={moveSessionToProject}
            onReorder={handlePinnedDragEnd}
            onResumeSession={onResumeSession}
            onToggle={() => setSidebarPinsOpen(!pinsOpen)}
            onTogglePin={unpinSession}
            open={pinsOpen}
            pinned
            projectMoveTargets={projectMoveTargets}
            rootClassName="shrink-0 p-0 pb-1"
            sessions={pinnedSessions}
            sortable={pinnedSessions.length > 1}
            workingSessionIdSet={workingSessionIdSet}
          />
        )}

        {sidebarOpen && showSessionSections && !trimmedQuery && (
          <SidebarSessionsSection
            activeSessionId={activeSidebarSessionId}
            contentClassName={recentsContentClassName}
            dndSensors={dndSensors}
            emptyState={showSessionSkeletons ? <SidebarSessionSkeletons /> : <SidebarAllPinnedState />}
            footer={
              // Hide "load more" only when workspace-grouped (those groups page
              // themselves). ALL-profiles now pages per-profile from each profile
              // header; the global footer only applies to non-ALL views.
              !showAllProfiles && !agentsGrouped && !showSessionSkeletons && hasMoreSessions ? (
                <SidebarLoadMoreRow
                  loading={sessionsLoading}
                  onClick={onLoadMoreSessions}
                  step={Math.min(SIDEBAR_SESSIONS_PAGE_SIZE, remainingSessionCount)}
                />
              ) : null
            }
            forceEmptyState={showSessionSkeletons}
            groups={showAllProfiles ? profileGroups : agentsGrouped ? agentGroups : undefined}
            headerAction={
              // Always reserve the icon-xs (size-6) slot so the header keeps the
              // same height whether or not the toggle renders — otherwise the
              // "Sessions" label jumps when switching to the ALL-profiles view.
              // Grouping operates on unpinned recents; if everything is pinned
              // the toggle does nothing, and it's irrelevant in the ALL-profiles
              // view (always grouped by profile), so hide the button (not the slot).
              <div className="grid size-6 shrink-0 place-items-center">
                {!showAllProfiles && agentSessions.length > 0 ? (
                  <Tip label={agentsGrouped ? s.groupTitleGrouped : s.groupTitleUngrouped}>
                    <Button
                      aria-label={agentsGrouped ? s.groupAriaGrouped : s.groupAriaUngrouped}
                      className={cn(
                        'text-(--ui-text-tertiary) opacity-70 hover:bg-(--ui-control-hover-background) hover:text-foreground hover:opacity-100 focus-visible:opacity-100',
                        agentsGrouped && 'bg-(--ui-control-active-background) text-foreground opacity-100'
                      )}
                      onClick={event => {
                        event.stopPropagation()
                        setSidebarRecentsOpen(true)
                        setSidebarAgentsGrouped(!agentsGrouped)
                      }}
                      size="icon-xs"
                      variant="ghost"
                    >
                      <Codicon name={agentsGrouped ? 'list-unordered' : 'root-folder'} size="0.75rem" />
                    </Button>
                  </Tip>
                ) : null}
              </div>
            }
            label={recentsLabel}
            labelMeta={projectMode ? undefined : recentsMeta}
            onArchiveSession={onArchiveSession}
            onDeleteSession={onDeleteSession}
            onMoveSessionToProject={moveSessionToProject}
            onNewSessionInWorkspace={showAllProfiles ? undefined : onNewSessionInWorkspace}
            onReorder={showAllProfiles ? undefined : handleAgentDragEnd}
            onResumeSession={onResumeSession}
            onToggle={() => setSidebarRecentsOpen(!agentsOpen)}
            onTogglePin={pinSession}
            open={agentsOpen}
            pinned={false}
            projectMoveTargets={projectMoveTargets}
            rootClassName={recentsRootClassName}
            sessions={agentSessions}
            sortable={!showAllProfiles && agentSessions.length > 1}
            workingSessionIdSet={workingSessionIdSet}
          />
        )}

        {sidebarOpen && showSessionSections && !trimmedQuery && projectMode && <div className="min-h-0 flex-1" />}

        {sidebarOpen && !showSessionSections && <div className="min-h-0 flex-1" />}

        {sidebarOpen && (
          <div className="shrink-0 px-0.5 pb-1 pt-0.5">
            <ProfileRail />
          </div>
        )}
      </SidebarContent>
    </Sidebar>
  )
}

interface SidebarSectionHeaderProps {
  label: string
  open: boolean
  onToggle: () => void
  action?: React.ReactNode
  meta?: React.ReactNode
}

function SidebarSectionHeader({ label, open, onToggle, action, meta }: SidebarSectionHeaderProps) {
  return (
    <div className="group/section flex shrink-0 items-center justify-between pb-1 pt-1.5">
      <button
        className="group/section-label flex w-fit items-center gap-1 bg-transparent text-left leading-none"
        onClick={onToggle}
        type="button"
      >
        <SidebarPanelLabel>{label}</SidebarPanelLabel>
        {meta && <SidebarCount>{meta}</SidebarCount>}
        <DisclosureCaret
          className="text-(--ui-text-tertiary) opacity-0 transition group-hover/section-label:opacity-100"
          open={open}
        />
      </button>
      {action}
    </div>
  )
}

function SidebarSessionSkeletons() {
  return (
    <div aria-hidden="true" className="grid gap-px">
      {['w-32', 'w-40', 'w-28', 'w-36', 'w-24'].map((width, i) => (
        <div className="grid min-h-7 grid-cols-[minmax(0,1fr)_1.5rem] items-center rounded-lg" key={`${width}-${i}`}>
          <Skeleton className={cn('h-3.5 rounded-full', width)} />
          <Skeleton className="mx-auto size-4 rounded-md opacity-60" />
        </div>
      ))}
    </div>
  )
}

function SidebarAllPinnedState() {
  const { t } = useI18n()

  return (
    <div className="grid min-h-24 place-items-center rounded-lg text-center text-xs text-(--ui-text-tertiary)">
      {t.sidebar.allPinned}
    </div>
  )
}

function SidebarPinnedEmptyState() {
  const { t } = useI18n()

  return (
    <div className="flex min-h-7 items-center gap-1.5 rounded-lg pl-2 text-[0.75rem] text-(--ui-text-tertiary)">
      <span className="grid w-3.5 shrink-0 place-items-center text-(--ui-text-quaternary)">
        <Codicon name="pin" size="0.75rem" />
      </span>
      <span>{t.sidebar.shiftClickHint}</span>
    </div>
  )
}

interface ProjectIntakeValue {
  approval: string
  evidence: string
  forbidden: string
  goal: string
  name: string
  source: string
  success: string
}

interface ProjectIntakeFormProps {
  error: string
  onCancel: () => void
  onChange: (value: ProjectIntakeValue) => void
  onSubmit: () => void
  saving: boolean
  value: ProjectIntakeValue
}

function ProjectIntakeForm({ error, onCancel, onChange, onSubmit, saving, value }: ProjectIntakeFormProps) {
  const update = (key: keyof ProjectIntakeValue) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    onChange({ ...value, [key]: event.currentTarget.value })

  return (
    <form
      className="mx-1 mt-1 grid gap-1.5 rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) p-2"
      onSubmit={event => {
        event.preventDefault()
        onSubmit()
      }}
    >
      <div className="text-[0.75rem] font-medium text-foreground">New project</div>
      <input
        className="h-7 rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('name')}
        placeholder="Project name"
        value={value.name}
      />
      <textarea
        className="min-h-14 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('goal')}
        placeholder="What should Jenny help you accomplish?"
        value={value.goal}
      />
      <input
        className="h-7 rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('source')}
        placeholder="Source of truth, repo, folder, or notes"
        value={value.source}
      />
      <textarea
        className="min-h-12 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('success')}
        placeholder="Wins / success criteria, one per line"
        value={value.success}
      />
      <textarea
        className="min-h-12 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('evidence')}
        placeholder="Evidence Jenny must return, one per line"
        value={value.evidence}
      />
      <textarea
        className="min-h-12 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('approval')}
        placeholder="Approval or stop rules, one per line"
        value={value.approval}
      />
      <textarea
        className="min-h-12 resize-none rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-[0.75rem] text-foreground outline-none placeholder:text-(--ui-text-tertiary)"
        onChange={update('forbidden')}
        placeholder="Forbidden actions or risks, one per line"
        value={value.forbidden}
      />
      {error && <div className="text-[0.6875rem] text-red-400">{error}</div>}
      <div className="flex gap-1.5">
        <Button className="h-7 flex-1 text-[0.75rem]" disabled={saving} type="submit" variant="default">
          {saving ? 'Creating...' : 'Create'}
        </Button>
        <Button className="h-7 flex-1 text-[0.75rem]" disabled={saving} onClick={onCancel} type="button" variant="ghost">
          Cancel
        </Button>
      </div>
    </form>
  )
}

interface SidebarSessionGroup {
  id: string
  label: string
  path: null | string
  sessions: SessionInfo[]
  // Profile color for the ALL-profiles view; absent for workspace groups.
  color?: null | string
  loadingMore?: boolean
  mode?: 'profile' | 'project' | 'workspace'
  onLoadMore?: () => void
  totalCount?: number
}

interface SidebarSessionsSectionProps {
  label: string
  open: boolean
  onToggle: () => void
  sessions: SessionInfo[]
  activeSessionId: null | string
  workingSessionIdSet: Set<string>
  onResumeSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
  onMoveSessionToProject?: (session: SessionInfo, projectId: string, projectName: string) => void
  onArchiveSession: (sessionId: string) => void
  onTogglePin: (sessionId: string) => void
  onNewSessionInProject?: (projectId: string, projectName: string) => void
  onNewSessionInWorkspace?: (path: null | string) => void
  onSelectProject?: (projectId: string, projectName: string) => void
  pinned: boolean
  projectMoveTargets?: ProjectMoveTarget[]
  rootClassName?: string
  contentClassName?: string
  emptyState: React.ReactNode
  forceEmptyState?: boolean
  headerAction?: React.ReactNode
  footer?: React.ReactNode
  groups?: SidebarSessionGroup[]
  activeGroupId?: null | string
  labelMeta?: React.ReactNode
  sortable?: boolean
  onReorder?: (event: DragEndEvent) => void
  dndSensors?: ReturnType<typeof useSensors>
}

function SidebarSessionsSection({
  label,
  open,
  onToggle,
  sessions,
  activeSessionId,
  workingSessionIdSet,
  onResumeSession,
  onDeleteSession,
  onMoveSessionToProject,
  onArchiveSession,
  onTogglePin,
  onNewSessionInProject,
  onNewSessionInWorkspace,
  onSelectProject,
  pinned,
  projectMoveTargets,
  rootClassName,
  contentClassName,
  emptyState,
  forceEmptyState = false,
  headerAction,
  footer,
  groups,
  activeGroupId,
  labelMeta,
  sortable = false,
  onReorder,
  dndSensors
}: SidebarSessionsSectionProps) {
  const showEmptyState = forceEmptyState || sessions.length === 0
  const dndActive = sortable && !!onReorder

  const renderRow = (session: SessionInfo, group?: SidebarSessionGroup) => {
    const rowProps = {
      isPinned: pinned,
      isSelected: session.id === activeSessionId,
      isWorking: workingSessionIdSet.has(session.id),
      onArchive: () => onArchiveSession(session.id),
      onDelete: () => onDeleteSession(session.id),
      onMoveToProject: onMoveSessionToProject
        ? (projectId: string, projectName: string) => onMoveSessionToProject(session, projectId, projectName)
        : undefined,
      onPin: () => onTogglePin(sessionPinId(session)),
      onResume: () => {
        if (group?.mode === 'project') {
          onSelectProject?.(group.id, group.label)
        }

        onResumeSession(session.id)
      },
      projectMoveTargets,
      session,
      hideCurrentProjectMove: group?.mode === 'project' && group.id === activeGroupId
    }

    return sortable ? (
      <SortableSidebarSessionRow key={session.id} {...rowProps} />
    ) : (
      <SidebarSessionRow key={session.id} {...rowProps} />
    )
  }

  const renderRows = (items: SessionInfo[], group?: SidebarSessionGroup) => items.map(session => renderRow(session, group))

  const renderSessionList = (items: SessionInfo[], group?: SidebarSessionGroup) =>
    dndActive ? (
      <SortableContext items={items.map(s => s.id)} strategy={verticalListSortingStrategy}>
        {renderRows(items, group)}
      </SortableContext>
    ) : (
      renderRows(items, group)
    )

  const flatVirtualized = !showEmptyState && !groups?.length && sessions.length >= VIRTUALIZE_THRESHOLD

  let inner: React.ReactNode

  if (showEmptyState) {
    inner = emptyState
  } else if (groups?.length) {
    const groupNodes = groups.map(group =>
      dndActive ? (
        <SortableSidebarWorkspaceGroup
          active={group.id === activeGroupId}
          group={group}
          key={group.id}
          onNewSession={onNewSessionInWorkspace}
          onNewSessionInProject={onNewSessionInProject}
          onSelectProject={onSelectProject}
          renderRows={renderSessionList}
        />
      ) : (
        <SidebarWorkspaceGroup
          active={group.id === activeGroupId}
          group={group}
          key={group.id}
          onNewSession={onNewSessionInWorkspace}
          onNewSessionInProject={onNewSessionInProject}
          onSelectProject={onSelectProject}
          renderRows={renderSessionList}
        />
      )
    )

    inner = dndActive ? (
      <SortableContext items={groups.map(g => wsId(g.id))} strategy={verticalListSortingStrategy}>
        {groupNodes}
      </SortableContext>
    ) : (
      groupNodes
    )
  } else if (flatVirtualized) {
    inner = (
      <VirtualSessionList
        activeSessionId={activeSessionId}
        onArchiveSession={onArchiveSession}
        onDeleteSession={onDeleteSession}
        onMoveSessionToProject={onMoveSessionToProject}
        onResumeSession={onResumeSession}
        onTogglePin={onTogglePin}
        pinned={pinned}
        projectMoveTargets={projectMoveTargets}
        sessions={sessions}
        sortable={sortable}
        workingSessionIdSet={workingSessionIdSet}
      />
    )
  } else {
    inner = renderSessionList(sessions)
  }

  const body =
    dndActive && !showEmptyState ? (
      <DndContext collisionDetection={closestCenter} onDragEnd={onReorder} sensors={dndSensors}>
        {inner}
      </DndContext>
    ) : (
      inner
    )

  // The virtualizer owns its own scroller, so suppress the wrapper's overflow
  // to avoid a double scroll container.
  const resolvedContentClassName = cn(contentClassName, flatVirtualized && 'overflow-y-visible')

  return (
    <SidebarGroup className={rootClassName}>
      <SidebarSectionHeader action={headerAction} label={label} meta={labelMeta} onToggle={onToggle} open={open} />
      {open && (
        <SidebarGroupContent className={resolvedContentClassName}>
          {body}
          {footer}
        </SidebarGroupContent>
      )}
    </SidebarGroup>
  )
}

interface SidebarWorkspaceGroupProps extends React.ComponentProps<'div'> {
  group: SidebarSessionGroup
  renderRows: (sessions: SessionInfo[], group?: SidebarSessionGroup) => React.ReactNode
  onNewSession?: (path: null | string) => void
  onNewSessionInProject?: (projectId: string, projectName: string) => void
  onSelectProject?: (projectId: string, projectName: string) => void
  active?: boolean
  reorderable?: boolean
  dragging?: boolean
  dragHandleProps?: React.HTMLAttributes<HTMLElement>
}

function SidebarWorkspaceGroup({
  group,
  renderRows,
  onNewSession,
  onNewSessionInProject,
  onSelectProject,
  active = false,
  reorderable = false,
  dragging = false,
  dragHandleProps,
  className,
  style,
  ref,
  ...rest
}: SidebarWorkspaceGroupProps) {
  const { t } = useI18n()
  const s = t.sidebar
  const isProfileGroup = group.mode === 'profile'
  const isProjectGroup = group.mode === 'project'
  const pageStep = isProfileGroup ? PROFILE_INITIAL_PAGE : WORKSPACE_PAGE
  const [open, setOpen] = useState(true)
  const [visibleCount, setVisibleCount] = useState(pageStep)

  const loadedCount = group.sessions.length
  // Profile groups know their on-disk total (children excluded); workspace
  // groups only ever page within what's already loaded.
  const totalCount = isProfileGroup || isProjectGroup ? Math.max(group.totalCount ?? loadedCount, loadedCount) : loadedCount
  const visibleSessions = group.sessions.slice(0, visibleCount)
  const hiddenCount = Math.max(0, totalCount - visibleSessions.length)
  const nextCount = Math.min(pageStep, hiddenCount)

  // Reveal already-loaded rows first; only hit the backend when the next page
  // crosses what's been fetched for this profile.
  const handleProfileLoadMore = () => {
    const target = visibleCount + pageStep

    setVisibleCount(target)

    if (target > loadedCount && loadedCount < totalCount) {
      group.onLoadMore?.()
    }
  }

  return (
    <div
      className={cn(
        'grid gap-px',
        active && 'rounded-md border border-(--ui-accent)/35 bg-(--ui-control-active-background)',
        dragging && 'z-10 opacity-60',
        className
      )}
      ref={ref}
      style={style}
      {...rest}
    >
      <div className="group/workspace flex min-h-6 items-center gap-1 px-2 pt-1 text-[0.6875rem] font-medium text-(--ui-text-tertiary)">
        <button
          className="flex min-w-0 items-center gap-1.5 bg-transparent text-left hover:text-(--ui-text-secondary)"
          onClick={() => {
            if (isProjectGroup) {
              onSelectProject?.(group.id, group.label)
            }

            setOpen(value => !value)
          }}
          type="button"
        >
          {group.color ? (
            <span aria-hidden="true" className="size-2 shrink-0 rounded-full" style={{ backgroundColor: group.color }} />
          ) : null}
          <span className="truncate">{group.label}</span>
          {active && isProjectGroup ? (
            <span className="rounded-full border border-(--ui-accent)/35 px-1.5 py-px text-[0.625rem] font-medium text-(--ui-accent)">
              Current
            </span>
          ) : null}
          <SidebarCount>
            {isProfileGroup ? countLabel(visibleSessions.length, totalCount) : group.sessions.length}
          </SidebarCount>
          <DisclosureCaret
            className="text-(--ui-text-tertiary) opacity-0 transition group-hover/workspace:opacity-100"
            open={open}
          />
        </button>
        {(onNewSession || onNewSessionInProject || isProfileGroup) && (
          <Tip label={s.newSessionIn(group.label)}>
            <button
              aria-label={s.newSessionIn(group.label)}
              className={cn(
                'grid size-4 shrink-0 place-items-center rounded-sm bg-transparent text-(--ui-text-quaternary) opacity-0 transition-opacity hover:bg-(--ui-control-hover-background) hover:text-foreground group-hover/workspace:opacity-100',
                active && isProjectGroup && 'opacity-100 text-(--ui-text-secondary)'
              )}
              // Profile groups start a fresh session in that profile but keep the
              // all-profiles browse view (newSessionInProfile leaves the scope
              // alone); workspace groups seed the new session's cwd from the path.
              onClick={() =>
                isProfileGroup
                  ? newSessionInProfile(group.id)
                  : isProjectGroup
                    ? onNewSessionInProject?.(group.id, group.label)
                    : onNewSession?.(group.path)
              }
              type="button"
            >
              <Codicon name="add" size="0.75rem" />
            </button>
          </Tip>
        )}
        {reorderable && (
          <span
            {...dragHandleProps}
            aria-label={s.reorderWorkspace(group.label)}
            className="ml-auto -my-0.5 grid w-4 shrink-0 cursor-grab touch-none place-items-center self-stretch overflow-hidden active:cursor-grabbing"
            onClick={event => event.stopPropagation()}
          >
            <Codicon
              className={cn(
                'text-(--ui-text-quaternary) opacity-0 transition-opacity group-hover/workspace:opacity-80 hover:text-(--ui-text-secondary)',
                dragging && 'text-(--ui-text-secondary) opacity-100'
              )}
              name="grabber"
              size="0.75rem"
            />
          </span>
        )}
      </div>
      {open && (
        <>
          {visibleSessions.length ? (
            renderRows(visibleSessions, group)
          ) : isProjectGroup ? (
            <div className="grid gap-1 rounded-md px-2 py-1.5 text-[0.75rem] text-(--ui-text-tertiary)">
              <span>No chats in this project yet.</span>
              {onNewSessionInProject ? (
                <button
                  className="w-fit rounded border border-(--ui-stroke-tertiary) px-2 py-1 text-[0.6875rem] font-medium text-(--ui-text-secondary) hover:bg-(--ui-control-hover-background) hover:text-foreground"
                  onClick={() => onNewSessionInProject(group.id, group.label)}
                  type="button"
                >
                  Start project chat
                </button>
              ) : null}
            </div>
          ) : null}
          {hiddenCount > 0 &&
            (isProfileGroup ? (
              <SidebarLoadMoreRow loading={Boolean(group.loadingMore)} onClick={handleProfileLoadMore} step={nextCount} />
            ) : (
              <Tip label={s.showMoreIn(nextCount, group.label)}>
                <button
                  aria-label={s.showMoreIn(nextCount, group.label)}
                  className="ml-auto grid size-5 place-items-center rounded-sm bg-transparent text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-control-hover-background) hover:text-foreground"
                  onClick={() => setVisibleCount(count => count + WORKSPACE_PAGE)}
                  type="button"
                >
                  <Codicon name="ellipsis" size="0.75rem" />
                </button>
              </Tip>
            ))}
        </>
      )}
    </div>
  )
}

interface SortableWorkspaceProps {
  group: SidebarSessionGroup
  renderRows: (sessions: SessionInfo[], group?: SidebarSessionGroup) => React.ReactNode
  onNewSession?: (path: null | string) => void
  onNewSessionInProject?: (projectId: string, projectName: string) => void
  onSelectProject?: (projectId: string, projectName: string) => void
  active?: boolean
}

function SortableSidebarWorkspaceGroup(props: SortableWorkspaceProps) {
  return <SidebarWorkspaceGroup {...props} {...useSortableBindings(wsId(props.group.id))} />
}

function SidebarCount({ children }: { children: React.ReactNode }) {
  return <span className="text-[0.6875rem] font-medium text-(--ui-text-quaternary)">{children}</span>
}

interface SortableSessionRowProps {
  hideCurrentProjectMove?: boolean
  session: SessionInfo
  isPinned: boolean
  isSelected: boolean
  isWorking: boolean
  onArchive: () => void
  onDelete: () => void
  onMoveToProject?: (projectId: string, projectName: string) => void
  onPin: () => void
  onResume: () => void
  projectMoveTargets?: ProjectMoveTarget[]
}

function SortableSidebarSessionRow(props: SortableSessionRowProps) {
  return <SidebarSessionRow {...props} {...useSortableBindings(props.session.id)} />
}

interface SidebarLoadMoreRowProps {
  loading: boolean
  onClick: () => void
  step: number
}

function SidebarLoadMoreRow({ loading, onClick, step }: SidebarLoadMoreRowProps) {
  const { t } = useI18n()
  const label = loading ? t.sidebar.loading : step > 0 ? t.sidebar.loadCount(step) : t.sidebar.loadMore

  return (
    <button
      className="flex min-h-5 items-center gap-1.5 self-start bg-transparent pl-2 text-left text-[0.6875rem] text-(--ui-text-tertiary) transition-colors duration-100 ease-out hover:text-foreground hover:transition-none disabled:cursor-default disabled:opacity-60 disabled:hover:text-(--ui-text-tertiary)"
      disabled={loading}
      onClick={onClick}
      type="button"
    >
      {/* Seat the icon in the same w-3.5 column session rows use for their dot
          so the chevron + label line up with the rows above. */}
      <span className="grid w-3.5 shrink-0 place-items-center">
        <Codicon className="opacity-70" name={loading ? 'loading' : 'chevron-down'} size="0.75rem" spinning={loading} />
      </span>
      <span>{label}</span>
    </button>
  )
}
