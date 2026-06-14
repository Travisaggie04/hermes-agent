import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { sessionRoute } from '@/app/routes'
import {
  answerMissionControlGitHubBridgeOnce,
  createMissionControlChallengeReview,
  createMissionControlGitHubBridgeRequest,
  createMissionControlLaneRequest,
  createMissionControlReport,
  createMissionControlSessionProjectLink,
  getMissionControlChallengeReviews,
  getMissionControlGitHubBridgeStatus,
  getMissionControlJennyBridgeInbox,
  getMissionControlJennyBridgeOutbox,
  getMissionControlJennyBridgePollerStatus,
  getMissionControlLaneRequests,
  getMissionControlProfileMemoryStorage,
  getMissionControlProjectBriefs,
  getMissionControlProjects,
  getMissionControlProjectSessions,
  getMissionControlProjectState,
  getMissionControlReports,
  getMissionControlWorkspaceStatus,
  type MissionControlChallengeReviewRecord,
  type MissionControlGitHubBridgeMessageRecord,
  type MissionControlGitHubBridgeStatusResponse,
  type MissionControlJennyBridgePollerStatusResponse,
  type MissionControlJennyBridgeRequestRecord,
  type MissionControlJennyBridgeResponseRecord,
  type MissionControlLaneRequestRecord,
  type MissionControlProfileMemoryStorageResponse,
  type MissionControlProjectBriefRecord,
  type MissionControlProjectRecord,
  type MissionControlProjectSession,
  type MissionControlProjectSessionGroup,
  type MissionControlProjectState,
  type MissionControlReportRecord,
  type MissionControlWorkspaceStatus
} from '@/hermes'
import { cn } from '@/lib/utils'

interface MissionControlSnapshot {
  challengeReviews: MissionControlChallengeReviewRecord[]
  jennyBridgeRequests: MissionControlJennyBridgeRequestRecord[]
  jennyBridgeResponses: MissionControlJennyBridgeResponseRecord[]
  jennyBridgePollerStatus: MissionControlJennyBridgePollerStatusResponse
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
  laneRequests: MissionControlLaneRequestRecord[]
  memoryStorage: MissionControlProfileMemoryStorageResponse
  projectBriefs: MissionControlProjectBriefRecord[]
  projectSessionGroups: MissionControlProjectSessionGroup[]
  projects: MissionControlProjectRecord[]
  projectStates: MissionControlProjectState[]
  reports: MissionControlReportRecord[]
  workspaceStatus: MissionControlWorkspaceStatus
}

const emptySnapshot: MissionControlSnapshot = {
  challengeReviews: [],
  jennyBridgeRequests: [],
  jennyBridgeResponses: [],
  jennyBridgePollerStatus: {},
  githubBridgeStatus: {},
  laneRequests: [],
  memoryStorage: {},
  projectBriefs: [],
  projectSessionGroups: [],
  projects: [],
  projectStates: [],
  reports: [],
  workspaceStatus: {}
}

const REAL_PROJECT_IDS = [
  'project-hermes-mission-control',
  'project-long-form-video',
  'project-shorts-video',
  'project-tool-tally',
  'project-waha-work'
]
const HERMES_PROJECT_ID = 'project-hermes-mission-control'
const HERMES_UPDATE_LANE_REQUEST = [
  'Start a safe Hermes update readiness lane for the VPS and laptop Hermes worker node.',
  'Inventory the existing VPS-triggered laptop worker-node update path and current installed versions first.',
  'Treat the native laptop desktop app bottom-bar version as a separate installed worker-node version; accepted-live merges and dashboard-only deploys do not update that installed app.',
  'Prepare a non-live VPS dashboard runtime at accepted-live and validate it before any dashboard-only switch.',
  'Keep gateway update as a separate explicit lane.',
  'Do not trigger the laptop worker-node update automatically, restart/switch gateway, dispatch, send sessions, use Waha/social/payment/customer actions, enable new background workers/timers/daemons/cron, or inspect/print secrets.'
].join(' ')
const HERMES_STORAGE_CLEANUP_LANE_REQUEST = [
  'Start a safe Hermes storage cleanup readiness lane for the VPS and laptop Hermes worker node.',
  'Inventory VPS disk usage, large runtime/worktree/cache/build artifacts, logs, and Mission Control record growth before recommending cleanup.',
  'Preserve rollback runtimes and accepted-live evidence. Do not delete anything without a separate explicit cleanup approval.',
  'Prefer moving review artifacts or exports to connected long-term storage when useful: OneDrive travis_Littleton@msn.com, Family Hub secondary storage, or the 5TB Google Drive.',
  'Keep laptop cleanup advisory-only unless Travis separately approves worker-node cleanup.',
  'Do not delete files, prune runtimes, mutate records/config/state.db, restart/switch gateway, dispatch, send sessions, use Waha/social/payment/customer actions, enable workers/timers/daemons/cron, or inspect/print secrets.'
].join(' ')

const REAL_PROJECT_NAMES = [
  'Hermes / Mission Control',
  'Long-form Video',
  'Shorts Video',
  'Tool & Tally',
  'Waha Work'
]

const CANONICAL_REAL_PROJECTS: MissionControlProjectRecord[] = [
  {
    current_goal: 'Make Mission Control the primary Jenny workspace before resuming other projects.',
    name: 'Hermes / Mission Control',
    next_recommended_lane: 'Continue the Mission Control/Jenny recovery lane.',
    project_id: 'project-hermes-mission-control',
    source_of_truth: 'Mission Control recovery records',
    status: 'Active recovery lane'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Long-form Video',
    next_recommended_lane: 'Resume with a read-only toolchain/proof plan after Jenny is stable.',
    project_id: 'project-long-form-video',
    source_of_truth: 'Mission Control project anchor',
    status: 'Paused'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Shorts Video',
    next_recommended_lane: 'Resume with a read-only queue/status audit after Jenny is stable.',
    project_id: 'project-shorts-video',
    source_of_truth: 'Mission Control project anchor',
    status: 'Paused'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Tool & Tally',
    next_recommended_lane: 'Resume with report-engine fixture recovery before checkout or outreach.',
    project_id: 'project-tool-tally',
    source_of_truth: 'Mission Control project anchor',
    status: 'Paused'
  },
  {
    current_goal: 'Paused until Jenny/Mission Control is stable.',
    name: 'Waha Work',
    next_recommended_lane: 'Resume only after isolated Waha approval gates are clear.',
    project_id: 'project-waha-work',
    source_of_truth: 'Mission Control project anchor',
    status: 'Paused'
  }
]

const ACTIVE_OS_PROJECT_IDS = [HERMES_PROJECT_ID]

const PAUSED_PROJECT_IDS = [
  'project-shorts-video',
  'project-long-form-video',
  'project-tool-tally',
  'project-waha-work'
]

const MAX_COPY_PROMPT_CHARS = 2000
const MAX_PHONE_SAFE_PACKET_CHARS = 1900

function text(value: unknown, fallback = 'Not recorded'): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function yesNo(value: unknown): string {
  return value === true ? 'yes' : value === false ? 'no' : 'unknown'
}

function formatBytes(value: unknown): string {
  const bytes = typeof value === 'number' && Number.isFinite(value) ? value : 0
  if (bytes < 1024) {
    return `${bytes} B`
  }
  const units = ['KB', 'MB', 'GB', 'TB']
  let amount = bytes / 1024
  for (const unit of units) {
    if (amount < 1024 || unit === units[units.length - 1]) {
      return `${amount.toFixed(amount >= 10 ? 0 : 1)} ${unit}`
    }
    amount /= 1024
  }
  return `${bytes} B`
}

function listText(values: unknown, fallback = 'None recorded'): string {
  if (!Array.isArray(values) || values.length === 0) {
    return fallback
  }

  return values.map(item => String(item)).filter(Boolean).join(', ') || fallback
}

function lineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map(item => item.trim())
    .filter(Boolean)
}

function reportArtifactLinks(report: MissionControlReportRecord | null, state: MissionControlProjectState | null): string[] {
  return state?.artifact_links ?? report?.metadata?.artifact_links ?? report?.changed_files ?? []
}

function reportContractMissing(report: MissionControlReportRecord | null): string[] {
  if (!report) {
    return ['report']
  }

  const hasRisks = Boolean(report.risks?.length || report.blockers?.length)
  const hasEvidence = Boolean(report.changed_files?.length || report.metadata?.artifact_links?.length)

  return [
    report.summary ? '' : 'summary',
    report.result ? '' : 'result',
    hasRisks ? '' : 'risks/blockers',
    hasEvidence ? '' : 'evidence',
    report.tests?.length ? '' : 'tests',
    report.next_recommended_lane ? '' : 'next lane'
  ].filter(Boolean)
}

function reportContractSummary(report: MissionControlReportRecord | null): string {
  const missing = reportContractMissing(report)

  if (missing.includes('report')) {
    return 'No report yet'
  }

  return missing.length ? `Missing: ${missing.join(', ')}` : 'Complete'
}

function reportContractSummaryForState(
  state: MissionControlProjectState | null,
  report: MissionControlReportRecord | null
): string {
  const contract = state?.report_contract
  const missing = contract?.missing_fields?.filter(Boolean) ?? []
  if (contract?.state === 'missing_report' || missing.includes('report')) {
    return 'No report yet'
  }
  if (missing.length) {
    return `Missing: ${missing.join(', ')}`
  }
  if (contract?.complete === true || contract?.state === 'complete') {
    return 'Complete'
  }
  return reportContractSummary(report)
}

function freshnessLabel(state: MissionControlProjectState | null): string {
  if (state?.has_real_report) {
    return 'Live report available'
  }

  return 'Seed only — needs first report'
}

function truncate(value: string, maxChars: number): string {
  if (value.length <= maxChars) {
    return value
  }

  return `${value.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`
}

function compactText(value: string | string[] | null | undefined, maxChars: number): string {
  const raw = Array.isArray(value) ? value.filter(Boolean).join('; ') : value ?? ''
  const normalized = raw.replace(/\s+/g, ' ').trim()

  return normalized.length > maxChars ? `${normalized.slice(0, Math.max(0, maxChars - 3)).trim()}...` : normalized
}

function projectRequestPreview(value: string, maxChars: number): string {
  const requestMatch = value.match(/Request:\s*([\s\S]*?)(?:\n\s*\nCurrent brief:|\n\s*\nChallenge state:|$)/i)
  return compactText(requestMatch?.[1] ?? value, maxChars)
}

function chatStatusLabel(value: string | undefined): string {
  switch (value) {
    case 'queued':
      return 'sent'
    case 'replied':
      return 'replied'
    case 'retry_requested':
      return 'retry requested'
    case 'response_appended':
      return 'reply received'
    default:
      return value || 'sent'
  }
}

function pendingJennyMessageCount(
  requests: MissionControlJennyBridgeRequestRecord[],
  responses: MissionControlJennyBridgeResponseRecord[]
): number {
  const repliedRequestIds = new Set(responses.map(response => response.request_id).filter(Boolean))
  return requests.filter(request => {
    const state = request.bridge_state ?? request.status ?? 'queued'
    return state !== 'replied' && !(request.request_id && repliedRequestIds.has(request.request_id))
  }).length
}

function latestPendingGitHubBridgeMessage(messages: MissionControlGitHubBridgeMessageRecord[]): MissionControlGitHubBridgeMessageRecord | null {
  const repliedRequestIds = new Set(
    messages
      .filter(message => message.status === 'replied' || message.from_agent === 'jenny')
      .map(message => message.request_id)
      .filter(Boolean)
  )
  const pending = messages.filter(message =>
    message.to_agent === 'jenny' &&
    ['queued', 'retry_requested'].includes(message.status ?? '') &&
    !repliedRequestIds.has(message.request_id)
  )
  return pending.length ? pending[pending.length - 1] : null
}

function isDiagnosticChatMessage(message?: string): boolean {
  const text = (message ?? '').toLowerCase()
  return [
    'codex app-server startup failed',
    'desktop phone bridge',
    'error guard',
    'failure guarded',
    'local error',
    'mission control two process',
    'reply with one sentence',
    'success smoke reached',
    'bridge works',
    'smoke'
  ].some(marker => text.includes(marker))
}

function bridgeRequestId(): string {
  const fallback = Math.random().toString(16).slice(2, 14)
  return `mission-control-chat-${globalThis.crypto?.randomUUID?.() ?? fallback}`
}

function jennyDeliveryStatus(
  pendingCount: number,
  responseCount: number,
  bridgeStatus: MissionControlJennyBridgePollerStatusResponse,
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
): string {
  if (bridgeStatus.last_error || githubBridgeStatus.last_error) {
    return 'Jenny bridge needs attention'
  }
  if (githubBridgeStatus.foreground_watch_running) {
    return pendingCount ? `${pendingCount} waiting while bridge is watching` : 'Bridge watching for replies'
  }
  if (pendingCount) {
    return `${pendingCount} sent; waiting for Jenny`
  }
  if (responseCount) {
    return 'Replies up to date'
  }
  return 'Ready for your first message'
}

function jennyConnectionState(
  pendingCount: number,
  responseCount: number,
  bridgeStatus: MissionControlJennyBridgePollerStatusResponse,
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
): { detail: string; label: string; tone: 'bad' | 'good' | 'idle' | 'warn' } {
  if (bridgeStatus.last_error || githubBridgeStatus.last_error) {
    return {
      detail: 'Open advanced controls, check the bridge error, then refresh replies.',
      label: 'Jenny needs attention',
      tone: 'bad'
    }
  }
  if (githubBridgeStatus.foreground_watch_running) {
    return {
      detail: pendingCount ? `${pendingCount} message${pendingCount === 1 ? '' : 's'} waiting while the bridge watches.` : 'Bridge is watching for replies.',
      label: 'Jenny is watching',
      tone: 'good'
    }
  }
  if (pendingCount) {
    return {
      detail: `${pendingCount} message${pendingCount === 1 ? '' : 's'} sent; waiting for Jenny.`,
      label: 'Waiting for Jenny',
      tone: 'warn'
    }
  }
  if (responseCount) {
    return {
      detail: 'Review the latest reply, then send the next bounded message.',
      label: 'Jenny replied',
      tone: 'good'
    }
  }
  return {
    detail: 'Type one bounded project message to start.',
    label: 'Ready to message',
    tone: 'idle'
  }
}

function jennyStatusToneClass(tone: 'bad' | 'good' | 'idle' | 'warn'): string {
  if (tone === 'bad') {
    return 'border-destructive/40 bg-destructive/10 text-destructive'
  }
  if (tone === 'good') {
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
  }
  if (tone === 'warn') {
    return 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
  }
  return 'border-border/70 bg-muted/40 text-muted-foreground'
}

function jennyNextStep(
  pendingCount: number,
  responseCount: number,
  hasRunnablePendingMessage: boolean,
  bridgeStatus: MissionControlJennyBridgePollerStatusResponse,
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
): string {
  if (bridgeStatus.last_error || githubBridgeStatus.last_error) {
    return 'Open safety details, check the bridge error, then refresh replies.'
  }
  if (hasRunnablePendingMessage) {
    return 'Click Get Jenny reply to ask Jenny for one response to the latest message.'
  }
  if (pendingCount) {
    return 'A message is waiting; refresh replies or wait for the bridge.'
  }
  if (responseCount) {
    return 'Review Jenny\'s latest reply, then send the next bounded message.'
  }
  return 'Type one bounded project message, then click Send to Jenny.'
}

function unwrapRecords<T>(items: Array<{ record?: T } | T> | undefined): T[] {
  if (!Array.isArray(items)) {
    return []
  }

  return items.map(item => ('record' in Object(item) ? (item as { record?: T }).record : item)).filter(Boolean) as T[]
}

function isRealProject(project: MissionControlProjectRecord): boolean {
  return REAL_PROJECT_IDS.includes(project.project_id) || REAL_PROJECT_NAMES.includes(project.name)
}

function isSmokeProject(project: MissionControlProjectRecord): boolean {
  return /smoke/i.test(`${project.project_id} ${project.name} ${project.status ?? ''}`)
}

function sortRealProjects(projects: MissionControlProjectRecord[]): MissionControlProjectRecord[] {
  return [...projects].sort((a, b) => {
    const aIndex = REAL_PROJECT_IDS.includes(a.project_id) ? REAL_PROJECT_IDS.indexOf(a.project_id) : REAL_PROJECT_NAMES.indexOf(a.name)
    const bIndex = REAL_PROJECT_IDS.includes(b.project_id) ? REAL_PROJECT_IDS.indexOf(b.project_id) : REAL_PROJECT_NAMES.indexOf(b.name)

    return (aIndex < 0 ? Number.MAX_SAFE_INTEGER : aIndex) - (bIndex < 0 ? Number.MAX_SAFE_INTEGER : bIndex)
  })
}

function canonicalRealProjects(projects: MissionControlProjectRecord[]): MissionControlProjectRecord[] {
  return CANONICAL_REAL_PROJECTS.map(canonical => {
    const existing = projects.find(project => project.project_id === canonical.project_id)
      ?? projects.find(project => project.name === canonical.name)

    return existing ? { ...canonical, ...existing } : canonical
  })
}

function stateForProject(project: MissionControlProjectRecord, states: MissionControlProjectState[]) {
  return states.find(state => state.project_id === project.project_id) ?? null
}

function sessionGroupForProject(project: MissionControlProjectRecord, groups: MissionControlProjectSessionGroup[]) {
  return groups.find(group => group.project_id === project.project_id) ?? null
}

function unassignedSessionGroup(groups: MissionControlProjectSessionGroup[]) {
  return groups.find(group => group.project_id === 'unassigned-general') ?? null
}

function suggestedSessionsForProject(projectId: string, groups: MissionControlProjectSessionGroup[]): MissionControlProjectSession[] {
  return (unassignedSessionGroup(groups)?.sessions ?? []).filter(session => session.suggested_project_id === projectId).slice(0, 3)
}

function projectNameForId(projectId: string, projects: MissionControlProjectRecord[]): string {
  return projects.find(project => project.project_id === projectId)?.name ?? projectId
}

function sessionTitle(session: MissionControlProjectSession): string {
  return text(session.title || session.preview || session.session_id, 'Untitled session')
}

function basename(path: string | null | undefined): string {
  if (!path) {
    return ''
  }

  return path
    .replace(/[\\/]+$/, '')
    .split(/[\\/]/)
    .filter(Boolean)
    .pop() ?? path
}

function sessionMeta(session: MissionControlProjectSession): string {
  const meta = [session.profile, session.source, basename(session.cwd)].filter(Boolean)

  return meta.length ? meta.join(' · ') : 'No profile/source recorded'
}

function latestLaneForProject(projectId: string, lanes: MissionControlLaneRequestRecord[]) {
  return [...lanes].reverse().find(lane => lane.project_id === projectId) ?? null
}

function latestReportForProject(projectId: string, reports: MissionControlReportRecord[]) {
  return [...reports].reverse().find(report => report.project_id === projectId) ?? null
}

function latestForProject<T extends { project_id?: string }>(projectId: string, records: T[]) {
  return [...records].reverse().find(record => record.project_id === projectId) ?? null
}

export function summarizeWorkspaceStatus(status: MissionControlWorkspaceStatus) {
  return {
    activeLaneCount: status.lane?.active_lane_count ?? 0,
    deploymentGapState: status.deployment_gap?.state ?? 'unknown',
    deploymentNeeded: status.deployment_gap?.dashboard_deploy_needed ?? false,
    deployedHead: status.deployment_gap?.deployed_head ?? status.accepted_baseline?.head ?? 'unknown',
    dispatch: status.safety?.dispatch_in_gateway,
    guard: status.runtime_worktree_guard?.decision_state ?? 'unknown',
    head: status.deployment_gap?.accepted_live_head ?? status.accepted_baseline?.head ?? 'unknown',
    latestMergedPr: status.deployment_gap?.latest_merged_pr ?? '',
    runtime: status.accepted_baseline?.runtime_path ?? 'unknown',
    staleWarnings: status.stale_context?.warnings ?? []
  }
}

function dashboardUpdateNotice(status: ReturnType<typeof summarizeWorkspaceStatus>): string {
  if (!status.deploymentNeeded) {
    return ''
  }

  const latest = status.latestMergedPr ? ` PR #${status.latestMergedPr}` : ' the latest accepted-live changes'
  return `Desktop can be current while phone/web waits for a safe dashboard-only update.${latest} is merged but not served by the dashboard yet.`
}

interface ProjectRenderModel {
  artifactLinks: string[]
  blockers: unknown
  latestActivityAt: string
  latestActivitySource: string
  latestReportSummary: string
  latestResult: string
  missingStateFields: string[]
  nextLane: string
  reportContract: string
  risks: unknown
}

type ProjectKanbanColumnId =
  | 'intake'
  | 'needs-clarification'
  | 'challenge-review'
  | 'lane-draft'
  | 'awaiting-approval'
  | 'active'
  | 'evidence-review'
  | 'accepted'
  | 'blocked-rollback'

interface ProjectKanbanColumn {
  description: string
  id: ProjectKanbanColumnId
  title: string
}

interface ProjectKanbanCard {
  columnId: ProjectKanbanColumnId
  detail: string
  lane: MissionControlLaneRequestRecord | null
  nextLane: string
  project: MissionControlProjectRecord
  readiness: ReturnType<typeof projectReadinessLabel>
  report: MissionControlReportRecord | null
  reportContract: string
}

interface ActiveLaneCard {
  brief: MissionControlProjectBriefRecord | null
  currentGoal: string
  latestEvidence: string
  lane: MissionControlLaneRequestRecord | null
  nextLane: string
  project: MissionControlProjectRecord
  readiness: ReturnType<typeof projectReadinessLabel>
  report: MissionControlReportRecord | null
  reportContract: string
  review: MissionControlChallengeReviewRecord | null
  status: string
}

const PROJECT_KANBAN_COLUMNS: ProjectKanbanColumn[] = [
  { id: 'intake', title: 'Intake', description: 'Needs a project brief or source-of-truth anchor.' },
  { id: 'needs-clarification', title: 'Needs Clarification', description: 'Jenny should question scope, risks, or requested approach.' },
  { id: 'challenge-review', title: 'Challenge Review', description: 'Waiting for the challenge gate before lane drafting.' },
  { id: 'lane-draft', title: 'Lane Draft', description: 'Clear challenge review exists; draft a bounded lane.' },
  { id: 'awaiting-approval', title: 'Awaiting Approval', description: 'Drafted or approval-needed work must wait on Travis.' },
  { id: 'active', title: 'Active', description: 'Approved work in progress; watch evidence and stop conditions.' },
  { id: 'evidence-review', title: 'Evidence Review', description: 'Jenny reported results; verify files, checks, and risks.' },
  { id: 'accepted', title: 'Accepted', description: 'Accepted result or completed lane with recorded evidence.' },
  { id: 'blocked-rollback', title: 'Blocked / Rollback', description: 'Unsafe, wrong-approach, blocked, or rollback-aware work.' }
]

interface ReportFormState {
  projectId: string
  laneRequestId: string
  summary: string
  result: string
  risks: string
  changedFiles: string
  tests: string
  artifactLinks: string
  nextRecommendedLane: string
}

const emptyReportForm: ReportFormState = {
  artifactLinks: '',
  changedFiles: '',
  laneRequestId: '',
  nextRecommendedLane: '',
  projectId: '',
  result: '',
  risks: '',
  summary: '',
  tests: ''
}

type SessionLinkAction = 'link' | 'move' | 'suggested'

interface SessionLinkDialogState {
  action: SessionLinkAction
  confirmed: boolean
  currentProjectId: string
  projectId: string
  session: MissionControlProjectSession
}

function durableSessionId(session: MissionControlProjectSession): string {
  return session.lineage_root_id || session.durable_session_id || session.session_id
}

function sessionLinkPayload(dialog: SessionLinkDialogState) {
  const durable = durableSessionId(dialog.session)

  return {
    confidence: 'manual',
    cwd_snapshot: dialog.session.cwd || undefined,
    lineage_root_id: durable || undefined,
    link_method: 'manual',
    profile: dialog.session.profile || undefined,
    project_id: dialog.projectId,
    session_id: dialog.session.session_id,
    source: dialog.session.source || undefined,
    status: 'active',
    title_snapshot: sessionTitle(dialog.session)
  }
}

function projectOptionsForDialog(projects: MissionControlProjectRecord[], dialog: SessionLinkDialogState | null): MissionControlProjectRecord[] {
  if (!dialog || dialog.action !== 'move') {
    return projects
  }

  return projects.filter(project => project.project_id !== dialog.currentProjectId)
}

function projectForDialog(projects: MissionControlProjectRecord[], projectId: string): MissionControlProjectRecord | null {
  return projects.find(project => project.project_id === projectId) ?? null
}

function projectRenderModel(
  project: MissionControlProjectRecord,
  report: MissionControlReportRecord | null,
  state: MissionControlProjectState | null
): ProjectRenderModel {
  return {
    artifactLinks: reportArtifactLinks(report, state),
    blockers: state?.blockers ?? report?.blockers,
    latestActivityAt: text(state?.latest_activity_at, 'No activity time recorded'),
    latestActivitySource: text(state?.latest_activity_source, 'project'),
    latestReportSummary: text(state?.latest_report_summary || report?.summary, 'No report yet'),
    latestResult: text(state?.latest_result || report?.result, 'No result yet'),
    missingStateFields: state?.missing_state_fields ?? [],
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane, 'No recommended lane yet'),
    reportContract: reportContractSummaryForState(state, report),
    risks: state?.risks ?? state?.risks_blockers ?? report?.risks
  }
}

interface ProjectLaneTemplate {
  allowed: string
  forbidden: string
  objective: string
  preflight: string
  report: string
  stop: string
}

const PROJECT_LANE_TEMPLATES: Record<string, ProjectLaneTemplate> = {
  'project-hermes-mission-control': {
    allowed: 'Read APIs, inspect Desktop/backend state, edit scoped Desktop source/tests only when implementation is explicitly approved.',
    forbidden: 'No deploy, restart, runtime switch, records/config mutation, dispatch, queue/model routing, enforcement, hidden workers, or secrets.',
    objective: 'Improve Mission Control as the primary Desktop workspace while keeping backend source-of-truth and manual-copy controls.',
    preflight: 'Confirm accepted runtime/head, Runtime Worktree Guard=pass, dispatch=false, active_lane_count=0, stale_warnings=[].',
    report: 'preflight, changed files, UI/source proof, tests, PR/status, no-forbidden-mutation confirmation.',
    stop: 'Stop if live runtime drifts, guard fails, dispatch enables, stale warnings appear, or a deploy/restart would be needed.'
  },
  'project-long-form-video': {
    allowed: 'Plan/review adult animated/vector explainer pipeline, toolchain proofs, scripts, QA criteria, and manual next-lane packets.',
    forbidden: 'No posting, paid API render, avatar-first pivot, generic static-card fallback, long unattended render, or public/customer action.',
    objective: 'Advance the long-form adult animated explainer lane with reusable character/prop workflow and evidence-backed watchability.',
    preflight: 'Check current concept/toolchain status, cost/risk gates, review artifacts, and whether a small proof is safer than long production.',
    report: 'objective, source/toolchain checks, recommended proof, risks/costs, review package path if any, next decision needed.',
    stop: 'Stop if paid spend, public publishing, account linking, or a long render is required without fresh approval.'
  },
  'project-shorts-video': {
    allowed: 'Plan short-form topics/hooks, review proof packages, improve prompts/QA, and prepare manual production packets.',
    forbidden: 'No posting, paid API spend, account changes, fake evidence framing, avatar fallback, or unreviewed batch publishing.',
    objective: 'Improve Shorts/Signal Room style output with strong hooks, readable typography, motion quality, and platform-safe packaging.',
    preflight: 'Check channel/status lock, latest proof quality, topic fit, cost/credit exposure, and no public-action gate is crossed.',
    report: 'hook/topic, proof status, QA notes, risks, exact next production lane, approval needed before posting/spend.',
    stop: 'Stop if posting, paid rendering, credential/account mutation, or unbounded batch work is needed.'
  },
  'project-tool-tally': {
    allowed: 'Inspect staging/public pages, draft careful PRs, validate read-only customer-facing copy, and prepare gated launch/hardening packets.',
    forbidden: 'No payments, paid-order mutation, launch, customer delivery, outreach, public intake changes, or production deploy without approval.',
    objective: 'Move Tool & Tally forward safely while preserving launch gates, payment safety, and evidence-first customer-facing quality.',
    preflight: 'Confirm environment, changed-file scope, no live/payment/outreach path, order watchdog unaffected, and customer-facing copy is sanitized.',
    report: 'preflight, files/URLs checked, risk/payment/outreach gates, tests or browser QA, PR/status, next approval gate.',
    stop: 'Stop if payment/order data, public launch, customer contact, deploy, or credential change becomes necessary.'
  },
  'project-waha-work': {
    allowed: 'Prepare owner-side Waha inspection packets, review technical docs, and keep work isolated to Waha profile/context.',
    forbidden: 'No cross-profile memory bleed, no business/social/Family Hub contamination, no unapproved numbers as final, no public/customer action.',
    objective: 'Support Waha owner-side inspection engineering with isolated, evidence-based technical review and clear management-safe outputs.',
    preflight: 'Confirm Waha profile/thread/context, document scope, source standards, assumptions, and review-only status before analysis.',
    report: 'scope, documents/standards used, findings, R/Y/G or technical notes, assumptions, exact Travis review questions.',
    stop: 'Stop if context belongs outside Waha, source docs are missing, numbers need approval, or cross-contamination risk appears.'
  }
}

function templateForProject(project: MissionControlProjectRecord): ProjectLaneTemplate {
  return PROJECT_LANE_TEMPLATES[project.project_id] ?? {
    allowed: 'Read current project state and prepare a manual next-lane packet only.',
    forbidden: 'No dispatch, deploy, restart, records/config mutation, public/customer action, payments, or secrets.',
    objective: `Prepare the next safe lane for ${project.name}.`,
    preflight: 'Confirm source-of-truth state, guard status, dispatch=false, active_lane_count=0, and stale_warnings=[].',
    report: 'preflight, recommended lane, blockers, verification, no-forbidden-mutation confirmation.',
    stop: 'Stop if the task requires mutation or approval outside the current manual-copy lane.'
  }
}

export function buildMissionControlCopyPrompt({
  project,
  status,
  state,
  report
}: {
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
}): string {
  const model = projectRenderModel(project, report, state)
  const template = templateForProject(project)
  const risksBlockers = [listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'
  const noHistory = model.latestReportSummary === 'No report yet' && model.latestResult === 'No result yet'
  const historyFallback = noHistory ? 'No prior report/result exists; start by verifying current state before acting.' : ''

  const prompt = `PROJECT NEXT LANE — REVIEW PACKET

Project: ${project.name}
Objective: ${template.objective}
Current goal: ${text(state?.current_goal ?? project.current_goal)}
Status: ${text(state?.status ?? project.status)}
Latest report: ${model.latestReportSummary}
Latest result: ${model.latestResult}
${historyFallback ? `Fallback: ${historyFallback}
` : ''}Risks/blockers: ${risksBlockers}
Next lane: ${model.nextLane}

Allowed actions: ${template.allowed}
Forbidden actions: ${template.forbidden}
Preflight checks: ${template.preflight}
Stop conditions: ${template.stop}
Expected report format: ${template.report}

Safety: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}; stale_warnings=${status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'}.
Use the guarded project chat to send this through the Jenny mailbox, or copy manually after review. Direct session send remains disabled.`

  return truncate(prompt, MAX_COPY_PROMPT_CHARS)
}

function projectReadinessLabel(
  brief: MissionControlProjectBriefRecord | null,
  review: MissionControlChallengeReviewRecord | null
): { detail: string; label: string } {
  if (!brief) {
    return { detail: 'Create or update the project brief before Jenny drafts work.', label: 'Needs brief' }
  }
  if (!review) {
    return { detail: 'Run the Jenny challenge gate before creating a lane draft.', label: 'Needs challenge' }
  }
  if (review.decision_state === 'clear_and_safe') {
    return { detail: 'Latest challenge review cleared a bounded lane draft.', label: 'Lane draft ok' }
  }
  if (review.decision_state === 'needs_approval') {
    return { detail: 'Travis needs to approve the path before Jenny proceeds.', label: 'Needs approval' }
  }
  if (review.decision_state === 'unsafe' || review.decision_state === 'wrong_approach_likely') {
    return { detail: 'Jenny should push back and recommend a safer path.', label: 'Challenge blocked' }
  }

  return { detail: 'Clarify the request or split it before a lane draft.', label: 'Spec first' }
}

function laneDraftBlockMessage(review: MissionControlChallengeReviewRecord | null): string | null {
  if (!review) {
    return 'Create a Jenny challenge review before saving a lane request draft.'
  }

  if (review.decision_state !== 'clear_and_safe') {
    return `Latest challenge review is ${review.decision_state || 'missing'}. Resolve that before saving a lane request draft.`
  }

  return null
}

function normalizedText(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(item => String(item)).join(' ').toLowerCase()
  }

  return String(value ?? '').toLowerCase()
}

function hasBlockingSignal(model: ProjectRenderModel, review: MissionControlChallengeReviewRecord | null): boolean {
  const reviewState = review?.decision_state ?? ''
  if (reviewState === 'unsafe' || reviewState === 'wrong_approach_likely') {
    return true
  }

  const combined = `${normalizedText(model.blockers)} ${normalizedText(model.risks)}`
  return /\b(blocked|blocker|rollback|unsafe|wrong approach)\b/.test(combined) && !/\b(no blockers?|none)\b/.test(combined)
}

function projectKanbanColumnFor({
  brief,
  lane,
  model,
  report,
  review,
  state
}: {
  brief: MissionControlProjectBriefRecord | null
  lane: MissionControlLaneRequestRecord | null
  model: ProjectRenderModel
  report: MissionControlReportRecord | null
  review: MissionControlChallengeReviewRecord | null
  state: MissionControlProjectState | null
}): ProjectKanbanColumnId {
  if (hasBlockingSignal(model, review)) {
    return 'blocked-rollback'
  }
  if (!brief) {
    return 'intake'
  }
  if (!review) {
    return 'challenge-review'
  }
  if (review.decision_state === 'needs_spec_first') {
    return 'needs-clarification'
  }
  if (review.decision_state === 'needs_approval') {
    return 'awaiting-approval'
  }
  if (review.decision_state !== 'clear_and_safe') {
    return 'needs-clarification'
  }
  if (!lane) {
    return 'lane-draft'
  }

  const laneStatus = (lane.status ?? '').toLowerCase()
  if (laneStatus === 'accepted' || laneStatus === 'completed' || laneStatus === 'complete') {
    return 'accepted'
  }
  if (laneStatus === 'active' || laneStatus === 'approved' || laneStatus === 'running') {
    return 'active'
  }
  if (state?.has_real_report || report) {
    return 'evidence-review'
  }
  if (laneStatus === 'draft' || laneStatus === 'pending' || laneStatus === 'proposed' || laneStatus === '') {
    return 'awaiting-approval'
  }

  return 'lane-draft'
}

function projectKanbanCardFor(project: MissionControlProjectRecord, snapshot: MissionControlSnapshot): ProjectKanbanCard {
  const state = stateForProject(project, snapshot.projectStates)
  const brief = latestForProject(project.project_id, snapshot.projectBriefs)
  const review = latestForProject(project.project_id, snapshot.challengeReviews)
  const lane = state?.latest_lane_request ?? latestLaneForProject(project.project_id, snapshot.laneRequests)
  const report = state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)
  const model = projectRenderModel(project, report, state)
  const readiness = projectReadinessLabel(brief, review)

  return {
    columnId: projectKanbanColumnFor({ brief, lane, model, report, review, state }),
    detail: readiness.detail,
    lane,
    nextLane: model.nextLane,
    project,
    readiness,
    report,
    reportContract: model.reportContract
  }
}

function activeLaneCardFor(project: MissionControlProjectRecord, snapshot: MissionControlSnapshot): ActiveLaneCard {
  const state = stateForProject(project, snapshot.projectStates)
  const brief = latestForProject(project.project_id, snapshot.projectBriefs)
  const review = latestForProject(project.project_id, snapshot.challengeReviews)
  const lane = state?.latest_lane_request ?? latestLaneForProject(project.project_id, snapshot.laneRequests)
  const report = state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)
  const model = projectRenderModel(project, report, state)

  return {
    brief,
    currentGoal: text(state?.current_goal ?? project.current_goal, 'No current goal recorded'),
    latestEvidence: text(model.latestReportSummary === 'No report yet' ? model.latestResult : model.latestReportSummary, 'No evidence recorded'),
    lane,
    nextLane: model.nextLane,
    project,
    readiness: projectReadinessLabel(brief, review),
    report,
    reportContract: model.reportContract,
    review,
    status: text(state?.status ?? project.status, 'Status not recorded')
  }
}

function activeLaneStage(card: ActiveLaneCard): string {
  if (!card.brief) {
    return 'needs brief'
  }
  if (!card.review) {
    return 'needs challenge'
  }
  if (card.review.decision_state !== 'clear_and_safe') {
    return `challenge: ${card.review.decision_state ?? 'unknown'}`
  }
  if (!card.lane) {
    return 'ready for lane draft'
  }

  return card.lane.status ? `${card.lane.status} lane` : 'lane drafted'
}

function structuredJennyHandoff(projectName: string): string {
  return `Structured handoff:
Goal: answer the request for ${projectName} as a bounded engineering lane.
Scope: use this project room context and approved repo/runtime evidence only.
Challenge: question unclear, unsafe, or wrong-approach requests before implementation.
Definition of done: state exact change, evidence, remaining risk, and next safe lane.
Validation: list checks run or why a check is blocked.
Report format: preflight, recommendation, work done, validation, risks, safety confirmation.`
}

function buildPhoneSafeProjectPacket({
  brief,
  project,
  requestText,
  review,
  state,
  status
}: {
  brief: MissionControlProjectBriefRecord | null
  project: MissionControlProjectRecord
  requestText: string
  review: MissionControlChallengeReviewRecord | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
}): string {
  const readiness = projectReadinessLabel(brief, review)
  const categories = review?.challenge_categories?.length ? review.challenge_categories.join(', ') : 'none recorded'
  const verdicts = review?.blocking_verdicts?.length ? review.blocking_verdicts.join(', ') : 'none recorded'
  const packet = `Project room request:
${project.name}

Request:
${compactText(requestText, 420) || '<write the request>'}

Current brief:
${compactText(brief?.outcome, 220) || 'missing project brief'}

Challenge state:
${compactText(review?.decision_state, 60) || 'missing'} / ${compactText(review?.recommended_path, 240) || 'challenge review required before lane draft'}
Categories: ${compactText(categories, 240)}
Blocking verdicts: ${compactText(verdicts, 240)}

Readiness:
${readiness.label}

Current goal:
${compactText(state?.current_goal ?? project.current_goal, 220) || 'not recorded'}

Allowed: read approved context, report status, recommend next safe lane.
Forbidden: no direct session send, live mutation, Waha, queue, model, social, payment, worker, timer, deploy, restart, runtime switch, config/state, or secrets unless separately approved.

Safety: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}; stale_warnings=${status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'}.

${structuredJennyHandoff(project.name)}`

  return truncate(packet.trim(), MAX_PHONE_SAFE_PACKET_CHARS)
}

function buildHermesUpdateLanePacket(status: ReturnType<typeof summarizeWorkspaceStatus>): string {
  return [
    'Hermes update lane request:',
    '',
    HERMES_UPDATE_LANE_REQUEST,
    '',
    'Required safe sequence:',
    '1. Read-only inventory of VPS dashboard/gateway runtime paths/heads and current package versions.',
    '2. Read-only inventory of the existing VPS-triggered laptop worker-node update path and laptop installed version.',
    '3. Prepare a non-live VPS dashboard runtime at accepted-live only after source and worker-node target are clear.',
    '4. Validate markers, record compatibility, dashboard assets, and rollback path before any dashboard-only switch.',
    '5. Keep gateway update and laptop worker-node update as separate explicit approval steps.',
    '',
    'Allowed: read-only inventory, non-live runtime preparation, tests/checks, report exact next approval.',
    'Forbidden: laptop worker-node auto-update, gateway restart/switch, dispatch, session sending, Waha/social/payment/customer action, new background worker/timer/daemon/cron, secrets, in-place runtime mutation.',
    '',
    `Current Mission Control safety status: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}.`
  ].join('\n')
}

function buildHermesStorageCleanupLanePacket(status: ReturnType<typeof summarizeWorkspaceStatus>): string {
  return [
    'Hermes storage cleanup lane request:',
    '',
    HERMES_STORAGE_CLEANUP_LANE_REQUEST,
    '',
    'Required safe sequence:',
    '1. Read-only inventory of VPS disk usage, largest Hermes runtimes/worktrees/caches/build outputs/logs, and current rollback runtimes.',
    '2. Identify what is safe to archive versus what must stay for accepted-live rollback, audit evidence, or current services.',
    '3. Recommend a cleanup plan with exact paths, expected bytes recovered, rollback risk, and archive destination if needed.',
    '4. Stop before deleting, pruning, moving, or uploading anything; request a separate explicit cleanup approval.',
    '',
    'Allowed: read-only storage inventory, cleanup recommendation, archive recommendation, and exact next approval.',
    'Forbidden: delete/prune/move/upload files, mutate records/config/state.db, gateway restart/switch, laptop worker-node cleanup, dispatch, session sending, Waha/social/payment/customer action, workers/timers/daemons/cron, or secrets.',
    '',
    `Current Mission Control safety status: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}.`
  ].join('\n')
}

async function loadMissionControlSnapshot(): Promise<MissionControlSnapshot> {
  const [
    workspaceStatus,
    projects,
    projectBriefs,
    challengeReviews,
    laneRequests,
    reports,
    projectState,
    projectSessions,
    jennyBridgeOutbox,
    jennyBridgeInbox,
    jennyBridgePollerStatus,
    githubBridgeStatus,
    memoryStorage
  ] = await Promise.all([
    getMissionControlWorkspaceStatus(),
    getMissionControlProjects(),
    getMissionControlProjectBriefs(),
    getMissionControlChallengeReviews(),
    getMissionControlLaneRequests(),
    getMissionControlReports(),
    getMissionControlProjectState(),
    getMissionControlProjectSessions(),
    getMissionControlJennyBridgeOutbox(),
    getMissionControlJennyBridgeInbox(),
    getMissionControlJennyBridgePollerStatus(),
    getMissionControlGitHubBridgeStatus(),
    getMissionControlProfileMemoryStorage()
  ])

  return {
    challengeReviews: unwrapRecords(challengeReviews.challenge_reviews),
    jennyBridgeRequests: unwrapRecords(jennyBridgeOutbox.requests),
    jennyBridgeResponses: unwrapRecords(jennyBridgeInbox.responses),
    jennyBridgePollerStatus,
    githubBridgeStatus,
    laneRequests: unwrapRecords(laneRequests.lane_requests),
    memoryStorage,
    projectBriefs: unwrapRecords(projectBriefs.project_briefs),
    projectSessionGroups: projectSessions.groups ?? [],
    projects: unwrapRecords(projects.projects),
    projectStates: projectState.project_states ?? [],
    reports: unwrapRecords(reports.reports),
    workspaceStatus
  }
}

export function MissionControlView() {
  const navigate = useNavigate()
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(emptySnapshot)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copiedProjectId, setCopiedProjectId] = useState('')
  const [reportForm, setReportForm] = useState<ReportFormState>(emptyReportForm)
  const [reportSaving, setReportSaving] = useState(false)
  const [reportMessage, setReportMessage] = useState('')
  const [sessionLinkDialog, setSessionLinkDialog] = useState<SessionLinkDialogState | null>(null)
  const [sessionLinkSaving, setSessionLinkSaving] = useState(false)
  const [sessionLinkMessage, setSessionLinkMessage] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [projectRequest, setProjectRequest] = useState('')
  const [projectRoomMessage, setProjectRoomMessage] = useState('')
  const [projectRoomSaving, setProjectRoomSaving] = useState(false)

  async function refreshMissionControlSnapshot(message = '') {
    setProjectRoomSaving(true)
    setError('')
    try {
      setSnapshot(await loadMissionControlSnapshot())
      if (message) {
        setProjectRoomMessage(message)
      }
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function refreshMissionControlSnapshotQuietly() {
    try {
      setSnapshot(await loadMissionControlSnapshot())
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError('')
        const nextSnapshot = await loadMissionControlSnapshot()

        if (cancelled) {
          return
        }

        setSnapshot(nextSnapshot)
      } catch (err) {
        if (!cancelled) {
          setError(String(err instanceof Error ? err.message : err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!selectedProjectId && !snapshot.projects.length) {
      return
    }

    const timer = window.setInterval(() => {
      void refreshMissionControlSnapshotQuietly()
    }, 15000)

    return () => window.clearInterval(timer)
  }, [selectedProjectId, snapshot.projects.length])

  const status = useMemo(() => summarizeWorkspaceStatus(snapshot.workspaceStatus), [snapshot.workspaceStatus])
  const updateNotice = useMemo(() => dashboardUpdateNotice(status), [status])
  const realProjects = useMemo(() => canonicalRealProjects(sortRealProjects(snapshot.projects.filter(isRealProject))), [snapshot.projects])
  const activeProjects = useMemo(() => {
    const projects = realProjects.filter(project => ACTIVE_OS_PROJECT_IDS.includes(project.project_id))
    return projects.length ? projects : realProjects
  }, [realProjects])
  const pausedProjects = useMemo(
    () => realProjects.filter(project => PAUSED_PROJECT_IDS.includes(project.project_id) || !ACTIVE_OS_PROJECT_IDS.includes(project.project_id)),
    [realProjects]
  )
  const projectRoomProjects = realProjects.length ? realProjects : activeProjects
  const unassignedGroup = useMemo(() => unassignedSessionGroup(snapshot.projectSessionGroups), [snapshot.projectSessionGroups])
  const selectedProject = useMemo(
    () => projectRoomProjects.find(project => project.project_id === selectedProjectId) ?? projectRoomProjects[0] ?? null,
    [projectRoomProjects, selectedProjectId]
  )

  const supportingProjects = useMemo(
    () => snapshot.projects.filter(project => !isRealProject(project) || isSmokeProject(project)),
    [snapshot.projects]
  )

  async function copyPrompt(project: MissionControlProjectRecord) {
    const state = stateForProject(project, snapshot.projectStates)
    const report = state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)
    const prompt = buildMissionControlCopyPrompt({ project, report, state, status })
    await navigator.clipboard?.writeText(prompt)
    setCopiedProjectId(project.project_id)
  }

  function packetForProject(project: MissionControlProjectRecord) {
    return buildPhoneSafeProjectPacket({
      brief: latestForProject(project.project_id, snapshot.projectBriefs),
      project,
      requestText: projectRequest,
      review: latestForProject(project.project_id, snapshot.challengeReviews),
      state: stateForProject(project, snapshot.projectStates),
      status
    })
  }

  async function copyProjectRoomPacket(project: MissionControlProjectRecord) {
    await navigator.clipboard?.writeText(packetForProject(project))
    setProjectRoomMessage('Copied phone-safe project packet.')
  }

  async function queueJennyBridgeRequest(project: MissionControlProjectRecord) {
    if (!projectRequest.trim()) {
      setProjectRoomMessage('Write one bounded request before queuing a Jenny bridge message.')

      return
    }

    setProjectRoomSaving(true)
    setProjectRoomMessage('')

    try {
      await createMissionControlGitHubBridgeRequest({
        from_agent: 'travis',
        message: packetForProject(project),
        project_id: project.project_id,
        request_id: bridgeRequestId(),
        to_agent: 'jenny'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage('Sent to Jenny mailbox. Replies refresh automatically; use Refresh replies if you want to check now.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function runJennyOnce(project: MissionControlProjectRecord) {
    const pending = latestPendingGitHubBridgeMessage(
      unwrapRecords(snapshot.githubBridgeStatus.recent_messages).filter(message => message.project_id === project.project_id)
    )
    if (!pending?.request_id) {
      setProjectRoomMessage('Send Jenny a project message first; there is no pending request to answer.')

      return
    }

    setProjectRoomSaving(true)
    setProjectRoomMessage('Jenny is answering one pending message...')

    try {
      const result = await answerMissionControlGitHubBridgeOnce({
        project_id: project.project_id,
        request_id: pending.request_id
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage(
        result.answered
          ? 'Jenny replied to the latest pending project message.'
          : `Jenny did not reply: ${String((result.status as { last_error?: unknown } | undefined)?.last_error ?? 'no matching pending request')}`
      )
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function queueHermesUpdateLane(project: MissionControlProjectRecord) {
    setProjectRoomSaving(true)
    setProjectRoomMessage('')
    setProjectRequest(HERMES_UPDATE_LANE_REQUEST)

    try {
      await createMissionControlGitHubBridgeRequest({
        from_agent: 'travis',
        message: buildHermesUpdateLanePacket(status),
        project_id: project.project_id,
        request_id: bridgeRequestId(),
        to_agent: 'jenny'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage('Sent safe Hermes update lane to Jenny mailbox. It is append-only and does not update the laptop worker node, switch runtimes, or restart gateway.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function queueHermesStorageCleanupLane(project: MissionControlProjectRecord) {
    setProjectRoomSaving(true)
    setProjectRoomMessage('')
    setProjectRequest(HERMES_STORAGE_CLEANUP_LANE_REQUEST)

    try {
      await createMissionControlGitHubBridgeRequest({
        from_agent: 'travis',
        message: buildHermesStorageCleanupLanePacket(status),
        project_id: project.project_id,
        request_id: bridgeRequestId(),
        to_agent: 'jenny'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage('Sent safe Hermes storage cleanup lane to Jenny mailbox. It is append-only and does not delete, move, upload, restart, or switch anything.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function saveChallengeDraft(project: MissionControlProjectRecord) {
    if (!projectRequest.trim()) {
      setProjectRoomMessage('Write one bounded request before saving a challenge draft.')

      return
    }

    setProjectRoomSaving(true)
    setProjectRoomMessage('')

    try {
      await createMissionControlChallengeReview({
        blocking_verdicts: ['requires_spec_update', 'blocks_lane_draft'],
        challenge_categories: ['questions_required', 'missing_context'],
        concerns: ['request entered from Desktop project room requires Jenny challenge review'],
        decision_state: 'needs_spec_first',
        project_id: project.project_id,
        questions: ['What outcome should this project request produce?'],
        recommended_path: 'Clarify the request, update the project brief if needed, then draft a bounded read-only lane.',
        request_summary: projectRequest.trim(),
        required_approvals: ['explicit approval before any send path or live action'],
        suggested_lane_title: compactText(projectRequest, 90) || 'Read-only project room request'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage('Saved challenge draft. Jenny should question or narrow this before work starts.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function saveReadOnlyLaneDraft(project: MissionControlProjectRecord) {
    if (!projectRequest.trim()) {
      setProjectRoomMessage('Write one bounded request before saving a lane draft.')

      return
    }

    const review = latestForProject(project.project_id, snapshot.challengeReviews)
    const blockMessage = laneDraftBlockMessage(review)
    if (blockMessage) {
      setProjectRoomMessage(blockMessage)

      return
    }

    setProjectRoomSaving(true)
    setProjectRoomMessage('')

    try {
      await createMissionControlLaneRequest({
        allowed_actions: ['read approved project context', 'report status', 'recommend next safe lane'],
        draft_prompt: packetForProject(project),
        expected_report_format: ['preflight', 'recommendation', 'risks', 'next lane', 'safety confirmation'],
        forbidden_actions: ['dispatch', 'run tools', 'queue mutation', 'Waha mutation', 'model routing', 'automatic send'],
        objective: projectRequest.trim(),
        project_id: project.project_id,
        stop_conditions: ['workspace-status preflight fails', 'request requires approval'],
        title: compactText(review?.suggested_lane_title || projectRequest, 120) || 'Read-only project room request'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage('Saved read-only lane draft. It remains inert until separately approved.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  function updateReportField(field: keyof ReportFormState, value: string) {
    setReportForm(current => ({ ...current, [field]: value }))
  }

  async function saveManualReport() {
    if (!reportForm.projectId || !reportForm.summary.trim()) {
      setReportMessage('Choose a project and enter a report summary before saving.')

      return
    }

    setReportSaving(true)
    setReportMessage('')

    try {
      await createMissionControlReport({
        artifact_links: lineList(reportForm.artifactLinks),
        changed_files: lineList(reportForm.changedFiles),
        lane_request_id: reportForm.laneRequestId.trim() || undefined,
        next_recommended_lane: reportForm.nextRecommendedLane.trim() || undefined,
        project_id: reportForm.projectId,
        result: reportForm.result.trim() || undefined,
        risks: lineList(reportForm.risks),
        summary: reportForm.summary.trim(),
        tests: lineList(reportForm.tests)
      })
      setReportForm({ ...emptyReportForm, projectId: reportForm.projectId })
      setReportMessage('Jenny report saved manually. Use project chat for guarded Jenny messages.')
      setSnapshot(await loadMissionControlSnapshot())
    } catch (err) {
      setReportMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setReportSaving(false)
    }
  }

  function openSessionLinkDialog(
    action: SessionLinkAction,
    session: MissionControlProjectSession,
    projectId = '',
    currentProjectId = ''
  ) {
    setSessionLinkMessage('')
    setSessionLinkDialog({ action, confirmed: false, currentProjectId, projectId, session })
  }

  function updateSessionLinkDialog(next: Partial<Pick<SessionLinkDialogState, 'confirmed' | 'projectId'>>) {
    setSessionLinkDialog(current => (current ? { ...current, ...next } : current))
  }

  async function saveSessionProjectLink() {
    if (!sessionLinkDialog || !sessionLinkDialog.confirmed || !sessionLinkDialog.projectId) {
      setSessionLinkMessage('Choose a project and confirm that one append-only record will be written.')

      return
    }

    setSessionLinkSaving(true)
    setSessionLinkMessage('')

    try {
      await createMissionControlSessionProjectLink(sessionLinkPayload(sessionLinkDialog))
      setSessionLinkMessage('Session link record appended. Direct session send remains disabled.')
      setSessionLinkDialog(null)
      setSnapshot(await loadMissionControlSnapshot())
    } catch (err) {
      setSessionLinkMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setSessionLinkSaving(false)
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col overflow-auto bg-(--ui-chat-surface-background) px-5 py-5 text-foreground">
      <header className="mb-5 flex flex-col gap-2 border-b border-border/60 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Jenny Workspace</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Pick a project, talk to Jenny, and keep the safety controls in the background. Hermes / Mission Control is the active recovery lane.
            </p>
          </div>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
            Jenny bridge guarded
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Project chat is record-backed. Deploys, gateway restarts, posting, payments, outreach, and hidden workers still require the normal approval gates.
        </p>
      </header>

      {error ? <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div> : null}
      {loading ? <div className="rounded-lg border border-border/70 p-4 text-sm text-muted-foreground">Loading Mission Control workspace…</div> : null}

      {updateNotice ? (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200">
          {updateNotice}
        </div>
      ) : null}

      {selectedProject ? (
        <ProjectRoomsWorkspace
          bridgeRequests={snapshot.jennyBridgeRequests.filter(request => request.project_id === selectedProject.project_id)}
          bridgeResponses={snapshot.jennyBridgeResponses.filter(response => response.project_id === selectedProject.project_id)}
          bridgeStatus={snapshot.jennyBridgePollerStatus}
          brief={latestForProject(selectedProject.project_id, snapshot.projectBriefs)}
          githubBridgeMessages={unwrapRecords(snapshot.githubBridgeStatus.recent_messages).filter(message => message.project_id === selectedProject.project_id)}
          githubBridgeStatus={snapshot.githubBridgeStatus}
          memoryStorage={snapshot.memoryStorage}
          message={projectRoomMessage}
          onCopyPacket={() => void copyProjectRoomPacket(selectedProject)}
          onOpenSession={session => navigate(sessionRoute(session.session_id))}
          onQueueBridge={() => void queueJennyBridgeRequest(selectedProject)}
          onQueueHermesUpdate={selectedProject.project_id === HERMES_PROJECT_ID ? () => void queueHermesUpdateLane(selectedProject) : undefined}
          onQueueStorageCleanup={selectedProject.project_id === HERMES_PROJECT_ID ? () => void queueHermesStorageCleanupLane(selectedProject) : undefined}
          onRefreshBridge={() => void refreshMissionControlSnapshot('Refreshed bridge inbox/outbox.')}
          onRequestChange={setProjectRequest}
          onRunJennyOnce={() => void runJennyOnce(selectedProject)}
          onSaveChallenge={() => void saveChallengeDraft(selectedProject)}
          onSaveLane={() => void saveReadOnlyLaneDraft(selectedProject)}
          onSelectProject={projectId => {
            setSelectedProjectId(projectId)
            setProjectRoomMessage('')
          }}
          packet={packetForProject(selectedProject)}
          paused={!ACTIVE_OS_PROJECT_IDS.includes(selectedProject.project_id)}
          project={selectedProject}
          projects={projectRoomProjects}
          report={
            stateForProject(selectedProject, snapshot.projectStates)?.latest_report ??
            stateForProject(selectedProject, snapshot.projectStates)?.latest_jenny_report ??
            latestReportForProject(selectedProject.project_id, snapshot.reports)
          }
          request={projectRequest}
          review={latestForProject(selectedProject.project_id, snapshot.challengeReviews)}
          saving={projectRoomSaving}
          sessionGroup={sessionGroupForProject(selectedProject, snapshot.projectSessionGroups)}
          state={stateForProject(selectedProject, snapshot.projectStates)}
        />
      ) : null}

      <details className="mt-5 rounded-xl border border-border/70 bg-background/40 p-4">
        <summary className="cursor-pointer text-sm font-semibold">Advanced status and reports</summary>
        <div className="mt-4 grid gap-5">
          <WorkspaceStatusPanel status={status} />

          <ActiveLanesPanel
            cards={activeProjects.map(project => activeLaneCardFor(project, snapshot))}
            status={status}
          />

          <ProjectKanbanBoard cards={activeProjects.map(project => projectKanbanCardFor(project, snapshot))} />

      <ManualReportIngestion
        form={reportForm}
        message={reportMessage}
        onChange={updateReportField}
        onSave={() => void saveManualReport()}
        projects={realProjects}
        saving={reportSaving}
      />

      <details className="mt-5 rounded-xl border border-border/70 bg-background/40 p-4">
        <summary className="cursor-pointer text-sm font-semibold">Project details and reports</summary>
        <div className="mt-3 mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold">Project report archive</h2>
            <p className="text-xs text-muted-foreground">Detailed cards stay here for audit and source-of-truth review. Use the project chat above for normal work.</p>
          </div>
          <span className="text-xs text-muted-foreground">{activeProjects.length} active / {pausedProjects.length} paused</span>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {activeProjects.length === 0 ? (
            <div className="rounded-xl border border-border/70 p-4 text-sm text-muted-foreground">
              No real Mission Control ProjectRecord entries found yet.
            </div>
          ) : (
            activeProjects.map(project => {
              const state = stateForProject(project, snapshot.projectStates)

              return (
                <ProjectCard
                  copied={copiedProjectId === project.project_id}
                  key={project.project_id}
                  lane={state?.latest_lane_request ?? latestLaneForProject(project.project_id, snapshot.laneRequests)}
                  onConfirmSuggestedLink={session => openSessionLinkDialog('suggested', session, project.project_id)}
                  onCopy={() => void copyPrompt(project)}
                  onMoveLink={session => openSessionLinkDialog('move', session, '', project.project_id)}
                  project={project}
                  report={state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)}
                  sessionGroup={sessionGroupForProject(project, snapshot.projectSessionGroups)}
                  state={state}
                  status={status}
                  suggestedSessions={suggestedSessionsForProject(project.project_id, snapshot.projectSessionGroups)}
                />
              )
            })
          )}
        </div>
      </details>

      <UnassignedSessionsPanel
        group={unassignedGroup}
        onLinkManual={session => openSessionLinkDialog('link', session, session.suggested_project_id || '')}
        projects={realProjects}
      />

      <SessionLinkConfirmationDialog
        dialog={sessionLinkDialog}
        message={sessionLinkMessage}
        onCancel={() => setSessionLinkDialog(null)}
        onChange={updateSessionLinkDialog}
        onSave={() => void saveSessionProjectLink()}
        projects={realProjects}
        saving={sessionLinkSaving}
      />

      {supportingProjects.length ? (
        <section className="rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 opacity-70">
          <h2 className="text-sm font-semibold">Supporting / smoke records</h2>
          <p className="mt-1 text-xs text-muted-foreground">These records stay available for audit context but are not part of the daily workspace.</p>
          <div className="mt-3 grid gap-2">
            {supportingProjects.map(project => (
              <div className="rounded-lg border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground" key={project.project_id}>
                <span className="font-medium text-foreground/80">{project.name}</span> — de-emphasized smoke/support record
              </div>
            ))}
          </div>
        </section>
      ) : null}
        </div>
        {pausedProjects.length ? (
          <section className="mt-4 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4">
            <h3 className="text-sm font-semibold">Projects on hold</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              These records stay visible for audit context, but they are not active work until Jenny/Mission Control is reliable.
            </p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {pausedProjects.map(project => (
                <div className="rounded-lg border border-border/60 bg-background/50 p-3 text-xs text-muted-foreground" key={project.project_id}>
                  <div className="font-medium text-foreground/80">{project.name}</div>
                  <p className="mt-1">On hold. No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </details>
    </section>
  )
}

function ActiveLanesPanel({
  cards,
  status
}: {
  cards: ActiveLaneCard[]
  status: ReturnType<typeof summarizeWorkspaceStatus>
}) {
  return (
    <section aria-label="Active Jenny OS lane" className="mt-5 rounded-xl border border-border/70 bg-background/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Active Jenny OS Lane</h2>
          <p className="text-xs text-muted-foreground">
            Mission Control/Jenny stability lane only. Display-only; lane state is derived from briefs, challenge reviews, lane drafts, and reports.
          </p>
        </div>
        <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2.5 py-1 text-xs text-sky-700 dark:text-sky-300">
          display-only / no dispatch
        </span>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-4">
        {cards.map(card => (
          <article className="rounded-lg border border-border/70 bg-background/70 p-3 text-sm" key={card.project.project_id}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold leading-tight">{card.project.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{card.status}</p>
              </div>
              <span className="shrink-0 rounded-full border border-border/70 px-2 py-0.5 text-[0.68rem] text-muted-foreground">
                {activeLaneStage(card)}
              </span>
            </div>
            <div className="mt-3 grid gap-2 text-xs">
              <Field label="current goal" value={compactText(card.currentGoal, 160) || 'No current goal recorded'} />
              <Field label="next safe lane" value={compactText(card.nextLane, 180) || 'No recommended lane recorded'} />
              <Field label="latest evidence" value={compactText(card.latestEvidence, 160) || 'No evidence recorded'} />
              <Field label="report contract" value={card.reportContract} />
              <Field label="readiness" value={card.readiness.detail} />
            </div>
          </article>
        ))}
      </div>

      <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
        <div>Runtime guard: {status.guard}</div>
        <div>Dispatch: {yesNo(status.dispatch)}</div>
        <div>Active lane count: {status.activeLaneCount}</div>
      </div>
    </section>
  )
}

function PausedProjectResumeChecklist() {
  const requirements = [
    'Project brief is current',
    'Jenny challenge review clears the approach',
    'Allowed and forbidden actions are explicit',
    'Travis approval is recorded before work resumes'
  ]

  return (
    <section className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
      <h3 className="font-semibold text-amber-800 dark:text-amber-200">Resume requirements</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        This project is on hold. Jenny cannot receive work here until these checks are true.
      </p>
      <ul className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
        {requirements.map(requirement => (
          <li className="rounded-md border border-amber-500/20 bg-background/60 px-3 py-2" key={requirement}>
            {requirement}
          </li>
        ))}
      </ul>
    </section>
  )
}

function ProjectRoomsWorkspace({
  brief,
  bridgeRequests,
  bridgeResponses,
  bridgeStatus,
  githubBridgeStatus,
  githubBridgeMessages,
  memoryStorage,
  message,
  onCopyPacket,
  onQueueBridge,
  onQueueHermesUpdate,
  onQueueStorageCleanup,
  onRefreshBridge,
  onRequestChange,
  onRunJennyOnce,
  onOpenSession,
  onSaveChallenge,
  onSaveLane,
  onSelectProject,
  packet,
  paused,
  project,
  projects,
  request,
  report,
  review,
  saving,
  sessionGroup,
  state
}: {
  brief: MissionControlProjectBriefRecord | null
  bridgeRequests: MissionControlJennyBridgeRequestRecord[]
  bridgeResponses: MissionControlJennyBridgeResponseRecord[]
  bridgeStatus: MissionControlJennyBridgePollerStatusResponse
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
  githubBridgeMessages: MissionControlGitHubBridgeMessageRecord[]
  memoryStorage: MissionControlProfileMemoryStorageResponse
  message: string
  onCopyPacket: () => void
  onQueueBridge: () => void
  onQueueHermesUpdate?: () => void
  onQueueStorageCleanup?: () => void
  onRefreshBridge: () => void
  onRequestChange: (value: string) => void
  onRunJennyOnce: () => void
  onOpenSession: (session: MissionControlProjectSession) => void
  onSaveChallenge: () => void
  onSaveLane: () => void
  onSelectProject: (projectId: string) => void
  packet: string
  paused: boolean
  project: MissionControlProjectRecord
  projects: MissionControlProjectRecord[]
  request: string
  report: MissionControlReportRecord | null
  review: MissionControlChallengeReviewRecord | null
  saving: boolean
  sessionGroup: MissionControlProjectSessionGroup | null
  state: MissionControlProjectState | null
}) {
  const readiness = projectReadinessLabel(brief, review)
  const sessions = state?.recent_sessions?.length ? state.recent_sessions : (sessionGroup?.sessions ?? [])
  const visibleBridgeRequests = bridgeRequests.filter(request => !isDiagnosticChatMessage(request.message))
  const visibleBridgeResponses = bridgeResponses.filter(response => !isDiagnosticChatMessage(response.message))
  const visibleGitHubBridgeMessages = githubBridgeMessages.filter(message => !isDiagnosticChatMessage(message.message))
  const repliedRequestIds = new Set(visibleBridgeResponses.map(response => response.request_id).filter(Boolean))
  const githubResponseIds = new Set(
    visibleGitHubBridgeMessages
      .filter(message => message.status === 'replied' || message.from_agent === 'jenny')
      .map(message => message.request_id)
      .filter(Boolean)
  )
  const githubPendingCount = visibleGitHubBridgeMessages.filter(message =>
    message.to_agent === 'jenny' &&
    ['queued', 'retry_requested'].includes(message.status) &&
    !githubResponseIds.has(message.request_id)
  ).length
  const latestPending = latestPendingGitHubBridgeMessage(visibleGitHubBridgeMessages)
  const githubResponseCount = visibleGitHubBridgeMessages.filter(message => message.status === 'replied' || message.from_agent === 'jenny').length
  const pendingCount = pendingJennyMessageCount(visibleBridgeRequests, visibleBridgeResponses) + githubPendingCount
  const responseCount = visibleBridgeResponses.length + githubResponseCount
  const deliveryStatus = jennyDeliveryStatus(pendingCount, responseCount, bridgeStatus, githubBridgeStatus)
  const connectionState = jennyConnectionState(pendingCount, responseCount, bridgeStatus, githubBridgeStatus)
  const nextStep = jennyNextStep(pendingCount, responseCount, Boolean(latestPending), bridgeStatus, githubBridgeStatus)
  const chatMessages = [
    ...visibleBridgeRequests.map(request => ({
      body: request.message,
      id: request.request_id,
      meta: chatStatusLabel(request.bridge_state ?? (request.request_id && repliedRequestIds.has(request.request_id) ? 'replied' : request.status ?? 'queued')),
      speaker: 'You',
      time: request.created_at
    })),
    ...visibleBridgeResponses.map(response => ({
      body: response.message,
      id: response.response_id,
      meta: chatStatusLabel(response.status ?? 'reply'),
      speaker: 'Jenny',
      time: response.created_at
    })),
    ...visibleGitHubBridgeMessages.map(message => ({
      body: message.message,
      id: message.github_comment_id || message.request_id,
      meta: chatStatusLabel(message.status),
      speaker: message.from_agent === 'jenny' || message.status === 'replied' ? 'Jenny' : 'You',
      time: message.created_at
    }))
  ].sort((left, right) => String(left.time ?? '').localeCompare(String(right.time ?? ''))).slice(-8)

  return (
    <section aria-label="Project chat workspace" className="mt-5 grid gap-4 rounded-xl border border-border/70 bg-background/50 p-4 xl:grid-cols-[16rem_minmax(0,1fr)]">
      <aside>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold">Projects</h2>
          <span className="rounded-full border border-border/70 px-2.5 py-1 text-xs text-muted-foreground">{projects.length} projects</span>
        </div>
        <div className="mt-3 grid gap-2">
          {projects.map(candidate => (
            <button
              className={cn(
                'rounded-lg border px-3 py-2 text-left text-sm hover:bg-muted',
                candidate.project_id === project.project_id ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-border/70 bg-background/60'
              )}
              key={candidate.project_id}
              onClick={() => onSelectProject(candidate.project_id)}
              type="button"
            >
              <span className="block font-medium">{candidate.name}</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                {candidate.project_id === HERMES_PROJECT_ID ? 'Active recovery lane' : 'Paused until Jenny is stable'}
              </span>
            </button>
          ))}
        </div>
      </aside>

      <div className="min-w-0">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Chat room</p>
            <h2 className="mt-1 text-xl font-semibold">{project.name}</h2>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <span className={cn('rounded-full border px-2.5 py-1 text-xs font-semibold', jennyStatusToneClass(connectionState.tone))}>
              {connectionState.label}
            </span>
            <span className={cn(
              'rounded-full border px-2.5 py-1 text-xs',
              paused
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
            )}>
              {paused ? 'Paused' : readiness.label}
            </span>
          </div>
        </div>

        <div className="mt-3 rounded-xl border border-border/70 bg-background/70 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="font-semibold text-foreground/90">Goal</span>
            <span className="text-muted-foreground">{compactText(state?.current_goal ?? project.current_goal, 180) || 'No current goal recorded.'}</span>
            <span className="hidden h-4 w-px bg-border md:block" />
            <span className="font-semibold text-foreground/90">Jenny</span>
            <span className="text-muted-foreground">{deliveryStatus}. {connectionState.detail}</span>
          </div>
          <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Next step</div>
                <p className="mt-1 text-sm text-foreground/90">
                  {paused ? 'Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.' : nextStep}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="rounded-full border border-border/70 px-2 py-1">Pending {pendingCount}</span>
                <span className="rounded-full border border-border/70 px-2 py-1">Replies {responseCount}</span>
              </div>
            </div>
          </div>
          <details className="mt-2">
            <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">About this project</summary>
            <div className="mt-2 grid gap-2 text-xs md:grid-cols-3">
              <Field label="readiness" value={readiness.detail} />
              <Field label="last update" value={compactText(report?.summary || report?.result, 220) || 'No update recorded yet.'} />
              <Field label="report contract" value={reportContractSummaryForState(state, report)} />
            </div>
          </details>
        </div>

        <section aria-label="Project chat transcript" className="mt-4 rounded-xl border border-border/70 bg-background/80 p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Conversation</h3>
            <span className="text-xs text-muted-foreground">{chatMessages.length ? `${chatMessages.length} recent messages` : 'No messages yet'}</span>
          </div>
          <div className="mt-3 grid min-h-[18rem] max-h-[32rem] gap-3 overflow-auto pr-1">
            {chatMessages.length ? (
              chatMessages.map(chat => (
                <article
                  className={cn(
                    'max-w-[85%] rounded-xl border px-3 py-2 text-sm',
                    chat.speaker === 'You'
                      ? 'justify-self-end border-emerald-500/30 bg-emerald-500/10'
                      : 'justify-self-start border-border/70 bg-muted/40'
                  )}
                  key={`${chat.speaker}:${chat.id}`}
                >
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                    <span className="font-semibold">{chat.speaker}</span>
                    <span className="text-muted-foreground">{chat.meta}</span>
                  </div>
                  <p className="whitespace-pre-wrap break-words text-foreground/90">
                    {chat.speaker === 'You' ? projectRequestPreview(chat.body, 900) : compactText(chat.body, 900)}
                  </p>
                </article>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-border/70 p-4 text-sm text-muted-foreground">
                Ask Jenny a bounded question or give her one safe next task below.
              </div>
            )}
          </div>
        </section>

        <label className="mt-4 grid gap-1 text-sm font-medium">
          Message Jenny
          <textarea
            className="min-h-32 rounded-xl border border-border/80 bg-background px-3 py-2 text-sm"
            disabled={paused}
            onChange={event => onRequestChange(event.target.value)}
            placeholder={paused ? 'This project is on hold until Jenny is stable.' : 'Tell Jenny what you want to discuss or ask her to do next...'}
            value={request}
          />
        </label>

        <div className="mt-3 flex flex-wrap gap-2">
          <button className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-500/15 disabled:opacity-60 dark:text-emerald-300" disabled={saving || paused} onClick={onQueueBridge} type="button">
            Send to Jenny
          </button>
          <button
            className="rounded-md border border-sky-500/40 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-700 hover:bg-sky-500/15 disabled:opacity-60 dark:text-sky-300"
            disabled={saving || paused || !latestPending}
            onClick={onRunJennyOnce}
            type="button"
          >
            Get Jenny reply
          </button>
          <button className="rounded-md border border-border/80 px-4 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving} onClick={onRefreshBridge} type="button">
            Refresh replies
          </button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {paused
            ? 'This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.'
            : 'Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates.'}
        </p>
        {paused ? <PausedProjectResumeChecklist /> : null}
        {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}

        <section className="mt-4 rounded-xl border border-border/70 bg-background/60 p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Previous sessions</h3>
            <span className="text-xs text-muted-foreground">{sessions.length} linked</span>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            {sessions.length ? (
              sessions.slice(0, 6).map(session => (
                <button
                  className="rounded-lg border border-border/60 bg-background/70 p-3 text-left text-xs hover:bg-muted"
                  key={session.durable_session_id || session.session_id}
                  onClick={() => onOpenSession(session)}
                  type="button"
                >
                  <span className="block font-medium text-foreground/90">{sessionTitle(session)}</span>
                  <span className="mt-1 block text-muted-foreground">{sessionMeta(session)}</span>
                </button>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No linked sessions for this project yet.</p>
            )}
          </div>
        </section>

        <details className="mt-4 rounded-xl border border-border/70 bg-background/40 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Advanced controls</summary>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Field label="project brief" value={compactText(brief?.outcome, 320) || 'No project brief recorded'} />
            <Field label="challenge review" value={review ? `${review.decision_state ?? 'unknown'} / ${review.recommended_path ?? 'No recommended path recorded'}` : 'No challenge review recorded'} />
            <Field label="latest report contract" value={reportContractSummaryForState(state, report)} />
            <Field label="bridge mode" value={`manual relay: ${bridgeStatus.manual_start_only === false ? 'disabled' : 'manual-start only'} / GitHub: ${githubBridgeStatus.manual_start_only === false ? 'disabled' : 'manual-start only'}`} />
          </div>

          <div className="mt-3 grid gap-2 md:grid-cols-4">
            <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving} onClick={onCopyPacket} type="button">
              Copy phone-safe packet
            </button>
            <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving || paused} onClick={onSaveChallenge} type="button">
              Save challenge draft
            </button>
            <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving || paused} onClick={onSaveLane} type="button">
              Save read-only lane draft
            </button>
            <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving} onClick={onRefreshBridge} type="button">
              Refresh bridge
            </button>
          </div>
          <div className="sr-only">Queue for Jenny bridge</div>

          {onQueueHermesUpdate ? (
            <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold">Hermes update lane</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Starts a guarded update checklist for the VPS and laptop Hermes worker node. The bottom-bar desktop app version is separate from accepted-live/dashboard deploys. This queues a bridge request only; no runtime switch, restart, or laptop update happens here.
                  </p>
                </div>
                <button className="rounded-md border border-amber-500/40 px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-500/10 disabled:opacity-60 dark:text-amber-300" disabled={saving} onClick={onQueueHermesUpdate} type="button">
                  Start Hermes update lane
                </button>
              </div>
            </div>
          ) : null}

          {onQueueStorageCleanup ? (
            <div className="mt-3 rounded-lg border border-sky-500/30 bg-sky-500/5 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold">Hermes storage cleanup lane</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Starts a guarded storage inventory for VPS programming buildup and laptop worker-node posture. This queues a request only; no files are deleted, moved, uploaded, pruned, restarted, or switched.
                  </p>
                </div>
                <button className="rounded-md border border-sky-500/40 px-3 py-2 text-sm font-semibold text-sky-700 hover:bg-sky-500/10 disabled:opacity-60 dark:text-sky-300" disabled={saving} onClick={onQueueStorageCleanup} type="button">
                  Start storage cleanup lane
                </button>
              </div>
            </div>
          ) : null}

          <section className="mt-3 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold">Jenny memory storage</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Read-only memory file levels for the main profile and named profiles. This does not edit memories.
                </p>
              </div>
              <span className="rounded-full border border-violet-500/30 px-2 py-0.5 text-xs text-violet-700 dark:text-violet-300">
                {memoryStorage.profile_count ?? memoryStorage.profiles?.length ?? 0} profiles / {formatBytes(memoryStorage.total_bytes)}
              </span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {(memoryStorage.profiles ?? []).length ? (
                (memoryStorage.profiles ?? []).map(profile => (
                  <article className="rounded-md border border-violet-500/20 bg-background/60 p-2 text-xs" key={profile.profile ?? profile.home}>
                    <div className="font-semibold text-foreground/90">{profile.profile ?? 'profile'}</div>
                    <div className="mt-2 grid gap-1 text-muted-foreground">
                      <div>Memory: {formatBytes(profile.memory?.bytes)} / {profile.memory?.chars ?? 0} chars / {profile.memory?.percent_used ?? 0}%</div>
                      <div>User: {formatBytes(profile.user?.bytes)} / {profile.user?.chars ?? 0} chars / {profile.user?.percent_used ?? 0}%</div>
                      {profile.memory?.error || profile.user?.error ? <div className="text-destructive">Read issue: {profile.memory?.error || profile.user?.error}</div> : null}
                    </div>
                  </article>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">No profile memory files reported.</p>
              )}
            </div>
          </section>

          <div className="mt-4 grid gap-3 xl:grid-cols-2">
            <section className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold">Jenny bridge</h3>
                <span className="rounded-full border border-emerald-500/30 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-300">
                  record-backed / no dispatch
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Outbound records are ready for Jenny bridge polling. Use refresh to check for inbox replies. Direct session send remains disabled.
              </p>
              <div className="mt-3 grid gap-2 rounded-md border border-emerald-500/20 bg-background/60 p-2 text-xs md:grid-cols-2">
                <Field label="manual relay" value={bridgeStatus.manual_start_only === false ? 'disabled' : 'manual-start only'} />
                <Field label="pending" value={String(bridgeStatus.pending_count ?? visibleBridgeRequests.filter(request => (request.bridge_state ?? request.status ?? 'queued') !== 'replied').length)} />
                <Field label="last status" value={bridgeStatus.last_status ?? 'idle'} />
                <Field label="last response" value={bridgeStatus.last_response_request_id || bridgeStatus.last_response_at || 'none'} />
                <Field label="last error" value={bridgeStatus.last_error || 'none'} />
                <Field label="worker/timer" value={`worker ${bridgeStatus.worker_enabled ? 'enabled' : 'disabled'} / timer ${bridgeStatus.timer_enabled ? 'enabled' : 'disabled'}`} />
              </div>
              <div className="mt-3 grid gap-2 rounded-md border border-sky-500/20 bg-sky-500/5 p-2 text-xs md:grid-cols-2">
                <Field label="GitHub mailbox" value={githubBridgeStatus.manual_start_only === false ? 'disabled' : 'manual-start only'} />
                <Field label="GitHub mode" value={githubBridgeStatus.mode || 'manual'} />
                <Field label="GitHub pending" value={String(githubBridgeStatus.pending_count ?? 0)} />
                <Field label="GitHub last poll" value={githubBridgeStatus.last_poll_at || githubBridgeStatus.last_status || 'not polled'} />
                <Field label="GitHub last response" value={githubBridgeStatus.last_response_request_id || githubBridgeStatus.last_response_at || 'none'} />
                <Field label="GitHub last error" value={githubBridgeStatus.last_error || 'none'} />
                <Field label="daemon/worker/timer" value={`daemon ${githubBridgeStatus.daemon_enabled ? 'enabled' : 'disabled'} / worker ${githubBridgeStatus.worker_enabled ? 'enabled' : 'disabled'} / timer ${githubBridgeStatus.timer_enabled ? 'enabled' : 'disabled'}`} />
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <BridgeList empty="No queued bridge messages." items={visibleBridgeRequests} renderItem={request => (
                  <>
                    <div className="font-medium text-foreground/90">
                      {request.bridge_state ?? (request.request_id && repliedRequestIds.has(request.request_id) ? 'replied' : request.status ?? 'queued')} / {request.target_agent ?? 'jenny'}
                    </div>
                    <div className="mt-1 line-clamp-3 text-muted-foreground">{request.message}</div>
                  </>
                )} title="Outbound to Jenny" />
                <BridgeList empty="No bridge replies yet." items={visibleBridgeResponses} renderItem={response => (
                  <>
                    <div className="font-medium text-foreground/90">{response.responder ?? 'jenny'} / {response.status ?? 'received'}</div>
                    <div className="mt-1 line-clamp-3 text-muted-foreground">{response.message}</div>
                  </>
                )} title="Jenny replies" />
              </div>
            </section>

            <section className="rounded-lg border border-border/70 bg-background/60 p-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold">Phone-safe packet</h3>
                <span className="text-xs text-muted-foreground">{packet.length}/{MAX_PHONE_SAFE_PACKET_CHARS}</span>
              </div>
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-muted-foreground">{packet}</pre>
            </section>
          </div>
        </details>
      </div>
    </section>
  )
}

function BridgeList<T>({
  empty,
  items,
  renderItem,
  title
}: {
  empty: string
  items: T[]
  renderItem: (item: T) => ReactNode
  title: string
}) {
  return (
    <section className="rounded-md border border-border/70 bg-background/60 p-2 text-xs">
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-semibold text-foreground/90">{title}</h4>
        <span className="text-muted-foreground">{items.length}</span>
      </div>
      <div className="mt-2 grid gap-2">
        {items.length ? (
          items.slice(-3).reverse().map((item, index) => (
            <div className="rounded-md border border-border/60 bg-background/70 p-2" key={index}>
              {renderItem(item)}
            </div>
          ))
        ) : (
          <p className="text-muted-foreground">{empty}</p>
        )}
      </div>
    </section>
  )
}

function ProjectKanbanBoard({ cards }: { cards: ProjectKanbanCard[] }) {
  const cardsByColumn = new Map<ProjectKanbanColumnId, ProjectKanbanCard[]>()
  for (const column of PROJECT_KANBAN_COLUMNS) {
    cardsByColumn.set(column.id, [])
  }
  for (const card of cards) {
    cardsByColumn.get(card.columnId)?.push(card)
  }

  return (
    <section aria-label="Project Kanban" className="mt-5 rounded-xl border border-border/70 bg-background/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Project Kanban</h2>
          <p className="text-xs text-muted-foreground">
            Record-backed work lifecycle. Dragging is disabled; movement comes from briefs, challenge reviews, lane drafts, approvals, and reports.
          </p>
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-800 dark:text-amber-200">
          read-only board / no queue mutation
        </span>
      </div>

      <div className="mt-4 overflow-x-auto pb-2">
        <div className="grid min-w-[1320px] grid-cols-9 gap-3">
          {PROJECT_KANBAN_COLUMNS.map(column => {
            const columnCards = cardsByColumn.get(column.id) ?? []

            return (
              <section className="rounded-lg border border-border/70 bg-background/60 p-2" key={column.id}>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold">{column.title}</h3>
                  <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.68rem] text-muted-foreground">{columnCards.length}</span>
                </div>
                <p className="mt-1 min-h-9 text-[0.68rem] leading-snug text-muted-foreground">{column.description}</p>
                <div className="mt-2 grid gap-2">
                  {columnCards.length ? (
                    columnCards.map(card => <ProjectKanbanCardView card={card} key={card.project.project_id} />)
                  ) : (
                    <p className="rounded-md border border-dashed border-border/70 p-2 text-[0.68rem] text-muted-foreground">No project cards.</p>
                  )}
                </div>
              </section>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function ProjectKanbanCardView({ card }: { card: ProjectKanbanCard }) {
  return (
    <article className="rounded-md border border-border/70 bg-background/80 p-2 text-xs shadow-sm">
      <div className="font-semibold leading-snug text-foreground/90">{card.project.name}</div>
      <div className="mt-1 rounded-full border border-border/60 px-2 py-0.5 text-[0.68rem] text-muted-foreground">{card.readiness.label}</div>
      <p className="mt-2 line-clamp-3 text-[0.7rem] leading-snug text-muted-foreground">{card.detail}</p>
      <div className="mt-2 grid gap-1 text-[0.68rem] text-muted-foreground">
        <div>
          <span className="font-medium text-foreground/70">Lane:</span> {card.lane?.title ?? 'No lane draft'}
        </div>
        <div>
          <span className="font-medium text-foreground/70">Next:</span> {card.nextLane}
        </div>
        <div>
          <span className="font-medium text-foreground/70">Report:</span> {card.report?.summary ?? 'No report yet'}
        </div>
        <div>
          <span className="font-medium text-foreground/70">Contract:</span> {card.reportContract}
        </div>
      </div>
    </article>
  )
}

function ManualReportIngestion({
  form,
  message,
  onChange,
  onSave,
  projects,
  saving
}: {
  form: ReportFormState
  message: string
  onChange: (field: keyof ReportFormState, value: string) => void
  onSave: () => void
  projects: MissionControlProjectRecord[]
  saving: boolean
}) {
  return (
    <section aria-label="Manual Jenny report ingestion" className="mt-5 rounded-xl border border-border/70 bg-background/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Manual Jenny report ingestion</h2>
          <p className="text-xs text-muted-foreground">
            Append-only report save for real project state. Direct session send remains disabled; this does not dispatch work.
          </p>
        </div>
        <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-700 dark:text-blue-300">
          POST allowed only: reports/create
        </span>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <label className="grid gap-1 text-xs font-medium">
          Project
          <select
            className="rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
            onChange={event => onChange('projectId', event.target.value)}
            value={form.projectId}
          >
            <option value="">Choose one of five real projects</option>
            {projects.map(project => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <ReportInput label="Optional lane request ID" onChange={value => onChange('laneRequestId', value)} value={form.laneRequestId} />
        <ReportInput label="Jenny report summary" onChange={value => onChange('summary', value)} required value={form.summary} />
        <ReportInput label="Latest result" onChange={value => onChange('result', value)} value={form.result} />
        <ReportInput label="Risks/blockers — one per line" onChange={value => onChange('risks', value)} value={form.risks} />
        <ReportInput label="Artifact/report links — one per line" onChange={value => onChange('artifactLinks', value)} value={form.artifactLinks} />
        <ReportInput label="Changed files or evidence paths — one per line" onChange={value => onChange('changedFiles', value)} value={form.changedFiles} />
        <ReportInput label="Tests/checks — one per line" onChange={value => onChange('tests', value)} value={form.tests} />
        <ReportInput className="lg:col-span-2" label="Next recommended lane" onChange={value => onChange('nextRecommendedLane', value)} value={form.nextRecommendedLane} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60"
          disabled={saving}
          onClick={onSave}
          type="button"
        >
          {saving ? 'Saving report…' : 'Save Jenny report manually'}
        </button>
        <span className="text-xs text-muted-foreground">Manual-copy only · no session send · no queue mutation · no model routing</span>
      </div>
      {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
    </section>
  )
}

function ReportInput({
  className,
  label,
  onChange,
  required,
  value
}: {
  className?: string
  label: string
  onChange: (value: string) => void
  required?: boolean
  value: string
}) {
  return (
    <label className={cn('grid gap-1 text-xs font-medium', className)}>
      {label}
      <textarea
        className="min-h-20 rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
        onChange={event => onChange(event.target.value)}
        required={required}
        value={value}
      />
    </label>
  )
}

function WorkspaceStatusPanel({ status }: { status: ReturnType<typeof summarizeWorkspaceStatus> }) {
  const deploymentTone = status.deploymentGapState === 'deployed_and_accepted' ? 'good' : status.deploymentNeeded ? 'warn' : undefined
  return (
    <div className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-3">
      <StatusItem label="Runtime Worktree Guard" tone={status.guard === 'pass' ? 'good' : 'warn'} value={status.guard} />
      <StatusItem label="dispatch_in_gateway" tone={status.dispatch === false ? 'good' : 'warn'} value={yesNo(status.dispatch)} />
      <StatusItem label="active_lane_count" tone={status.activeLaneCount === 0 ? 'good' : 'warn'} value={String(status.activeLaneCount)} />
      <StatusItem label="deploy state" tone={deploymentTone} value={status.deploymentGapState.replaceAll('_', ' ')} />
      <StatusItem className="md:col-span-2" label="accepted runtime" value={status.runtime} />
      <StatusItem label="accepted-live head" value={status.head.slice(0, 12)} />
      <StatusItem label="deployed head" value={status.deployedHead.slice(0, 12)} />
      <StatusItem label="latest merged PR" value={status.latestMergedPr || 'unknown'} />
      <StatusItem className="md:col-span-3" label="desktop app install" tone="warn" value="separate laptop worker-node update; bottom-bar version is not changed by accepted-live/dashboard deploy" />
      <StatusItem className="md:col-span-3" label="stale warnings" tone={status.staleWarnings.length ? 'warn' : 'good'} value={status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'} />
    </div>
  )
}

function ProjectSessionSummary({
  linkedCount,
  onConfirmSuggestedLink,
  onMoveLink,
  recentSessions,
  suggestedSessions
}: {
  linkedCount: number
  onConfirmSuggestedLink: (session: MissionControlProjectSession) => void
  onMoveLink: (session: MissionControlProjectSession) => void
  recentSessions: MissionControlProjectSession[]
  suggestedSessions: MissionControlProjectSession[]
}) {
  return (
    <section aria-label="Project sessions" className="rounded-lg border border-border/70 bg-background/60 p-3 text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-foreground/80">Project sessions</span>
        <span>{linkedCount} linked</span>
      </div>
      {recentSessions.length ? (
        <div className="mt-2 grid gap-2">
          {recentSessions.slice(0, 3).map(session => (
            <SessionSummaryRow
              actionLabel="Move link"
              badge="Linked · source of truth"
              key={session.durable_session_id || session.session_id}
              onAction={() => onMoveLink(session)}
              session={session}
            />
          ))}
        </div>
      ) : (
        <p className="mt-2">No linked sessions yet.</p>
      )}
      {suggestedSessions.length ? (
        <div className="mt-3 rounded-md border border-dashed border-amber-500/40 bg-amber-500/5 p-2">
          <div className="font-medium text-amber-800 dark:text-amber-200">Suggested sessions — display-only</div>
          <p className="mt-1">Suggestions do not create links or become source-of-truth records.</p>
          <div className="mt-2 grid gap-2">
            {suggestedSessions.map(session => (
              <SessionSummaryRow
                actionLabel="Review link"
                badge="Display-only suggestion"
                key={session.durable_session_id || session.session_id}
                onAction={() => onConfirmSuggestedLink(session)}
                session={session}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function SessionSummaryRow({
  actionLabel,
  badge,
  onAction,
  session
}: {
  actionLabel?: string
  badge?: string
  onAction?: () => void
  session: MissionControlProjectSession
}) {
  return (
    <div className="rounded-md border border-border/60 bg-background/70 p-2">
      <div className="font-medium text-foreground/90">{sessionTitle(session)}</div>
      <div className="mt-0.5 text-[0.7rem] text-muted-foreground">{sessionMeta(session)}</div>
      {badge ? <div className="mt-1 text-[0.7rem] font-medium text-amber-700 dark:text-amber-200">{badge}</div> : null}
      {onAction && actionLabel ? (
        <button className="mt-2 rounded-md border border-border/70 px-2 py-1 text-[0.7rem] font-medium text-foreground hover:bg-muted" onClick={onAction} type="button">
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}

function UnassignedSessionsPanel({
  group,
  onLinkManual,
  projects
}: {
  group: MissionControlProjectSessionGroup | null
  onLinkManual: (session: MissionControlProjectSession) => void
  projects: MissionControlProjectRecord[]
}) {
  const sessions = group?.sessions ?? []
  const suggestionCount = group?.unassigned_suggestion_count ?? sessions.filter(session => session.suggested_project_id).length

  return (
    <section className="mt-6 rounded-xl border border-border/70 bg-background/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Unassigned / General sessions</h2>
          <p className="text-xs text-muted-foreground">Recent sessions not linked to a Mission Control project yet.</p>
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-800 dark:text-amber-200">
          {sessions.length} recent · {suggestionCount} suggestions
        </span>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Suggested project badges are display-only. They do not create SessionProjectLinkRecord truth.</p>
      {sessions.length ? (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {sessions.slice(0, 6).map(session => (
            <div className="rounded-lg border border-border/60 bg-background/60 p-3 text-xs" key={session.durable_session_id || session.session_id}>
              <div className="font-medium text-foreground/90">{sessionTitle(session)}</div>
              <div className="mt-1 text-muted-foreground">{sessionMeta(session)}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {session.suggested_project_id ? (
                  <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[0.68rem] font-medium text-blue-700 dark:text-blue-300">
                    Suggested: {projectNameForId(session.suggested_project_id, projects)} · display-only
                  </span>
                ) : (
                  <span className="text-[0.68rem] text-muted-foreground">No suggested project</span>
                )}
                <button className="rounded-md border border-border/70 px-2 py-1 text-[0.7rem] font-medium text-foreground hover:bg-muted" onClick={() => onLinkManual(session)} type="button">
                  Link manually
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-border/60 bg-background/60 p-3 text-sm text-muted-foreground">No unassigned sessions returned.</div>
      )}
    </section>
  )
}

function ProjectCard({
  copied,
  lane,
  onConfirmSuggestedLink,
  onCopy,
  onMoveLink,
  project,
  report,
  sessionGroup,
  state,
  status,
  suggestedSessions
}: {
  copied: boolean
  lane: MissionControlLaneRequestRecord | null
  onConfirmSuggestedLink: (session: MissionControlProjectSession) => void
  onCopy: () => void
  onMoveLink: (session: MissionControlProjectSession) => void
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  sessionGroup: MissionControlProjectSessionGroup | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
  suggestedSessions: MissionControlProjectSession[]
}) {
  const model = projectRenderModel(project, report, state)
  const linkedSessionCount = state?.linked_session_count ?? sessionGroup?.linked_session_count ?? sessionGroup?.sessions.length ?? 0
  const recentSessions = state?.recent_sessions?.length ? state.recent_sessions : (sessionGroup?.sessions ?? [])
  const risksBlockers = [listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'
  const prompt = buildMissionControlCopyPrompt({ project, report, state, status })

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border/70 bg-background/50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{project.name}</h3>
          <p className="text-xs text-muted-foreground">{project.project_id}</p>
        </div>
        <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-700 dark:text-emerald-300">Primary project</span>
      </div>
      <Field label="status" value={state?.status ?? project.status} />
      <Field label="current goal" value={state?.current_goal ?? project.current_goal} />
      <Field label="freshness" value={freshnessLabel(state)} />
      <Field label="latest lane" value={lane ? `${lane.title}${lane.status ? ` (${lane.status})` : ''}${lane.objective ? ` — ${lane.objective}` : ''}` : 'No draft lane request recorded'} />
      <Field label="latest Jenny report summary" value={model.latestReportSummary} />
      <Field label="report contract" value={model.reportContract} />
      <Field label="latest result" value={model.latestResult} />
      <Field label="risks/blockers" value={risksBlockers} />
      <Field label="last action time" value={`${model.latestActivityAt} (${model.latestActivitySource})`} />
      <Field label="artifact/report links" value={listText(model.artifactLinks, 'No artifact/report links recorded')} />
      <Field label="missing state fields" value={listText(model.missingStateFields, 'None — report state is current')} />
      <Field label="next recommended lane" value={model.nextLane} />
      <Field label="source of truth" value={project.source_of_truth} />
      <ProjectSessionSummary
        linkedCount={linkedSessionCount}
        onConfirmSuggestedLink={onConfirmSuggestedLink}
        onMoveLink={onMoveLink}
        recentSessions={recentSessions}
        suggestedSessions={suggestedSessions}
      />
      <div className="grid gap-2 rounded-lg border border-border/70 bg-background/60 p-3 text-xs text-muted-foreground sm:grid-cols-3">
        <span>send_to_jenny: disabled</span>
        <span>dispatch: disabled</span>
        <span>execution: disabled</span>
      </div>
      <div className="rounded-lg border border-dashed border-border/80 p-3 text-xs text-muted-foreground">
        <div className="mb-2 font-medium text-foreground/80">Next lane prompt preview ({prompt.length}/{MAX_COPY_PROMPT_CHARS})</div>
        <p className="line-clamp-4 whitespace-pre-wrap">{prompt}</p>
        <button
          className="mt-3 rounded-md border border-border/80 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
          onClick={onCopy}
          type="button"
        >
          {copied ? 'Prompt copied' : 'Copy next lane prompt'}
        </button>
      </div>
    </article>
  )
}

function SessionLinkConfirmationDialog({
  dialog,
  message,
  onCancel,
  onChange,
  onSave,
  projects,
  saving
}: {
  dialog: SessionLinkDialogState | null
  message: string
  onCancel: () => void
  onChange: (next: Partial<Pick<SessionLinkDialogState, 'confirmed' | 'projectId'>>) => void
  onSave: () => void
  projects: MissionControlProjectRecord[]
  saving: boolean
}) {
  if (!dialog) {
    return message ? <p className="mt-3 text-sm text-muted-foreground">{message}</p> : null
  }

  const availableProjects = projectOptionsForDialog(projects, dialog)
  const selectedProject = projectForDialog(projects, dialog.projectId)
  const title = dialog.action === 'move' ? 'Move linked session' : dialog.action === 'suggested' ? 'Confirm suggested link' : 'Link session manually'
  const buttonLabel = dialog.action === 'move' ? 'Append superseding link record' : dialog.action === 'suggested' ? 'Confirm suggested link' : 'Append manual link record'
  const disabled = saving || !dialog.confirmed || !dialog.projectId || (dialog.action === 'move' && dialog.projectId === dialog.currentProjectId)

  return (
    <div aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog">
      <section className="max-w-2xl rounded-xl border border-border bg-background p-5 shadow-xl">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Append a manual SessionProjectLinkRecord for <span className="font-medium text-foreground">{sessionTitle(dialog.session)}</span>
          {selectedProject ? ` to ${selectedProject.name}` : ''}.
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          <li>One append-only SessionProjectLinkRecord will be written.</li>
          <li>This does not edit the session database.</li>
          <li>This does not send work to Jenny.</li>
          <li>This does not dispatch anything.</li>
          <li>This does not enable routing.</li>
          <li>Suggestions are display-only until confirmed.</li>
          <li>Moving a link appends a newer record instead of changing old records.</li>
        </ul>
        <div className="mt-4 grid gap-3">
          <label className="grid gap-1 text-xs font-medium">
            Project
            <select
              className="rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
              onChange={event => onChange({ projectId: event.target.value })}
              value={dialog.projectId}
            >
              <option value="">Choose one project</option>
              {availableProjects.map(project => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          {dialog.session.suggested_project_id ? (
            <p className="text-xs text-amber-700 dark:text-amber-200">
              Suggested project: {projectNameForId(dialog.session.suggested_project_id, projects)} · display-only until confirmed.
            </p>
          ) : null}
          <label className="flex items-start gap-2 text-xs text-muted-foreground">
            <input checked={dialog.confirmed} onChange={event => onChange({ confirmed: event.target.checked })} type="checkbox" />
            <span>I understand this appends one Mission Control record only.</span>
          </label>
        </div>
        {message ? <p className="mt-3 text-sm text-muted-foreground">{message}</p> : null}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-medium hover:bg-muted" onClick={onCancel} type="button">
            Cancel
          </button>
          <button
            className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60"
            disabled={disabled}
            onClick={onSave}
            type="button"
          >
            {saving ? 'Appending record…' : buttonLabel}
          </button>
        </div>
      </section>
    </div>
  )
}

function Field({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="grid gap-1">
      <span className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">{label}</span>
      <span className="text-sm leading-relaxed text-foreground/90">{text(value)}</span>
    </div>
  )
}

function StatusItem({
  className,
  label,
  tone,
  value
}: {
  className?: string
  label: string
  tone?: 'good' | 'warn'
  value: string
}) {
  return (
    <div className={cn('min-w-0 rounded-lg border border-border/60 bg-background/70 p-3', className)}>
      <div className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">{label}</div>
      <div
        className={cn(
          'mt-1 break-words text-sm font-medium',
          tone === 'good' && 'text-emerald-700 dark:text-emerald-300',
          tone === 'warn' && 'text-amber-700 dark:text-amber-300'
        )}
      >
        {value}
      </div>
    </div>
  )
}
