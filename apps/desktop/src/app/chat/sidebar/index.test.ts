import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('chat sidebar project workspace affordances', () => {
  it('makes project creation and empty project chats visible', () => {
    expect(source).toContain('New project')
    expect(source).toContain('aria-label="Create project"')
    expect(source).not.toContain('Create a guarded project')
    expect(source).toContain('No chats in this project yet.')
    expect(source).toContain('Start project chat')
    expect(source).toContain('onNewSessionInProject(group.id, group.label)')
  })

  it('makes new project setup capture evidence and approval stop rules', () => {
    expect(source).toContain('Evidence Jenny must return, one per line')
    expect(source).toContain('Approval or stop rules, one per line')
    expect(source).toContain('Jenny must define evidence, tests, rollback/stop conditions, and approval needs before broad work.')
    expect(source).toContain('Evidence required: ${item}')
    expect(source).toContain('Approval/stop rule: ${item}')
    expect(source).toContain("setProjectIntake({ approval: '', evidence: '', forbidden: '', goal: '', name: '', source: '', success: '' })")
  })

  it('makes Jenny OS the primary native project chat entry', () => {
    expect(source).toContain("label: 'Jenny OS'")
    expect(source).toContain("action: 'jenny-os'")
    expect(source).toContain('Open Jenny chat in ${HERMES_PROJECT_NAME}')
    expect(source).toContain("item.action === 'jenny-os' && currentView === 'chat' && Boolean(selectedMissionControlProjectId.trim())")
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

  it('pins the selected project to the top of the native project list', () => {
    expect(source).toContain('const visibleProjectGroups = useMemo')
    expect(source).toContain('const activeProjectId = selectedMissionControlProjectId.trim()')
    expect(source).toContain('if (a.id === activeProjectId) {')
    expect(source).toContain('return -1')
    expect(source).toContain('groups={visibleProjectGroups}')
    expect(source).toContain('sessions={visibleProjectGroups.flatMap(group => group.sessions)}')
  })

  it('marks the selected project as current instead of exposing Mission Control details', () => {
    expect(source).toContain("active && 'rounded-md border border-(--ui-accent)/35 bg-(--ui-control-active-background)'")
    expect(source).toContain('active && isProjectGroup')
    expect(source).toContain('Current')
  })

  it('keeps the new-chat button visible for the selected project', () => {
    expect(source).toContain("active && isProjectGroup && 'opacity-100 text-(--ui-text-secondary)'")
    expect(source).toContain('isProjectGroup')
    expect(source).toContain('onNewSessionInProject?.(group.id, group.label)')
  })

  it('refreshes project groups when a native chat is linked to a project', () => {
    expect(source).toContain('MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('window.addEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('window.removeEventListener(MISSION_CONTROL_PROJECT_LINK_CREATED')
    expect(source).toContain('refreshProjectGroups()')
  })

  it('selects the project before resuming a project-linked chat', () => {
    expect(source).toContain("if (group?.mode === 'project')")
    expect(source).toContain('onSelectProject?.(group.id, group.label)')
    expect(source).toContain('onResumeSession(session.id)')
    expect(source).toContain('renderRows(visibleSessions, group)')
  })

  it('makes old sessions secondary while a project is selected', () => {
    expect(source).toContain('const projectMode = Boolean(selectedMissionControlProjectId.trim())')
    expect(source).toContain("const recentsLabel = projectMode ? 'Unfiled chats' : s.sessions")
    expect(source).toContain("const recentsRootClassName = projectMode ? 'shrink-0 p-0 pb-1 opacity-90' : 'min-h-0 flex-1 p-0'")
    expect(source).toContain("'flex max-h-52 shrink-0 flex-col overflow-y-auto overscroll-contain rounded-lg pb-1.75'")
    expect(source).toContain('label={recentsLabel}')
    expect(source).toContain('labelMeta={projectMode ? undefined : recentsMeta}')
    expect(source).toContain('rootClassName={recentsRootClassName}')
  })

  it('keeps project-linked chats out of the unfiled recents list while project mode is active', () => {
    expect(source).toContain('const projectLinkedSessionIds = useMemo')
    expect(source).toContain('for (const group of projectGroups)')
    expect(source).toContain('ids.add(session.id)')
    expect(source).toContain('ids.add(session._lineage_root_id)')
    expect(source).toContain('if (!projectMode) {')
    expect(source).toContain("!projectLinkedSessionIds.has(session.id) && !projectLinkedSessionIds.has(session._lineage_root_id || '')")
  })

  it('keeps project groups visible if one Mission Control project endpoint is unavailable', () => {
    expect(source).toContain('Promise.allSettled([getMissionControlProjects(), getMissionControlProjectSessions()])')
    expect(source).toContain("projectsResult.status === 'fulfilled' ? nativeChatProjects")
    expect(source).toContain("sessionsResult.status === 'fulfilled' ? sessionsResult.value.groups || [] : []")
  })
})
