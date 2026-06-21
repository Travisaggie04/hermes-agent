import type { MissionControlProjectRecord, MissionControlProjectSession, MissionControlProjectSessionGroup } from '@/hermes'

export const NATIVE_PROJECT_SESSION_LIMIT = 50
export const UNASSIGNED_PROJECT_GROUP_ID = 'unassigned-general'

const RECENT_PROJECT_SESSIONS = 4

export interface NativeProjectChatSession {
  id: string
  title: string
}

export interface NativeProjectChatOption {
  id: string
  lastSessionId: string
  lastSessionTitle: string
  name: string
  recentSessions: NativeProjectChatSession[]
  sessionCount: number
}

export interface NativeProjectChatModel {
  otherChatCount: number
  otherChats: NativeProjectChatSession[]
  projects: NativeProjectChatOption[]
}

export const DEFAULT_NATIVE_CHAT_PROJECTS: MissionControlProjectRecord[] = [
  {
    current_goal: 'Make Jenny reliable enough to coordinate engineering work from desktop and phone.',
    name: 'Hermes / Mission Control',
    next_recommended_lane: 'Continue the Jenny OS recovery lane.',
    project_id: 'project-hermes-mission-control',
    source_of_truth: 'Mission Control records',
    status: 'active'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Long-form Video',
    next_recommended_lane: 'Resume after Jenny can safely supervise project work.',
    project_id: 'project-long-form-video',
    source_of_truth: 'Mission Control project anchor',
    status: 'on_hold'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Shorts Video',
    next_recommended_lane: 'Resume after Jenny can safely supervise project work.',
    project_id: 'project-shorts-video',
    source_of_truth: 'Mission Control project anchor',
    status: 'on_hold'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Tool & Tally',
    next_recommended_lane: 'Resume after Jenny can safely supervise project work.',
    project_id: 'project-tool-tally',
    source_of_truth: 'Mission Control project anchor',
    status: 'on_hold'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Waha Work',
    next_recommended_lane: 'Resume after Jenny can safely supervise project work.',
    project_id: 'project-waha-work',
    source_of_truth: 'Mission Control project anchor',
    status: 'on_hold'
  }
]

function isInternalProject(project: MissionControlProjectRecord): boolean {
  const id = project.project_id?.trim().toLowerCase() || ''
  const name = project.name?.trim().toLowerCase() || ''

  return (
    id.startsWith('project-smoke-') ||
    id.includes('smoke-test') ||
    id.includes('fixture') ||
    /\bsmoke test\b/.test(name) ||
    /\bfixture\b/.test(name)
  )
}

export function nativeChatProjects(projects: MissionControlProjectRecord[] = []): MissionControlProjectRecord[] {
  const seen = new Set<string>()
  const out: MissionControlProjectRecord[] = []

  for (const project of projects) {
    const id = project.project_id?.trim()
    const name = project.name?.trim()

    if (!id || !name || seen.has(id) || isInternalProject(project)) {
      continue
    }

    seen.add(id)
    out.push(project)
  }

  for (const project of DEFAULT_NATIVE_CHAT_PROJECTS) {
    const id = project.project_id?.trim()
    const name = project.name?.trim()

    if (!id || !name || seen.has(id)) {
      continue
    }

    seen.add(id)
    out.push(project)
  }

  return out.sort((a, b) => {
    if (a.project_id === 'project-hermes-mission-control') {
      return -1
    }

    if (b.project_id === 'project-hermes-mission-control') {
      return 1
    }

    return a.name.localeCompare(b.name)
  })
}

export function fallbackProjectGroups(): MissionControlProjectSessionGroup[] {
  return nativeChatProjects().map(project => ({
    name: project.name,
    project_id: project.project_id,
    sessions: []
  }))
}

export function projectSessionStableId(session: MissionControlProjectSession): string {
  return session.durable_session_id?.trim() || session.session_id?.trim() || ''
}

function projectSessionTime(session: MissionControlProjectSession): number {
  return session.last_active || session.started_at || 0
}

function latestProjectSession(group?: MissionControlProjectSessionGroup): MissionControlProjectSession | null {
  return (group?.sessions ?? []).reduce<MissionControlProjectSession | null>(
    (latest, session) => (!latest || projectSessionTime(session) > projectSessionTime(latest) ? session : latest),
    null
  )
}

function projectSessionTitle(session: MissionControlProjectSession): string {
  return session.title?.trim() || session.preview?.trim() || session.session_id
}

function latestProjectSessionTitle(group?: MissionControlProjectSessionGroup): string {
  const latestSession = latestProjectSession(group)

  return latestSession?.title?.trim() || latestSession?.preview?.trim() || ''
}

function recentProjectSessions(group?: MissionControlProjectSessionGroup): NativeProjectChatSession[] {
  return [...(group?.sessions ?? [])]
    .sort((left, right) => projectSessionTime(right) - projectSessionTime(left))
    .slice(0, RECENT_PROJECT_SESSIONS)
    .map(session => ({
      id: projectSessionStableId(session),
      title: projectSessionTitle(session)
    }))
    .filter(session => Boolean(session.id))
}

export function nativeProjectChatModel(
  projects: MissionControlProjectRecord[] = [],
  groups: MissionControlProjectSessionGroup[] = []
): NativeProjectChatModel {
  const sessionGroupsByProject = new Map(groups.map(group => [group.project_id, group]))
  const unassigned = sessionGroupsByProject.get(UNASSIGNED_PROJECT_GROUP_ID)

  return {
    otherChatCount: unassigned?.sessions.length ?? 0,
    otherChats: recentProjectSessions(unassigned),
    projects: nativeChatProjects(projects).map(project => {
      const sessionGroup = sessionGroupsByProject.get(project.project_id)
      const sessionCount = sessionGroup?.linked_session_count ?? sessionGroup?.sessions.length ?? 0
      const latestSession = latestProjectSession(sessionGroup)
      const recentSessions = recentProjectSessions(sessionGroup)

      return {
        id: project.project_id,
        lastSessionId: latestSession ? projectSessionStableId(latestSession) : '',
        lastSessionTitle: latestProjectSessionTitle(sessionGroup),
        name: project.name,
        recentSessions,
        sessionCount
      }
    })
  }
}
