import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

describe('Agents activity overlay', () => {
  it('shows Jenny async and delegation readiness without adding execution controls', () => {
    expect(source).toContain('function JennyActivityReadiness')
    expect(source).toContain('getMissionControlAsyncAgentStatus')
    expect(source).toContain("queryKey: ['mission-control-async-agent-status']")
    expect(source).toContain("import { asyncAgentLiveFlagEnabled, asyncAgentLiveSafetyReason } from '@/lib/mission-control-live-flags'")
    expect(source).toContain('const safetyReason = asyncAgentLiveSafetyReason(status)')
    expect(source).toContain('Jenny activity safety check')
    expect(source).toContain('This panel stays status-only and does not start workers.')
    expect(source).toContain('Async agents available')
    expect(source).toContain('Delegation activity available')
    expect(source).toContain('Native async-agent controls are not active in this runtime yet.')
    expect(source).toContain('Starts and steering remain approval-gated.')
    expect(source).not.toContain('Run async agent')
    expect(source).not.toContain('Start async agent')
    expect(source).not.toContain('Spawn async agent')
  })

  it('keeps protected execution flags visible as status only', () => {
    expect(source).toContain("['Would execute', asyncAgentLiveFlagEnabled(status?.would_execute) ? 'on' : 'off']")
    expect(source).toContain("['Execution', asyncAgentLiveFlagEnabled(status?.execution_enabled) ? 'on' : 'off']")
    expect(source).toContain("['Dispatch', asyncAgentLiveFlagEnabled(status?.dispatch_enabled) ? 'on' : 'off']")
    expect(source).toContain("['Worker', asyncAgentLiveFlagEnabled(status?.worker_enabled) ? 'on' : 'off']")
    expect(source).toContain("['Timer', asyncAgentLiveFlagEnabled(status?.timer_enabled) ? 'on' : 'off']")
  })
})
