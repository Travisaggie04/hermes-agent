import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  getMissionControlLaneRequests,
  getMissionControlProjects,
  getMissionControlProjectState,
  getMissionControlReports,
  getMissionControlWorkspaceStatus
} from './hermes'

describe('Mission Control desktop API helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('uses GET-only Mission Control backend endpoints', async () => {
    const api = vi.fn().mockResolvedValue({})
    vi.stubGlobal('window', { hermesDesktop: { api } })

    await getMissionControlWorkspaceStatus()
    await getMissionControlProjects()
    await getMissionControlLaneRequests()
    await getMissionControlReports()
    await getMissionControlProjectState()

    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace-status' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/projects' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/lane-requests' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/reports' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/project-state' })

    for (const [request] of api.mock.calls as Array<[{ method?: string; body?: unknown }]>) {
      expect(request.method).toBeUndefined()
      expect(request.body).toBeUndefined()
    }
  })
})
