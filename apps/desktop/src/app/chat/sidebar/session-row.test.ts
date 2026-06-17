import { describe, expect, it } from 'vitest'

import indexSource from './index.tsx?raw'
import source from './session-row.tsx?raw'

describe('sidebar session row project filing affordance', () => {
  it('offers a direct move-to-current-project action without adding a new backend path', () => {
    expect(source).toContain('$selectedMissionControlProjectId')
    expect(source).toContain('$selectedMissionControlProjectName')
    expect(source).toContain('const currentProjectMoveTarget')
    expect(source).toContain('const fileProjectMoveTarget = currentProjectMoveTarget ?? suggestedProjectMoveTarget')
    expect(source).toContain('File ${title} in ${fileProjectMoveTarget.name}')
    expect(source).toContain('onMoveToProject(fileProjectMoveTarget.project_id, fileProjectMoveTarget.name)')
    expect(source).toContain('Codicon name="folder-active"')
  })

  it('can use a backend suggested project target for unfiled chats', () => {
    expect(source).toContain('suggestedProjectMoveTarget?: ProjectMoveTarget')
    expect(source).toContain('suggestedProjectMoveTarget,')
    expect(source).toContain('const fileProjectMoveTarget = currentProjectMoveTarget ?? suggestedProjectMoveTarget')
  })

  it('suppresses the quick move action for chats already shown in the current project group', () => {
    expect(source).toContain('hideCurrentProjectMove')
    expect(source).toContain('!hideCurrentProjectMove && selectedProjectId')
    expect(indexSource).toContain("hideCurrentProjectMove: group?.mode === 'project' && group.id === activeGroupId")
  })
})
