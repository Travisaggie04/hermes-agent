import { describe, expect, it } from 'vitest'

import {
  fallbackProjectGroups,
  NATIVE_PROJECT_SESSION_LIMIT,
  nativeChatProjects,
  nativeProjectChatModel,
  projectSessionStableId,
  UNASSIGNED_PROJECT_GROUP_ID
} from './native-projects'

describe('native chat projects', () => {
  it('uses the widest safe Mission Control session window for native project grouping', () => {
    expect(NATIVE_PROJECT_SESSION_LIMIT).toBe(50)
  })

  it('keeps the native Jenny workspace project-first when Mission Control project records are unavailable', () => {
    expect(nativeChatProjects().map(project => project.name)).toEqual([
      'Hermes / Mission Control',
      'Long-form Video',
      'Shorts Video',
      'Tool & Tally',
      'Waha Work'
    ])
  })

  it('deduplicates records, pins Hermes / Mission Control first, and keeps missing anchors visible', () => {
    expect(
      nativeChatProjects([
        { name: 'Tool & Tally', project_id: 'project-tool-tally' },
        { name: 'Hermes / Mission Control', project_id: 'project-hermes-mission-control' },
        { name: 'Duplicate', project_id: 'project-tool-tally' },
        { name: '', project_id: 'missing-name' }
      ]).map(project => project.name)
    ).toEqual(['Hermes / Mission Control', 'Long-form Video', 'Shorts Video', 'Tool & Tally', 'Waha Work'])
  })

  it('keeps backend project details when filling missing default anchors', () => {
    expect(
      nativeChatProjects([{ current_goal: 'Recover Jenny OS', name: 'Hermes / Mission Control', project_id: 'project-hermes-mission-control' }])
    ).toEqual([
      expect.objectContaining({ current_goal: 'Recover Jenny OS', name: 'Hermes / Mission Control' }),
      expect.objectContaining({ name: 'Long-form Video', status: 'on_hold' }),
      expect.objectContaining({ name: 'Shorts Video', status: 'on_hold' }),
      expect.objectContaining({ name: 'Tool & Tally', status: 'on_hold' }),
      expect.objectContaining({ name: 'Waha Work', status: 'on_hold' })
    ])
  })

  it('keeps smoke and fixture records out of the native chat project picker', () => {
    const names = nativeChatProjects([
      { name: 'Smoke Test Project', project_id: 'project-smoke-test' },
      { name: 'Fixture Review', project_id: 'project-fixture-review' },
      { name: 'Personal Admin', project_id: 'project-personal-admin' }
    ]).map(project => project.name)

    expect(names).toContain('Personal Admin')
    expect(names).not.toContain('Smoke Test Project')
    expect(names).not.toContain('Fixture Review')
  })

  it('provides empty-session fallback groups for the sidebar', () => {
    expect(fallbackProjectGroups()[0]).toMatchObject({
      name: 'Hermes / Mission Control',
      project_id: 'project-hermes-mission-control',
      sessions: []
    })
  })

  it('normalizes project chat sessions to durable ids for header and intro reuse', () => {
    expect(projectSessionStableId({ durable_session_id: 'session-root', session_id: 'session-tip' })).toBe('session-root')
    expect(projectSessionStableId({ session_id: 'session-tip' })).toBe('session-tip')

    const model = nativeProjectChatModel(
      [{ name: 'Hermes / Mission Control', project_id: 'project-hermes-mission-control' }],
      [
        {
          linked_session_count: 1,
          name: 'Hermes / Mission Control',
          project_id: 'project-hermes-mission-control',
          sessions: [{ durable_session_id: 'session-root', session_id: 'session-tip', title: 'Durable chat' }]
        },
        {
          name: 'Unassigned / General',
          project_id: UNASSIGNED_PROJECT_GROUP_ID,
          sessions: [{ durable_session_id: 'legacy-root', session_id: 'legacy-tip', title: 'Legacy chat' }]
        }
      ]
    )

    expect(model.projects[0].lastSessionId).toBe('session-root')
    expect(model.projects[0].recentSessions[0]).toEqual({ id: 'session-root', title: 'Durable chat' })
    expect(model.otherChats[0]).toEqual({ id: 'legacy-root', title: 'Legacy chat' })
  })

  it('uses linked session ids when detailed project session rows are unavailable', () => {
    const model = nativeProjectChatModel(
      [{ name: 'Hermes / Mission Control', project_id: 'project-hermes-mission-control' }],
      [
        {
          linked_session_count: 2,
          linked_session_ids: ['root-recent', 'root-older'],
          name: 'Hermes / Mission Control',
          project_id: 'project-hermes-mission-control',
          sessions: []
        }
      ]
    )

    expect(model.projects[0]).toMatchObject({
      lastSessionId: 'root-recent',
      lastSessionTitle: 'Saved chat',
      sessionCount: 2
    })
    expect(model.projects[0].recentSessions).toEqual([
      { id: 'root-recent', title: 'Saved chat 1' },
      { id: 'root-older', title: 'Saved chat 2' }
    ])
  })
})
