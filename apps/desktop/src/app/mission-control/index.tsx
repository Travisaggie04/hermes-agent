import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { sessionRoute } from '@/app/routes'
import {
  answerMissionControlGitHubBridgeOnce,
  createMissionControlChallengeReview,
  createMissionControlGitHubBridgeRequest,
  createMissionControlJennyReplyReview,
  createMissionControlLaneRequest,
  createMissionControlReport,
  createMissionControlSessionProjectLink,
  getMissionControlChallengeReviews,
  getMissionControlGitHubBridgeStatus,
  getMissionControlJennyBridgeInbox,
  getMissionControlJennyBridgeOutbox,
  getMissionControlJennyBridgePollerStatus,
  getMissionControlJennyReplyReviews,
  getMissionControlLaneRequests,
  getMissionControlProfileMemoryStorage,
  getMissionControlProjectBriefs,
  getMissionControlProjects,
  getMissionControlProjectSessions,
  getMissionControlProjectState,
  getMissionControlReports,
  getMissionControlWorkspaceStatus,
  type MissionControlChallengeReviewRecord,
  type MissionControlGitHubBridgeMailboxStatusRecord,
  type MissionControlGitHubBridgeMessageRecord,
  type MissionControlGitHubBridgeStatusResponse,
  type MissionControlJennyBridgePollerStatusResponse,
  type MissionControlJennyBridgeRequestRecord,
  type MissionControlJennyBridgeResponseRecord,
  type MissionControlJennyReplyReviewRecord,
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
  jennyReplyReviews: MissionControlJennyReplyReviewRecord[]
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
  jennyReplyReviews: [],
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
  'Start a safe Hermes storage cleanup lane for the VPS, with a target of about 50% disk usage when practical.',
  'Inventory VPS disk usage, large runtime/worktree/cache/build artifacts, logs, backup/snapshot directories, and Mission Control record growth before cleanup.',
  'Create a timestamped dry-run manifest before deleting anything; include exact paths, protected paths, expected GiB recovered, and rollback risk.',
  'Preserve the current dashboard runtime, gateway runtime, shared runtime venv, latest rollback runtime, records, secrets, service files, live app data, dirty project worktrees, and report-builder/customer/payment/outreach data.',
  'With explicit cleanup approval, safe candidates may include clean stale Hermes runtime worktrees, clean stale review worktrees, old caches, old build outputs, and obsolete logs.',
  'Measure df -h and top du consumers before and after each cleanup pass; stop when the VPS is near 50% usage or remaining candidates are risky.',
  'Prefer moving review artifacts or exports to connected long-term storage when useful: OneDrive travis_Littleton@msn.com, Family Hub secondary storage, or the 5TB Google Drive.',
  'Keep laptop cleanup advisory-only unless Travis separately approves worker-node cleanup.',
  'Do not touch dirty worktrees, Tool & Tally report-builder data, records/config/state.db, secrets, current/rollback runtimes, gateway, dispatch, session send, Waha/social/payment/customer actions, workers/timers/daemons/cron, or laptop cleanup without separate approval.'
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

function formatPercent(value: unknown): string {
  const percent = typeof value === 'number' && Number.isFinite(value) ? value : 0
  return `${Math.max(0, Math.round(percent))}%`
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

  return `${value.slice(0, Math.max(0, maxChars - 3)).trimEnd()}...`
}

function compactText(value: string | string[] | null | undefined, maxChars: number): string {
  const raw = Array.isArray(value) ? value.filter(Boolean).join('; ') : value ?? ''
  const normalized = raw.replace(/\s+/g, ' ').trim()

  return normalized.length > maxChars ? `${normalized.slice(0, Math.max(0, maxChars - 3)).trim()}...` : normalized
}

function projectRequestPreview(value: string, maxChars: number): string {
  const normalized = value.replace(/\s+/g, ' ').trim()
  const requestMatch = normalized.match(
    /(?:^|[\s/])Request:\s*([\s\S]*?)(?=\s+(?:Request intake:|Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i
  )
  const inlineRequestMatch = normalized.match(
    /^[\w &/-]+ Request:\s*([\s\S]*?)(?=\s+(?:Current brief:|Request intake:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i
  )
  const fallbackMatch = normalized.match(
    /^(.+?)\s+(?=Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)/i
  )
  const candidate = requestMatch?.[1] ?? inlineRequestMatch?.[1] ?? fallbackMatch?.[1] ?? value
  return compactText(candidate, maxChars)
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

interface JennyReplyContract {
  label: string
  tone: 'complete' | 'missing'
}

function jennyReplyContract(value: string): JennyReplyContract {
  const lower = value.toLowerCase()
  const checks = [
    { label: 'recommendation', present: /\b(recommend|recommendation|next safe lane|next lane|next step)\b/.test(lower) },
    { label: 'evidence', present: /\b(evidence|validation|validated|test|tests|checked|verified|pass|ci)\b/.test(lower) },
    { label: 'risks', present: /\b(risk|risks|blocker|blockers|remaining risk)\b/.test(lower) },
    { label: 'approval/rollback', present: /\b(approval|approved|rollback|required approval|approval needed|roll back)\b/.test(lower) },
    { label: 'safety', present: /\b(safety|forbidden|no deploy|no dispatch|guard|gated)\b/.test(lower) }
  ]
  const missing = checks.filter(check => !check.present).map(check => check.label)
  const matched = checks.length - missing.length

  if (!missing.length) {
    return { label: `Reply quality ${matched}/${checks.length}: complete`, tone: 'complete' }
  }

  return {
    label: `Reply quality ${matched}/${checks.length}: missing ${missing.join(', ')}`,
    tone: 'missing'
  }
}

function buildJennyReplyReviewPrompt(action: 'accept' | 'evidence' | 'safer-plan', projectName: string, reply: string): string {
  const replyPreview = compactText(reply, 500)

  if (action === 'accept') {
    return [
      `Review this Jenny reply for ${projectName}.`,
      'If it is complete, convert it into a concise accepted-result summary with evidence, risks/blockers, tests/checks, and the next safe lane.',
      'If it is not complete, say exactly what is missing before Travis relies on it.',
      '',
      `Jenny reply: ${replyPreview}`
    ].join('\n')
  }

  if (action === 'evidence') {
    return [
      `The last Jenny reply for ${projectName} needs stronger evidence.`,
      'Reply with the exact files, commands, checks, PR/CI status, runtime status, and remaining risks that prove or disprove the recommendation.',
      'Do not take action. Report evidence only.',
      '',
      `Jenny reply: ${replyPreview}`
    ].join('\n')
  }

  return [
    `Challenge the last Jenny reply for ${projectName} like a senior engineer.`,
    'Identify unsafe assumptions, missing approvals, wrong approach risk, rollback concerns, and the smallest safer next lane.',
    'Do not implement or trigger live actions.',
    '',
    `Jenny reply: ${replyPreview}`
  ].join('\n')
}

type JennyReplyReviewDecision = 'accepted' | 'needs_evidence' | 'needs_safer_plan'

interface ProjectChatMessage {
  body: string
  displayBody?: string
  id: string
  meta: string
  speaker: 'Jenny' | 'You'
  time?: string
}

function jennyReplyReviewDecisionLabel(decision: string | undefined): string {
  switch (decision) {
    case 'accepted':
      return 'Reviewed: accepted'
    case 'needs_evidence':
      return 'Reviewed: needs evidence'
    case 'needs_safer_plan':
      return 'Reviewed: needs safer plan'
    default:
      return 'Not reviewed yet'
  }
}

function latestReplyReviewByResponseId(reviews: MissionControlJennyReplyReviewRecord[]): Map<string, MissionControlJennyReplyReviewRecord> {
  const map = new Map<string, MissionControlJennyReplyReviewRecord>()
  for (const review of reviews) {
    if (review.response_id) {
      map.set(review.response_id, review)
    }
  }
  return map
}

function latestReviewedJennyReply(
  chatMessages: ProjectChatMessage[],
  reviewsByResponseId: Map<string, MissionControlJennyReplyReviewRecord>
): MissionControlJennyReplyReviewRecord | null {
  for (const chat of [...chatMessages].reverse()) {
    if (chat.speaker !== 'Jenny') {
      continue
    }
    const review = reviewsByResponseId.get(chat.id)
    if (review) {
      return review
    }
  }
  return null
}

function jennyReplyReviewStatus(review: MissionControlJennyReplyReviewRecord | null): { detail: string; label: string; nextStep: string | null; tone: 'accepted' | 'blocked' | 'none' | 'warn' } {
  if (!review) {
    return {
      detail: 'No Jenny reply has been accepted or challenged yet.',
      label: 'Reply not reviewed',
      nextStep: null,
      tone: 'none'
    }
  }

  if (review.decision === 'accepted') {
    return {
      detail: 'Travis accepted the latest reviewed Jenny reply. Continue with the next bounded lane.',
      label: 'Reply accepted',
      nextStep: null,
      tone: 'accepted'
    }
  }

  if (review.decision === 'needs_evidence') {
    return {
      detail: 'Travis marked the latest reviewed Jenny reply as needing stronger evidence.',
      label: 'Needs evidence',
      nextStep: 'Ask Jenny for exact files, commands, checks, CI/runtime status, and remaining risks before relying on that reply.',
      tone: 'warn'
    }
  }

  if (review.decision === 'needs_safer_plan') {
    return {
      detail: 'Travis marked the latest reviewed Jenny reply as needing a safer plan.',
      label: 'Needs safer plan',
      nextStep: 'Challenge Jenny for unsafe assumptions, missing approvals, rollback concerns, and the smallest safer next lane.',
      tone: 'blocked'
    }
  }

  return {
    detail: 'The latest reply review decision is unknown. Treat the reply as not accepted.',
    label: 'Review unclear',
    nextStep: 'Ask Jenny to restate the evidence, risks, and next safe lane before proceeding.',
    tone: 'warn'
  }
}

function jennyReplyReviewStatusClass(tone: 'accepted' | 'blocked' | 'none' | 'warn'): string {
  switch (tone) {
    case 'accepted':
      return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    case 'blocked':
      return 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300'
    case 'warn':
      return 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
    default:
      return 'border-[#f3ebda]/10 bg-[#15101a]/60 text-[#a59783]'
  }
}

interface JennyRunProgress {
  detail: string
  phase: 'complete' | 'error' | 'queued' | 'starting' | 'waiting'
}

type JennyWorkSessionStepState = 'active' | 'blocked' | 'done' | 'idle'

interface JennyWorkSessionStep {
  detail: string
  label: string
  state: JennyWorkSessionStepState
}

interface JennyLiveStatusItem {
  label: string
  value: string
}

function jennyRunProgressCopy(progress: JennyRunProgress | null, elapsedSeconds: number): { detail: string; label: string } {
  if (!progress) {
    return {
      detail: 'Jenny is standing by.',
      label: 'Standing by'
    }
  }

  if (progress.phase === 'queued') {
    return {
      detail: progress.detail || 'Your message is queued for Jenny.',
      label: 'Queued'
    }
  }
  if (progress.phase === 'complete') {
    return {
      detail: progress.detail || 'Jenny replied. Review the latest response before sending the next message.',
      label: 'Reply received'
    }
  }
  if (progress.phase === 'error') {
    return {
      detail: progress.detail || 'Jenny hit a guarded error. No hidden action was treated as successful.',
      label: 'Needs attention'
    }
  }

  return {
    detail: `${progress.detail || 'Mission Control is waiting for Jenny to finish one guarded reply.'} Refreshing status every 2.5s. Elapsed ${elapsedSeconds}s.`,
    label: progress.phase === 'starting' ? 'Starting Jenny' : 'Waiting for Jenny'
  }
}

function jennyLiveStatusItems({
  elapsedSeconds,
  latestUserMessage,
  pendingCount,
  progress,
  responseCount,
  statusLabel
}: {
  elapsedSeconds: number
  latestUserMessage: string
  pendingCount: number
  progress: JennyRunProgress | null
  responseCount: number
  statusLabel: string
}): JennyLiveStatusItem[] {
  const phase = progress?.phase
    ? progress.phase.replaceAll('_', ' ')
    : pendingCount
      ? 'waiting'
      : responseCount
        ? 'replied'
        : 'ready'

  return [
    { label: 'Current phase', value: statusLabel || phase },
    { label: 'Last sent', value: latestUserMessage || 'No message sent yet' },
    { label: 'Reply state', value: pendingCount ? `${pendingCount} waiting` : responseCount ? `${responseCount} received` : 'No reply yet' },
    { label: 'Elapsed', value: isJennyRunActive(progress) ? `${elapsedSeconds}s` : 'not running' }
  ]
}

function isJennyRunActive(progress: JennyRunProgress | null): boolean {
  return progress?.phase === 'starting' || progress?.phase === 'waiting'
}

function jennyWorkSessionSteps({
  hasError,
  hasRunnablePendingMessage,
  pendingCount,
  progress,
  replyReviewTone,
  responseCount
}: {
  hasError: boolean
  hasRunnablePendingMessage: boolean
  pendingCount: number
  progress: JennyRunProgress | null
  replyReviewTone: 'accepted' | 'blocked' | 'none' | 'warn'
  responseCount: number
}): JennyWorkSessionStep[] {
  const activeRun = isJennyRunActive(progress)
  const hasReply = responseCount > 0 || progress?.phase === 'complete' || replyReviewTone !== 'none'
  const queued = pendingCount > 0 || hasRunnablePendingMessage || Boolean(progress)

  return [
    {
      detail: queued ? 'Message is in Jenny mailbox.' : 'Write and send one bounded message.',
      label: 'Queued',
      state: hasError ? 'blocked' : queued && !activeRun && !hasReply ? 'active' : queued || hasReply ? 'done' : 'idle'
    },
    {
      detail: activeRun ? 'One guarded reply is running.' : hasReply ? 'Jenny run finished.' : 'Use Get Jenny reply when ready.',
      label: 'Jenny working',
      state: hasError ? 'blocked' : activeRun ? 'active' : hasReply ? 'done' : 'idle'
    },
    {
      detail: hasReply ? 'Latest reply is available.' : 'No reply yet.',
      label: 'Reply received',
      state: hasError ? 'blocked' : hasReply ? 'done' : 'idle'
    },
    {
      detail: replyReviewTone === 'accepted'
        ? 'Reply accepted; send the next bounded message.'
        : replyReviewTone === 'blocked' || replyReviewTone === 'warn'
          ? 'Review asks Jenny for stronger evidence or a safer plan.'
          : hasReply
            ? 'Review the reply before relying on it.'
            : 'Waiting for a reply to review.',
      label: 'Review next',
      state: replyReviewTone === 'accepted'
        ? 'done'
        : replyReviewTone === 'blocked' || replyReviewTone === 'warn'
          ? 'blocked'
          : hasReply
            ? 'active'
            : 'idle'
    }
  ]
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
      .filter(message => message.from_agent === 'jenny')
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

function uniqueGitHubBridgeMessages(messages: MissionControlGitHubBridgeMessageRecord[]): MissionControlGitHubBridgeMessageRecord[] {
  const seen = new Set<string>()
  return messages.filter(message => {
    const key = [
      message.request_id ?? '',
      message.from_agent ?? '',
      message.to_agent ?? '',
      message.status ?? '',
      message.github_comment_id ?? '',
      message.created_at ?? ''
    ].join(':')
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })
}

function timestampValue(value?: string): number {
  const time = Date.parse(value ?? '')
  return Number.isFinite(time) ? time : 0
}

function latestJennyReplyTimestamp(
  responses: MissionControlJennyBridgeResponseRecord[],
  githubMessages: MissionControlGitHubBridgeMessageRecord[]
): number {
  const responseTimes = responses.map(response => timestampValue(response.created_at))
  const githubReplyTimes = githubMessages
    .filter(message => message.from_agent === 'jenny')
    .map(message => timestampValue(message.created_at))

  return Math.max(0, ...responseTimes, ...githubReplyTimes)
}

function isCurrentAfterReply(createdAt: string | undefined, latestReplyAt: number): boolean {
  if (!latestReplyAt) {
    return true
  }

  const created = timestampValue(createdAt)
  return !created || created > latestReplyAt
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

function isOperatorBridgeMessage(message: MissionControlGitHubBridgeMessageRecord): boolean {
  const fromAgent = message.from_agent?.toLowerCase() ?? ''
  const requestId = message.request_id?.toLowerCase() ?? ''
  const text = message.message?.toLowerCase() ?? ''
  return fromAgent === 'codex' ||
    requestId.startsWith('codex-') ||
    text.includes('bounded dashboard-only deploy check') ||
    text.includes('review pr #')
}

function visibleCurrentGitHubBridgeMessagesForProject(
  messages: MissionControlGitHubBridgeMessageRecord[],
  projectId: string
): MissionControlGitHubBridgeMessageRecord[] {
  const visibleMessages = uniqueGitHubBridgeMessages(messages)
    .filter(message => message.project_id === projectId)
    .filter(message => !isDiagnosticChatMessage(message.message) && !isOperatorBridgeMessage(message))
  const latestReplyAt = latestJennyReplyTimestamp([], visibleMessages)
  return visibleMessages.filter(message => isCurrentAfterReply(message.created_at, latestReplyAt))
}

function latestVisiblePendingGitHubBridgeMessageForProject(
  messages: MissionControlGitHubBridgeMessageRecord[],
  projectId: string
): MissionControlGitHubBridgeMessageRecord | null {
  return latestPendingGitHubBridgeMessage(visibleCurrentGitHubBridgeMessagesForProject(messages, projectId))
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

function jennyRunStatusToneClass(progress: JennyRunProgress | null, connectionTone: 'bad' | 'good' | 'idle' | 'warn'): string {
  if (progress?.phase === 'error' || connectionTone === 'bad') {
    return 'border-red-500/35 bg-red-500/10 text-red-100'
  }
  if (progress?.phase === 'starting' || progress?.phase === 'waiting') {
    return 'border-sky-500/35 bg-sky-500/10 text-sky-100'
  }
  if (progress?.phase === 'queued' || connectionTone === 'warn') {
    return 'border-amber-500/35 bg-amber-500/10 text-amber-100'
  }
  if (progress?.phase === 'complete' || connectionTone === 'good') {
    return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-100'
  }
  return 'border-[#f3ebda]/10 bg-[#15101a]/70 text-[#f3ebda]'
}

function jennyActivityLabel(status: string | undefined): string {
  switch (status) {
    case 'hermes_answer_started':
      return 'Jenny is thinking'
    case 'hermes_answer_completed':
      return 'Jenny replied'
    case 'hermes_answer_error':
      return 'Jenny hit an error'
    case 'hermes_answer_noop':
      return 'No pending message'
    case 'poll_completed':
    case 'watch_poll_completed':
      return 'Mailbox checked'
    case 'poll_error':
    case 'watch_poll_error':
      return 'Mailbox check failed'
    default:
      return status?.replaceAll('_', ' ') || 'Idle'
  }
}

function jennyActivityDetail(record: MissionControlGitHubBridgeMailboxStatusRecord): string {
  if (record.last_error) {
    return record.last_error
  }
  if (record.handled_request_id) {
    return `request ${record.handled_request_id}`
  }
  if (typeof record.pending_count === 'number') {
    return `${record.pending_count} pending`
  }
  return record.mode || 'manual bridge'
}

function jennyActivityItems(status: MissionControlGitHubBridgeStatusResponse): MissionControlGitHubBridgeMailboxStatusRecord[] {
  return unwrapRecords(status.status_records).slice(-4).reverse()
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

  return meta.length ? meta.join(' / ') : 'No profile/source recorded'
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
  const risksBlockers = [listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' / ') || 'None recorded'
  const noHistory = model.latestReportSummary === 'No report yet' && model.latestResult === 'No result yet'
  const historyFallback = noHistory ? 'No prior report/result exists; start by verifying current state before acting.' : ''

  const prompt = `PROJECT NEXT LANE - REVIEW PACKET

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
Report format: preflight, recommendation, work done, validation, risks, safety confirmation.
Evidence contract:
1. Recommendation: one-sentence next lane.
2. Evidence: exact files/commands/checks/PR/CI/runtime/links used.
3. Tests: pass/fail/not-run with reason.
4. Risks: blockers, unsafe assumptions, missing info.
5. Approval/rollback: approval needed before live action plus rollback path.
6. Next safe lane: smallest bounded step.
Rule: if evidence is missing, say "not proven"; do not present it as done.`
}

interface RequestIntakeAssessment {
  detail: string
  jennyInstruction: string
  label: string
  state: 'approval_required' | 'challenge_first' | 'ready' | 'spec_first'
}

function assessProjectRequest(requestText: string, review: MissionControlChallengeReviewRecord | null): RequestIntakeAssessment {
  const normalized = requestText.replace(/\s+/g, ' ').trim()
  const lower = normalized.toLowerCase()
  const riskyAction = /\b(deploy|restart|runtime switch|gateway|payment|checkout|outreach|post|publish|delete|remove|cleanup|worker|timer|daemon|cron|secret|token|waha|whatsapp)\b/.test(lower)
  const vagueRequest = normalized.length < 24 || /\b(fix it|make it better|do whatever|handle this|everything|autonomous|fully functional|robust)\b/.test(lower)

  if (!normalized) {
    return {
      detail: 'Write one bounded request before Jenny receives work.',
      jennyInstruction: 'Ask Travis for the missing request before proposing implementation.',
      label: 'Needs request',
      state: 'spec_first'
    }
  }
  if (riskyAction) {
    return {
      detail: 'Contains protected actions; Jenny should challenge scope and identify approvals before work.',
      jennyInstruction: 'Do not execute. First return a preflight, risks, required approvals, and a safer bounded lane.',
      label: 'Approval check',
      state: 'approval_required'
    }
  }
  if (!review || review.decision_state !== 'clear_and_safe') {
    return {
      detail: 'No clear challenge review is recorded for this project lane.',
      jennyInstruction: 'Treat this as challenge/spec-first. Ask clarifying questions or create a narrow plan before implementation.',
      label: 'Challenge first',
      state: 'challenge_first'
    }
  }
  if (vagueRequest) {
    return {
      detail: 'Request may be too broad or underspecified; Jenny should narrow it before implementation.',
      jennyInstruction: 'Question assumptions, split the request into a bounded lane, and ask Travis if critical details are missing.',
      label: 'Spec first',
      state: 'spec_first'
    }
  }
  return {
    detail: 'Request is bounded enough for a guarded Jenny reply.',
    jennyInstruction: 'Proceed with a bounded recommendation or implementation plan, still challenging unsafe assumptions first.',
    label: 'Ready',
    state: 'ready'
  }
}

function buildSpecFirstComposerText(projectName: string, requestText: string, intake: RequestIntakeAssessment): string {
  const request = compactText(requestText, 520) || '<write the request Travis is considering>'
  return `Spec-first request for Jenny:
Project: ${projectName}
Request Travis is considering:
${request}

Current intake: ${intake.label} / ${intake.detail}

Jenny, do not implement yet. First challenge the request like a senior engineer:
1. Restate the goal in plain English.
2. List missing facts or questions Travis must answer.
3. Call out wrong-approach risks, hidden assumptions, and protected actions.
4. Propose the smallest safe lane.
5. Define evidence, tests, rollback/stop conditions, and approval needs.

Return only the spec/challenge review and the recommended next safe lane.`
}

function shouldAutoChallengeRequest(intake: RequestIntakeAssessment): boolean {
  return intake.state !== 'ready'
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
  const intake = assessProjectRequest(requestText, review)
  const categories = review?.challenge_categories?.length ? review.challenge_categories.join(', ') : 'none recorded'
  const verdicts = review?.blocking_verdicts?.length ? review.blocking_verdicts.join(', ') : 'none recorded'
  const packet = `Project room request:
${project.name}

Request:
${compactText(requestText, 420) || '<write the request>'}

Request intake:
${intake.label} / ${intake.detail}
Jenny instruction: ${intake.jennyInstruction}

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

function buildJennyMailboxMessage({
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
  const intake = assessProjectRequest(requestText, review)
  if (shouldAutoChallengeRequest(intake)) {
    return buildSpecFirstComposerText(project.name, requestText, intake)
  }
  return buildPhoneSafeProjectPacket({ brief, project, requestText, review, state, status })
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
    '1. Read-only inventory of VPS disk usage, largest Hermes runtimes/worktrees/caches/build outputs/logs/backups, and current rollback runtimes.',
    '2. Build a timestamped dry-run manifest with exact candidate paths, protected paths, expected GiB recovered, and rollback risk.',
    '3. Protect current dashboard runtime, gateway runtime, shared runtime venv, latest rollback runtime, live records/secrets/service files, dirty project worktrees, report-builder/customer/payment/outreach data, and anything uncertain.',
    '4. With explicit cleanup approval, remove only clean stale Hermes runtime worktrees, clean stale review worktrees, old caches/build outputs/logs, and other manifest-approved low-risk artifacts.',
    '5. Measure df -h and top du consumers before and after each pass; target about 50% disk usage, then stop and report residual risk.',
    '',
    'Allowed: storage inventory, dry-run manifest, approved stale runtime/worktree/cache/log cleanup, archive recommendation, and before/after effectiveness report.',
    'Forbidden: dirty worktrees, Tool & Tally report-builder data, records/config/state.db, secrets, current/rollback runtimes, gateway restart/switch, laptop worker-node cleanup, dispatch, session sending, Waha/social/payment/customer action, workers/timers/daemons/cron.',
    '',
    `Current Mission Control safety status: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}.`
  ].join('\n')
}

function missionControlErrorMessage(err: unknown): string {
  return String(err instanceof Error ? err.message : err)
}

async function loadMissionControlEndpoint<T>(
  label: string,
  load: () => Promise<T>,
  fallback: T | ((error: string) => T)
): Promise<T> {
  try {
    return await load()
  } catch {
    try {
      return await load()
    } catch (err) {
      const message = missionControlErrorMessage(err)
      console.warn(`[mission-control] ${label} unavailable`, err)
      return typeof fallback === 'function' ? (fallback as (error: string) => T)(message) : fallback
    }
  }
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
    jennyReplyReviews,
    memoryStorage
  ] = await Promise.all([
    loadMissionControlEndpoint('workspace status', getMissionControlWorkspaceStatus, {}),
    loadMissionControlEndpoint('projects', getMissionControlProjects, { count: 0, projects: [] }),
    loadMissionControlEndpoint('project briefs', getMissionControlProjectBriefs, { count: 0, project_briefs: [] }),
    loadMissionControlEndpoint('challenge reviews', getMissionControlChallengeReviews, { challenge_reviews: [], count: 0 }),
    loadMissionControlEndpoint('lane requests', getMissionControlLaneRequests, { count: 0, lane_requests: [] }),
    loadMissionControlEndpoint('reports', getMissionControlReports, { count: 0, reports: [] }),
    loadMissionControlEndpoint('project state', getMissionControlProjectState, { count: 0, project_states: [] }),
    loadMissionControlEndpoint('project sessions', getMissionControlProjectSessions, { count: 0, groups: [] }),
    loadMissionControlEndpoint('Jenny bridge outbox', getMissionControlJennyBridgeOutbox, { count: 0, requests: [] }),
    loadMissionControlEndpoint('Jenny bridge inbox', getMissionControlJennyBridgeInbox, { count: 0, responses: [] }),
    loadMissionControlEndpoint('Jenny bridge poller status', getMissionControlJennyBridgePollerStatus, error => ({
      last_error: `Jenny bridge poller unavailable: ${error}`
    })),
    loadMissionControlEndpoint('GitHub bridge status', getMissionControlGitHubBridgeStatus, error => ({
      last_error: `Jenny activity unavailable: ${error}`,
      pending_messages: [],
      recent_messages: [],
      response_messages: []
    })),
    loadMissionControlEndpoint('Jenny reply reviews', getMissionControlJennyReplyReviews, { count: 0, reply_reviews: [] }),
    loadMissionControlEndpoint('profile storage', getMissionControlProfileMemoryStorage, error => ({
      errors: [{ error }],
      profiles: []
    }))
  ])

  return {
    challengeReviews: unwrapRecords(challengeReviews.challenge_reviews),
    jennyBridgeRequests: unwrapRecords(jennyBridgeOutbox.requests),
    jennyBridgeResponses: unwrapRecords(jennyBridgeInbox.responses),
    jennyBridgePollerStatus,
    githubBridgeStatus,
    jennyReplyReviews: unwrapRecords(jennyReplyReviews.reply_reviews),
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
  const [jennyRunElapsedSeconds, setJennyRunElapsedSeconds] = useState(0)
  const [jennyRunProgress, setJennyRunProgress] = useState<JennyRunProgress | null>(null)

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
      setError('')
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
    }, projectRoomSaving ? 2500 : 15000)

    return () => window.clearInterval(timer)
  }, [projectRoomSaving, selectedProjectId, snapshot.projects.length])

  useEffect(() => {
    if (!isJennyRunActive(jennyRunProgress)) {
      setJennyRunElapsedSeconds(0)

      return
    }

    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setJennyRunElapsedSeconds(Math.max(1, Math.floor((Date.now() - startedAt) / 1000)))
    }, 1000)

    return () => window.clearInterval(timer)
  }, [jennyRunProgress])

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

  function mailboxMessageForProject(project: MissionControlProjectRecord) {
    return buildJennyMailboxMessage({
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
        message: mailboxMessageForProject(project),
        project_id: project.project_id,
        request_id: bridgeRequestId(),
        to_agent: 'jenny'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setJennyRunProgress({
        detail: 'Message sent. Use Get Jenny reply when you want Jenny to answer this project message.',
        phase: 'queued'
      })
      setProjectRoomMessage('Sent to Jenny mailbox. Replies refresh automatically; use Refresh replies if you want to check now.')
    } catch (err) {
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function runJennyOnce(project: MissionControlProjectRecord) {
    const pending = latestVisiblePendingGitHubBridgeMessageForProject(
      [
        ...unwrapRecords(snapshot.githubBridgeStatus.pending_messages),
        ...unwrapRecords(snapshot.githubBridgeStatus.recent_messages),
        ...unwrapRecords(snapshot.githubBridgeStatus.response_messages)
      ],
      project.project_id
    )
    if (!pending?.request_id) {
      setProjectRoomMessage('Send Jenny a project message first; there is no pending request to answer.')

      return
    }

    setProjectRoomSaving(true)
    setJennyRunElapsedSeconds(0)
    setJennyRunProgress({
      detail: 'Starting the guarded one-reply Jenny run.',
      phase: 'starting'
    })
    setProjectRoomMessage('Jenny is answering one pending message...')

    try {
      setJennyRunProgress({
        detail: 'Mission Control sent the latest project message to Jenny and is waiting for one bounded reply.',
        phase: 'waiting'
      })
      const result = await answerMissionControlGitHubBridgeOnce({
        confirm_manual_hermes_answer: true,
        project_id: project.project_id,
        request_id: pending.request_id
      })
      setSnapshot(await loadMissionControlSnapshot())
      setJennyRunProgress({
        detail: result.answered
          ? 'Jenny replied to the latest project message.'
          : `Jenny did not reply: ${String((result.status as { last_error?: unknown } | undefined)?.last_error ?? 'no matching pending request')}`,
        phase: result.answered ? 'complete' : 'error'
      })
      setProjectRoomMessage(
        result.answered
          ? 'Jenny replied to the latest pending project message.'
          : `Jenny did not reply: ${String((result.status as { last_error?: unknown } | undefined)?.last_error ?? 'no matching pending request')}`
      )
    } catch (err) {
      setJennyRunProgress({
        detail: String(err instanceof Error ? err.message : err),
        phase: 'error'
      })
      setProjectRoomMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setProjectRoomSaving(false)
    }
  }

  async function reviewJennyReply(
    project: MissionControlProjectRecord,
    decision: JennyReplyReviewDecision,
    responseId: string,
    reply: string
  ) {
    const promptAction = decision === 'accepted' ? 'accept' : decision === 'needs_evidence' ? 'evidence' : 'safer-plan'
    setProjectRequest(buildJennyReplyReviewPrompt(promptAction, project.name, reply))
    setProjectRoomSaving(true)
    setProjectRoomMessage('')

    try {
      await createMissionControlJennyReplyReview({
        decision,
        note: jennyReplyReviewDecisionLabel(decision),
        project_id: project.project_id,
        response_id: responseId,
        reviewer: 'travis'
      })
      setSnapshot(await loadMissionControlSnapshot())
      setProjectRoomMessage(`${jennyReplyReviewDecisionLabel(decision)}. Follow-up prompt is ready to send if needed.`)
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
    <section className="h-full min-h-0 overflow-hidden bg-[#0e0b12] text-[#f7efe4]">
      <div className="grid h-full min-h-0 grid-cols-[15.5rem_minmax(0,1fr)]">
        <aside className="hidden min-h-0 border-r border-[#f7efe4]/10 bg-[#17111f] px-5 py-6 lg:block">
          <div className="text-[0.68rem] font-semibold uppercase tracking-[0.26em] text-[#a89782]">Local · studio</div>
          <div className="mt-4 text-xl font-semibold tracking-tight">Agentic <span className="font-serif italic text-[#d4a574]">OS</span></div>
          <nav className="mt-10 grid gap-2 text-sm">
            {[
              ['Mission Control', 'grid'],
              ['Paperclip', 'archive'],
              ['AI Agent Mastermind', 'chat'],
            ].map(([label, icon]) => (
              <div className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5',
                label === 'Mission Control' ? 'bg-[#2c2334] text-[#f7efe4]' : 'text-[#a89782]'
              )} key={label}>
                <span className="grid h-5 w-5 place-items-center rounded border border-[#f7efe4]/10 text-[0.62rem]">{icon.slice(0, 1).toUpperCase()}</span>
                <span>{label}</span>
              </div>
            ))}
          </nav>
          <div className="mt-10 text-[0.68rem] font-semibold uppercase tracking-[0.24em] text-[#a89782]">Agents</div>
          <div className="mt-4 grid gap-2 text-sm">
            {[
              ['Claude', 'bg-orange-500'],
              ['OpenClaw', 'bg-pink-500'],
              ['Jenny', 'bg-blue-500'],
              ['Hermes', 'bg-violet-500'],
              ['Codex', 'bg-emerald-500'],
            ].map(([label, color]) => (
              <div className={cn('flex items-center gap-3 rounded-lg px-3 py-2.5', label === 'Jenny' ? 'bg-[#3a2d45] text-[#f7efe4]' : 'text-[#a89782]')} key={label}>
                <span className={cn('h-6 w-6 rounded-full', color)} />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </aside>

        <main className="min-h-0 overflow-auto bg-[radial-gradient(circle_at_80%_20%,rgba(116,69,58,0.18),transparent_32%),linear-gradient(180deg,#160f1b_0%,#0e0b12_100%)] px-6 py-5">
          <header className="mb-5 border-b border-[#f7efe4]/10 pb-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-[#a89782]">
                  <span className="font-serif text-xl italic text-[#d4a574]">IV.</span>
                  <span className="ml-3">Agent · Jenny</span>
                </div>
                <h1 className="mt-5 text-6xl font-semibold tracking-tight text-[#fff8ed]">Jenny</h1>
                <span className="sr-only">Jenny Workspace</span>
                <p className="sr-only">
                  Pick a project and talk to Jenny. Safety checks stay in the background while Hermes / Mission Control is being recovered.
                </p>
                <p className="sr-only">Messages are saved. Higher-risk actions still need approval before anything live changes.</p>
                <p className="mt-3 text-lg text-[#a89782]">Mission Control, project rooms, guarded replies, and live bridge activity.</p>
                <div className="mt-6 text-xs font-semibold uppercase tracking-[0.24em] text-[#a89782]">Local · studio</div>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <span className="rounded-lg border border-[#f7efe4]/10 bg-[#1b1422]/70 px-3 py-2 text-xs text-[#c9b8a2]">⌘K Command palette</span>
                <span className="rounded-lg border border-[#f7efe4]/10 bg-[#1b1422]/70 px-3 py-2 text-xs text-[#c9b8a2]">All systems</span>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-300">
                  Jenny guarded
                </span>
              </div>
            </div>
            <div className="mt-8 flex min-w-0 flex-wrap gap-2">
              {['Chat', 'Talk', 'Jenny-Jarvis', 'Studio', 'Session hub', 'Workspace', 'MCPs', 'Manage', 'Control Room', 'Goal Mode'].map((tab, index) => (
                <span
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-sm',
                    index === 0 ? 'border-blue-400/60 bg-blue-500/10 text-blue-200' : 'border-[#f7efe4]/10 bg-[#15101a]/60 text-[#c9b8a2]'
                  )}
                  key={tab}
                >
                  {tab}
                </span>
              ))}
            </div>
          </header>

      {error ? <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div> : null}
      {loading ? <div className="rounded-lg border border-border/70 p-4 text-sm text-muted-foreground">Loading Mission Control workspace...</div> : null}

      {updateNotice ? (
        <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200">
          {updateNotice}
        </div>
      ) : null}

      {selectedProject ? (
        <div className="grid min-h-[34rem] gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
          <div className="xl:order-2">
            <JennyLiveActivityRail
              bridgeStatus={snapshot.jennyBridgePollerStatus}
              githubBridgeStatus={snapshot.githubBridgeStatus}
              jennyRunElapsedSeconds={jennyRunElapsedSeconds}
              jennyRunProgress={jennyRunProgress}
              projectRoomSaving={projectRoomSaving}
            />
          </div>
          <div className="xl:order-1">
            <ProjectRoomsWorkspace
              bridgeRequests={snapshot.jennyBridgeRequests.filter(request => request.project_id === selectedProject.project_id)}
              bridgeResponses={snapshot.jennyBridgeResponses.filter(response => response.project_id === selectedProject.project_id)}
              bridgeStatus={snapshot.jennyBridgePollerStatus}
              brief={latestForProject(selectedProject.project_id, snapshot.projectBriefs)}
              githubBridgeMessages={uniqueGitHubBridgeMessages([
                ...unwrapRecords(snapshot.githubBridgeStatus.pending_messages),
                ...unwrapRecords(snapshot.githubBridgeStatus.recent_messages),
                ...unwrapRecords(snapshot.githubBridgeStatus.response_messages)
              ]).filter(message => message.project_id === selectedProject.project_id)}
              githubBridgeStatus={snapshot.githubBridgeStatus}
              jennyRunElapsedSeconds={jennyRunElapsedSeconds}
              jennyRunProgress={jennyRunProgress}
              memoryStorage={snapshot.memoryStorage}
              message={projectRoomMessage}
              onCopyPacket={() => void copyProjectRoomPacket(selectedProject)}
              onOpenSession={session => navigate(sessionRoute(session.session_id))}
              onQueueBridge={() => void queueJennyBridgeRequest(selectedProject)}
              onQueueHermesUpdate={selectedProject.project_id === HERMES_PROJECT_ID ? () => void queueHermesUpdateLane(selectedProject) : undefined}
              onQueueStorageCleanup={selectedProject.project_id === HERMES_PROJECT_ID ? () => void queueHermesStorageCleanupLane(selectedProject) : undefined}
              onRefreshBridge={() => void refreshMissionControlSnapshot('Refreshed bridge inbox/outbox.')}
              onRequestChange={setProjectRequest}
              onReviewReply={(decision, responseId, reply) => void reviewJennyReply(selectedProject, decision, responseId, reply)}
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
              replyReviews={snapshot.jennyReplyReviews.filter(review => review.project_id === selectedProject.project_id)}
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
          </div>
        </div>
      ) : null}

      <details className="mt-5 rounded-xl border border-border/70 bg-background/40 p-4">
        <summary className="cursor-pointer text-sm font-semibold">Safety details and reports</summary>
        <div className="mt-4 grid gap-5">
          <HermesHealthDashboard
            activeProjects={activeProjects}
            pausedProjects={pausedProjects}
            snapshot={snapshot}
            status={status}
          />

          <KanbanParkedCard />

          <details className="rounded-xl border border-border/70 bg-background/50 p-4">
            <summary className="cursor-pointer text-sm font-semibold">Advanced diagnostic records</summary>
            <div className="mt-4 grid gap-5">
              <WorkspaceStatusPanel status={status} />

              <ActiveLanesPanel
                cards={activeProjects.map(project => activeLaneCardFor(project, snapshot))}
                status={status}
              />

              <details className="rounded-xl border border-border/70 bg-background/50 p-4">
                <summary className="cursor-pointer text-sm font-semibold">Manual record repair</summary>
                <ManualReportIngestion
                  form={reportForm}
                  message={reportMessage}
                  onChange={updateReportField}
                  onSave={() => void saveManualReport()}
                  projects={realProjects}
                  saving={reportSaving}
                />
              </details>
            </div>
          </details>

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
                <span className="font-medium text-foreground/80">{project.name}</span> - de-emphasized smoke/support record
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
        </main>
      </div>
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

function JennyLiveActivityRail({
  bridgeStatus,
  githubBridgeStatus,
  jennyRunElapsedSeconds,
  jennyRunProgress,
  projectRoomSaving
}: {
  bridgeStatus: MissionControlJennyBridgePollerStatusResponse
  githubBridgeStatus: MissionControlGitHubBridgeStatusResponse
  jennyRunElapsedSeconds: number
  jennyRunProgress: JennyRunProgress | null
  projectRoomSaving: boolean
}) {
  const activityItems = jennyActivityItems(githubBridgeStatus)
  const hasError = Boolean(bridgeStatus.last_error || githubBridgeStatus.last_error)
  const runCopy = jennyRunProgressCopy(jennyRunProgress, jennyRunElapsedSeconds)
  const runActive = isJennyRunActive(jennyRunProgress)
  const visiblePendingCount = githubBridgeStatus.visible_pending_count ?? githubBridgeStatus.pending_count ?? 0
  const liveLabel = runActive
    ? 'Jenny is working'
    : jennyRunProgress?.phase === 'complete'
      ? 'Last reply complete'
    : hasError
      ? 'Needs attention'
      : githubBridgeStatus.last_status === 'hermes_answer_completed'
        ? 'Last reply complete'
        : 'Standing by'

  return (
    <aside className="min-h-0 rounded-xl border border-[#f7efe4]/10 bg-[#1b1422]/80 p-4 shadow-[0_20px_70px_rgba(0,0,0,0.32)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#a89782]">Live activity</div>
          <h2 className="mt-2 text-xl font-semibold text-[#fff8ed]">{liveLabel}</h2>
        </div>
        <span className={cn(
          'h-3 w-3 rounded-full',
          runActive ? 'bg-blue-400 shadow-[0_0_24px_rgba(96,165,250,0.85)]' : hasError || jennyRunProgress?.phase === 'error' ? 'bg-red-400' : 'bg-emerald-400'
        )} />
      </div>

      <div className="mt-4 grid gap-3">
        <StatusItem label="bridge" value={bridgeStatus.last_status || 'idle'} />
        <StatusItem label="mailbox" value={githubBridgeStatus.mode || 'manual'} />
        <StatusItem label="pending" tone={visiblePendingCount ? 'warn' : 'good'} value={String(visiblePendingCount)} />
        <StatusItem label="last response" value={githubBridgeStatus.last_response_request_id || githubBridgeStatus.last_response_at || 'none'} />
      </div>

      <div className="mt-5 border-t border-[#f7efe4]/10 pt-4">
        <div className="mb-3 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#a89782]">Jenny stream</div>
        <div className="grid gap-2">
          {jennyRunProgress ? (
            <div className="rounded-lg border border-blue-400/30 bg-blue-500/10 p-3 text-sm text-blue-100">
              <div className="font-semibold">{runCopy.label}</div>
              <div className="mt-1 text-xs leading-relaxed">{runCopy.detail}</div>
            </div>
          ) : null}
          {activityItems.length ? (
            activityItems.map(item => (
              <article className="rounded-lg border border-[#f7efe4]/10 bg-[#100b15]/80 p-3 text-sm" key={item.status_id ?? `${item.status}:${item.created_at}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-[#fff8ed]">Stream: {jennyActivityLabel(item.status)}</span>
                  <span className="text-right text-xs text-[#a89782]">{item.created_at || 'time unknown'}</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-[#c9b8a2]">{jennyActivityDetail(item)}</p>
              </article>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-[#f7efe4]/10 p-3 text-sm text-[#a89782]">No live activity records yet.</div>
          )}
        </div>
      </div>
    </aside>
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
  jennyRunElapsedSeconds,
  jennyRunProgress,
  memoryStorage,
  message,
  onCopyPacket,
  onQueueBridge,
  onQueueHermesUpdate,
  onQueueStorageCleanup,
  onRefreshBridge,
  onReviewReply,
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
  replyReviews,
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
  jennyRunElapsedSeconds: number
  jennyRunProgress: JennyRunProgress | null
  memoryStorage: MissionControlProfileMemoryStorageResponse
  message: string
  onCopyPacket: () => void
  onQueueBridge: () => void
  onQueueHermesUpdate?: () => void
  onQueueStorageCleanup?: () => void
  onRefreshBridge: () => void
  onReviewReply: (decision: JennyReplyReviewDecision, responseId: string, reply: string) => void
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
  replyReviews: MissionControlJennyReplyReviewRecord[]
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
  const visibleGitHubBridgeMessages = githubBridgeMessages.filter(message => !isDiagnosticChatMessage(message.message) && !isOperatorBridgeMessage(message))
  const latestReplyAt = latestJennyReplyTimestamp(visibleBridgeResponses, visibleGitHubBridgeMessages)
  const currentPendingBridgeRequests = visibleBridgeRequests.filter(request => isCurrentAfterReply(request.created_at, latestReplyAt))
  const currentPendingGitHubBridgeMessages = visibleGitHubBridgeMessages.filter(message => isCurrentAfterReply(message.created_at, latestReplyAt))
  const repliedRequestIds = new Set(visibleBridgeResponses.map(response => response.request_id).filter(Boolean))
  const githubResponseIds = new Set(
    visibleGitHubBridgeMessages
      .filter(message => message.from_agent === 'jenny')
      .map(message => message.request_id)
      .filter(Boolean)
  )
  const githubPendingCount = currentPendingGitHubBridgeMessages.filter(message =>
    message.to_agent === 'jenny' &&
    ['queued', 'retry_requested'].includes(message.status) &&
    !githubResponseIds.has(message.request_id)
  ).length
  const latestPending = latestPendingGitHubBridgeMessage(currentPendingGitHubBridgeMessages)
  const githubResponseCount = visibleGitHubBridgeMessages.filter(message => message.from_agent === 'jenny').length
  const pendingCount = pendingJennyMessageCount(currentPendingBridgeRequests, visibleBridgeResponses) + githubPendingCount
  const responseCount = visibleBridgeResponses.length + githubResponseCount
  const deliveryStatus = jennyDeliveryStatus(pendingCount, responseCount, bridgeStatus, githubBridgeStatus)
  const connectionState = jennyConnectionState(pendingCount, responseCount, bridgeStatus, githubBridgeStatus)
  const bridgeNextStep = jennyNextStep(pendingCount, responseCount, Boolean(latestPending), bridgeStatus, githubBridgeStatus)
  const activityItems = jennyActivityItems(githubBridgeStatus)
  const requestIntake = assessProjectRequest(request, review)
  const specFirstComposerText = buildSpecFirstComposerText(project.name, request, requestIntake)
  const latestReviewByResponseId = latestReplyReviewByResponseId(replyReviews)
  const runActive = isJennyRunActive(jennyRunProgress)
  const runCopy = jennyRunProgressCopy(jennyRunProgress, jennyRunElapsedSeconds)
  const bridgeError = bridgeStatus.last_error || githubBridgeStatus.last_error || ''
  const chatMessages: ProjectChatMessage[] = [
    ...visibleBridgeRequests.map(request => ({
      body: request.message,
      displayBody: projectRequestPreview(request.message, 900),
      id: request.request_id || request.ack_key || request.created_at || 'bridge-request',
      meta: chatStatusLabel(request.bridge_state ?? (request.request_id && repliedRequestIds.has(request.request_id) ? 'replied' : request.status ?? 'queued')),
      speaker: 'You' as const,
      time: request.created_at
    })),
    ...visibleBridgeResponses.map(response => ({
      body: response.message,
      id: response.response_id || response.request_id || response.created_at || 'bridge-response',
      meta: chatStatusLabel(response.status ?? 'reply'),
      speaker: 'Jenny' as const,
      time: response.created_at
    })),
    ...visibleGitHubBridgeMessages.map(message => ({
      body: message.message,
      displayBody: message.from_agent === 'jenny' ? undefined : projectRequestPreview(message.message, 900),
      id: message.github_comment_id || message.request_id || message.created_at || 'github-message',
      meta: chatStatusLabel(message.status),
      speaker: message.from_agent === 'jenny' ? 'Jenny' as const : 'You' as const,
      time: message.created_at
    }))
  ].sort((left, right) => String(left.time ?? '').localeCompare(String(right.time ?? ''))).slice(-8)
  const latestReplyReview = latestReviewedJennyReply(chatMessages, latestReviewByResponseId)
  const replyReviewStatus = jennyReplyReviewStatus(latestReplyReview)
  const nextStep = replyReviewStatus.nextStep ?? bridgeNextStep
  const statusCopy = jennyRunProgress
    ? runCopy
    : { detail: paused ? 'This project is paused until Jenny is stable.' : nextStep, label: connectionState.label }
  const latestUserMessage = [...chatMessages].reverse().find(chat => chat.speaker === 'You')
  const liveStatusItems = jennyLiveStatusItems({
    elapsedSeconds: jennyRunElapsedSeconds,
    latestUserMessage: latestUserMessage ? projectRequestPreview(latestUserMessage.displayBody ?? latestUserMessage.body, 96) : '',
    pendingCount,
    progress: jennyRunProgress,
    responseCount,
    statusLabel: statusCopy.label
  })
  const workSessionSteps = jennyWorkSessionSteps({
    hasError: Boolean(bridgeError),
    hasRunnablePendingMessage: Boolean(latestPending),
    pendingCount,
    progress: jennyRunProgress,
    replyReviewTone: replyReviewStatus.tone,
    responseCount
  })

  return (
    <section
      aria-label="Project chat workspace"
      className="mt-2 flex h-[calc(100vh-6.5rem)] min-h-[34rem] flex-col overflow-hidden rounded-md border border-[#d4a574]/20 bg-[#15101a] shadow-[0_20px_70px_rgba(0,0,0,0.35)]"
    >
      <div className="border-b border-[#f3ebda]/10 bg-[#1c1622]/90 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2 overflow-x-auto pb-1">
          <span className="sr-only">Local studio</span>
          <span className="shrink-0 text-[0.66rem] font-semibold uppercase tracking-[0.18em] text-[#a59783]">Projects</span>
          <span className="sr-only">{projects.length} projects</span>
          {projects.map(candidate => (
            <button
              className={cn(
                'shrink-0 rounded-full border px-3 py-1.5 text-left text-xs transition hover:border-[#d4a574]/30 hover:bg-[#251d2c]/70',
                candidate.project_id === project.project_id
                  ? 'border-[#d4a574]/50 bg-[#2e2436]/80 text-[#f3ebda]'
                  : 'border-[#f3ebda]/10 bg-transparent'
              )}
              key={candidate.project_id}
              onClick={() => onSelectProject(candidate.project_id)}
              type="button"
            >
              <span className="font-medium text-[#f3ebda]">{candidate.name}</span>
              <span className="sr-only">
                {candidate.project_id === HERMES_PROJECT_ID ? 'Active recovery lane' : 'Paused until Jenny is stable'}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col p-2">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f3ebda]/10 pb-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="sr-only">IV. — Jenny workspace</span>
            <h2 className="truncate text-base font-semibold tracking-tight text-[#f3ebda]">{project.name}</h2>
            <span className="hidden max-w-[36rem] truncate text-xs text-[#a59783] md:inline">
              {compactText(state?.current_goal ?? project.current_goal, 130) || 'No current goal recorded.'}
            </span>
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
            <span className={cn('rounded-full border px-2.5 py-1 text-xs font-semibold', jennyReplyReviewStatusClass(replyReviewStatus.tone))}>
              {replyReviewStatus.label}
            </span>
          </div>
        </div>

        <details className="mt-1 rounded-md border border-[#f3ebda]/10 bg-[#1c1622]/50 px-3 py-1.5 text-xs">
          <summary className="cursor-pointer font-semibold text-[#a59783]">
            Room status
            <span className="sr-only">Next step</span>
          </summary>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-semibold text-[#f3ebda]">Goal</span>
            <span className="min-w-0 flex-1 truncate text-[#a59783]">{compactText(state?.current_goal ?? project.current_goal, 220) || 'No current goal recorded.'}</span>
            <span className="font-semibold text-[#f3ebda]">Jenny</span>
            <span className="text-[#a59783]">{deliveryStatus}. {connectionState.detail}</span>
            <span className="rounded-full border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-0.5 text-[#a59783]">Pending {pendingCount}</span>
            <span className="rounded-full border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-0.5 text-[#a59783]">Replies {responseCount}</span>
          </div>
          <p className="mt-2 text-sm text-[#f3ebda]">
            {paused ? 'Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.' : nextStep}
          </p>
          <div className="mt-2 grid gap-2 text-xs md:grid-cols-4">
            <Field label="readiness" value={readiness.detail} />
            <Field label="reply review" value={replyReviewStatus.detail} />
            <Field label="last update" value={compactText(report?.summary || report?.result, 220) || 'No update recorded yet.'} />
            <Field label="report contract" value={reportContractSummaryForState(state, report)} />
          </div>
        </details>

        <section
          aria-label="Jenny current status"
          className={cn('mt-2 rounded-md border px-3 py-2 text-sm', jennyRunStatusToneClass(jennyRunProgress, connectionState.tone))}
        >
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] opacity-75">Jenny status</div>
              <div className="mt-0.5 font-semibold">{statusCopy.label}</div>
            </div>
            <div className="flex flex-wrap gap-1.5 text-xs">
              <span className="rounded-full border border-current/20 px-2 py-0.5">Pending {pendingCount}</span>
              <span className="rounded-full border border-current/20 px-2 py-0.5">Replies {responseCount}</span>
              {runActive ? <span className="rounded-full border border-current/20 px-2 py-0.5">Elapsed {jennyRunElapsedSeconds}s</span> : null}
            </div>
          </div>
          <p className="mt-2 max-w-full text-sm leading-snug [overflow-wrap:anywhere]">{statusCopy.detail}</p>
          <div aria-label="Jenny live status" className="mt-2 grid gap-2 text-xs sm:grid-cols-4">
            {liveStatusItems.map(item => (
              <div className="min-w-0 rounded border border-current/15 bg-black/10 px-2 py-1" key={item.label}>
                <div className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] opacity-70">{item.label}</div>
                <div className="mt-0.5 truncate font-semibold">{item.value}</div>
              </div>
            ))}
          </div>
          {bridgeError ? <p className="mt-2 max-w-full text-xs [overflow-wrap:anywhere]">Bridge error: {bridgeError}</p> : null}
        </section>

        <JennyWorkSessionTimeline steps={workSessionSteps} />

        <section aria-label="Project chat transcript" className="mt-2 flex min-h-0 flex-1 flex-col rounded-md border border-[#f3ebda]/10 bg-[#251d2c]/70 p-2">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-[#f3ebda]">Conversation</h3>
            <span className="text-xs text-[#a59783]">{chatMessages.length ? `${chatMessages.length} recent messages` : 'No messages yet'}</span>
          </div>
          <div className="mt-2 grid min-h-0 flex-1 content-start gap-2 overflow-auto pr-1">
            {runActive ? (
              <article className="max-w-[85%] justify-self-start rounded-lg border border-[#60a5fa]/25 bg-[#60a5fa]/10 px-3 py-2 text-sm text-[#f3ebda] shadow-[0_10px_30px_rgba(0,0,0,0.18)]">
                <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                  <span className="font-semibold">Jenny</span>
                  <span className="text-[#93c5fd]">{runCopy.label}</span>
                </div>
                <p className="whitespace-pre-wrap break-words">
                  {runCopy.detail}
                </p>
              </article>
            ) : null}
            {chatMessages.length ? (
              chatMessages.map(chat => (
                <article
                  className={cn(
                    'max-w-[85%] rounded-lg border px-3 py-2 text-sm shadow-[0_10px_30px_rgba(0,0,0,0.18)]',
                    chat.speaker === 'You'
                      ? 'justify-self-end border-[#5ab896]/30 bg-[#5ab896]/10 text-[#f3ebda]'
                      : 'justify-self-start border-[#f3ebda]/10 bg-[#1c1622]/90 text-[#f3ebda]'
                  )}
                  key={`${chat.speaker}:${chat.id}`}
                >
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                    <span className="font-semibold">{chat.speaker}</span>
                    <span className="text-[#a59783]">{chat.meta}</span>
                  </div>
                  <p className="whitespace-pre-wrap break-words">
                    {chat.speaker === 'You' ? chat.displayBody ?? projectRequestPreview(chat.body, 900) : compactText(chat.body, 900)}
                  </p>
                  {chat.speaker === 'Jenny' ? (
                    <div className="mt-2 grid gap-2">
                      <p className={cn(
                        'rounded border px-2 py-1 text-xs',
                        jennyReplyContract(chat.body).tone === 'complete'
                          ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-200'
                          : 'border-amber-500/25 bg-amber-500/10 text-amber-100'
                      )}>
                        {jennyReplyContract(chat.body).label}
                      </p>
                      <p className="rounded border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-1 text-xs text-[#a59783]">
                        {jennyReplyReviewDecisionLabel(latestReviewByResponseId.get(chat.id)?.decision)}
                      </p>
                      <div aria-label="Jenny reply review actions" className="flex flex-wrap gap-1.5">
                        <button
                          className="rounded border border-[#5ab896]/30 px-2 py-1 text-xs font-semibold text-[#5ab896] hover:bg-[#5ab896]/10"
                          onClick={() => onReviewReply('accepted', chat.id, chat.body)}
                          type="button"
                        >
                          Draft acceptance note
                        </button>
                        <button
                          className="rounded border border-[#60a5fa]/30 px-2 py-1 text-xs font-semibold text-[#93c5fd] hover:bg-[#60a5fa]/10"
                          onClick={() => onReviewReply('needs_evidence', chat.id, chat.body)}
                          type="button"
                        >
                          Ask for evidence
                        </button>
                        <button
                          className="rounded border border-amber-500/30 px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-500/10"
                          onClick={() => onReviewReply('needs_safer_plan', chat.id, chat.body)}
                          type="button"
                        >
                          Challenge plan
                        </button>
                      </div>
                    </div>
                  ) : null}
                </article>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-[#f3ebda]/10 p-4 text-sm text-[#a59783]">
                Ask Jenny a bounded question or give her one safe next task below.
              </div>
            )}
          </div>
        </section>

        <div className="mt-2 border-t border-[#f3ebda]/10 pt-2">
          <label className="grid gap-1 text-sm font-medium">
            Message Jenny
            <textarea
              className="min-h-16 rounded-md border border-[#f3ebda]/10 bg-[#15101a] px-3 py-2 text-sm text-[#f3ebda] outline-none transition placeholder:text-[#6e6353] focus:border-[#d4a574]/50"
              disabled={paused}
              onChange={event => onRequestChange(event.target.value)}
              placeholder={paused ? 'This project is on hold until Jenny is stable.' : 'Tell Jenny what you want to discuss or ask her to do next...'}
              value={request}
            />
          </label>

          <div className="mt-2 flex flex-wrap gap-2">
            <button className="rounded-md border border-[#5ab896]/40 bg-[#5ab896]/10 px-4 py-2 text-sm font-semibold text-[#5ab896] hover:bg-[#5ab896]/15 disabled:opacity-60" disabled={saving || paused} onClick={onQueueBridge} type="button">
              Send to Jenny
            </button>
            <button
              className="rounded-md border border-[#60a5fa]/40 bg-[#60a5fa]/10 px-4 py-2 text-sm font-semibold text-[#93c5fd] hover:bg-[#60a5fa]/15 disabled:opacity-60"
              disabled={saving || paused || !latestPending}
              onClick={onRunJennyOnce}
              type="button"
            >
              Get Jenny reply
            </button>
            <button className="rounded-md border border-[#f3ebda]/10 px-4 py-2 text-sm font-semibold text-[#ddd0bb] hover:bg-[#251d2c] disabled:opacity-60" disabled={saving} onClick={onRefreshBridge} type="button">
              Refresh replies
            </button>
          </div>
          <div className={cn(
            'mt-2 rounded-md border px-3 py-2 text-xs',
            requestIntake.state === 'ready'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : requestIntake.state === 'approval_required'
                ? 'border-red-500/30 bg-red-500/10 text-red-200'
                : 'border-amber-500/30 bg-amber-500/10 text-amber-100'
          )}>
            <span className="font-semibold">Request intake: {requestIntake.label}.</span> {requestIntake.detail}
            {shouldAutoChallengeRequest(requestIntake) ? (
              <span className="mt-1 block">Send to Jenny will ask for a challenge/spec-first reply before any implementation plan.</span>
            ) : null}
          </div>
          <details className="mt-2 rounded-md border border-[#f3ebda]/10 bg-[#15101a]/60 px-3 py-2 text-xs">
            <summary className="cursor-pointer font-semibold text-[#ddd0bb]">Advanced request options</summary>
            <p className="mt-2 text-[#a59783]">
              Use these only when you want Jenny to challenge, narrow, or formalize the request before normal work.
            </p>
            {requestIntake.state !== 'ready' ? (
              <button
                className="mt-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-200 hover:bg-amber-500/15 disabled:opacity-60"
                disabled={saving || paused}
                onClick={() => onRequestChange(specFirstComposerText)}
                type="button"
              >
                Use spec-first prompt
              </button>
            ) : (
              <p className="mt-2 text-[#a59783]">This request is currently bounded enough for a guarded Jenny reply.</p>
            )}
          </details>
          <p className="mt-1 text-xs text-[#a59783]">
            {paused
              ? 'This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.'
              : 'Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates.'}
          </p>
          {paused ? <PausedProjectResumeChecklist /> : null}
          {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
        </div>

        </div>

        <details aria-label="Workspace inspector" className="mt-2 rounded-md border border-[#f3ebda]/10 bg-[#1c1622]/70 px-3 py-2" role="complementary">
          <summary className="cursor-pointer text-sm font-semibold text-[#f3ebda]">Activity, sessions, and safety details</summary>
          <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <section aria-label="Jenny activity" className="rounded-lg border border-[#60a5fa]/25 bg-[#60a5fa]/10 p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-[#f3ebda]">Jenny activity</h3>
            <span className="text-xs text-[#a59783]">
              {runActive ? 'refreshing every 2.5s' : 'recent bridge status'}
            </span>
          </div>
          <div className="mt-2 grid gap-2">
            {runActive ? (
              <p className="rounded-md border border-[#60a5fa]/20 bg-[#15101a]/70 p-2 text-xs text-[#93c5fd]">
                {runCopy.label}: {runCopy.detail}
              </p>
            ) : null}
            {activityItems.length ? (
              activityItems.map(item => (
                <article className="rounded-md border border-[#60a5fa]/20 bg-[#15101a]/70 p-2 text-xs" key={item.status_id ?? `${item.status}:${item.created_at}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-[#f3ebda]">{jennyActivityLabel(item.status)}</span>
                    <span className="text-right text-[#a59783]">{item.created_at || 'time unknown'}</span>
                  </div>
                  <p className="mt-1 text-[#a59783]">{jennyActivityDetail(item)}</p>
                </article>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-[#60a5fa]/20 p-2 text-xs text-[#a59783]">
                No Jenny activity records yet.
              </p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-[#f3ebda]/10 bg-[#15101a]/60 p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-[#f3ebda]">Previous sessions</h3>
            <span className="text-xs text-[#a59783]">{sessions.length} linked</span>
          </div>
          <div className="mt-2 grid gap-2">
            {sessions.length ? (
              sessions.slice(0, 6).map(session => (
                <button
                  className="rounded-lg border border-[#f3ebda]/10 bg-[#15101a]/70 p-3 text-left text-xs transition hover:border-[#d4a574]/30 hover:bg-[#251d2c]/80"
                  key={session.durable_session_id || session.session_id}
                  onClick={() => onOpenSession(session)}
                  type="button"
                >
                  <span className="block font-medium text-[#f3ebda]">{sessionTitle(session)}</span>
                  <span className="mt-1 block text-[#a59783]">{sessionMeta(session)}</span>
                </button>
              ))
            ) : (
              <p className="text-xs text-[#a59783]">No linked sessions for this project yet.</p>
            )}
          </div>
        </section>

          </div>
        <details className="mt-3 rounded-lg border border-[#f3ebda]/10 bg-[#15101a]/60 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Safety and maintenance</summary>
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
                      <div>Mount: {profile.mount?.path ?? 'unknown'} / {formatBytes(profile.mount?.used_bytes)} used of {formatBytes(profile.mount?.total_bytes)} / {formatPercent(profile.mount?.percent_used)}</div>
                      {profile.memory?.error || profile.user?.error || profile.mount?.error ? <div className="text-destructive">Read issue: {profile.memory?.error || profile.user?.error || profile.mount?.error}</div> : null}
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
                <Field label="pending" value={String(pendingCount)} />
                <Field label="last status" value={bridgeStatus.last_status ?? 'idle'} />
                <Field label="last response" value={bridgeStatus.last_response_request_id || bridgeStatus.last_response_at || 'none'} />
                <Field label="last error" value={bridgeStatus.last_error || 'none'} />
                <Field label="worker/timer" value={`worker ${bridgeStatus.worker_enabled ? 'enabled' : 'disabled'} / timer ${bridgeStatus.timer_enabled ? 'enabled' : 'disabled'}`} />
              </div>
              <div className="mt-3 grid gap-2 rounded-md border border-sky-500/20 bg-sky-500/5 p-2 text-xs md:grid-cols-2">
                <Field label="GitHub mailbox" value={githubBridgeStatus.manual_start_only === false ? 'disabled' : 'manual-start only'} />
                <Field label="GitHub mode" value={githubBridgeStatus.mode || 'manual'} />
                <Field
                  label="GitHub pending"
                  value={`visible ${githubBridgeStatus.visible_pending_count ?? githubBridgeStatus.pending_count ?? 0} / background ${githubBridgeStatus.background_pending_count ?? 0}`}
                />
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
    <section aria-label="Manual record repair" className="mt-4 rounded-xl border border-border/70 bg-background/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Save a missing Jenny report</h2>
          <p className="text-xs text-muted-foreground">
            Repair tool for when Jenny gave a useful report but Mission Control did not capture it automatically. Not needed for normal chat.
          </p>
        </div>
        <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-700 dark:text-blue-300">
          repair only
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
          {saving ? 'Saving report...' : 'Save missing report'}
        </button>
        <span className="text-xs text-muted-foreground">Creates a record only. No session send, queue mutation, dispatch, or model routing.</span>
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

function HermesHealthDashboard({
  activeProjects,
  pausedProjects,
  snapshot,
  status
}: {
  activeProjects: MissionControlProjectRecord[]
  pausedProjects: MissionControlProjectRecord[]
  snapshot: MissionControlSnapshot
  status: ReturnType<typeof summarizeWorkspaceStatus>
}) {
  const bridgeError = snapshot.githubBridgeStatus.last_error || snapshot.jennyBridgePollerStatus.last_error || ''
  const bridgePending = snapshot.githubBridgeStatus.visible_pending_count ?? snapshot.githubBridgeStatus.pending_count ?? snapshot.jennyBridgePollerStatus.pending_count ?? 0
  const bridgeWatching = snapshot.githubBridgeStatus.foreground_watch_running === true
  const reportCount = activeProjects.filter(project => {
    const state = stateForProject(project, snapshot.projectStates)
    return state?.has_real_report || state?.latest_report || state?.latest_jenny_report || latestReportForProject(project.project_id, snapshot.reports)
  }).length
  const memoryErrors = snapshot.memoryStorage.errors ?? []
  const safetyOk = status.guard === 'pass' && status.dispatch === false && status.activeLaneCount <= 1 && status.staleWarnings.length === 0
  const blockingIssues = [
    bridgeError ? `Jenny bridge error: ${bridgeError}` : '',
    status.guard !== 'pass' ? `Runtime guard is ${status.guard}` : '',
    status.dispatch !== false ? 'Dispatch safety is not confirmed off' : '',
    status.activeLaneCount > 1 ? `${status.activeLaneCount} active lanes recorded` : '',
    status.deploymentNeeded ? 'Phone/web dashboard needs a dashboard-only update' : '',
    status.staleWarnings.length ? `Stale context: ${status.staleWarnings.join(', ')}` : '',
    memoryErrors.length ? `${memoryErrors.length} memory storage warning${memoryErrors.length === 1 ? '' : 's'}` : ''
  ].filter(Boolean)
  const overallTone: HealthTone = blockingIssues.length ? 'warn' : 'good'
  const bridgeTone: HealthTone = bridgeError ? 'bad' : bridgePending ? 'warn' : 'good'
  const maxMountPercent = Math.max(0, ...(snapshot.memoryStorage.profiles ?? []).map(profile => profile.mount?.percent_used ?? 0))

  return (
    <section aria-label="Hermes health dashboard" className="rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Hermes health dashboard</h2>
          <p className="text-xs text-muted-foreground">Owner view for Jenny, phone/web, safety locks, project coverage, and parked tools.</p>
        </div>
        <HealthBadge tone={overallTone}>{blockingIssues.length ? 'Needs attention' : 'Healthy'}</HealthBadge>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <HealthTile
          detail={blockingIssues.length ? blockingIssues[0] : 'No blocking Mission Control health issue is currently recorded.'}
          label="Overall"
          tone={overallTone}
          value={blockingIssues.length ? `${blockingIssues.length} item${blockingIssues.length === 1 ? '' : 's'}` : 'Ready'}
        />
        <HealthTile
          detail={bridgeError || (bridgeWatching ? 'Live reply refresh is watching for Jenny.' : bridgePending ? 'A message is waiting for Jenny.' : 'No bridge error is recorded.')}
          label="Jenny bridge"
          tone={bridgeTone}
          value={bridgeError ? 'Error' : bridgePending ? `${bridgePending} pending` : 'Ready'}
        />
        <HealthTile
          detail={status.deploymentNeeded ? 'Desktop may be current while phone/web waits for the dashboard bundle.' : `Served head ${status.deployedHead.slice(0, 8)}.`}
          label="Phone and web"
          tone={status.deploymentNeeded ? 'warn' : 'good'}
          value={status.deploymentNeeded ? 'Update waiting' : 'Current'}
        />
        <HealthTile
          detail={`Guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active lanes=${status.activeLaneCount}.`}
          label="Safety locks"
          tone={safetyOk ? 'good' : 'warn'}
          value={safetyOk ? 'Holding' : 'Check'}
        />
        <HealthTile
          detail={`${reportCount} active project${reportCount === 1 ? '' : 's'} have live report evidence. ${pausedProjects.length} projects remain intentionally on hold.`}
          label="Project rooms"
          tone={activeProjects.length === 1 && pausedProjects.length === 4 ? 'good' : 'warn'}
          value={`${activeProjects.length} active / ${pausedProjects.length} paused`}
        />
        <HealthTile
          detail={`${snapshot.memoryStorage.profile_count ?? snapshot.memoryStorage.profiles?.length ?? 0} profiles. Highest mount usage ${formatPercent(maxMountPercent)}. ${memoryErrors.length ? memoryErrors[0]?.error ?? 'Storage warning recorded.' : 'No memory storage errors recorded.'}`}
          label="Memory"
          tone={memoryErrors.length ? 'warn' : 'good'}
          value={formatBytes(snapshot.memoryStorage.total_bytes)}
        />
      </div>

      <ProfileStorageTable memoryStorage={snapshot.memoryStorage} />

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <section className="rounded-lg border border-border/70 bg-background/60 p-3">
          <h3 className="text-sm font-semibold">Needs attention</h3>
          {blockingIssues.length ? (
            <ul className="mt-2 grid gap-1 text-xs text-muted-foreground">
              {blockingIssues.map(issue => <li key={issue}>{issue}</li>)}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">Nothing urgent is recorded. Keep using Hermes / Mission Control as the only active lane.</p>
          )}
        </section>
        <section className="rounded-lg border border-border/70 bg-background/60 p-3">
          <h3 className="text-sm font-semibold">Safe next actions</h3>
          <ul className="mt-2 grid gap-1 text-xs text-muted-foreground">
            <li>Review Jenny's latest reply before sending the next bounded message.</li>
            <li>Keep Long-form, Shorts, Tool & Tally, and Waha paused until you explicitly resume them.</li>
            <li>Use Kanban later after the real task board is reliable.</li>
          </ul>
        </section>
      </div>
    </section>
  )
}

function ProfileStorageTable({ memoryStorage }: { memoryStorage: MissionControlProfileMemoryStorageResponse }) {
  const profiles = memoryStorage.profiles ?? []
  return (
    <section aria-label="Profile storage usage" className="mt-4 rounded-lg border border-border/70 bg-background/60 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">Profile storage usage</h3>
        <div className="text-xs text-muted-foreground">
          {profiles.length} profiles / {formatBytes(memoryStorage.total_profile_data_bytes ?? memoryStorage.total_bytes)} profile data
        </div>
      </div>
      {profiles.length ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-xs">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border/70">
                <th className="py-2 pr-3 font-medium">Profile</th>
                <th className="py-2 pr-3 font-medium">Profile data</th>
                <th className="py-2 pr-3 font-medium">State DB</th>
                <th className="py-2 pr-3 font-medium">Sessions</th>
                <th className="py-2 pr-3 font-medium">Recall files</th>
                <th className="py-2 pr-3 font-medium">Mount</th>
                <th className="py-2 pr-3 font-medium">Mount max</th>
                <th className="py-2 pr-3 font-medium">Mount used</th>
                <th className="py-2 font-medium">Mount %</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map(profile => (
                <tr className="border-b border-border/40 last:border-0" key={`${profile.profile ?? 'profile'}-${profile.home ?? ''}`}>
                  <td className="py-2 pr-3 font-medium">{profile.profile ?? 'default'}</td>
                  <td className="py-2 pr-3">{formatBytes(profile.data?.bytes ?? profile.total_bytes)}</td>
                  <td className="py-2 pr-3">{formatBytes(profile.data?.components?.state?.bytes)}</td>
                  <td className="py-2 pr-3">{formatBytes(profile.data?.components?.sessions?.bytes)}</td>
                  <td className="py-2 pr-3" title={`MEMORY.md ${formatBytes(profile.memory?.bytes)} / USER.md ${formatBytes(profile.user?.bytes)}`}>
                    {formatBytes(profile.recall_file_bytes ?? ((profile.memory?.bytes ?? 0) + (profile.user?.bytes ?? 0)))}
                  </td>
                  <td className="max-w-[240px] truncate py-2 pr-3" title={profile.mount?.path ?? profile.home ?? ''}>{profile.mount?.path ?? 'unknown'}</td>
                  <td className="py-2 pr-3">{formatBytes(profile.mount?.total_bytes)}</td>
                  <td className="py-2 pr-3">{formatBytes(profile.mount?.used_bytes)}</td>
                  <td className="py-2">{formatPercent(profile.mount?.percent_used)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">No profile storage records are available yet.</p>
      )}
    </section>
  )
}

type HealthTone = 'bad' | 'good' | 'idle' | 'warn'

function HealthBadge({ children, tone }: { children: ReactNode; tone: HealthTone }) {
  return (
    <span className={cn('rounded-full border px-2.5 py-1 text-xs font-semibold', healthToneClass(tone))}>
      {children}
    </span>
  )
}

function HealthTile({
  detail,
  label,
  tone,
  value
}: {
  detail: string
  label: string
  tone: HealthTone
  value: string
}) {
  return (
    <article className="rounded-lg border border-border/70 bg-background/70 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
          <div className="mt-1 text-sm font-semibold">{value}</div>
        </div>
        <span aria-hidden="true" className={cn('h-2.5 w-2.5 shrink-0 rounded-full', healthDotClass(tone))} />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{detail}</p>
    </article>
  )
}

function KanbanParkedCard() {
  return (
    <section aria-label="Kanban parked" className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Kanban parked for later</h2>
          <p className="text-xs text-muted-foreground">
            The task board is intentionally hidden from this daily view until it can show real tasks and reliable controls.
          </p>
        </div>
        <HealthBadge tone="idle">Later</HealthBadge>
      </div>
    </section>
  )
}

function healthToneClass(tone: HealthTone): string {
  if (tone === 'bad') {
    return 'border-destructive/40 bg-destructive/10 text-destructive'
  }
  if (tone === 'good') {
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
  }
  if (tone === 'warn') {
    return 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-200'
  }
  return 'border-border/70 bg-muted/40 text-muted-foreground'
}

function healthDotClass(tone: HealthTone): string {
  if (tone === 'bad') {
    return 'bg-destructive'
  }
  if (tone === 'good') {
    return 'bg-emerald-500'
  }
  if (tone === 'warn') {
    return 'bg-amber-500'
  }
  return 'bg-muted-foreground'
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
              badge="Linked / source of truth"
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
      <Field label="latest lane" value={lane ? `${lane.title}${lane.status ? ` (${lane.status})` : ''}${lane.objective ? ` - ${lane.objective}` : ''}` : 'No draft lane request recorded'} />
      <Field label="latest Jenny report summary" value={model.latestReportSummary} />
      <Field label="report contract" value={model.reportContract} />
      <Field label="latest result" value={model.latestResult} />
      <Field label="risks/blockers" value={risksBlockers} />
      <Field label="last action time" value={`${model.latestActivityAt} (${model.latestActivitySource})`} />
      <Field label="artifact/report links" value={listText(model.artifactLinks, 'No artifact/report links recorded')} />
      <Field label="missing state fields" value={listText(model.missingStateFields, 'None - report state is current')} />
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
              Suggested project: {projectNameForId(dialog.session.suggested_project_id, projects)} / display-only until confirmed.
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
            {saving ? 'Appending record...' : buttonLabel}
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

function jennyWorkSessionStepClass(state: JennyWorkSessionStepState): string {
  if (state === 'done') {
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'
  }
  if (state === 'active') {
    return 'border-sky-500/35 bg-sky-500/10 text-sky-100'
  }
  if (state === 'blocked') {
    return 'border-red-500/35 bg-red-500/10 text-red-100'
  }
  return 'border-[#f3ebda]/10 bg-[#15101a]/70 text-[#a59783]'
}

function JennyWorkSessionTimeline({ steps }: { steps: JennyWorkSessionStep[] }) {
  return (
    <section aria-label="Jenny work session" className="mt-2 rounded-md border border-[#f3ebda]/10 bg-[#15101a]/60 p-2">
      <div className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-[#a59783]">Work session</div>
      <div className="mt-2 grid gap-2 md:grid-cols-4">
        {steps.map((step, index) => (
          <article className={cn('rounded-md border px-2.5 py-2 text-xs', jennyWorkSessionStepClass(step.state))} key={step.label}>
            <div className="flex items-center gap-2 font-semibold">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full border border-current/25 text-[0.65rem]">{index + 1}</span>
              <span>{step.label}</span>
            </div>
            <p className="mt-1 leading-snug opacity-80 [overflow-wrap:anywhere]">{step.detail}</p>
          </article>
        ))}
      </div>
    </section>
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
