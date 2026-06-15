import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('native project chat header', () => {
  it('keeps the header visible for a selected project draft before a session exists', () => {
    expect(source).toContain("const selectedProjectTitle = selectedProjectName.trim()")
    expect(source).toContain("selectedProjectTitle ? 'New project chat' : 'New session'")
    expect(source).toContain('!isRoutedSessionView && !selectedProjectTitle')
  })

  it('does not attach session actions to a project draft with no backend session yet', () => {
    expect(source).toContain('selectedSessionId || activeSessionId ? (')
    expect(source).toContain('<SessionActionsMenu')
    expect(source).toContain('<div className="flex h-6 min-w-0 items-center px-2 [-webkit-app-region:no-drag]">')
  })

  it('shows a slim Jenny status strip for selected project chats', () => {
    expect(source).toContain('function ProjectJennyStatusStrip')
    expect(source).toContain('aria-label="Jenny project status"')
    expect(source).toContain('Project: <span className="font-medium text-foreground">{projectName}</span>')
    expect(source).toContain('<ProjectJennyStatusStrip activeTurnRunning={busy} gatewayOpen={gatewayOpen} />')
  })

  it('shows Jenny as working for the full native chat busy turn', () => {
    expect(source).toContain('activeTurnRunning={busy}')
    expect(source).not.toContain('activeTurnRunning={busy && awaitingResponse}')
  })

  it('keeps the Jenny status strip hidden until a project is selected', () => {
    expect(source).toContain('if (!projectName) {')
    expect(source).toContain('return null')
  })
})
