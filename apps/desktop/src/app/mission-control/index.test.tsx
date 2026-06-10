import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMissionControlWorkspaceStatus = vi.fn()
const getMissionControlProjects = vi.fn()
const getMissionControlLaneRequests = vi.fn()
const getMissionControlReports = vi.fn()
const getMissionControlProjectState = vi.fn()

vi.mock('@/hermes', () => ({
  getMissionControlWorkspaceStatus: () => getMissionControlWorkspaceStatus(),
  getMissionControlProjects: () => getMissionControlProjects(),
  getMissionControlLaneRequests: () => getMissionControlLaneRequests(),
  getMissionControlReports: () => getMissionControlReports(),
  getMissionControlProjectState: () => getMissionControlProjectState()
}))

function renderMissionControl() {
  return import('./index').then(({ MissionControlView }) =>
    render(
      <MemoryRouter initialEntries={['/mission-control']}>
        <MissionControlView />
      </MemoryRouter>
    )
  )
}

beforeEach(() => {
  getMissionControlWorkspaceStatus.mockResolvedValue({
    accepted_baseline: {
      head: '53c3c9f4c36a2d2da20b2b67c44d7d7ef3940e0c',
      runtime_path: '/home/jenny/.hermes/hermes-runtime-project-state-projection-53c3c9f'
    },
    lane: { active_lane_count: 0 },
    runtime_worktree_guard: { decision_state: 'pass' },
    safety: { dispatch_in_gateway: false, send_to_jenny_enabled: false },
    stale_context: { warnings: [] }
  })
  getMissionControlProjects.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    projects: [
      {
        record: {
          project_id: 'project-hermes',
          name: 'Hermes / Mission Control',
          status: 'Live workspace',
          current_goal: 'Make desktop the main workspace.',
          next_recommended_lane: 'Desktop read-only Mission Control page',
          source_of_truth: 'Mission Control records'
        },
        record_type: 'ProjectRecord'
      }
    ]
  })
  getMissionControlLaneRequests.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    lane_requests: [
      {
        record: {
          lane_request_id: 'lane-1',
          project_id: 'project-hermes',
          title: 'Read-only status refresh',
          status: 'draft'
        },
        record_type: 'LaneRequestRecord'
      }
    ]
  })
  getMissionControlReports.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    reports: [
      {
        record: {
          report_id: 'report-1',
          project_id: 'project-hermes',
          summary: 'Jenny finished the desktop architecture review.',
          result: 'Use Mission Control backend with desktop frontend.',
          risks: ['dashboard overbuild'],
          blockers: ['none'],
          next_recommended_lane: 'Desktop read-only workspace v1'
        },
        record_type: 'JennyReportRecord'
      }
    ]
  })
  getMissionControlProjectState.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    stored: false,
    project_states: [
      {
        project_id: 'project-hermes',
        name: 'Hermes / Mission Control',
        status: 'Live workspace',
        current_goal: 'Make desktop the main workspace.',
        latest_report_summary: 'Jenny finished the desktop architecture review.',
        latest_result: 'Use Mission Control backend with desktop frontend.',
        risks: ['dashboard overbuild'],
        blockers: ['none'],
        next_recommended_lane: 'Desktop read-only workspace v1',
        latest_lane_request: {
          lane_request_id: 'lane-1',
          project_id: 'project-hermes',
          title: 'Read-only status refresh',
          status: 'draft'
        },
        latest_report: {
          report_id: 'report-1',
          project_id: 'project-hermes',
          summary: 'Jenny finished the desktop architecture review.',
          result: 'Use Mission Control backend with desktop frontend.',
          risks: ['dashboard overbuild'],
          blockers: ['none'],
          next_recommended_lane: 'Desktop read-only workspace v1'
        }
      }
    ]
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MissionControlView', () => {
  it('fetches read-only Mission Control endpoints and renders project state', async () => {
    await renderMissionControl()

    await waitFor(() => expect(getMissionControlProjectState).toHaveBeenCalledTimes(1))
    expect(getMissionControlWorkspaceStatus).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjects).toHaveBeenCalledTimes(1)
    expect(getMissionControlLaneRequests).toHaveBeenCalledTimes(1)
    expect(getMissionControlReports).toHaveBeenCalledTimes(1)

    expect(await screen.findByText('Hermes / Mission Control')).toBeTruthy()
    expect(screen.getByText('Jenny finished the desktop architecture review.')).toBeTruthy()
    expect(screen.getByText('Use Mission Control backend with desktop frontend.')).toBeTruthy()
    expect(screen.getByText('dashboard overbuild · none')).toBeTruthy()
    expect(screen.getByText('Desktop read-only workspace v1')).toBeTruthy()
    expect(screen.getByText('Read-only status refresh (draft)')).toBeTruthy()
  })

  it('shows workspace-status guard summary and disabled send boundary', async () => {
    await renderMissionControl()

    expect(await screen.findByText('pass')).toBeTruthy()
    expect(screen.getByText('dispatch_in_gateway')).toBeTruthy()
    expect(screen.getByText('active_lane_count')).toBeTruthy()
    expect(screen.getAllByText(/Send to Jenny disabled/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/No dispatch, queue mutation, protected-domain mutation, routing change, guard enforcement, or hidden worker/i)).toBeTruthy()
  })
})
