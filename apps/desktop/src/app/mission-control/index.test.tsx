import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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

const realProjects = [
  ['project-hermes-mission-control', 'Hermes / Mission Control'],
  ['project-long-form-video', 'Long-form Video'],
  ['project-shorts-video', 'Shorts Video'],
  ['project-tool-tally', 'Tool & Tally'],
  ['project-waha-work', 'Waha Work']
] as const

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
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined)
    }
  })

  getMissionControlWorkspaceStatus.mockResolvedValue({
    accepted_baseline: {
      head: '9f8863c0bf28dc0b7da702480b9b3337b983e7e8',
      runtime_path: '/home/jenny/.hermes/hermes-runtime-project-seed-9f8863c'
    },
    lane: { active_lane_count: 0 },
    runtime_worktree_guard: { decision_state: 'pass' },
    safety: { dispatch_in_gateway: false, send_to_jenny_enabled: false },
    stale_context: { warnings: [] }
  })
  getMissionControlProjects.mockResolvedValue({
    count: 6,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    projects: [
      {
        record: {
          project_id: 'project-smoke',
          name: 'Smoke Test Project',
          status: 'smoke-test',
          current_goal: 'Verify smoke behavior.',
          next_recommended_lane: 'Smoke lane',
          source_of_truth: 'Smoke fixture'
        },
        record_type: 'ProjectRecord'
      },
      ...realProjects.map(([project_id, name]) => ({
        record: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        record_type: 'ProjectRecord'
      }))
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
          project_id: 'project-hermes-mission-control',
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
          project_id: 'project-hermes-mission-control',
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
    count: 6,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    stored: false,
    project_states: [
      {
        project_id: 'project-smoke',
        name: 'Smoke Test Project',
        status: 'smoke-test',
        current_goal: 'Verify smoke behavior.',
        latest_report_summary: 'Smoke report.',
        latest_result: 'Smoke result.',
        risks: ['none'],
        blockers: [],
        next_recommended_lane: 'Smoke lane'
      },
      {
        project_id: 'project-hermes-mission-control',
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
          project_id: 'project-hermes-mission-control',
          title: 'Read-only status refresh',
          status: 'draft'
        },
        latest_report: {
          report_id: 'report-1',
          project_id: 'project-hermes-mission-control',
          summary: 'Jenny finished the desktop architecture review.',
          result: 'Use Mission Control backend with desktop frontend.',
          risks: ['dashboard overbuild'],
          blockers: ['none'],
          next_recommended_lane: 'Desktop read-only workspace v1'
        }
      },
      ...realProjects.slice(1).map(([project_id, name]) => ({
        project_id,
        name,
        status: `${name} status`,
        current_goal: `${name} goal`,
        latest_report_summary: '',
        latest_result: '',
        risks: [],
        blockers: [],
        next_recommended_lane: `${name} next lane`
      }))
    ]
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MissionControlView', () => {
  it('fetches read-only Mission Control endpoints and renders the five real projects as primary cards', async () => {
    await renderMissionControl()

    await waitFor(() => expect(getMissionControlProjectState).toHaveBeenCalledTimes(1))
    expect(getMissionControlWorkspaceStatus).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjects).toHaveBeenCalledTimes(1)
    expect(getMissionControlLaneRequests).toHaveBeenCalledTimes(1)
    expect(getMissionControlReports).toHaveBeenCalledTimes(1)

    expect(screen.getByText('Real project workspace')).toBeTruthy()
    expect(screen.getByText('5 of 5 real projects loaded')).toBeTruthy()

    for (const [, name] of realProjects) {
      expect(await screen.findByText(name)).toBeTruthy()
      expect(screen.getAllByText('Primary project').length).toBeGreaterThanOrEqual(5)
    }
  })

  it('shows real project state, fallback empty-state copy, and disabled safety flags', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Jenny finished the desktop architecture review.')).toBeTruthy()
    expect(screen.getByText('Use Mission Control backend with desktop frontend.')).toBeTruthy()
    expect(screen.getByText('dashboard overbuild · none')).toBeTruthy()
    expect(screen.getByText('Desktop read-only workspace v1')).toBeTruthy()
    expect(screen.getByText('Read-only status refresh (draft)')).toBeTruthy()
    expect(screen.getAllByText('No report yet').length).toBeGreaterThan(0)
    expect(screen.getAllByText('No result yet').length).toBeGreaterThan(0)
    expect(screen.getAllByText('None recorded').length).toBeGreaterThan(0)
    expect(screen.getAllByText('send_to_jenny: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dispatch: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('execution: disabled').length).toBeGreaterThan(0)
  })

  it('de-emphasizes smoke records outside the primary workspace', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Supporting / smoke records')).toBeTruthy()
    expect(screen.getByText(/Smoke Test Project/)).toBeTruthy()
    expect(screen.getByText(/de-emphasized smoke\/support record/)).toBeTruthy()
  })

  it('copies a bounded manual prompt without enabling send or dispatch', async () => {
    await renderMissionControl()

    const buttons = await screen.findAllByRole('button', { name: 'Copy prompt' })
    fireEvent.click(buttons[0])

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    const prompt = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]
    expect(prompt.length).toBeLessThanOrEqual(2000)
    expect(prompt).toContain('MISSION CONTROL PROJECT LANE')
    expect(prompt).toContain('MANUAL COPY ONLY')
    expect(prompt).toContain('Forbidden: dispatch')
    expect(screen.getAllByText(/Send to Jenny disabled/i).length).toBeGreaterThan(0)
  })

  it('keeps Mission Control view source free of POST, dispatch wiring, timers, storage, and workers', async () => {
    const source = await import('./index?raw')
    const text = source.default as string

    for (const forbidden of [
      "method: 'POST'",
      'method: "POST"',
      '.post(',
      '/dispatch',
      '/execute',
      '/api/plugins/kanban/tasks',
      'session-send',
      'sendSession',
      'localStorage',
      'sessionStorage',
      'setInterval',
      'setTimeout',
      'Worker(',
      'new Worker'
    ]) {
      expect(text).not.toContain(forbidden)
    }
  })
})
