import { describe, expect, it } from 'vitest'

import source from './use-session-actions.ts?raw'

describe('native project chat session linking', () => {
  it('does not create project links during session creation', () => {
    expect(source).not.toContain('createMissionControlSessionProjectLink')
    expect(source).not.toContain('notifyMissionControlProjectLinkCreated')
    expect(source).toContain('Project filing happens in submitPromptText immediately before the')
    expect(source).toContain('avoids writing duplicate')
  })

  it('routes the Jenny OS nav action into the Hermes project chat draft', () => {
    const actionStart = source.indexOf("if (item.action === 'jenny-os')")
    const actionEnd = source.indexOf('if (item.route)', actionStart)
    const actionBlock = source.slice(actionStart, actionEnd)

    expect(actionBlock).toContain('setSelectedMissionControlProject(HERMES_PROJECT_ID, HERMES_PROJECT_NAME)')
    expect(actionBlock).toContain('startFreshSessionDraft()')
    expect(actionBlock).toContain('navigate(NEW_CHAT_ROUTE)')
  })

  it('branches native chat from visible text instead of recovered hidden runtime packets', () => {
    const branchStart = source.indexOf('const branchMessages = currentMessages')
    const branchEnd = source.indexOf("title: 'Branch'", branchStart)
    const branchBlock = source.slice(branchStart, branchEnd)

    expect(branchBlock).toContain('content: chatMessageText(message)')
    expect(branchBlock).not.toContain('chatMessageRuntimeText')
    expect(branchBlock).not.toContain('chatMessageHiddenContext')
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
