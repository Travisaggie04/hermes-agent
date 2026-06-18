import type { MissionControlProjectRecord, MissionControlProjectSessionGroup } from '@/hermes'

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
