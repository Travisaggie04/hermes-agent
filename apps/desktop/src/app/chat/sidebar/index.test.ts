import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('chat sidebar project workspace affordances', () => {
  it('makes project creation and empty project chats visible', () => {
    expect(source).toContain('New project')
    expect(source).toContain('No chats in this project yet.')
    expect(source).toContain('Start project chat')
    expect(source).toContain('onNewSessionInProject(group.id, group.label)')
  })

  it('labels the main new session action as project chat when a project is selected', () => {
    expect(source).toContain('New project chat')
    expect(source).toContain('New chat in ${selectedMissionControlProjectName || selectedMissionControlProjectId}')
  })

  it('keeps the native sidebar project-first after project selection', () => {
    expect(source).toContain('setSidebarRecentsOpen(false)')
    expect(source).toContain('const selectProjectGroup')
    expect(source).toContain('const startProjectChat')
    expect(source).toContain('onSelectProject={selectProjectGroup}')
    expect(source).toContain('onNewSessionInProject={startProjectChat}')
  })

  it('refreshes project groups when a native chat is linked to a project', () => {
    expect(source).toContain('MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('window.addEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('window.removeEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('refreshProjectGroups()')
  })
})
