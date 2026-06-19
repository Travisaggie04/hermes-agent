import { describe, expect, it } from 'vitest'

import { asyncAgentLiveSafetyReason } from './mission-control-live-flags'

describe('asyncAgentLiveSafetyReason', () => {
  it('allows status-only async-agent availability when live controls remain off', () => {
    expect(
      asyncAgentLiveSafetyReason({
        async_agent_controls_available: true,
        async_agent_controls_enabled: false,
        dispatch_enabled: false,
        execution_enabled: false,
        send_to_jenny_enabled: false,
        session_send_enabled: false,
        trusted_for_execution: false,
        worker_dispatch_enabled: false,
        worker_enabled: false
      })
    ).toBe('')
  })

  it('blocks presentation as ready when any live async-agent flag is enabled', () => {
    for (const flag of [
      'async_agent_controls_enabled',
      'dispatch_enabled',
      'execution_enabled',
      'send_to_jenny_enabled',
      'session_send_enabled',
      'worker_dispatch_enabled',
      'worker_enabled',
      'timer_enabled',
      'daemon_enabled',
      'model_routing_enabled',
      'trusted_for_execution'
    ] as const) {
      expect(asyncAgentLiveSafetyReason({ [flag]: true })).toBe('live async-agent controls are not confirmed off')
    }
  })
})
