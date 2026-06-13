import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMissionControlWorkspaceStatus = vi.fn()
const getMissionControlProjects = vi.fn()
const getMissionControlProjectBriefs = vi.fn()
const getMissionControlChallengeReviews = vi.fn()
const getMissionControlJennyBridgeInbox = vi.fn()
const getMissionControlJennyBridgeOutbox = vi.fn()
const getMissionControlJennyBridgePollerStatus = vi.fn()
const getMissionControlGitHubBridgeStatus = vi.fn()
const getMissionControlLaneRequests = vi.fn()
const getMissionControlProfileMemoryStorage = vi.fn()
const getMissionControlReports = vi.fn()
const getMissionControlProjectState = vi.fn()
const getMissionControlProjectSessions = vi.fn()
const createMissionControlChallengeReview = vi.fn()
const createMissionControlGitHubBridgeRequest = vi.fn()
const answerMissionControlGitHubBridgeOnce = vi.fn()
const createMissionControlJennyBridgeRequest = vi.fn()
const createMissionControlLaneRequest = vi.fn()
const createMissionControlReport = vi.fn()
const createMissionControlSessionProjectLink = vi.fn()

vi.mock('@/hermes', () => ({
  answerMissionControlGitHubBridgeOnce: (payload: unknown) => answerMissionControlGitHubBridgeOnce(payload),
  createMissionControlChallengeReview: (payload: unknown) => createMissionControlChallengeReview(payload),
  createMissionControlGitHubBridgeRequest: (payload: unknown) => createMissionControlGitHubBridgeRequest(payload),
  createMissionControlJennyBridgeRequest: (payload: unknown) => createMissionControlJennyBridgeRequest(payload),
  createMissionControlLaneRequest: (payload: unknown) => createMissionControlLaneRequest(payload),
  createMissionControlReport: (payload: unknown) => createMissionControlReport(payload),
  createMissionControlSessionProjectLink: (payload: unknown) => createMissionControlSessionProjectLink(payload),
  getMissionControlChallengeReviews: () => getMissionControlChallengeReviews(),
  getMissionControlJennyBridgeInbox: () => getMissionControlJennyBridgeInbox(),
  getMissionControlJennyBridgeOutbox: () => getMissionControlJennyBridgeOutbox(),
  getMissionControlJennyBridgePollerStatus: () => getMissionControlJennyBridgePollerStatus(),
  getMissionControlGitHubBridgeStatus: () => getMissionControlGitHubBridgeStatus(),
  getMissionControlWorkspaceStatus: () => getMissionControlWorkspaceStatus(),
  getMissionControlProjectBriefs: () => getMissionControlProjectBriefs(),
  getMissionControlProjects: () => getMissionControlProjects(),
  getMissionControlLaneRequests: () => getMissionControlLaneRequests(),
  getMissionControlProfileMemoryStorage: () => getMissionControlProfileMemoryStorage(),
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
    deployment_gap: {
      accepted_live_head: '0f87620038d220eb016612ba0b466c2407663743',
      dashboard_deploy_needed: true,
      deployed_head: '9f8863c0bf28dc0b7da702480b9b3337b983e7e8',
      latest_merged_pr: '108',
      state: 'merged_not_deployed'
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
  createMissionControlChallengeReview.mockResolvedValue({
    challenge_review: {
      decision_state: 'needs_spec_first',
      project_id: 'project-hermes-mission-control',
      request_summary: 'Make Mission Control usable from project rooms'
    },
    dispatch_enabled: false,
    manual_copy_only: true,
    record_type: 'ChallengeReviewRecord',
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlLaneRequest.mockResolvedValue({
    dispatch_enabled: false,
    lane_request: {
      lane_request_id: 'lane-created',
      project_id: 'project-hermes-mission-control',
      status: 'draft',
      title: 'Read-only project room request'
    },
    manual_copy_only: true,
    record_type: 'LaneRequestRecord',
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlJennyBridgeRequest.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: false,
    record_type: 'JennyBridgeMessageRequestRecord',
    request: {
      message: 'Project room request packet',
      project_id: 'project-hermes-mission-control',
      request_id: 'bridge-request-created',
      status: 'queued',
      target_agent: 'jenny'
    },
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlGitHubBridgeRequest.mockResolvedValue({
    dispatch_enabled: false,
    github_bridge_enabled: true,
    manual_copy_only: false,
    message: {
      created_at: '2026-06-13T01:01:00Z',
      from_agent: 'travis',
      message: 'Project room request packet',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created',
      status: 'queued',
      to_agent: 'jenny'
    },
    record_type: 'GitHubBridgeMessageRecord',
    send_to_jenny_enabled: true,
    stored: true
  })
  getMissionControlProfileMemoryStorage.mockResolvedValue({
    display_only: true,
    dry_run_only: true,
    profile_count: 2,
    profiles: [
      {
        home: '/home/jenny/.hermes',
        memory: { bytes: 1100, chars: 1100, exists: true, percent_used: 50 },
        profile: 'default',
        total_bytes: 1300,
        user: { bytes: 200, chars: 200, exists: true, percent_used: 15 }
      },
      {
        home: '/home/jenny/.hermes/profiles/wahainspection',
        memory: { bytes: 0, chars: 0, exists: false, percent_used: 0 },
        profile: 'wahainspection',
        total_bytes: 0,
        user: { bytes: 0, chars: 0, exists: false, percent_used: 0 }
      }
    ],
    stored: false,
    total_bytes: 1300,
    total_memory_bytes: 1100,
    total_user_bytes: 200
  })
  answerMissionControlGitHubBridgeOnce.mockResolvedValue({
    answered: true,
    dispatch_enabled: false,
    manual_start_only: true,
    request: {
      created_at: '2026-06-13T01:06:00Z',
      from_agent: 'travis',
      message: 'Second request.',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-2',
      status: 'queued',
      to_agent: 'jenny'
    },
    response: {
      created_at: '2026-06-13T01:07:00Z',
      from_agent: 'jenny',
      message: 'Jenny answered the second request.',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-2',
      status: 'replied',
      to_agent: 'travis'
    },
    send_to_jenny_enabled: true,
    stored: true,
    worker_enabled: false,
    timer_enabled: false
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
  getMissionControlProjectBriefs.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    project_briefs: [
      {
        record: {
          approval_rules: ['explicit approval before send path'],
          constraints: ['manual-copy only'],
          outcome: 'Make Mission Control the obvious operating surface before enabling execution.',
          project_id: 'project-hermes-mission-control',
          status: 'active',
          success_criteria: ['project rooms visible', 'challenge gate visible']
        },
        record_type: 'ProjectBriefRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlChallengeReviews.mockResolvedValue({
    challenge_reviews: [
      {
        record: {
          concerns: [],
          decision_state: 'clear_and_safe',
          project_id: 'project-hermes-mission-control',
          recommended_path: 'Use a bounded read-only workspace usability lane.',
          request_summary: 'Make project rooms visible',
          required_approvals: ['deploy/restart approval'],
          status: 'accepted',
          suggested_lane_title: 'Read-only project room usability check'
        },
        record_type: 'ChallengeReviewRecord'
      }
    ],
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false
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
        missing_state_fields: ['report_contract'],
        report_contract: {
          complete: false,
          display_only: true,
          missing_fields: ['evidence', 'tests'],
          required_fields: ['summary', 'result', 'risks/blockers', 'evidence', 'tests', 'next lane'],
          state: 'incomplete',
          trusted_for_execution: false
        },
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
        missing_state_fields: ['latest_lane', 'latest_jenny_report', 'latest_result', 'risks_blockers', 'artifact_links', 'report_contract'],
        report_contract: {
          complete: false,
          display_only: true,
          missing_fields: ['report'],
          required_fields: ['summary', 'result', 'risks/blockers', 'evidence', 'tests', 'next lane'],
          state: 'missing_report',
          trusted_for_execution: false
        },
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
  getMissionControlJennyBridgeOutbox.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: false,
    requests: [
      {
        record: {
          message: 'Review PR #75 and report readiness.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-1',
          status: 'queued',
          target_agent: 'jenny'
        },
        record_type: 'JennyBridgeMessageRequestRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlJennyBridgeInbox.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: false,
    responses: [
      {
        record: {
          message: 'Safe to mark ready.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-1',
          responder: 'jenny',
          response_id: 'bridge-response-1',
          status: 'received'
        },
        record_type: 'JennyBridgeMessageResponseRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlJennyBridgePollerStatus.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    last_error: '',
    last_poll_at: '2026-06-12T15:22:00Z',
    last_response_at: '2026-06-12T15:23:00Z',
    last_response_request_id: 'bridge-request-1',
    last_status: 'response_appended',
    manual_start_only: true,
    pending_count: 0,
    send_to_jenny_enabled: false,
    session_send_enabled: false,
    status_records: [],
    stored: false,
    timer_enabled: false,
    worker_enabled: false
  })
  getMissionControlGitHubBridgeStatus.mockResolvedValue({
    count: 1,
    daemon_enabled: false,
    discord_automation_enabled: false,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    last_error: '',
    last_poll_at: '2026-06-13T01:00:00Z',
    last_response_at: '2026-06-13T01:05:00Z',
    last_response_request_id: 'github-bridge-request-1',
    last_status: 'poll_completed',
    manual_start_only: true,
    mode: 'watch_foreground',
    foreground_watch_supported: true,
    foreground_watch_running: true,
    model_routing_enabled: false,
    pending_count: 1,
    recent_messages: [
      {
        record: {
          created_at: '2026-06-13T01:00:00Z',
          from_agent: 'travis',
          message: 'Review the Mission Control room.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-1',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:00Z',
          from_agent: 'jenny',
          message: 'I can see the Mission Control room request.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-1',
          status: 'replied',
          to_agent: 'travis'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:06:00Z',
          from_agent: 'travis',
          message: 'Local error guard smoke. This should not post a reply.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-1',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:07:00Z',
          from_agent: 'jenny',
          message: 'Error: codex app-server startup failed: initialize timed out.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-2',
          status: 'replied',
          to_agent: 'travis'
        }
      }
    ],
    response_messages: [],
    send_to_jenny_enabled: false,
    session_send_enabled: false,
    status_records: [],
    stored: false,
    timer_enabled: false,
    worker_enabled: false
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
    expect(getMissionControlProjectBriefs).toHaveBeenCalledTimes(1)
    expect(getMissionControlChallengeReviews).toHaveBeenCalledTimes(1)
    expect(getMissionControlLaneRequests).toHaveBeenCalledTimes(1)
    expect(getMissionControlReports).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjectSessions).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgeOutbox).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgeInbox).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgePollerStatus).toHaveBeenCalledTimes(1)
    expect(getMissionControlGitHubBridgeStatus).toHaveBeenCalledTimes(1)

    expect(screen.getByText('Project report archive')).toBeTruthy()
    expect(screen.getByText('Advanced status and reports')).toBeTruthy()
    expect(screen.getByText('Active Jenny OS Lane')).toBeTruthy()
    expect(screen.getByText('Mission Control/Jenny stability lane only. Display-only; lane state is derived from briefs, challenge reviews, lane drafts, and reports.')).toBeTruthy()
    expect(screen.getByText('display-only / no dispatch')).toBeTruthy()
    expect(screen.getAllByText('next safe lane').length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: 'Project chat workspace' })).toBeTruthy()
    expect(screen.getByText('Projects')).toBeTruthy()
    expect(screen.getAllByText('5 projects').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Paused until Jenny is stable').length).toBe(4)
    expect(screen.getByText('Chat room')).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getAllByText('Jenny').length).toBeGreaterThan(0)
    expect(screen.getByText('Bridge watching for replies')).toBeTruthy()
    expect(screen.getByText('Next step')).toBeTruthy()
    expect(screen.getByText('Review Jenny\'s latest reply, then send the next bounded message.')).toBeTruthy()
    expect(screen.getAllByText('Pending 0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Replies 2').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Local error guard smoke/i)).toBeNull()
    expect(screen.queryByText(/codex app-server startup failed/i)).toBeNull()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Advanced controls')).toBeTruthy()
    expect(screen.getByText('Jenny bridge')).toBeTruthy()
    expect(screen.getAllByText('manual-start only').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('replied').length).toBeGreaterThan(0)
    expect(screen.getByText('GitHub mailbox')).toBeTruthy()
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('daemon disabled / worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('deploy state')).toBeTruthy()
    expect(screen.getByText('merged not deployed')).toBeTruthy()
    expect(screen.getByText('accepted-live head')).toBeTruthy()
    expect(screen.getByText('0f87620038d2')).toBeTruthy()
    expect(screen.getByText('deployed head')).toBeTruthy()
    expect(screen.getByText('9f8863c0bf28')).toBeTruthy()
    expect(screen.getByText('desktop app install')).toBeTruthy()
    expect(screen.getByText('separate laptop worker-node update; bottom-bar version is not changed by accepted-live/dashboard deploy')).toBeTruthy()
    expect(screen.getByText('Outbound to Jenny')).toBeTruthy()
    expect(screen.getByText('Jenny replies')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh bridge' })).toBeTruthy()
    expect(screen.getByText(/replied \/ jenny/)).toBeTruthy()
    expect(screen.getByText('Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates.')).toBeTruthy()
    expect(screen.getByText('Project Kanban')).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Hermes update lane')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Start Hermes update lane' })).toBeTruthy()
    expect(screen.getByText(/bottom-bar desktop app version is separate from accepted-live\/dashboard deploys/)).toBeTruthy()
    expect(screen.getAllByText('report contract').length).toBeGreaterThan(0)
    expect(screen.getByText('latest report contract')).toBeTruthy()
    expect(screen.getAllByText(/Missing:.*evidence.*tests/).length).toBeGreaterThan(0)
    expect(screen.getByText('1 active / 4 paused')).toBeTruthy()
    expect(screen.getByText('Projects on hold')).toBeTruthy()

    for (const [, name] of realProjects) {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText('Primary project').length).toBeGreaterThanOrEqual(1)
  })

  it('renders a read-only project kanban lifecycle without queue mutation controls', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Project Kanban')).toBeTruthy()
    for (const expected of [
      'Intake',
      'Needs Clarification',
      'Challenge Review',
      'Lane Draft',
      'Awaiting Approval',
      'Active',
      'Evidence Review',
      'Accepted',
      'Blocked / Rollback'
    ]) {
      expect(screen.getByText(expected)).toBeTruthy()
    }

    expect(screen.getByText(/Dragging is disabled/)).toBeTruthy()
    expect(screen.getByText(/read-only board/)).toBeTruthy()
    expect(screen.getAllByText(/no queue mutation/).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /move card/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /start work/i })).toBeNull()
  })

  it('renders the active Jenny OS lane as the only active project board', async () => {
    await renderMissionControl()

    const panel = await screen.findByRole('region', { name: 'Active Jenny OS lane' })
    expect(panel.textContent).toContain('Hermes / Mission Control')
    expect(panel.textContent).not.toContain('Shorts Video')
    expect(panel.textContent).not.toContain('Long-form Video')
    expect(panel.textContent).not.toContain('Tool & Tally')
    expect(panel.textContent).not.toContain('Waha Work')
    expect(panel.textContent).toContain('Display-only')
    expect(panel.textContent).toContain('Active lane count: 0')
    expect(panel.querySelectorAll('button')).toHaveLength(0)
  })

  it('shows paused project rooms but keeps their Jenny actions disabled', async () => {
    await renderMissionControl()

    fireEvent.click((await screen.findAllByRole('button', { name: /Long-form Video/ })).at(0)!)

    expect(screen.getByRole('heading', { name: 'Long-form Video' })).toBeTruthy()
    expect(screen.getAllByText('Paused').length).toBeGreaterThan(0)
    expect(screen.getByText('Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.')).toBeTruthy()
    expect(screen.getByText('This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Send to Jenny' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Run Jenny once' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Save challenge draft' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Save read-only lane draft' })).toHaveProperty('disabled', true)
  })

  it('shows real project state, fallback empty-state copy, and disabled safety flags', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Jenny finished the desktop architecture review.')).length).toBeGreaterThan(0)
    expect(screen.getByText('Manual Jenny report ingestion')).toBeTruthy()
    expect(screen.getByText('Save Jenny report manually')).toBeTruthy()
    expect(screen.getByText('Use Mission Control backend with desktop frontend.')).toBeTruthy()
    expect(screen.getByText('dashboard overbuild · none')).toBeTruthy()
    expect(screen.getByText('reports/hermes/desktop-review.md')).toBeTruthy()
    expect(screen.getByText('Live report available')).toBeTruthy()
    expect(screen.getByText('2026-06-11T10:00:00Z (report)')).toBeTruthy()
    expect(screen.getAllByText('Desktop read-only workspace v1').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only status refresh (draft)')).toBeTruthy()
    expect(screen.getByText('Projects on hold')).toBeTruthy()
    expect(screen.getAllByText('Shorts Video').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Long-form Video').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tool & Tally').length).toBeGreaterThan(0)
    expect(screen.getAllByText('send_to_jenny: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dispatch: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('execution: disabled').length).toBeGreaterThan(0)
  })

  it('renders linked, suggested, and unassigned sessions without creating source-of-truth links', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Project sessions')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 linked').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mission Control linked session').length).toBeGreaterThan(0)
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
    expect(prompt).toContain('REVIEW PACKET')
    expect(prompt).toContain('Forbidden actions:')
    expect(prompt).toContain('Direct session send remains disabled')
    expect(screen.getByText(/Project chat is record-backed/)).toBeTruthy()
  })

  it('shows project room controls and creates only inert challenge and lane drafts', async () => {
    await renderMissionControl()

    expect((await screen.findAllByRole('heading', { name: 'Hermes / Mission Control' })).length).toBeGreaterThan(0)
    expect(screen.getByText('Message Jenny')).toBeTruthy()
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getByText('Phone-safe packet')).toBeTruthy()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Hermes storage cleanup lane')).toBeTruthy()
    expect(screen.getByText('Jenny memory storage')).toBeTruthy()
    expect(screen.getByText(/2 profiles/)).toBeTruthy()
    expect(screen.getByText('wahainspection')).toBeTruthy()
    expect(screen.getAllByText('Lane draft ok').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Use a bounded read-only workspace usability lane/).length).toBeGreaterThan(0)

    fireEvent.change(screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...'), {
      target: { value: 'Make the visible Mission Control page show project rooms on laptop and phone.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Copy phone-safe packet' }))
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Project room request:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Categories:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Blocking verdicts:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Structured handoff:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Challenge: question unclear, unsafe, or wrong-approach requests before implementation.')

    fireEvent.click(screen.getByRole('button', { name: 'Send to Jenny' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Project room request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Structured handoff:')
      })
    )
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Save challenge draft' }))
    await waitFor(() => expect(createMissionControlChallengeReview).toHaveBeenCalledTimes(1))
    expect(createMissionControlChallengeReview).toHaveBeenCalledWith(
      expect.objectContaining({
        blocking_verdicts: ['requires_spec_update', 'blocks_lane_draft'],
        challenge_categories: ['questions_required', 'missing_context'],
        decision_state: 'needs_spec_first',
        project_id: 'project-hermes-mission-control',
        request_summary: 'Make the visible Mission Control page show project rooms on laptop and phone.'
      })
    )

    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))
    await waitFor(() => expect(createMissionControlLaneRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlLaneRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        forbidden_actions: expect.arrayContaining(['dispatch', 'automatic send']),
        project_id: 'project-hermes-mission-control',
        title: 'Read-only project room usability check'
      })
    )

    fireEvent.click(screen.getByRole('button', { name: 'Start Hermes update lane' }))
    await waitFor(() => expect(createMissionControlJennyBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlJennyBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        ack_key: expect.stringContaining('project-hermes-mission-control:hermes-update:'),
        message: expect.stringContaining('Hermes update lane request:'),
        project_id: 'project-hermes-mission-control',
        sender: 'codex',
        target_agent: 'jenny'
      })
    )
    expect(createMissionControlJennyBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('gateway update as a separate explicit lane')

    fireEvent.click(screen.getByRole('button', { name: 'Start storage cleanup lane' }))
    await waitFor(() => expect(createMissionControlJennyBridgeRequest).toHaveBeenCalledTimes(2))
    expect(createMissionControlJennyBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        ack_key: expect.stringContaining('project-hermes-mission-control:hermes-storage-cleanup:'),
        message: expect.stringContaining('Hermes storage cleanup lane request:'),
        project_id: 'project-hermes-mission-control',
        sender: 'codex',
        target_agent: 'jenny'
      })
    )
    expect(createMissionControlJennyBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('Stop before deleting, pruning, moving, or uploading anything')
  })

  it('keeps paused project hold panels read-only', async () => {
    await renderMissionControl()

    await screen.findByText('Projects on hold')
    expect(screen.queryByRole('button', { name: 'Queue audit/proof lane' })).toBeNull()
    expect(screen.getAllByText('On hold. No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.').length).toBeGreaterThanOrEqual(4)
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('runs Jenny once for the latest pending GitHub bridge request only', async () => {
    getMissionControlGitHubBridgeStatus.mockResolvedValue({
      count: 1,
      daemon_enabled: false,
      discord_automation_enabled: false,
      dispatch_enabled: false,
      display_only: true,
      execution_enabled: false,
      last_error: '',
      last_poll_at: '2026-06-13T01:00:00Z',
      last_response_at: '2026-06-13T01:05:00Z',
      last_response_request_id: 'github-bridge-request-1',
      last_status: 'poll_completed',
      manual_start_only: true,
      mode: 'watch_foreground',
      foreground_watch_supported: true,
      foreground_watch_running: true,
      model_routing_enabled: false,
      pending_count: 1,
      recent_messages: [
        {
          record: {
            created_at: '2026-06-13T01:00:00Z',
            from_agent: 'travis',
            message: 'Review the Mission Control room.',
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-request-1',
            status: 'queued',
            to_agent: 'jenny'
          }
        },
        {
          record: {
            created_at: '2026-06-13T01:05:00Z',
            from_agent: 'jenny',
            message: 'I can see the Mission Control room request.',
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-request-1',
            status: 'replied',
            to_agent: 'travis'
          }
        },
        {
          record: {
            created_at: '2026-06-13T01:06:00Z',
            from_agent: 'travis',
            message: 'Second request.',
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-request-2',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      response_messages: [],
      send_to_jenny_enabled: false,
      session_send_enabled: false,
      status_records: [],
      stored: false,
      timer_enabled: false,
      worker_enabled: false
    })

    await renderMissionControl()

    fireEvent.click(await screen.findByRole('button', { name: 'Run Jenny once' }))
    await waitFor(() => expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledTimes(1))
    expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledWith({
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-2'
    })
    expect(await screen.findByText('Jenny replied to the latest pending project message.')).toBeTruthy()
  })

  it('blocks desktop lane drafts when the newest challenge review is not clear', async () => {
    getMissionControlChallengeReviews.mockResolvedValue({
      challenge_reviews: [
        {
          record: {
            decision_state: 'clear_and_safe',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Older clear review.',
            request_summary: 'Old request',
            status: 'accepted',
            suggested_lane_title: 'Old clear lane'
          },
          record_type: 'ChallengeReviewRecord'
        },
        {
          record: {
            decision_state: 'needs_spec_first',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Newest review requires a spec first.',
            request_summary: 'New request',
            status: 'draft',
            suggested_lane_title: 'Blocked lane'
          },
          record_type: 'ChallengeReviewRecord'
        }
      ],
      count: 2,
      dispatch_enabled: false,
      manual_copy_only: true,
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    fireEvent.change(await screen.findByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...'), {
      target: { value: 'Start a broad Mission Control lane without a spec.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))

    expect(await screen.findByText('Latest challenge review is needs_spec_first. Resolve that before saving a lane request draft.')).toBeTruthy()
    expect(createMissionControlLaneRequest).not.toHaveBeenCalled()
  })

  it('allows desktop lane drafts when the newest challenge review is clear', async () => {
    getMissionControlChallengeReviews.mockResolvedValue({
      challenge_reviews: [
        {
          record: {
            decision_state: 'needs_spec_first',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Older review required a spec.',
            request_summary: 'Old request',
            status: 'draft',
            suggested_lane_title: 'Old blocked lane'
          },
          record_type: 'ChallengeReviewRecord'
        },
        {
          record: {
            decision_state: 'clear_and_safe',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Newest review cleared a bounded lane.',
            request_summary: 'New request',
            status: 'accepted',
            suggested_lane_title: 'Newest clear lane'
          },
          record_type: 'ChallengeReviewRecord'
        }
      ],
      count: 2,
      dispatch_enabled: false,
      manual_copy_only: true,
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    fireEvent.change(await screen.findByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...'), {
      target: { value: 'Inspect whether Project Rooms are usable now.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))

    await waitFor(() => expect(createMissionControlLaneRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlLaneRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: 'project-hermes-mission-control',
        title: 'Newest clear lane'
      })
    )
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
    expect(screen.getByText(/Use project chat for guarded Jenny messages/i)).toBeTruthy()
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
      'setTimeout',
      'Worker(',
      'new Worker'
    ]) {
      expect(text).not.toContain(forbidden)
    }
  })
})
