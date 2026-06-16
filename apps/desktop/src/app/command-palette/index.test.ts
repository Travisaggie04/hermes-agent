import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('command palette Jenny OS navigation', () => {
  it('makes native Jenny project chat primary and keeps the console secondary', () => {
    expect(source).toContain("const HERMES_PROJECT_ID = 'project-hermes-mission-control'")
    expect(source).toContain('const openJennyOsChat = useCallback')
    expect(source).toContain('setSelectedMissionControlProject(HERMES_PROJECT_ID, HERMES_PROJECT_NAME)')
    expect(source).toContain("id: 'nav-jenny-os-chat'")
    expect(source).toContain("label: 'Jenny OS project chat'")
    expect(source).toContain("keywords: ['mission control', 'projects', 'workspace', 'chat', 'jenny', 'primary']")
    expect(source).toContain("label: 'Advanced audit console'")
    expect(source).toContain("keywords: ['advanced', 'audit', 'reports', 'lanes', 'debug', 'guardrails']")
  })
})
