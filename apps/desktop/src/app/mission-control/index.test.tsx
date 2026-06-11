import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMissionControlWorkspaceStatus = vi.fn()
const getMissionControlProjects = vi.fn()
const getMissionControlLaneRequests = vi.fn()
const getMissionControlReports = vi.fn()
const getMissionControlProjectState = vi.fn()
const getMissionControlProjectSessions = vi.fn()
const createMissionControlReport = vi.fn()
const createMissionControlSessionProjectLink = vi.fn()

vi.mock('@/hermes', () => ({
  createMissionControlReport: (payload: unknown) => createMissionControlReport(payload),
  createMissionControlSessionProjectLink: (payload: unknown) => createMissionControlSessionProjectLink(payload),
  getMissionControlWorkspaceStatus: () => getMissionControlWorkspaceStatus(),
  getMissionControlProjects: () => getMissionControlProjects(),
  getMissionControlLaneRequests: () => getMissionControlLaneRequests(),
  getMissionControlReports: () => getMissionControlReports(),
  getMissionControlProjectState: () => getMissionControlProjectState(),
  getMissionControlProjectSessions: () => getMissionControlProjectSessions()
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
  createMissionControlReport.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: true,
    report: {
      project_id: 'project-hermes-mission-control',
      report_id: 'report-created',
      summary: 'Manual report saved'
    },
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlSessionProjectLink.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: true,
    record_index: 38,
    record_type: 'SessionProjectLinkRecord',
    send_to_jenny_enabled: false,
    session_project_link: {
      durable_session_id: 'root-suggested-hermes',
      link_id: 'session-project-link-test',
      link_method: 'manual',
      project_id: 'project-hermes-mission-control',
      session_id: 'session-suggested-hermes',
      status: 'active'
    },
    stored: true
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
        artifact_links: ['reports/hermes/desktop-review.md'],
        has_real_report: true,
        latest_activity_at: '2026-06-11T10:00:00Z',
        latest_activity_source: 'report',
        linked_session_count: 1,
        recent_sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-linked-hermes',
            last_active: 1781202705,
            linked_project_id: 'project-hermes-mission-control',
            profile: 'default',
            session_id: 'session-linked-hermes',
            source: 'discord',
            suggested_project_id: '',
            title: 'Mission Control linked session'
          }
        ],
        unassigned_suggestion_count: 2,
        missing_state_fields: [],
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
        has_real_report: false,
        missing_state_fields: ['latest_lane', 'latest_jenny_report', 'latest_result', 'risks_blockers', 'artifact_links'],
        latest_activity_source: 'project',
        risks: [],
        blockers: [],
        next_recommended_lane: `${name} next lane`
      }))
    ]
  })
  getMissionControlProjectSessions.mockResolvedValue({
    active_link_count: 1,
    count: 6,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    groups: [
      {
        linked_session_count: 1,
        name: 'Hermes / Mission Control',
        project_id: 'project-hermes-mission-control',
        sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-linked-hermes',
            last_active: 1781202705,
            linked_project_id: 'project-hermes-mission-control',
            profile: 'default',
            session_id: 'session-linked-hermes',
            source: 'discord',
            suggested_project_id: '',
            title: 'Mission Control linked session'
          }
        ],
        unassigned_suggestion_count: 0
      },
      {
        linked_session_count: 0,
        name: 'Unassigned / General',
        project_id: 'unassigned-general',
        sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-suggested-hermes',
            last_active: 1781202600,
            linked_project_id: '',
            profile: 'default',
            session_id: 'session-suggested-hermes',
            source: 'discord',
            suggested_project_id: 'project-hermes-mission-control',
            title: 'Suggested Mission Control session'
          },
          {
            cwd: '',
            durable_session_id: 'root-general',
            last_active: 1781202500,
            linked_project_id: '',
            profile: 'default',
            session_id: 'session-general',
            source: 'discord',
            suggested_project_id: '',
            title: 'General unassigned session'
          }
        ],
        unassigned_suggestion_count: 1
      }
    ],
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    stored: false,
    trusted_for_execution: false
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
    expect(getMissionControlProjectSessions).toHaveBeenCalledTimes(1)

    expect(screen.getByText('Real project workspace')).toBeTruthy()
    expect(screen.getByText('5 of 5 real projects loaded')).toBeTruthy()

    for (const [, name] of realProjects) {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0)
      expect(screen.getAllByText('Primary project').length).toBeGreaterThanOrEqual(5)
    }
  })

  it('shows real project state, fallback empty-state copy, and disabled safety flags', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Jenny finished the desktop architecture review.')).toBeTruthy()
    expect(screen.getByText('Manual Jenny report ingestion')).toBeTruthy()
    expect(screen.getByText('Save Jenny report manually')).toBeTruthy()
    expect(screen.getByText('Use Mission Control backend with desktop frontend.')).toBeTruthy()
    expect(screen.getByText('dashboard overbuild · none')).toBeTruthy()
    expect(screen.getByText('reports/hermes/desktop-review.md')).toBeTruthy()
    expect(screen.getByText('Live report available')).toBeTruthy()
    expect(screen.getByText('2026-06-11T10:00:00Z (report)')).toBeTruthy()
    expect(screen.getByText('Desktop read-only workspace v1')).toBeTruthy()
    expect(screen.getByText('Read-only status refresh (draft)')).toBeTruthy()
    expect(screen.getAllByText('No report yet').length).toBeGreaterThan(0)
    expect(screen.getAllByText('No result yet').length).toBeGreaterThan(0)
    expect(screen.getAllByText('None recorded').length).toBeGreaterThan(0)
    expect(screen.getAllByText('send_to_jenny: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dispatch: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('execution: disabled').length).toBeGreaterThan(0)
  })

  it('renders linked, suggested, and unassigned sessions without creating source-of-truth links', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Project sessions')).length).toBeGreaterThan(0)
    expect(screen.getByText('1 linked')).toBeTruthy()
    expect(screen.getByText('Mission Control linked session')).toBeTruthy()
    expect(screen.getByText('Suggested sessions — display-only')).toBeTruthy()
    expect(screen.getByText('Suggestions do not create links or become source-of-truth records.')).toBeTruthy()
    expect(screen.getAllByText('Suggested Mission Control session').length).toBeGreaterThan(0)
    expect(screen.getByText('Unassigned / General sessions')).toBeTruthy()
    expect(screen.getByText('2 recent · 1 suggestions')).toBeTruthy()
    expect(screen.getByText('General unassigned session')).toBeTruthy()
    expect(screen.getByText('Suggested: Hermes / Mission Control · display-only')).toBeTruthy()
    expect(screen.getByText('No suggested project')).toBeTruthy()

    expect(createMissionControlReport).not.toHaveBeenCalled()
    expect(createMissionControlSessionProjectLink).not.toHaveBeenCalled()
  })

  it('requires confirmation before suggested sessions write exactly one manual active link record', async () => {
    await renderMissionControl()

    fireEvent.click(await screen.findByRole('button', { name: 'Review link' }))
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getAllByText('Confirm suggested link').length).toBeGreaterThan(0)
    expect(screen.getByText('One append-only SessionProjectLinkRecord will be written.')).toBeTruthy()
    expect(screen.getByText('This does not edit the session database.')).toBeTruthy()
    expect(screen.getByText('This does not send work to Jenny.')).toBeTruthy()
    expect(screen.getByText('This does not dispatch anything.')).toBeTruthy()
    expect(screen.getByText('This does not enable routing.')).toBeTruthy()
    expect(screen.getByText('Suggestions are display-only until confirmed.')).toBeTruthy()
    expect(screen.getByText('Moving a link appends a newer record instead of changing old records.')).toBeTruthy()
    expect(createMissionControlSessionProjectLink).not.toHaveBeenCalled()

    const submit = screen.getByRole('button', { name: 'Confirm suggested link' })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(submit)

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        cwd_snapshot: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
        lineage_root_id: 'root-suggested-hermes',
        link_method: 'manual',
        profile: 'default',
        project_id: 'project-hermes-mission-control',
        session_id: 'session-suggested-hermes',
        source: 'discord',
        status: 'active',
        title_snapshot: 'Suggested Mission Control session'
      })
    )
    expect(getMissionControlProjectSessions).toHaveBeenCalledTimes(2)
  })

  it('requires project selection and checkbox before manual unassigned links', async () => {
    await renderMissionControl()

    const manualButtons = await screen.findAllByRole('button', { name: 'Link manually' })
    fireEvent.click(manualButtons[1])

    const submit = screen.getByRole('button', { name: 'Append manual link record' })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.change(screen.getAllByLabelText('Project').at(-1)!, { target: { value: 'project-tool-tally' } })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(submit)

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        lineage_root_id: 'root-general',
        link_method: 'manual',
        project_id: 'project-tool-tally',
        session_id: 'session-general',
        status: 'active'
      })
    )
  })

  it('moves linked sessions by appending a newer active record for the same durable session id', async () => {
    await renderMissionControl()

    fireEvent.click(await screen.findByRole('button', { name: 'Move link' }))
    fireEvent.change(screen.getAllByLabelText('Project').at(-1)!, { target: { value: 'project-tool-tally' } })
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(screen.getByRole('button', { name: 'Append superseding link record' }))

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        lineage_root_id: 'root-linked-hermes',
        link_method: 'manual',
        project_id: 'project-tool-tally',
        session_id: 'session-linked-hermes',
        status: 'active'
      })
    )
  })

  it('does not expose unlink, removal, bulk, or multi-select linking controls', async () => {
    await renderMissionControl()

    for (const label of [/unlink/i, /remove link/i, /link all/i, /confirm all/i, /bulk/i, /multi-select/i]) {
      expect(screen.queryByRole('button', { name: label })).toBeNull()
    }
  })

  it('de-emphasizes smoke records outside the primary workspace', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Supporting / smoke records')).toBeTruthy()
    expect(screen.getByText(/Smoke Test Project/)).toBeTruthy()
    expect(screen.getByText(/de-emphasized smoke\/support record/)).toBeTruthy()
  })

  it('copies a bounded manual prompt without enabling send or dispatch', async () => {
    await renderMissionControl()

    const buttons = await screen.findAllByRole('button', { name: 'Copy next lane prompt' })
    fireEvent.click(buttons[0])

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    const prompt = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]
    expect(prompt.length).toBeLessThanOrEqual(2000)
    expect(prompt).toContain('PROJECT NEXT LANE')
    expect(prompt).toContain('MANUAL COPY ONLY')
    expect(prompt).toContain('Forbidden actions:')
    expect(prompt).toContain('Send to Jenny remains disabled')
    expect(screen.getAllByText(/Send to Jenny disabled/i).length).toBeGreaterThan(0)
  })

  it('builds distinct project-specific next-lane prompts for all five real projects', async () => {
    const { buildMissionControlCopyPrompt, summarizeWorkspaceStatus } = await import('./index')
    const status = summarizeWorkspaceStatus(await getMissionControlWorkspaceStatus())

    const prompts = realProjects.map(([project_id, name]) =>
      buildMissionControlCopyPrompt({
        project: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        report: null,
        state: null,
        status
      })
    )

    expect(new Set(prompts).size).toBe(5)

    for (const prompt of prompts) {
      expect(prompt.length).toBeLessThanOrEqual(2000)
      expect(prompt).toContain('Allowed actions:')
      expect(prompt).toContain('Forbidden actions:')
      expect(prompt).toContain('Preflight checks:')
      expect(prompt).toContain('Stop conditions:')
      expect(prompt).toContain('Expected report format:')
      expect(prompt).toContain('No prior report/result exists')
    }
  })

  it('keeps project-specific restrictions in the generated lane packets', async () => {
    const { buildMissionControlCopyPrompt, summarizeWorkspaceStatus } = await import('./index')
    const status = summarizeWorkspaceStatus(await getMissionControlWorkspaceStatus())

    const promptFor = (project_id: string, name: string) =>
      buildMissionControlCopyPrompt({
        project: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        report: null,
        state: null,
        status
      })

    const longForm = promptFor('project-long-form-video', 'Long-form Video')
    expect(longForm).toContain('adult animated explainer')
    expect(longForm).toContain('reusable character/prop workflow')
    expect(longForm).not.toContain('Improve Mission Control as the primary Desktop workspace')

    const toolTally = promptFor('project-tool-tally', 'Tool & Tally')
    expect(toolTally).toContain('No payments')
    expect(toolTally).toContain('outreach')
    expect(toolTally).toContain('public launch')

    const waha = promptFor('project-waha-work', 'Waha Work')
    expect(waha).toContain('Waha profile/context')
    expect(waha).toContain('No cross-profile memory bleed')
    expect(waha).toContain('cross-contamination')
  })

  it('saves manual reports through the append-only reports/create route only', async () => {
    await renderMissionControl()

    const projectSelect = await screen.findByLabelText('Project')
    fireEvent.change(projectSelect, { target: { value: 'project-hermes-mission-control' } })
    fireEvent.change(screen.getByLabelText('Jenny report summary'), { target: { value: 'Current Hermes report' } })
    fireEvent.change(screen.getByLabelText('Latest result'), { target: { value: 'Desktop and mobile now read projected state.' } })
    fireEvent.change(screen.getByLabelText('Risks/blockers — one per line'), { target: { value: 'proxy 9121 mismatch' } })
    fireEvent.change(screen.getByLabelText('Artifact/report links — one per line'), { target: { value: 'reports/hermes/current.md' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Jenny report manually' }))

    await waitFor(() => expect(createMissionControlReport).toHaveBeenCalledTimes(1))
    expect(createMissionControlReport).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact_links: ['reports/hermes/current.md'],
        project_id: 'project-hermes-mission-control',
        result: 'Desktop and mobile now read projected state.',
        risks: ['proxy 9121 mismatch'],
        summary: 'Current Hermes report'
      })
    )
    expect(screen.getByText(/Send to Jenny is still disabled/i)).toBeTruthy()
  })

  it('keeps Mission Control view source free of disallowed POST, dispatch wiring, timers, storage, and workers', async () => {
    const source = await import('./index?raw')
    const text = source.default as string

    expect(text).toContain('createMissionControlReport')
    expect(text).toContain('createMissionControlSessionProjectLink')

    for (const forbidden of [
      '.post(',
      '/dispatch',
      '/execute',
      '/api/plugins/kanban/tasks',
      'PATCH',
      'DELETE',
      '/api/sessions/',
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
