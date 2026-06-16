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

  it('deduplicates records and pins Hermes / Mission Control first', () => {
    expect(
      nativeChatProjects([
        { name: 'Tool & Tally', project_id: 'project-tool-tally' },
        { name: 'Hermes / Mission Control', project_id: 'project-hermes-mission-control' },
        { name: 'Duplicate', project_id: 'project-tool-tally' },
        { name: '', project_id: 'missing-name' }
      ]).map(project => project.name)
    ).toEqual(['Hermes / Mission Control', 'Tool & Tally'])
  })

  it('provides empty-session fallback groups for the sidebar', () => {
    expect(fallbackProjectGroups()[0]).toMatchObject({
      name: 'Hermes / Mission Control',
      project_id: 'project-hermes-mission-control',
      sessions: []
    })
  })
})
