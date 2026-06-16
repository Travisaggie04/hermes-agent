import type { MissionControlGitHubBridgeStatusResponse } from '@/hermes'

export type NativeJennyStatusTone = 'idle' | 'ok' | 'pending' | 'working' | 'warn'

export interface NativeJennyStatus {
  detail: string
  label: string
  summary: string
  tone: NativeJennyStatusTone
}

export interface NativeJennyStatusInput {
  activeTurnRunning?: boolean
  bridgeStatus?: MissionControlGitHubBridgeStatusResponse | null
  gatewayOpen: boolean
  loading?: boolean
  nowMs?: number
  projectId?: string
  queryError?: unknown
}

const BENIGN_NO_PENDING_ERROR_RE = /no matching pending mission control mailbox request/i
const WORKING_STATUS_FRESH_MS = 30_000

const ANSWER_WORKING_STATUSES = new Set(['hermes_answer_started', 'manual_hermes_answer_started'])
const WATCH_WORKING_STATUSES = new Set(['watch_started', 'watch_poll_completed'])

const REPLIED_STATUSES = new Set(['hermes_answer_completed', 'response_appended', 'replied'])

function dateMs(value?: string): number {
  if (!value) {
    return 0
  }

  const ms = Date.parse(value)

  return Number.isFinite(ms) ? ms : 0
}

function isFreshStatus(value: string | undefined, nowMs: number): boolean {
  const ms = dateMs(value)

  return ms > 0 && nowMs >= ms && nowMs - ms <= WORKING_STATUS_FRESH_MS
}

function friendlyBridgeError(message: string): string {
  const lower = message.toLowerCase()

  if (lower.includes('bridge field is too large') || lower.includes('field is too large')) {
    return 'Jenny could not process that message because it was too large. Send a shorter request or split it into one smaller task.'
  }

  if (lower.includes('connect econnrefused') || lower.includes('gateway offline')) {
    return 'Jenny could not reach the Hermes gateway. Check the gateway connection, then retry from this chat.'
  }

  if (lower.includes('responder failed') || lower.includes('app-server startup failed') || lower.includes('timed out')) {
    return 'Jenny failed before finishing a reply. Retry once, and open details if it fails again.'
  }

  return 'Jenny had trouble finishing that message. Retry once, or open details.'
}

export function nativeJennyStatus({
  activeTurnRunning = false,
  bridgeStatus,
  gatewayOpen,
  loading = false,
  nowMs = Date.now(),
  projectId = '',
  queryError
}: NativeJennyStatusInput): NativeJennyStatus {
  if (!gatewayOpen) {
    return {
      detail: 'Gateway is offline. Jenny cannot receive chat work yet.',
      label: 'Gateway offline',
      summary: 'Reconnect gateway',
      tone: 'warn'
    }
  }

  if (!projectId.trim()) {
    return {
      detail: 'Pick a project so Jenny gets the right hidden context and guardrails.',
      label: 'Pick a project',
      summary: 'Choose a project',
      tone: 'idle'
    }
  }

  if (activeTurnRunning) {
    return {
      detail: 'Jenny is working on this chat. Progress and the final reply appear here.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    }
  }

  if (queryError) {
    return {
      detail: 'Send a message here; Jenny will reply in this project chat. Background status is unavailable.',
      label: 'Jenny ready',
      summary: 'Chat still works',
      tone: 'ok'
    }
  }

  if (loading && !bridgeStatus) {
    return {
      detail: 'Checking Jenny.',
      label: 'Checking Jenny',
      summary: 'Checking',
      tone: 'idle'
    }
  }

  const lastStatus = bridgeStatus?.last_status?.trim() || ''
  const lastError = bridgeStatus?.last_error?.trim() || ''
  const benignNoPending = Boolean(lastError && BENIGN_NO_PENDING_ERROR_RE.test(lastError))
  const pending = bridgeStatus?.visible_pending_count ?? bridgeStatus?.pending_count ?? 0
  const backgroundPending = bridgeStatus?.background_pending_count ?? 0
  const statusIsFresh = isFreshStatus(bridgeStatus?.last_poll_at, nowMs)
  const latestReplyIsNewerThanStatus =
    dateMs(bridgeStatus?.last_response_at) > 0 && dateMs(bridgeStatus?.last_response_at) >= dateMs(bridgeStatus?.last_poll_at)
  const staleOrBackgroundOnlyError = pending === 0 && (backgroundPending > 0 || latestReplyIsNewerThanStatus)
  const answerIsWorking = ANSWER_WORKING_STATUSES.has(lastStatus) && statusIsFresh
  const watchIsWorking = Boolean(
    bridgeStatus?.foreground_watch_running && WATCH_WORKING_STATUSES.has(lastStatus) && statusIsFresh
  )

  if (lastError && !benignNoPending && !staleOrBackgroundOnlyError) {
    return {
      detail: friendlyBridgeError(lastError),
      label: 'Jenny needs attention',
      summary: 'Check details and retry',
      tone: 'warn'
    }
  }

  if (answerIsWorking || watchIsWorking) {
    return {
      detail: 'Jenny is working on the latest project message.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    }
  }

  if (pending > 0) {
    return {
      detail: `Jenny has ${pending} older queued project message${pending === 1 ? '' : 's'}, but this chat is ready. Send a message here and Jenny will reply in this project chat.`,
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
    }
  }

  if (REPLIED_STATUSES.has(lastStatus) || bridgeStatus?.last_response_at || bridgeStatus?.last_response_request_id) {
    return {
      detail: 'Jenny replied. Review the latest answer before relying on it.',
      label: 'Jenny replied',
      summary: 'Review latest reply',
      tone: 'ok'
    }
  }

  return {
    detail: benignNoPending ? 'No project message is waiting for Jenny.' : 'Send a message here; Jenny will reply in this project chat.',
    label: 'Jenny ready',
    summary: 'Send a message',
    tone: 'ok'
  }
}
