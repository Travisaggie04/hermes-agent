import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('native project chat header', () => {
  it('keeps the header visible for a selected project draft before a session exists', () => {
    expect(source).toContain("const selectedProjectTitle = selectedProjectName.trim()")
    expect(source).toContain("selectedProjectTitle ? 'New project chat' : 'New session'")
    expect(source).toContain('!isRoutedSessionView && !projectPickerAvailable')
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
    expect(source).toContain('{jennyStatus.summary}')
    expect(source).toContain('<ProjectJennyStatusStrip activeTurnRunning={busy} gatewayOpen={gatewayOpen} />')
  })

  it('makes the native composer feel project-scoped when a project is selected', () => {
    expect(source).toContain('const selectedProjectTitle = selectedProjectName.trim()')
    expect(source).toContain('placeholderOverride={')
    expect(source).toContain('Message Jenny about ${selectedProjectTitle}')
  })

  it('lets the native chat header switch Jenny projects without opening Mission Control', () => {
    expect(source).toContain('getMissionControlProjects')
    expect(source).toContain("queryKey: ['mission-control-projects-native-chat']")
    expect(source).toContain('function ProjectHeaderSelect')
    expect(source).toContain('aria-label="Jenny project"')
    expect(source).toContain('setSelectedMissionControlProject(project?.project_id ?? null, project?.name ?? null)')
  })

  it('keeps the project picker visible on the blank native chat home', () => {
    expect(source).toContain('const projectPickerAvailable = projectsQuery.isLoading || projects.length > 0 || Boolean(selectedProjectTitle)')
    expect(source).toContain('!projectPickerAvailable')
    expect(source).toContain('native chat home can act')
  })

  it('keeps the native project picker scoped to existing project records', () => {
    expect(source).toContain('function nativeChatProjects')
    expect(source).toContain('const seen = new Set<string>()')
    expect(source).toContain('return out.sort((a, b) => a.name.localeCompare(b.name))')
  })

  it('lets the native chat header create a structured Jenny project brief', () => {
    expect(source).toContain('function NativeProjectIntakeDialog')
    expect(source).toContain('Create Jenny project')
    expect(source).toContain('createMissionControlProject({')
    expect(source).toContain('createMissionControlProjectBrief({')
    expect(source).toContain('Jenny must challenge vague, risky, or wrong-approach requests before implementation.')
    expect(source).toContain('setSelectedMissionControlProject(projectId, projectName)')
    expect(source).toContain('Start with a spec-first project setup review.')
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
