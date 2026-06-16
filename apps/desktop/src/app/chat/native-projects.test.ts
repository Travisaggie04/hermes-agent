import { describe, expect, it } from 'vitest'

import { fallbackProjectGroups, nativeChatProjects } from './native-projects'

describe('native chat projects', () => {
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

  it('provides empty-session fallback groups for the sidebar', () => {
    expect(fallbackProjectGroups()[0]).toMatchObject({
      name: 'Hermes / Mission Control',
      project_id: 'project-hermes-mission-control',
      sessions: []
    })
  })
})
