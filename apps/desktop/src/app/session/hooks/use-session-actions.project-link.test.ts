import { describe, expect, it } from 'vitest'

import source from './use-session-actions.ts?raw'

describe('native project chat session linking', () => {
  it('announces successful Mission Control project links so the sidebar refreshes', () => {
    expect(source).toContain('notifyMissionControlProjectLinkCreated')
    expect(source).toContain('createMissionControlSessionProjectLink')
    expect(source).toContain('sessionId: stored')
  })

  it('does not silently swallow project link failures', () => {
    const linkStart = source.indexOf('void createMissionControlSessionProjectLink({')
    const linkEnd = source.indexOf('setFreshDraftReady(false)', linkStart)
    const linkBlock = source.slice(linkStart, linkEnd)

    expect(linkBlock).toContain('Project chat was created, but Mission Control could not link it to ${projectName}')
    expect(linkBlock).toContain('.catch(err => {')
    expect(linkBlock).not.toContain('catch(() => undefined)')
  })
})
