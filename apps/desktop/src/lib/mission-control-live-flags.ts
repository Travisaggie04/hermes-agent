import type { MissionControlAsyncAgentStatusResponse } from '@/hermes'

const ASYNC_AGENT_LIVE_FLAGS: Array<keyof MissionControlAsyncAgentStatusResponse> = [
  'async_agent_controls_enabled',
  'would_dispatch',
  'would_execute',
  'would_session_send',
  'dispatch_enabled',
  'dispatch_in_gateway',
  'dispatch_state',
  'execution_enabled',
  'execution_ready',
  'live_operations_enabled',
  'send_to_jenny_enabled',
  'session_send_enabled',
  'worker_dispatch_enabled',
  'worker_enabled',
  'workers_enabled',
  'timer_enabled',
  'daemon_enabled',
  'model_routing_enabled',
  'payment_enabled',
  'queue_mutation_enabled',
  'social_enabled',
  'waha_enabled',
  'trusted_for_execution'
]

export function asyncAgentLiveSafetyReason(status?: MissionControlAsyncAgentStatusResponse | null): string {
  if (!status) {
    return ''
  }

  return ASYNC_AGENT_LIVE_FLAGS.some(flag => asyncAgentLiveFlagEnabled(status[flag]))
    ? 'live async-agent controls are not confirmed off'
    : ''
}

export function asyncAgentLiveFlagEnabled(value: unknown): boolean {
  if (value === true) {
    return true
  }

  if (typeof value === 'number') {
    return value !== 0
  }

  if (typeof value === 'string') {
    return ['1', 'true', 'yes', 'y', 'on', 'enabled'].includes(value.trim().toLowerCase())
  }

  return false
}
