import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  createMissionControlChallengeReview,
  createMissionControlLaneRequest,
  createMissionControlProject,
  createMissionControlProjectBrief,
  getMissionControlChallengeReviews,
  getMissionControlLaneRequests,
  getMissionControlProjectBriefs,
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
    await getMissionControlProjectBriefs()
    await getMissionControlChallengeReviews()
    await getMissionControlLaneRequests()
    await getMissionControlReports()
    await getMissionControlProjectState()

    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace-status' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/projects' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/project-briefs' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/challenge-reviews' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/lane-requests' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/reports' })
    expect(api).toHaveBeenCalledWith({ path: '/api/plugins/mission-control-governance/workspace/project-state' })

    for (const [request] of api.mock.calls as Array<[{ method?: string; body?: unknown }]>) {
      expect(request.method).toBeUndefined()
      expect(request.body).toBeUndefined()
    }
  })

  it('uses explicit inert POST endpoints for project intake, challenge, and lane draft records', async () => {
    const api = vi.fn().mockResolvedValue({})
    vi.stubGlobal('window', { hermesDesktop: { api } })

    await createMissionControlProject({
      current_goal: 'Make Jenny reliable.',
      name: 'Hermes / Mission Control',
      project_id: 'project-hermes-mission-control',
      status: 'active'
    })
    await createMissionControlProjectBrief({
      constraints: ['No gateway restart'],
      name: 'Hermes initial brief',
      outcome: 'Make Jenny reliable.',
      project_id: 'project-hermes-mission-control',
      status: 'active',
      success_criteria: ['Chat-first project workspace']
    })
    await createMissionControlChallengeReview({
      decision_state: 'needs_spec_first',
      project_id: 'project-hermes-mission-control',
      request_summary: 'Clarify Mission Control project rooms'
    })
    await createMissionControlLaneRequest({
      objective: 'Inspect project room usability.',
      project_id: 'project-hermes-mission-control',
      title: 'Read-only project room usability check'
    })

    expect(api).toHaveBeenCalledWith({
      body: {
        current_goal: 'Make Jenny reliable.',
        name: 'Hermes / Mission Control',
        project_id: 'project-hermes-mission-control',
        status: 'active'
      },
      method: 'POST',
      path: '/api/plugins/mission-control-governance/workspace/projects/create'
    })
    expect(api).toHaveBeenCalledWith({
      body: {
        constraints: ['No gateway restart'],
        name: 'Hermes initial brief',
        outcome: 'Make Jenny reliable.',
        project_id: 'project-hermes-mission-control',
        status: 'active',
        success_criteria: ['Chat-first project workspace']
      },
      method: 'POST',
      path: '/api/plugins/mission-control-governance/workspace/project-briefs/create'
    })
    expect(api).toHaveBeenCalledWith({
      body: {
        decision_state: 'needs_spec_first',
        project_id: 'project-hermes-mission-control',
        request_summary: 'Clarify Mission Control project rooms'
      },
      method: 'POST',
      path: '/api/plugins/mission-control-governance/workspace/challenge-reviews/create'
    })
    expect(api).toHaveBeenCalledWith({
      body: {
        objective: 'Inspect project room usability.',
        project_id: 'project-hermes-mission-control',
        title: 'Read-only project room usability check'
      },
      method: 'POST',
      path: '/api/plugins/mission-control-governance/workspace/lane-requests/create'
    })
  })
})
