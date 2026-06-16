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

  it('routes the Jenny OS nav action into the Hermes project chat draft', () => {
    const actionStart = source.indexOf("if (item.action === 'jenny-os')")
    const actionEnd = source.indexOf('if (item.route)', actionStart)
    const actionBlock = source.slice(actionStart, actionEnd)

    expect(actionBlock).toContain('setSelectedMissionControlProject(HERMES_PROJECT_ID, HERMES_PROJECT_NAME)')
    expect(actionBlock).toContain('startFreshSessionDraft()')
    expect(actionBlock).toContain('navigate(NEW_CHAT_ROUTE)')
  })

  it('keeps the relabeled New project chat action from inheriting an unrelated workspace', () => {
    const actionStart = source.indexOf("if (item.action === 'new-session')")
    const actionEnd = source.indexOf("if (item.action === 'jenny-os')", actionStart)
    const actionBlock = source.slice(actionStart, actionEnd)

    expect(actionBlock).toContain('const projectId = $selectedMissionControlProjectId.get().trim()')
    expect(actionBlock).toContain('startFreshSessionDraft()')
    expect(actionBlock).toContain('if (projectId) {')
    expect(actionBlock).toContain("setCurrentCwd('')")
    expect(actionBlock).toContain("setCurrentBranch('')")
  })
})
