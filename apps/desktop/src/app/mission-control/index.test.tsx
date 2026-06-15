import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMissionControlWorkspaceStatus = vi.fn()
const getMissionControlProjects = vi.fn()
const getMissionControlProjectBriefs = vi.fn()
const getMissionControlChallengeReviews = vi.fn()
const getMissionControlJennyBridgeInbox = vi.fn()
const getMissionControlJennyBridgeOutbox = vi.fn()
const getMissionControlJennyBridgePollerStatus = vi.fn()
const getMissionControlJennyReplyReviews = vi.fn()
const getMissionControlGitHubBridgeStatus = vi.fn()
const getMissionControlLaneRequests = vi.fn()
const getMissionControlProfileMemoryStorage = vi.fn()
const getMissionControlReports = vi.fn()
const getMissionControlProjectState = vi.fn()
const getMissionControlProjectSessions = vi.fn()
const createMissionControlChallengeReview = vi.fn()
const createMissionControlGitHubBridgeRequest = vi.fn()
const createMissionControlJennyReplyReview = vi.fn()
const answerMissionControlGitHubBridgeOnce = vi.fn()
const createMissionControlJennyBridgeRequest = vi.fn()
const createMissionControlLaneRequest = vi.fn()
const createMissionControlReport = vi.fn()
const createMissionControlSessionProjectLink = vi.fn()

vi.mock('@/hermes', () => ({
  answerMissionControlGitHubBridgeOnce: (payload: unknown) => answerMissionControlGitHubBridgeOnce(payload),
  createMissionControlChallengeReview: (payload: unknown) => createMissionControlChallengeReview(payload),
  createMissionControlGitHubBridgeRequest: (payload: unknown) => createMissionControlGitHubBridgeRequest(payload),
  createMissionControlJennyReplyReview: (payload: unknown) => createMissionControlJennyReplyReview(payload),
  createMissionControlJennyBridgeRequest: (payload: unknown) => createMissionControlJennyBridgeRequest(payload),
  createMissionControlLaneRequest: (payload: unknown) => createMissionControlLaneRequest(payload),
  createMissionControlReport: (payload: unknown) => createMissionControlReport(payload),
  createMissionControlSessionProjectLink: (payload: unknown) => createMissionControlSessionProjectLink(payload),
  getMissionControlChallengeReviews: () => getMissionControlChallengeReviews(),
  getMissionControlJennyBridgeInbox: () => getMissionControlJennyBridgeInbox(),
  getMissionControlJennyBridgeOutbox: () => getMissionControlJennyBridgeOutbox(),
  getMissionControlJennyBridgePollerStatus: () => getMissionControlJennyBridgePollerStatus(),
  getMissionControlJennyReplyReviews: () => getMissionControlJennyReplyReviews(),
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
  createMissionControlJennyReplyReview.mockResolvedValue({
    dispatch_enabled: false,
    manual_start_only: true,
    record_type: 'JennyReplyReviewRecord',
    reply_review: {
      decision: 'needs_evidence',
      note: 'Reviewed: needs evidence',
      project_id: 'project-hermes-mission-control',
      response_id: 'bridge-response-1',
      review_id: 'reply-review-created',
      reviewer: 'travis'
    },
    send_to_jenny_enabled: false,
    stored: true,
    timer_enabled: false,
    worker_enabled: false
  })
  getMissionControlProfileMemoryStorage.mockResolvedValue({
    display_only: true,
    dry_run_only: true,
    profile_count: 2,
    profiles: [
      {
        data: {
          bytes: 6_442_450_944,
          components: {
            memories: { bytes: 32_768, exists: true, path: '/home/jenny/.hermes/memories' },
            sessions: { bytes: 2_790_309_888, exists: true, path: '/home/jenny/.hermes/sessions' },
            state: { bytes: 3_652_108_288, exists: true, path: '/home/jenny/.hermes/state.db' }
          },
          exists: true,
          path: '/home/jenny/.hermes',
          scope: 'default_profile_state_sessions_memories'
        },
        home: '/home/jenny/.hermes',
        memory: { bytes: 1100, chars: 1100, exists: true, limit_chars: 2200, percent_used: 50 },
        mount: { free_bytes: 4_294_967_296, path: '/', percent_used: 76, total_bytes: 17_179_869_184, used_bytes: 12_884_901_888 },
        profile: 'default',
        recall_file_bytes: 1300,
        total_bytes: 6_442_450_944,
        user: { bytes: 200, chars: 200, exists: true, limit_chars: 1375, percent_used: 15 }
      },
      {
        data: {
          bytes: 49_283_072,
          components: {
            memories: { bytes: 4096, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/memories' },
            sessions: { bytes: 12_582_912, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/sessions' },
            state: { bytes: 36_696_064, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/state.db' }
          },
          exists: true,
          path: '/home/jenny/.hermes/profiles/wahainspection',
          scope: 'profile_directory'
        },
        home: '/home/jenny/.hermes/profiles/wahainspection',
        memory: { bytes: 0, chars: 0, exists: false, limit_chars: 2200, percent_used: 0 },
        mount: { free_bytes: 4_294_967_296, path: '/', percent_used: 76, total_bytes: 17_179_869_184, used_bytes: 12_884_901_888 },
        profile: 'wahainspection',
        recall_file_bytes: 0,
        total_bytes: 49_283_072,
        user: { bytes: 0, chars: 0, exists: false, limit_chars: 1375, percent_used: 0 }
      }
    ],
    stored: false,
    total_bytes: 6_491_734_016,
    total_memory_bytes: 1100,
    total_profile_data_bytes: 6_491_734_016,
    total_recall_file_bytes: 1300,
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
    count: 2,
    dispatch_enabled: false,
    manual_copy_only: false,
    requests: [
      {
        record: {
          created_at: '2026-06-12T15:21:00Z',
          message: 'Old unanswered bridge request that should not keep the room pending.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-old',
          status: 'queued',
          target_agent: 'jenny'
        },
        record_type: 'JennyBridgeMessageRequestRecord'
      },
      {
        record: {
          created_at: '2026-06-12T15:22:00Z',
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
          created_at: '2026-06-12T15:23:00Z',
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
  getMissionControlJennyReplyReviews.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_start_only: true,
    reply_reviews: [
      {
        record: {
          created_at: '2026-06-12T15:24:00Z',
          decision: 'needs_evidence',
          note: 'Reviewed: needs evidence',
          project_id: 'project-hermes-mission-control',
          response_id: 'bridge-response-1',
          review_id: 'reply-review-1',
          reviewer: 'travis'
        },
        record_type: 'JennyReplyReviewRecord'
      }
    ],
    send_to_jenny_enabled: false,
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
    visible_pending_count: 0,
    background_pending_count: 1,
    recent_messages: [
      {
        record: {
          created_at: '2026-06-13T01:00:00Z',
          from_agent: 'travis',
          message: 'Hermes / Mission Control Request: Review the Mission Control room. Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          metadata: {
            user_message: 'Review the Mission Control room.'
          },
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
          created_at: '2026-06-13T01:05:30Z',
          from_agent: 'travis',
          message: 'Hermes / Mission Control Request: testing. tell me a short story Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-replied-user',
          status: 'replied',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:40Z',
          from_agent: 'travis',
          message: 'Project room request: Hermes / Mission Control Request: fix the two way communication with codex through the bridge Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-project-room-legacy',
          status: 'replied',
          to_agent: 'jenny'
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
      },
      {
        record: {
          created_at: '2026-06-13T01:08:00Z',
          from_agent: 'jenny',
          message: 'Bridge works. The success smoke reached Jenny and failures are guarded.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-3',
          status: 'replied',
          to_agent: 'travis'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:09:00Z',
          from_agent: 'codex',
          message: 'Bounded dashboard-only deploy check request for accepted-live.',
          project_id: 'project-hermes-mission-control',
          request_id: 'codex-pr151-dashboard-deploy-structured-20260614-001',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:10:00Z',
          from_agent: 'jenny',
          message: 'Dashboard-only deploy check completed for Codex.',
          project_id: 'project-hermes-mission-control',
          request_id: 'codex-pr151-dashboard-deploy-structured-20260614-001',
          status: 'replied',
          to_agent: 'codex'
        }
      }
    ],
    response_messages: [],
    send_to_jenny_enabled: false,
    session_send_enabled: false,
    status_records: [
      {
        record: {
          created_at: '2026-06-13T01:04:00Z',
          handled_request_id: 'github-bridge-request-1',
          mode: 'manual_hermes_answer',
          pending_count: 1,
          status: 'hermes_answer_started',
          status_id: 'github-status-started'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:00Z',
          handled_request_id: 'github-bridge-request-1',
          mode: 'manual_hermes_answer',
          pending_count: 0,
          status: 'hermes_answer_completed',
          status_id: 'github-status-completed'
        }
      }
    ],
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
    expect(screen.getAllByText('More').length).toBeGreaterThan(0)
    expect(screen.getByText('Active Jenny OS Lane')).toBeTruthy()
    expect(screen.getByText('Mission Control/Jenny stability lane only. Display-only; lane state is derived from briefs, challenge reviews, lane drafts, and reports.')).toBeTruthy()
    expect(screen.getByText('display-only / no dispatch')).toBeTruthy()
    expect(screen.getAllByText('next safe lane').length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: 'Project chat workspace' })).toBeTruthy()
    expect(screen.getByText('Projects')).toBeTruthy()
    expect(screen.getAllByText('5 projects').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Paused until Jenny is stable').length).toBe(4)
    expect(screen.getByText('Local studio')).toBeTruthy()
    expect(screen.getByText('IV. — Jenny workspace')).toBeTruthy()
    expect(screen.getByRole('complementary', { name: 'Workspace inspector' })).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getByLabelText('Jenny chat status')).toBeTruthy()
    expect(screen.getByText('Jenny status')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Jenny' })).toBeTruthy()
    expect(screen.getAllByText((_, element) => element?.textContent?.includes('Next: Review before relying') ?? false).length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: 'Latest Jenny outcome' })).toBeTruthy()
    expect(screen.getByText('Review before relying')).toBeTruthy()
    expect(screen.getAllByText(/Review Jenny's latest reply before relying on it/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Open Review reply on the latest Jenny message/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Next: Use the reply review buttons/)).toBeTruthy()
    expect(screen.getByLabelText('Jenny operator guidance')).toBeTruthy()
    expect(screen.getByText('Review Jenny reply')).toBeTruthy()
    expect(screen.getByText(/Ask for evidence or challenge the plan/)).toBeTruthy()
    expect(screen.getAllByText('one reply at a time').length).toBeGreaterThan(0)
    expect(screen.getAllByText('evidence required').length).toBeGreaterThan(0)
    expect(screen.getAllByText('no hidden execution').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Current phase').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Last sent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply state').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elapsed').length).toBeGreaterThan(0)
    expect(screen.getByText('Jenny activity')).toBeTruthy()
    expect(screen.getByText('recent bridge status')).toBeTruthy()
    expect(screen.getByText('Jenny is thinking')).toBeTruthy()
    expect(screen.getAllByText('request github-bridge-request-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny is watching').length).toBeGreaterThan(0)
    expect(screen.getByText(/Bridge watching for replies/)).toBeTruthy()
    expect(screen.getByText(/Bridge is watching for replies/)).toBeTruthy()
    expect(screen.getByText('Next step')).toBeTruthy()
    expect(screen.getAllByText(/Ask Jenny for exact files, commands, checks, CI\/runtime status/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Pending 0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Replies 2').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Local error guard smoke/i)).toBeNull()
    expect(screen.queryByText(/codex app-server startup failed/i)).toBeNull()
    expect(screen.queryByText(/Bridge works/i)).toBeNull()
    expect(screen.queryByText(/success smoke reached/i)).toBeNull()
    expect(screen.queryByText(/Bounded dashboard-only deploy check/i)).toBeNull()
    expect(screen.queryByText(/Dashboard-only deploy check completed/i)).toBeNull()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Advanced')).toBeTruthy()
    expect(screen.getAllByText('Jenny bridge').length).toBeGreaterThan(0)
    expect(screen.getAllByText('manual-start only').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('replied').length).toBeGreaterThan(0)
    expect(screen.getByText('GitHub mailbox')).toBeTruthy()
    expect(screen.getByText('visible 0 / background 1')).toBeTruthy()
    expect(screen.getByText('worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('daemon disabled / worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('deploy state')).toBeTruthy()
    expect(screen.getByText('merged not deployed')).toBeTruthy()
    expect(screen.getByText(/Desktop can be current while phone\/web waits for a safe dashboard-only update/)).toBeTruthy()
    expect(screen.getByText('accepted-live head')).toBeTruthy()
    expect(screen.getByText('0f87620038d2')).toBeTruthy()
    expect(screen.getByText('deployed head')).toBeTruthy()
    expect(screen.getByText('9f8863c0bf28')).toBeTruthy()
    expect(screen.getByText('desktop app install')).toBeTruthy()
    expect(screen.getByText('separate laptop worker-node update; bottom-bar version is not changed by accepted-live/dashboard deploy')).toBeTruthy()
    expect(screen.queryByText('⌘K Command palette')).toBeNull()
    expect(screen.queryByText('All systems')).toBeNull()
    expect(screen.getByText('Outbound to Jenny')).toBeTruthy()
    expect(screen.getByText('Jenny replies')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh bridge' })).toBeTruthy()
    expect(screen.getByText(/replied \/ jenny/)).toBeTruthy()
    expect(screen.getByText('Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates.')).toBeTruthy()
    expect(screen.getByText('Hermes health dashboard')).toBeTruthy()
    expect(screen.getByText('Profile storage usage')).toBeTruthy()
    expect(screen.getByText('Profile data')).toBeTruthy()
    expect(screen.getByText('State DB')).toBeTruthy()
    expect(screen.getByText('Sessions')).toBeTruthy()
    expect(screen.getByText('Recall files')).toBeTruthy()
    expect(screen.queryByText('Total memory files')).toBeNull()
    expect(screen.queryByText('MEMORY.md')).toBeNull()
    expect(screen.queryByText('USER.md')).toBeNull()
    expect(screen.queryByText('Memory cap')).toBeNull()
    expect(screen.queryByText('Memory %')).toBeNull()
    expect(screen.getByText('Mount max')).toBeTruthy()
    expect(screen.getByText('Mount used')).toBeTruthy()
    expect(screen.getAllByText('6.0 GB').length).toBeGreaterThan(0)
    expect(screen.getByText('3.4 GB')).toBeTruthy()
    expect(screen.getByText('2.6 GB')).toBeTruthy()
    expect(screen.getByText('Mount %')).toBeTruthy()
    expect(screen.getAllByText('16 GB').length).toBeGreaterThan(0)
    expect(screen.getAllByText('12 GB').length).toBeGreaterThan(0)
    expect(screen.getAllByText('76%').length).toBeGreaterThan(0)
    expect(screen.getByText('Kanban parked for later')).toBeTruthy()
    expect(screen.getByText('Advanced diagnostic records')).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Hermes update lane')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Start Hermes update lane' })).toBeTruthy()
    expect(screen.getByText(/bottom-bar desktop app version is separate from accepted-live\/dashboard deploys/)).toBeTruthy()
    expect(screen.getAllByText('report contract').length).toBeGreaterThan(0)
    expect(screen.getByText('latest report contract')).toBeTruthy()
    expect(screen.getAllByText(/Missing:.*evidence.*tests/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 active / 4 paused').length).toBeGreaterThan(0)
    expect(screen.getByText('Projects on hold')).toBeTruthy()

    for (const [, name] of realProjects) {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText('Primary project').length).toBeGreaterThanOrEqual(1)
  })

  it('keeps all five project chat rooms visible when project records are partially projected', async () => {
    getMissionControlProjects.mockResolvedValueOnce({
      count: 1,
      dispatch_enabled: false,
      manual_copy_only: true,
      projects: [
        {
          record: {
            current_goal: 'Make desktop the main workspace.',
            name: 'Hermes / Mission Control',
            next_recommended_lane: 'Desktop read-only workspace v1',
            project_id: 'project-hermes-mission-control',
            source_of_truth: 'Mission Control records',
            status: 'Live workspace'
          },
          record_type: 'ProjectRecord'
        }
      ],
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    expect(await screen.findByRole('region', { name: 'Project chat workspace' })).toBeTruthy()
    expect(screen.getAllByText('5 projects').length).toBeGreaterThan(0)
    for (const [, name] of realProjects) {
      expect(screen.getAllByText(name).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText('Paused until Jenny is stable').length).toBe(4)
  })

  it('parks Kanban until the real task board is reliable', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Kanban parked for later')).toBeTruthy()
    expect(screen.getByText(/hidden from this daily view until it can show real tasks and reliable controls/)).toBeTruthy()
    expect(screen.queryByText('Project Kanban')).toBeNull()
    expect(screen.queryByRole('button', { name: /move card/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /start work/i })).toBeNull()
  })

  it('renders the active Jenny OS lane as the only active project board', async () => {
    await renderMissionControl()

    const advanced = await screen.findByText('Advanced diagnostic records')
    expect(advanced).toBeTruthy()
    expect(screen.getByText('Active Jenny OS Lane')).toBeTruthy()
    expect(screen.getByText('Active lane count: 0')).toBeTruthy()
  })

  it('shows paused project rooms but keeps their Jenny actions disabled', async () => {
    await renderMissionControl()

    fireEvent.change(await screen.findByLabelText('Active project'), { target: { value: 'project-long-form-video' } })

    expect(screen.getByRole('heading', { name: 'Long-form Video' })).toBeTruthy()
    expect(screen.getAllByText('Paused').length).toBeGreaterThan(0)
    expect(screen.getByText('Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.')).toBeTruthy()
    expect(screen.getByText('This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.')).toBeTruthy()
    expect(screen.getByText('Resume requirements')).toBeTruthy()
    expect(screen.getByText('Jenny challenge review clears the approach')).toBeTruthy()
    expect(screen.getByText('Travis approval is recorded before work resumes')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Send' })).toHaveProperty('disabled', true)
    expect(screen.queryByRole('button', { name: 'Ask Jenny to review first' })).toBeNull()
    expect(screen.queryByRole('button', { name: "Get Jenny's reply" })).toBeNull()
    expect(screen.getByRole('button', { name: 'Save challenge draft' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Save read-only lane draft' })).toHaveProperty('disabled', true)
  })

  it('shows real project state, fallback empty-state copy, and disabled safety flags', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Jenny finished the desktop architecture review.')).length).toBeGreaterThan(0)
    expect(screen.getByText('Manual record repair')).toBeTruthy()
    expect(screen.getByText('Save a missing Jenny report')).toBeTruthy()
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
    expect(screen.getByText(/Messages are saved/)).toBeTruthy()
  })

  it('shows project room controls and creates only inert challenge and lane drafts', async () => {
    await renderMissionControl()

    expect((await screen.findAllByRole('heading', { name: 'Hermes / Mission Control' })).length).toBeGreaterThan(0)
    expect(screen.getByText('Message Jenny')).toBeTruthy()
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getByText('Jenny status')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Latest Jenny outcome' })).toBeTruthy()
    expect(screen.getByText('Review before relying')).toBeTruthy()
    expect(screen.getAllByText('Current phase').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Last sent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply state').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elapsed').length).toBeGreaterThan(0)
    expect(screen.getByText('Work session')).toBeTruthy()
    expect(screen.getAllByText('Queued').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny working').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply received').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Review next').length).toBeGreaterThan(0)
    expect(screen.getAllByText('More').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Pending \d+/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Replies \d+/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Reply quality/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Review reply').length).toBeGreaterThan(0)
    expect(screen.getByText('Phone-safe packet')).toBeTruthy()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Hermes storage cleanup lane')).toBeTruthy()
    expect(screen.getByText('Jenny memory storage')).toBeTruthy()
    expect(screen.getAllByText(/2 profiles/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('wahainspection').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lane draft ok').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Use a bounded read-only workspace usability lane/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Request intake: Needs request/).length).toBeGreaterThan(0)
    expect(screen.getByText('Review the Mission Control room.')).toBeTruthy()
    const transcript = within(screen.getByLabelText('Project chat transcript'))
    expect(transcript.getByText('testing. tell me a short story')).toBeTruthy()
    expect(transcript.getByText('fix the two way communication with codex through the bridge')).toBeTruthy()
    expect(transcript.getByText('Review the Mission Control room.')).toBeTruthy()
    expect(transcript.queryByText(/Project room request: Hermes/)).toBeNull()
    expect(transcript.queryByText(/Current brief: Replace Discord as Travis primary workspace/)).toBeNull()
    expect(transcript.queryByText(/Allowed: read approved context/)).toBeNull()
    expect(transcript.queryByText(/Forbidden: no direct session send/)).toBeNull()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    fireEvent.click(screen.getByRole('button', { name: 'Use spec-first prompt' }))
    expect((composer as HTMLTextAreaElement).value).toContain('Spec-first request for Jenny:')
    expect((composer as HTMLTextAreaElement).value).toContain('Jenny, do not implement yet. First challenge the request like a senior engineer:')
    expect((composer as HTMLTextAreaElement).value).toContain('Return only the spec/challenge review and the recommended next safe lane.')
    expect(screen.getAllByRole('button', { name: 'Draft acceptance note' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Ask for evidence' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Challenge plan' }).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reviewed: needs evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Needs evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Ask Jenny for exact files, commands, checks, CI\/runtime status/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByRole('button', { name: 'Ask for evidence' })[0])
    await waitFor(() => expect(createMissionControlJennyReplyReview).toHaveBeenCalledTimes(1))
    expect(createMissionControlJennyReplyReview).toHaveBeenCalledWith(
      expect.objectContaining({
        decision: 'needs_evidence',
        project_id: 'project-hermes-mission-control',
        response_id: 'bridge-response-1',
        reviewer: 'travis'
      })
    )
    expect((composer as HTMLTextAreaElement).value).toContain('needs stronger evidence')
    expect((composer as HTMLTextAreaElement).value).toContain('Do not take action. Report evidence only.')
    expect(createMissionControlGitHubBridgeRequest).not.toHaveBeenCalled()

    fireEvent.change(composer, {
      target: { value: 'Make the visible Mission Control page show project rooms on laptop and phone.' }
    })
    expect(screen.getAllByText(/Request intake: Ready/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Copy phone-safe packet' }))
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Project room request:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Request intake:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Ready / Request is bounded enough for a guarded Jenny reply.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Jenny instruction:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Categories:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Blocking verdicts:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Structured handoff:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Challenge: question unclear, unsafe, or wrong-approach requests before implementation.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Evidence contract:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Recommendation: one-sentence next lane.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('if evidence is missing, say "not proven"')

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Project room request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: 'Make the visible Mission Control page show project rooms on laptop and phone.'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Request intake:'),
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Structured handoff:')
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Evidence contract:')
      })
    )
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()

    fireEvent.change(composer, {
      target: { value: 'Make the visible Mission Control page show project rooms on laptop and phone.' }
    })
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
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(2))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Hermes update lane request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: expect.stringContaining('Start a safe Hermes update readiness lane')
      })
    )
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('gateway update as a separate explicit lane')

    fireEvent.click(screen.getByRole('button', { name: 'Start storage cleanup lane' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(3))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Hermes storage cleanup lane request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: expect.stringContaining('Start a safe Hermes storage cleanup lane')
      })
    )
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('target of about 50% disk usage')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('timestamped dry-run manifest')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('Tool & Tally report-builder data')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('With explicit cleanup approval')
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('keeps paused project hold panels read-only', async () => {
    await renderMissionControl()

    await screen.findByText('Projects on hold')
    expect(screen.queryByRole('button', { name: 'Queue audit/proof lane' })).toBeNull()
    expect(screen.getAllByText('On hold. No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.').length).toBeGreaterThanOrEqual(4)
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('auto-routes broad project messages to a spec-first Jenny challenge', async () => {
    await renderMissionControl()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    fireEvent.change(composer, { target: { value: 'make Jenny fully functional and autonomous' } })

    await waitFor(() => expect((composer as HTMLTextAreaElement).value).toBe('make Jenny fully functional and autonomous'))
    await waitFor(() => expect(screen.getAllByText(/Spec first/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Jenny will challenge this request before planning any implementation/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny must challenge first').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Question missing facts and unsafe assumptions.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Push back on protected actions or broad scope.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Return the smallest safe lane with evidence and approval needs.').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Spec-first request for Jenny:'),
        project_id: 'project-hermes-mission-control',
        to_agent: 'jenny',
        user_message: 'make Jenny fully functional and autonomous'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Jenny, do not implement yet. First challenge the request like a senior engineer:')
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.not.stringContaining('Project room request:')
      })
    )
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('routes update and install requests through the approval challenge gate', async () => {
    await renderMissionControl()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    fireEvent.change(composer, { target: { value: 'update Hermes on the VPS and install the laptop worker node' } })

    await waitFor(() => expect(screen.getAllByText(/Approval check/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Contains protected actions; Jenny should challenge scope and identify approvals before work/).length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Current intake: Approval check / Contains protected actions'),
        user_message: 'update Hermes on the VPS and install the laptop worker node'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('First challenge the request like a senior engineer')
      })
    )
    await waitFor(() => expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledWith({
      confirm_manual_hermes_answer: true,
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created'
    }))
  })

  it('sends a chat message and immediately runs one guarded Jenny reply', async () => {
    let resolveAnswer: (value: unknown) => void = () => undefined
    answerMissionControlGitHubBridgeOnce.mockReturnValueOnce(new Promise(resolve => {
      resolveAnswer = resolve
    }))

    await renderMissionControl()

    fireEvent.change(await screen.findByLabelText('Message Jenny'), { target: { value: 'Please check the chat bridge.' } })
    const composer = screen.getByLabelText('Message Jenny') as HTMLTextAreaElement
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(composer.value).toBe(''))
    expect((await screen.findAllByText('Waiting for Jenny')).length).toBeGreaterThanOrEqual(2)
    expect((await screen.findAllByText(/Mission Control sent the latest project message to Jenny/)).length).toBeGreaterThanOrEqual(2)
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        request_id: expect.stringContaining('mission-control-chat-'),
        user_message: 'Please check the chat bridge.'
      })
    ))
    await waitFor(() => expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledTimes(1))
    expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledWith({
      confirm_manual_hermes_answer: true,
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created'
    })
    resolveAnswer({
      answered: true,
      dispatch_enabled: false,
      manual_start_only: true,
      response: {
        created_at: '2026-06-13T01:07:00Z',
        from_agent: 'jenny',
        message: 'Jenny answered the chat request.',
        project_id: 'project-hermes-mission-control',
        request_id: 'github-bridge-request-created',
        status: 'replied',
        to_agent: 'travis'
      },
      send_to_jenny_enabled: true,
      stored: true,
      timer_enabled: false,
      worker_enabled: false
    })
    expect(await screen.findByText('Jenny replied to the latest pending project message.')).toBeTruthy()
  })

  it('restores Jenny working status from bridge audit records after refresh', async () => {
    getMissionControlGitHubBridgeStatus.mockResolvedValue({
      count: 1,
      daemon_enabled: false,
      discord_automation_enabled: false,
      dispatch_enabled: false,
      display_only: true,
      execution_enabled: false,
      last_error: '',
      last_poll_at: '2026-06-13T02:01:00Z',
      last_response_at: '',
      last_response_request_id: '',
      last_status: 'hermes_answer_started',
      manual_start_only: true,
      mode: 'manual_hermes_answer',
      foreground_watch_supported: true,
      foreground_watch_running: false,
      model_routing_enabled: false,
      pending_count: 1,
      visible_pending_count: 1,
      background_pending_count: 0,
      pending_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      visible_pending_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      recent_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      response_messages: [],
      send_to_jenny_enabled: false,
      session_send_enabled: false,
      status_records: [
        {
          record: {
            created_at: '2026-06-13T02:01:00Z',
            handled_request_id: 'github-bridge-working-request',
            mode: 'manual_hermes_answer',
            pending_count: 1,
            status: 'hermes_answer_started',
            status_id: 'github-status-working'
          }
        }
      ],
      stored: false,
      timer_enabled: false,
      worker_enabled: false
    })

    await renderMissionControl()

    expect((await screen.findAllByText(/Jenny is working on the latest project message/)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Waiting for Jenny')).length).toBeGreaterThan(0)
    expect(answerMissionControlGitHubBridgeOnce).not.toHaveBeenCalled()
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

  it('saves missing Jenny reports through the append-only reports/create route only', async () => {
    await renderMissionControl()

    const projectSelect = await screen.findByLabelText('Project')
    fireEvent.change(projectSelect, { target: { value: 'project-hermes-mission-control' } })
    fireEvent.change(screen.getByLabelText('Jenny report summary'), { target: { value: 'Current Hermes report' } })
    fireEvent.change(screen.getByLabelText('Latest result'), { target: { value: 'Desktop and mobile now read projected state.' } })
    fireEvent.change(screen.getByLabelText('Risks/blockers — one per line'), { target: { value: 'proxy 9121 mismatch' } })
    fireEvent.change(screen.getByLabelText('Artifact/report links — one per line'), { target: { value: 'reports/hermes/current.md' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save missing report' }))

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
    expect(text).toContain('isNoPendingBridgeError')
    expect(text).toContain('normalizedBridgeError')
    expect(text).toContain('No message is waiting for Jenny. Send a message first.')

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
