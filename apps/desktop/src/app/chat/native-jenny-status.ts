import type { MissionControlGitHubBridgeStatusResponse } from '@/hermes'

export type NativeJennyStatusTone = 'idle' | 'ok' | 'pending' | 'working' | 'warn'

export interface NativeJennyStatus {
  detail: string
  label: string
  tone: NativeJennyStatusTone
}

export interface NativeJennyStatusInput {
  activeTurnRunning?: boolean
  bridgeStatus?: MissionControlGitHubBridgeStatusResponse | null
  gatewayOpen: boolean
  loading?: boolean
  projectId?: string
  queryError?: unknown
}

const BENIGN_NO_PENDING_ERROR_RE = /no matching pending mission control mailbox request/i

const WORKING_STATUSES = new Set([
  'hermes_answer_started',
  'manual_hermes_answer_started',
  'watch_started',
  'watch_poll_completed'
])

const REPLIED_STATUSES = new Set(['hermes_answer_completed', 'response_appended', 'replied'])

function dateMs(value?: string): number {
  if (!value) {
    return 0
  }

  const ms = Date.parse(value)

  return Number.isFinite(ms) ? ms : 0
}

export function nativeJennyStatus({
  activeTurnRunning = false,
  bridgeStatus,
  gatewayOpen,
  loading = false,
  projectId = '',
  queryError
}: NativeJennyStatusInput): NativeJennyStatus {
  if (!gatewayOpen) {
    return {
      detail: 'Gateway is offline. Jenny cannot receive chat work yet.',
      label: 'Gateway offline',
      tone: 'warn'
    }
  }

  if (!projectId.trim()) {
    return {
      detail: 'Pick a project so Jenny gets the right hidden context and guardrails.',
      label: 'Pick a project',
      tone: 'idle'
    }
  }

  if (queryError) {
    return {
      detail: 'Could not read Jenny bridge status. Chat remains guarded.',
      label: 'Status unavailable',
      tone: 'warn'
    }
  }

  if (activeTurnRunning) {
    return {
      detail: 'Jenny is working on the current chat turn.',
      label: 'Jenny working',
      tone: 'working'
    }
  }

  if (loading && !bridgeStatus) {
    return {
      detail: 'Checking the guarded Jenny bridge.',
      label: 'Checking Jenny',
      tone: 'idle'
    }
  }

  const lastStatus = bridgeStatus?.last_status?.trim() || ''
  const lastError = bridgeStatus?.last_error?.trim() || ''
  const benignNoPending = Boolean(lastError && BENIGN_NO_PENDING_ERROR_RE.test(lastError))
  const pending = bridgeStatus?.visible_pending_count ?? bridgeStatus?.pending_count ?? 0
  const backgroundPending = bridgeStatus?.background_pending_count ?? 0
  const latestReplyIsNewerThanStatus =
    dateMs(bridgeStatus?.last_response_at) > 0 && dateMs(bridgeStatus?.last_response_at) >= dateMs(bridgeStatus?.last_poll_at)
  const staleOrBackgroundOnlyError = pending === 0 && (backgroundPending > 0 || latestReplyIsNewerThanStatus)

  if (lastError && !benignNoPending && !staleOrBackgroundOnlyError) {
    return {
      detail: lastError,
      label: 'Jenny needs attention',
      tone: 'warn'
    }
  }

  if (bridgeStatus?.foreground_watch_running || WORKING_STATUSES.has(lastStatus)) {
    return {
      detail: 'Jenny is working on the latest project message.',
      label: 'Jenny working',
      tone: 'working'
    }
  }

  if (pending > 0) {
    return {
      detail: `${pending} message${pending === 1 ? '' : 's'} waiting for Jenny.`,
      label: 'Waiting for Jenny',
      tone: 'pending'
    }
  }

  if (REPLIED_STATUSES.has(lastStatus) || bridgeStatus?.last_response_at || bridgeStatus?.last_response_request_id) {
    return {
      detail: 'Jenny replied. Review the latest answer before relying on it.',
      label: 'Jenny replied',
      tone: 'ok'
    }
  }

  return {
    detail: benignNoPending ? 'No project message is waiting for Jenny.' : 'Ready for one bounded project message.',
    label: 'Jenny ready',
    tone: 'ok'
  }
}
