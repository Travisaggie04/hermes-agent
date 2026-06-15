import { JsonRpcGatewayClient } from '@hermes/shared'

import type {
  ActionResponse,
  ActionStatusResponse,
  AnalyticsResponse,
  AudioSpeakResponse,
  AudioTranscriptionResponse,
  AuxiliaryModelsResponse,
  ConfigSchemaResponse,
  CronJob,
  CronJobCreatePayload,
  CronJobUpdates,
  ElevenLabsVoicesResponse,
  EnvVarInfo,
  HermesConfig,
  HermesConfigRecord,
  LogsResponse,
  MessagingPlatformsResponse,
  MessagingPlatformTestResponse,
  MessagingPlatformUpdate,
  ModelAssignmentRequest,
  ModelAssignmentResponse,
  ModelInfoResponse,
  ModelOptionsResponse,
  OAuthPollResponse,
  OAuthProvidersResponse,
  OAuthStartResponse,
  OAuthSubmitResponse,
  PaginatedSessions,
  ProfileCreatePayload,
  ProfileSetupCommand,
  ProfileSoul,
  ProfilesResponse,
  SessionMessagesResponse,
  SessionSearchResponse,
  SkillInfo,
  StatusResponse,
  ToolsetConfig,
  ToolsetInfo
} from '@/types/hermes'

const DEFAULT_GATEWAY_REQUEST_TIMEOUT_MS = 30_000

export type {
  ActionResponse,
  ActionStatusResponse,
  AnalyticsDailyEntry,
  AnalyticsModelEntry,
  AnalyticsResponse,
  AnalyticsSkillEntry,
  AnalyticsSkillsSummary,
  AnalyticsTotals,
  AudioSpeakResponse,
  AudioTranscriptionResponse,
  AuxiliaryModelsResponse,
  ConfigFieldSchema,
  ConfigSchemaResponse,
  CronJob,
  CronJobCreatePayload,
  CronJobSchedule,
  CronJobUpdates,
  ElevenLabsVoice,
  ElevenLabsVoicesResponse,
  EnvVarInfo,
  GatewayReadyPayload,
  HermesConfig,
  HermesConfigRecord,
  LogsResponse,
  MessagingEnvVarInfo,
  MessagingHomeChannel,
  MessagingPlatformInfo,
  MessagingPlatformsResponse,
  MessagingPlatformTestResponse,
  MessagingPlatformUpdate,
  ModelAssignmentRequest,
  ModelAssignmentResponse,
  ModelInfoResponse,
  ModelOptionProvider,
  ModelOptionsResponse,
  PaginatedSessions,
  ProfileCreatePayload,
  ProfileInfo,
  ProfileSetupCommand,
  ProfileSoul,
  ProfilesResponse,
  RpcEvent,
  SessionCreateResponse,
  SessionInfo,
  SessionMessage,
  SessionMessagesResponse,
  SessionResumeResponse,
  SessionRuntimeInfo,
  SessionSearchResponse,
  SessionSearchResult,
  SkillInfo,
  StatusResponse,
  ToolsetConfig,
  ToolsetInfo
} from '@/types/hermes'

export class HermesGateway extends JsonRpcGatewayClient {
  constructor() {
    super({
      closedErrorMessage: 'Hermes gateway connection closed',
      connectErrorMessage: 'Could not connect to Hermes gateway',
      createRequestId: nextId => nextId,
      notConnectedErrorMessage: 'Hermes gateway is not connected',
      requestTimeoutMs: DEFAULT_GATEWAY_REQUEST_TIMEOUT_MS
    })
  }
}

// Profile that profile-scoped REST settings (config/env/skills/tools/model/…)
// should target. Mirrors $activeGatewayProfile, pushed in from the store via
// setApiRequestProfile so this module needs no store import (avoids a cycle).
// Electron main consumes request.profile to pick which backend *process* serves
// the call; each pooled backend already has its own HERMES_HOME, so no backend
// change is needed. Null → primary, so single-profile users are unaffected.
let _apiProfile: null | string = null

export function setApiRequestProfile(profile: null | string): void {
  _apiProfile = profile || null
}

function profileScoped(): { profile?: string } {
  return _apiProfile ? { profile: _apiProfile } : {}
}

export async function listSessions(
  limit = 40,
  minMessages = 0,
  archived: 'exclude' | 'include' | 'only' = 'exclude',
  order: 'created' | 'recent' = 'recent'
): Promise<PaginatedSessions> {
  const result = await window.hermesDesktop.api<PaginatedSessions>({
    path: `/api/sessions?limit=${limit}&offset=0&min_messages=${Math.max(0, minMessages)}&archived=${archived}&order=${order}`
  })

  return {
    ...result,
    sessions: result.sessions.slice(0, limit),
    offset: 0
  }
}

// Unified, read-only session list aggregated across ALL profiles. Served by the
// primary backend straight off each profile's state.db — no per-profile backend
// is spawned. Single-profile users get the same rows as listSessions(), tagged
// profile="default".
export async function listAllProfileSessions(
  limit = 40,
  minMessages = 0,
  archived: 'exclude' | 'include' | 'only' = 'exclude',
  order: 'created' | 'recent' = 'recent',
  profile: 'all' | (string & {}) = 'all'
): Promise<PaginatedSessions> {
  const result = await window.hermesDesktop.api<PaginatedSessions>({
    path:
      `/api/profiles/sessions?limit=${limit}&offset=0&min_messages=${Math.max(0, minMessages)}` +
      `&archived=${archived}&order=${order}&profile=${encodeURIComponent(profile)}`
  })

  return {
    ...result,
    sessions: result.sessions.slice(0, limit),
    offset: 0
  }
}

export interface MissionControlProjectRecord {
  project_id: string
  name: string
  status?: string
  current_goal?: string
  next_recommended_lane?: string
  mistakes_guards?: string
  source_of_truth?: string
  profile?: string
  updated_at?: string
}

export interface MissionControlProjectCreatePayload {
  current_goal?: string
  mistakes_guards?: string
  name: string
  next_recommended_lane?: string
  profile?: string
  project_id?: string
  source_of_truth?: string
  status?: string
}

export interface MissionControlRecordEnvelope<T> {
  record: T
  record_index?: number
  record_type?: string
}

export interface MissionControlLaneRequestRecord {
  lane_request_id: string
  project_id: string
  title: string
  mode?: string
  objective?: string
  status?: string
  updated_at?: string
}

export interface MissionControlLaneRequestCreatePayload {
  allowed_actions?: string[]
  draft_prompt?: string
  expected_report_format?: string[]
  forbidden_actions?: string[]
  mode?: string
  objective?: string
  project_id: string
  stop_conditions?: string[]
  title: string
}

export interface MissionControlProjectBriefRecord {
  approval_rules?: string[]
  constraints?: string[]
  outcome?: string
  project_id: string
  status?: string
  success_criteria?: string[]
}

export interface MissionControlProjectBriefCreatePayload {
  approval_rules?: string[]
  audience?: string
  constraints?: string[]
  context_pack_path?: string
  forbidden_actions?: string[]
  name: string
  outcome: string
  project_id: string
  source_of_truth?: string
  status?: string
  success_criteria?: string[]
}

export interface MissionControlChallengeReviewRecord {
  blocking_verdicts?: string[]
  challenge_categories?: string[]
  concerns?: string[]
  decision_state?: string
  project_id: string
  questions?: string[]
  recommended_path?: string
  request_summary?: string
  required_approvals?: string[]
  status?: string
  suggested_lane_title?: string
}

export interface MissionControlChallengeReviewCreatePayload {
  blocking_verdicts?: string[]
  challenge_categories?: string[]
  concerns?: string[]
  decision_state?: string
  project_id: string
  questions?: string[]
  recommended_path?: string
  request_summary: string
  required_approvals?: string[]
  suggested_lane_title?: string
}

export interface MissionControlJennyReplyReviewRecord {
  created_at?: string
  decision: 'accepted' | 'needs_evidence' | 'needs_safer_plan' | string
  metadata?: Record<string, unknown>
  note?: string
  project_id: string
  request_id?: string
  response_id: string
  review_id: string
  reviewer?: string
}

export interface MissionControlJennyReplyReviewCreatePayload {
  decision: 'accepted' | 'needs_evidence' | 'needs_safer_plan'
  note?: string
  project_id: string
  request_id?: string
  response_id: string
  reviewer?: string
}

export interface MissionControlReportRecord {
  report_id: string
  project_id: string
  lane_request_id?: string
  summary?: string
  result?: string
  changed_files?: string[]
  tests?: string[]
  risks?: string[]
  blockers?: string[]
  next_recommended_lane?: string
  created_at?: string
  updated_at?: string
  metadata?: { artifact_links?: string[]; [key: string]: unknown }
}

export interface MissionControlProjectSession {
  cwd?: null | string
  durable_session_id?: string
  is_default_profile?: boolean
  last_active?: number
  lineage_root_id?: null | string
  link_record?: unknown
  linked_project_id?: string
  message_count?: number
  preview?: null | string
  profile?: string
  session_id: string
  source?: null | string
  started_at?: number
  suggested_project_id?: string
  title?: null | string
  tool_call_count?: number
}

export interface MissionControlProjectSessionGroup {
  linked_session_count?: number
  name: string
  project_id: string
  sessions: MissionControlProjectSession[]
  unassigned_suggestion_count?: number
}

export interface MissionControlSessionProjectLinkRecord {
  confidence?: string
  cwd_snapshot?: string
  durable_session_id?: string
  lineage_root_id?: string
  link_id: string
  link_method?: string
  linked_at?: string
  linked_by?: string
  metadata?: Record<string, unknown>
  profile?: string
  project_id: string
  session_id: string
  source?: string
  status?: string
  title_snapshot?: string
}

export interface MissionControlSessionProjectLinkCreatePayload {
  confidence?: string
  cwd_snapshot?: string
  lineage_root_id?: string
  link_method?: string
  linked_by?: string
  profile?: string
  project_id: string
  session_id: string
  source?: string
  status?: string
  title_snapshot?: string
}

export interface MissionControlSessionProjectLinkCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  session_project_link: MissionControlSessionProjectLinkRecord
  stored?: boolean
}

export interface MissionControlProjectState {
  project_id: string
  name: string
  status?: string
  current_goal?: string
  latest_report_summary?: string
  latest_result?: string
  risks?: string[]
  blockers?: string[]
  risks_blockers?: string[]
  next_recommended_lane?: string
  latest_lane_request?: MissionControlLaneRequestRecord | null
  latest_report?: MissionControlReportRecord | null
  latest_jenny_report?: MissionControlReportRecord | null
  has_real_report?: boolean
  missing_state_fields?: string[]
  report_contract?: {
    complete?: boolean
    display_only?: boolean
    missing_fields?: string[]
    required_fields?: string[]
    state?: string
    trusted_for_execution?: boolean
  }
  latest_activity_at?: string
  latest_activity_source?: string
  artifact_links?: string[]
  linked_session_count?: number
  recent_sessions?: MissionControlProjectSession[]
  unassigned_suggestion_count?: number
}

export interface MissionControlReportCreatePayload {
  project_id: string
  lane_request_id?: string
  summary: string
  result?: string
  changed_files?: string[]
  tests?: string[]
  risks?: string[]
  next_recommended_lane?: string
  artifact_links?: string[]
}

export interface MissionControlReportCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  report: MissionControlReportRecord
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlJennyBridgeRequestRecord {
  request_id: string
  project_id: string
  lane_request_id?: string
  sender?: string
  target_agent?: string
  message: string
  status?: string
  bridge_state?: string
  has_response?: boolean
  ack_key?: string
  created_at?: string
  metadata?: Record<string, unknown>
}

export interface MissionControlJennyBridgeResponseRecord {
  response_id: string
  request_id: string
  project_id: string
  lane_request_id?: string
  responder?: string
  message: string
  status?: string
  created_at?: string
  metadata?: Record<string, unknown>
}

export interface MissionControlJennyBridgePollerStatusRecord {
  status_id: string
  poller_id?: string
  mode?: string
  status?: string
  pending_count?: number
  handled_request_id?: string
  handled_response_id?: string
  last_error?: string
  runtime_path?: string
  head?: string
  operator?: string
  created_at?: string
  metadata?: Record<string, unknown>
}

export interface MissionControlJennyBridgePollerStatusResponse {
  count?: number
  dispatch_enabled?: boolean
  execution_enabled?: boolean
  last_error?: string
  last_poll_at?: string
  last_response_at?: string
  last_response_request_id?: string
  last_status?: string
  manual_start_only?: boolean
  pending_count?: number
  send_to_jenny_enabled?: boolean
  session_send_enabled?: boolean
  status_records?: Array<MissionControlRecordEnvelope<MissionControlJennyBridgePollerStatusRecord>>
  stored?: boolean
  timer_enabled?: boolean
  worker_enabled?: boolean
}

export interface MissionControlGitHubBridgeMessageRecord {
  request_id: string
  project_id: string
  from_agent: string
  to_agent: string
  status: string
  message: string
  created_at?: string
  github_repo?: string
  github_issue_number?: number
  github_comment_id?: string
  metadata?: Record<string, unknown>
}

export interface MissionControlGitHubBridgeMailboxStatusRecord {
  status_id: string
  bridge_id?: string
  repo?: string
  issue_number?: number
  mode?: string
  status?: string
  pending_count?: number
  new_message_count?: number
  handled_request_id?: string
  handled_response_id?: string
  last_error?: string
  runtime_path?: string
  head?: string
  operator?: string
  created_at?: string
  metadata?: Record<string, unknown>
}

export interface MissionControlGitHubBridgeStatusResponse {
  count?: number
  daemon_enabled?: boolean
  discord_automation_enabled?: boolean
  dispatch_enabled?: boolean
  execution_enabled?: boolean
  last_error?: string
  last_poll_at?: string
  last_response_at?: string
  last_response_request_id?: string
  last_status?: string
  manual_start_only?: boolean
  mode?: string
  foreground_watch_supported?: boolean
  foreground_watch_running?: boolean
  model_routing_enabled?: boolean
  pending_count?: number
  visible_pending_count?: number
  background_pending_count?: number
  pending_messages?: Array<MissionControlRecordEnvelope<MissionControlGitHubBridgeMessageRecord>>
  visible_pending_messages?: Array<MissionControlRecordEnvelope<MissionControlGitHubBridgeMessageRecord>>
  recent_messages?: Array<MissionControlRecordEnvelope<MissionControlGitHubBridgeMessageRecord>>
  response_messages?: Array<MissionControlRecordEnvelope<MissionControlGitHubBridgeMessageRecord>>
  send_to_jenny_enabled?: boolean
  session_send_enabled?: boolean
  status_records?: Array<MissionControlRecordEnvelope<MissionControlGitHubBridgeMailboxStatusRecord>>
  stored?: boolean
  timer_enabled?: boolean
  worker_enabled?: boolean
}

export interface MissionControlGitHubBridgeRequestCreatePayload {
  from_agent?: string
  message: string
  project_id: string
  request_id?: string
  to_agent?: string
  user_message?: string
}

export interface MissionControlGitHubBridgeRequestCreateResponse {
  dispatch_enabled?: boolean
  github_bridge_enabled?: boolean
  manual_copy_only?: boolean
  message?: MissionControlGitHubBridgeMessageRecord | null
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlGitHubBridgeAnswerOncePayload {
  confirm_manual_hermes_answer: true
  project_id: string
  request_id: string
}

export interface MissionControlGitHubBridgeAnswerOnceResponse {
  answered?: boolean
  daemon_enabled?: boolean
  dispatch_enabled?: boolean
  execution_enabled?: boolean
  github_bridge_enabled?: boolean
  manual_start_only?: boolean
  request?: MissionControlGitHubBridgeMessageRecord | null
  response?: MissionControlGitHubBridgeMessageRecord | null
  send_to_jenny_enabled?: boolean
  session_send_enabled?: boolean
  status?: MissionControlGitHubBridgeMailboxStatusRecord | Record<string, unknown>
  stored?: boolean
  timer_enabled?: boolean
  worker_enabled?: boolean
}

export interface MissionControlJennyBridgeRequestCreatePayload {
  ack_key?: string
  dedupe_key?: string
  lane_request_id?: string
  message: string
  project_id: string
  sender?: string
  target_agent?: string
}

export interface MissionControlJennyBridgeResponseCreatePayload {
  lane_request_id?: string
  message: string
  project_id: string
  request_id: string
  responder?: string
}

export interface MissionControlJennyBridgeOutboxResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  requests: Array<MissionControlRecordEnvelope<MissionControlJennyBridgeRequestRecord>>
  send_to_jenny_enabled?: boolean
}

export interface MissionControlJennyBridgeInboxResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  responses: Array<MissionControlRecordEnvelope<MissionControlJennyBridgeResponseRecord>>
  send_to_jenny_enabled?: boolean
}

export interface MissionControlJennyBridgeRequestCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  request: MissionControlJennyBridgeRequestRecord
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlJennyBridgeResponseCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  response: MissionControlJennyBridgeResponseRecord
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlWorkspaceStatus {
  accepted_baseline?: { head?: string; runtime_path?: string }
  deployment_gap?: { dashboard_deploy_needed?: boolean; deployed_head?: string; accepted_live_head?: string; latest_merged_pr?: string; state?: string }
  lane?: { active_lane_count?: number; max_active_lane?: number }
  runtime_worktree_guard?: { decision_state?: string; reason?: string }
  safety?: { dispatch_in_gateway?: boolean; send_to_jenny_enabled?: boolean }
  stale_context?: { warnings?: string[] }
}

export interface MissionControlMemoryFileLevel {
  bytes?: number
  chars?: number
  error?: string
  exists?: boolean
  limit_chars?: number
  lines?: number
  path?: string
  percent_used?: number
}

export interface MissionControlProfileMountUsage {
  error?: string
  free_bytes?: number
  path?: string
  percent_used?: number
  total_bytes?: number
  used_bytes?: number
}

export interface MissionControlProfileStorageLevel {
  bytes?: number
  components?: Record<string, MissionControlProfileStorageLevel>
  error?: string
  exists?: boolean
  path?: string
  scope?: string
}

export interface MissionControlProfileMemoryStorage {
  data?: MissionControlProfileStorageLevel
  home?: string
  memory?: MissionControlMemoryFileLevel
  mount?: MissionControlProfileMountUsage
  profile?: string
  recall_file_bytes?: number
  total_bytes?: number
  user?: MissionControlMemoryFileLevel
}

export interface MissionControlProfileMemoryStorageResponse {
  count?: number
  display_only?: boolean
  dispatch_enabled?: boolean
  dry_run_only?: boolean
  errors?: Array<{ profile?: string; error?: string }>
  profile_count?: number
  profiles?: MissionControlProfileMemoryStorage[]
  send_to_jenny_enabled?: boolean
  source?: string
  stored?: boolean
  total_bytes?: number
  total_memory_bytes?: number
  total_profile_data_bytes?: number
  total_recall_file_bytes?: number
  total_user_bytes?: number
}

export interface MissionControlProjectsResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  projects: Array<MissionControlRecordEnvelope<MissionControlProjectRecord>>
  send_to_jenny_enabled?: boolean
}

export interface MissionControlProjectCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  project: MissionControlProjectRecord
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlLaneRequestsResponse {
  count: number
  dispatch_enabled?: boolean
  lane_requests: Array<MissionControlRecordEnvelope<MissionControlLaneRequestRecord>>
  manual_copy_only?: boolean
  send_to_jenny_enabled?: boolean
}

export interface MissionControlLaneRequestCreateResponse {
  dispatch_enabled?: boolean
  lane_request: MissionControlLaneRequestRecord
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlProjectBriefsResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  project_briefs: Array<MissionControlRecordEnvelope<MissionControlProjectBriefRecord>>
  send_to_jenny_enabled?: boolean
}

export interface MissionControlProjectBriefCreateResponse {
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  project_brief: MissionControlProjectBriefRecord
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlChallengeReviewsResponse {
  challenge_reviews: Array<MissionControlRecordEnvelope<MissionControlChallengeReviewRecord>>
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  send_to_jenny_enabled?: boolean
}

export interface MissionControlChallengeReviewCreateResponse {
  challenge_review: MissionControlChallengeReviewRecord
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  record_index?: number
  record_type?: string
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlJennyReplyReviewsResponse {
  count: number
  dispatch_enabled?: boolean
  manual_start_only?: boolean
  reply_reviews: Array<MissionControlRecordEnvelope<MissionControlJennyReplyReviewRecord>>
  send_to_jenny_enabled?: boolean
  stored?: boolean
  worker_enabled?: boolean
  timer_enabled?: boolean
}

export interface MissionControlJennyReplyReviewCreateResponse {
  dispatch_enabled?: boolean
  manual_start_only?: boolean
  record_index?: number
  record_type?: string
  reply_review: MissionControlJennyReplyReviewRecord
  send_to_jenny_enabled?: boolean
  stored?: boolean
  worker_enabled?: boolean
  timer_enabled?: boolean
}

export interface MissionControlReportsResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  reports: Array<MissionControlRecordEnvelope<MissionControlReportRecord>>
  send_to_jenny_enabled?: boolean
}

export interface MissionControlProjectStateResponse {
  count: number
  dispatch_enabled?: boolean
  manual_copy_only?: boolean
  project_states: MissionControlProjectState[]
  send_to_jenny_enabled?: boolean
  stored?: boolean
}

export interface MissionControlProjectSessionsResponse {
  active_link_count?: number
  count: number
  dispatch_enabled?: boolean
  display_only?: boolean
  errors?: string[]
  execution_enabled?: boolean
  groups: MissionControlProjectSessionGroup[]
  inert_context_only?: boolean
  manual_copy_only?: boolean
  send_to_jenny_enabled?: boolean
  session_count?: number
  stored?: boolean
  trusted_for_execution?: boolean
}

const MISSION_CONTROL_API = '/api/plugins/mission-control-governance'

export function getMissionControlWorkspaceStatus(): Promise<MissionControlWorkspaceStatus> {
  return window.hermesDesktop.api<MissionControlWorkspaceStatus>({ path: `${MISSION_CONTROL_API}/workspace-status` })
}

export function getMissionControlProfileMemoryStorage(): Promise<MissionControlProfileMemoryStorageResponse> {
  return window.hermesDesktop.api<MissionControlProfileMemoryStorageResponse>({
    path: `${MISSION_CONTROL_API}/workspace/profile-memory-storage`
  })
}

export function getMissionControlProjects(): Promise<MissionControlProjectsResponse> {
  return window.hermesDesktop.api<MissionControlProjectsResponse>({ path: `${MISSION_CONTROL_API}/workspace/projects` })
}

export function createMissionControlProject(
  payload: MissionControlProjectCreatePayload
): Promise<MissionControlProjectCreateResponse> {
  return window.hermesDesktop.api<MissionControlProjectCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/projects/create`
  })
}

export function getMissionControlLaneRequests(): Promise<MissionControlLaneRequestsResponse> {
  return window.hermesDesktop.api<MissionControlLaneRequestsResponse>({ path: `${MISSION_CONTROL_API}/workspace/lane-requests` })
}

export function createMissionControlLaneRequest(
  payload: MissionControlLaneRequestCreatePayload
): Promise<MissionControlLaneRequestCreateResponse> {
  return window.hermesDesktop.api<MissionControlLaneRequestCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/lane-requests/create`
  })
}

export function getMissionControlProjectBriefs(): Promise<MissionControlProjectBriefsResponse> {
  return window.hermesDesktop.api<MissionControlProjectBriefsResponse>({ path: `${MISSION_CONTROL_API}/workspace/project-briefs` })
}

export function createMissionControlProjectBrief(
  payload: MissionControlProjectBriefCreatePayload
): Promise<MissionControlProjectBriefCreateResponse> {
  return window.hermesDesktop.api<MissionControlProjectBriefCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/project-briefs/create`
  })
}

export function getMissionControlChallengeReviews(): Promise<MissionControlChallengeReviewsResponse> {
  return window.hermesDesktop.api<MissionControlChallengeReviewsResponse>({ path: `${MISSION_CONTROL_API}/workspace/challenge-reviews` })
}

export function createMissionControlChallengeReview(
  payload: MissionControlChallengeReviewCreatePayload
): Promise<MissionControlChallengeReviewCreateResponse> {
  return window.hermesDesktop.api<MissionControlChallengeReviewCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/challenge-reviews/create`
  })
}

export function getMissionControlJennyReplyReviews(): Promise<MissionControlJennyReplyReviewsResponse> {
  return window.hermesDesktop.api<MissionControlJennyReplyReviewsResponse>({ path: `${MISSION_CONTROL_API}/workspace/jenny-reply-reviews` })
}

export function createMissionControlJennyReplyReview(
  payload: MissionControlJennyReplyReviewCreatePayload
): Promise<MissionControlJennyReplyReviewCreateResponse> {
  return window.hermesDesktop.api<MissionControlJennyReplyReviewCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/jenny-reply-reviews/create`
  })
}

export function getMissionControlReports(): Promise<MissionControlReportsResponse> {
  return window.hermesDesktop.api<MissionControlReportsResponse>({ path: `${MISSION_CONTROL_API}/workspace/reports` })
}

export function createMissionControlReport(payload: MissionControlReportCreatePayload): Promise<MissionControlReportCreateResponse> {
  return window.hermesDesktop.api<MissionControlReportCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/reports/create`
  })
}

export function getMissionControlJennyBridgeOutbox(): Promise<MissionControlJennyBridgeOutboxResponse> {
  return window.hermesDesktop.api<MissionControlJennyBridgeOutboxResponse>({ path: `${MISSION_CONTROL_API}/workspace/jenny-bridge/outbox` })
}

export function createMissionControlJennyBridgeRequest(
  payload: MissionControlJennyBridgeRequestCreatePayload
): Promise<MissionControlJennyBridgeRequestCreateResponse> {
  return window.hermesDesktop.api<MissionControlJennyBridgeRequestCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/jenny-bridge/outbox/create`
  })
}

export function getMissionControlJennyBridgeInbox(): Promise<MissionControlJennyBridgeInboxResponse> {
  return window.hermesDesktop.api<MissionControlJennyBridgeInboxResponse>({ path: `${MISSION_CONTROL_API}/workspace/jenny-bridge/inbox` })
}

export function getMissionControlJennyBridgePollerStatus(): Promise<MissionControlJennyBridgePollerStatusResponse> {
  return window.hermesDesktop.api<MissionControlJennyBridgePollerStatusResponse>({
    path: `${MISSION_CONTROL_API}/workspace/jenny-bridge/poller-status`
  })
}

export function getMissionControlGitHubBridgeStatus(): Promise<MissionControlGitHubBridgeStatusResponse> {
  return window.hermesDesktop.api<MissionControlGitHubBridgeStatusResponse>({
    path: `${MISSION_CONTROL_API}/workspace/github-bridge/status`
  })
}

export function createMissionControlGitHubBridgeRequest(
  payload: MissionControlGitHubBridgeRequestCreatePayload
): Promise<MissionControlGitHubBridgeRequestCreateResponse> {
  return window.hermesDesktop.api<MissionControlGitHubBridgeRequestCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/github-bridge/outbox/create`
  })
}

export function answerMissionControlGitHubBridgeOnce(
  payload: MissionControlGitHubBridgeAnswerOncePayload
): Promise<MissionControlGitHubBridgeAnswerOnceResponse> {
  return window.hermesDesktop.api<MissionControlGitHubBridgeAnswerOnceResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/github-bridge/answer-once`
  })
}

export function createMissionControlJennyBridgeResponse(
  payload: MissionControlJennyBridgeResponseCreatePayload
): Promise<MissionControlJennyBridgeResponseCreateResponse> {
  return window.hermesDesktop.api<MissionControlJennyBridgeResponseCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/jenny-bridge/inbox/create`
  })
}

export function createMissionControlSessionProjectLink(
  payload: MissionControlSessionProjectLinkCreatePayload
): Promise<MissionControlSessionProjectLinkCreateResponse> {
  return window.hermesDesktop.api<MissionControlSessionProjectLinkCreateResponse>({
    body: payload,
    method: 'POST',
    path: `${MISSION_CONTROL_API}/workspace/session-project-links/create`
  })
}

export function getMissionControlProjectState(): Promise<MissionControlProjectStateResponse> {
  return window.hermesDesktop.api<MissionControlProjectStateResponse>({ path: `${MISSION_CONTROL_API}/workspace/project-state` })
}

export function getMissionControlProjectSessions(): Promise<MissionControlProjectSessionsResponse> {
  return window.hermesDesktop.api<MissionControlProjectSessionsResponse>({ path: `${MISSION_CONTROL_API}/workspace/project-sessions` })
}

// Mutations take the owning `profile` so Electron routes them to that profile's
// backend (remote pool or local primary) via request.profile — matching the
// read path. A remote session's row lives only on its remote host, so a mutation
// that hit the local primary would no-op or 404. Omit for the current/default.
export function setSessionArchived(id: string, archived: boolean, profile?: string | null): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...(profile ? { profile } : {}),
    path: `/api/sessions/${encodeURIComponent(id)}`,
    method: 'PATCH',
    body: { archived }
  })
}

export function searchSessions(query: string): Promise<SessionSearchResponse> {
  return window.hermesDesktop.api<SessionSearchResponse>({
    path: `/api/sessions/search?q=${encodeURIComponent(query)}`
  })
}

// Reads another profile's transcript. For a remote profile Electron reroutes
// this GET to the remote backend (which serves its own state.db); for a local
// profile the primary opens that profile's state.db via ?profile=. Omit for
// the current/default profile.
export function getSessionMessages(id: string, profile?: string | null): Promise<SessionMessagesResponse> {
  const suffix = profile ? `?profile=${encodeURIComponent(profile)}` : ''

  return window.hermesDesktop.api<SessionMessagesResponse>({
    path: `/api/sessions/${encodeURIComponent(id)}/messages${suffix}`
  })
}

export function deleteSession(id: string, profile?: string | null): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...(profile ? { profile } : {}),
    path: `/api/sessions/${encodeURIComponent(id)}`,
    method: 'DELETE'
  })
}

export function renameSession(
  id: string,
  title: string,
  profile?: string | null
): Promise<{ ok: boolean; title: string }> {
  return window.hermesDesktop.api<{ ok: boolean; title: string }>({
    ...(profile ? { profile } : {}),
    path: `/api/sessions/${encodeURIComponent(id)}`,
    method: 'PATCH',
    body: { title, ...(profile ? { profile } : {}) }
  })
}

export function getGlobalModelInfo(): Promise<ModelInfoResponse> {
  return window.hermesDesktop.api<ModelInfoResponse>({
    ...profileScoped(),
    path: '/api/model/info'
  })
}

export function getStatus(): Promise<StatusResponse> {
  return window.hermesDesktop.api<StatusResponse>({
    path: '/api/status'
  })
}

export function getLogs(params: {
  component?: string
  file?: string
  level?: string
  lines?: number
}): Promise<LogsResponse> {
  const query = new URLSearchParams()

  if (params.file) {
    query.set('file', params.file)
  }

  if (typeof params.lines === 'number') {
    query.set('lines', String(params.lines))
  }

  if (params.level && params.level !== 'ALL') {
    query.set('level', params.level)
  }

  if (params.component && params.component !== 'all') {
    query.set('component', params.component)
  }

  const suffix = query.toString()

  return window.hermesDesktop.api<LogsResponse>({
    ...profileScoped(),
    path: suffix ? `/api/logs?${suffix}` : '/api/logs'
  })
}

export function getHermesConfig(): Promise<HermesConfig> {
  return window.hermesDesktop.api<HermesConfig>({
    ...profileScoped(),
    path: '/api/config'
  })
}

export function getHermesConfigRecord(): Promise<HermesConfigRecord> {
  return window.hermesDesktop.api<HermesConfigRecord>({
    ...profileScoped(),
    path: '/api/config'
  })
}

export function getHermesConfigDefaults(): Promise<HermesConfigRecord> {
  return window.hermesDesktop.api<HermesConfigRecord>({
    ...profileScoped(),
    path: '/api/config/defaults'
  })
}

export function getHermesConfigSchema(): Promise<ConfigSchemaResponse> {
  return window.hermesDesktop.api<ConfigSchemaResponse>({
    ...profileScoped(),
    path: '/api/config/schema'
  })
}

export function saveHermesConfig(config: HermesConfigRecord): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...profileScoped(),
    path: '/api/config',
    method: 'PUT',
    body: { config }
  })
}

export function getEnvVars(): Promise<Record<string, EnvVarInfo>> {
  return window.hermesDesktop.api<Record<string, EnvVarInfo>>({
    ...profileScoped(),
    path: '/api/env'
  })
}

export function setEnvVar(key: string, value: string): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...profileScoped(),
    path: '/api/env',
    method: 'PUT',
    body: { key, value }
  })
}

export function validateProviderCredential(
  key: string,
  value: string
): Promise<{ ok: boolean; reachable: boolean; message: string; models?: string[] }> {
  return window.hermesDesktop.api<{ ok: boolean; reachable: boolean; message: string; models?: string[] }>({
    ...profileScoped(),
    path: '/api/providers/validate',
    method: 'POST',
    body: { key, value }
  })
}

export function deleteEnvVar(key: string): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...profileScoped(),
    path: '/api/env',
    method: 'DELETE',
    body: { key }
  })
}

export function revealEnvVar(key: string): Promise<{ key: string; value: string }> {
  return window.hermesDesktop.api<{ key: string; value: string }>({
    ...profileScoped(),
    path: '/api/env/reveal',
    method: 'POST',
    body: { key }
  })
}

export function listOAuthProviders(): Promise<OAuthProvidersResponse> {
  return window.hermesDesktop.api<OAuthProvidersResponse>({
    ...profileScoped(),
    path: '/api/providers/oauth'
  })
}

export function startOAuthLogin(providerId: string): Promise<OAuthStartResponse> {
  return window.hermesDesktop.api<OAuthStartResponse>({
    ...profileScoped(),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/start`,
    method: 'POST',
    body: {}
  })
}

export function submitOAuthCode(providerId: string, sessionId: string, code: string): Promise<OAuthSubmitResponse> {
  return window.hermesDesktop.api<OAuthSubmitResponse>({
    ...profileScoped(),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/submit`,
    method: 'POST',
    body: { session_id: sessionId, code }
  })
}

export function pollOAuthSession(providerId: string, sessionId: string): Promise<OAuthPollResponse> {
  return window.hermesDesktop.api<OAuthPollResponse>({
    ...profileScoped(),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/poll/${encodeURIComponent(sessionId)}`
  })
}

export function cancelOAuthSession(sessionId: string): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    ...profileScoped(),
    path: `/api/providers/oauth/sessions/${encodeURIComponent(sessionId)}`,
    method: 'DELETE'
  })
}

export function getSkills(): Promise<SkillInfo[]> {
  return window.hermesDesktop.api<SkillInfo[]>({
    ...profileScoped(),
    path: '/api/skills'
  })
}

export function toggleSkill(name: string, enabled: boolean): Promise<{ ok: boolean; name: string; enabled: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean; name: string; enabled: boolean }>({
    ...profileScoped(),
    path: '/api/skills/toggle',
    method: 'PUT',
    body: { name, enabled }
  })
}

export function getToolsets(): Promise<ToolsetInfo[]> {
  return window.hermesDesktop.api<ToolsetInfo[]>({
    ...profileScoped(),
    path: '/api/tools/toolsets'
  })
}

export function toggleToolset(
  name: string,
  enabled: boolean
): Promise<{ ok: boolean; name: string; enabled: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean; name: string; enabled: boolean }>({
    ...profileScoped(),
    path: `/api/tools/toolsets/${encodeURIComponent(name)}`,
    method: 'PUT',
    body: { enabled }
  })
}

export function getToolsetConfig(name: string): Promise<ToolsetConfig> {
  return window.hermesDesktop.api<ToolsetConfig>({
    ...profileScoped(),
    path: `/api/tools/toolsets/${encodeURIComponent(name)}/config`
  })
}

export function selectToolsetProvider(
  name: string,
  provider: string
): Promise<{ ok: boolean; name: string; provider: string }> {
  return window.hermesDesktop.api<{ ok: boolean; name: string; provider: string }>({
    ...profileScoped(),
    path: `/api/tools/toolsets/${encodeURIComponent(name)}/provider`,
    method: 'PUT',
    body: { provider }
  })
}

export function getMessagingPlatforms(): Promise<MessagingPlatformsResponse> {
  return window.hermesDesktop.api<MessagingPlatformsResponse>({
    path: '/api/messaging/platforms'
  })
}

export function updateMessagingPlatform(
  platformId: string,
  body: MessagingPlatformUpdate
): Promise<{ ok: boolean; platform: string }> {
  return window.hermesDesktop.api<{ ok: boolean; platform: string }>({
    path: `/api/messaging/platforms/${encodeURIComponent(platformId)}`,
    method: 'PUT',
    body
  })
}

export function testMessagingPlatform(platformId: string): Promise<MessagingPlatformTestResponse> {
  return window.hermesDesktop.api<MessagingPlatformTestResponse>({
    path: `/api/messaging/platforms/${encodeURIComponent(platformId)}/test`,
    method: 'POST'
  })
}

export function getCronJobs(): Promise<CronJob[]> {
  return window.hermesDesktop.api<CronJob[]>({
    path: '/api/cron/jobs'
  })
}

export function getCronJob(jobId: string): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}`
  })
}

export function createCronJob(body: CronJobCreatePayload): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: '/api/cron/jobs',
    method: 'POST',
    body
  })
}

export function updateCronJob(jobId: string, updates: CronJobUpdates): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}`,
    method: 'PUT',
    body: { updates }
  })
}

export function pauseCronJob(jobId: string): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}/pause`,
    method: 'POST'
  })
}

export function resumeCronJob(jobId: string): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}/resume`,
    method: 'POST'
  })
}

export function triggerCronJob(jobId: string): Promise<CronJob> {
  return window.hermesDesktop.api<CronJob>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}/trigger`,
    method: 'POST'
  })
}

export function deleteCronJob(jobId: string): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    path: `/api/cron/jobs/${encodeURIComponent(jobId)}`,
    method: 'DELETE'
  })
}

export function getProfiles(): Promise<ProfilesResponse> {
  return window.hermesDesktop.api<ProfilesResponse>({
    path: '/api/profiles'
  })
}

export function createProfile(body: ProfileCreatePayload): Promise<{ name: string; ok: boolean; path: string }> {
  return window.hermesDesktop.api<{ name: string; ok: boolean; path: string }>({
    path: '/api/profiles',
    method: 'POST',
    body
  })
}

export function renameProfile(name: string, newName: string): Promise<{ name: string; ok: boolean; path: string }> {
  return window.hermesDesktop.api<{ name: string; ok: boolean; path: string }>({
    path: `/api/profiles/${encodeURIComponent(name)}`,
    method: 'PATCH',
    body: { new_name: newName }
  })
}

export function deleteProfile(name: string): Promise<{ ok: boolean; path: string }> {
  return window.hermesDesktop.api<{ ok: boolean; path: string }>({
    path: `/api/profiles/${encodeURIComponent(name)}`,
    method: 'DELETE'
  })
}

export function getProfileSoul(name: string): Promise<ProfileSoul> {
  return window.hermesDesktop.api<ProfileSoul>({
    path: `/api/profiles/${encodeURIComponent(name)}/soul`
  })
}

export function updateProfileSoul(name: string, content: string): Promise<{ ok: boolean }> {
  return window.hermesDesktop.api<{ ok: boolean }>({
    path: `/api/profiles/${encodeURIComponent(name)}/soul`,
    method: 'PUT',
    body: { content }
  })
}

export function getProfileSetupCommand(name: string): Promise<ProfileSetupCommand> {
  return window.hermesDesktop.api<ProfileSetupCommand>({
    path: `/api/profiles/${encodeURIComponent(name)}/setup-command`
  })
}

export function getUsageAnalytics(days = 30): Promise<AnalyticsResponse> {
  return window.hermesDesktop.api<AnalyticsResponse>({
    ...profileScoped(),
    path: `/api/analytics/usage?days=${Math.max(1, Math.floor(days))}`
  })
}

export function getGlobalModelOptions(): Promise<ModelOptionsResponse> {
  return window.hermesDesktop.api<ModelOptionsResponse>({
    ...profileScoped(),
    path: '/api/model/options'
  })
}

export interface RecommendedDefaultModel {
  provider: string
  model: string
  /** True/false for Nous (free vs paid tier); null for other providers. */
  free_tier: boolean | null
}

// Recommended default model for a freshly-authenticated provider. Mirrors the
// curation `hermes model` does — for Nous it honors the free/paid tier so a
// free user gets a free model instead of a paid default.
export function getRecommendedDefaultModel(provider: string): Promise<RecommendedDefaultModel> {
  return window.hermesDesktop.api<RecommendedDefaultModel>({
    ...profileScoped(),
    path: `/api/model/recommended-default?provider=${encodeURIComponent(provider)}`
  })
}

export function setGlobalModel(
  provider: string,
  model: string
): Promise<{ ok: boolean; provider: string; model: string }> {
  return window.hermesDesktop.api<{ ok: boolean; provider: string; model: string }>({
    ...profileScoped(),
    path: '/api/model/set',
    method: 'POST',
    body: {
      scope: 'main',
      provider,
      model
    }
  })
}

export function getAuxiliaryModels(): Promise<AuxiliaryModelsResponse> {
  return window.hermesDesktop.api<AuxiliaryModelsResponse>({
    ...profileScoped(),
    path: '/api/model/auxiliary'
  })
}

export function setModelAssignment(body: ModelAssignmentRequest): Promise<ModelAssignmentResponse> {
  return window.hermesDesktop.api<ModelAssignmentResponse>({
    ...profileScoped(),
    path: '/api/model/set',
    method: 'POST',
    body
  })
}

export function restartGateway(): Promise<ActionResponse> {
  return window.hermesDesktop.api<ActionResponse>({
    path: '/api/gateway/restart',
    method: 'POST'
  })
}

export function updateHermes(): Promise<ActionResponse> {
  return window.hermesDesktop.api<ActionResponse>({
    path: '/api/hermes/update',
    method: 'POST'
  })
}

export function getActionStatus(name: string, lines = 200): Promise<ActionStatusResponse> {
  return window.hermesDesktop.api<ActionStatusResponse>({
    path: `/api/actions/${encodeURIComponent(name)}/status?lines=${Math.max(1, lines)}`
  })
}

export function transcribeAudio(dataUrl: string, mimeType?: string): Promise<AudioTranscriptionResponse> {
  return window.hermesDesktop.api<AudioTranscriptionResponse>({
    path: '/api/audio/transcribe',
    method: 'POST',
    body: {
      data_url: dataUrl,
      mime_type: mimeType
    }
  })
}

export function speakText(text: string): Promise<AudioSpeakResponse> {
  return window.hermesDesktop.api<AudioSpeakResponse>({
    path: '/api/audio/speak',
    method: 'POST',
    body: { text }
  })
}

export function getElevenLabsVoices(): Promise<ElevenLabsVoicesResponse> {
  return window.hermesDesktop.api<ElevenLabsVoicesResponse>({
    path: '/api/audio/elevenlabs/voices'
  })
}
