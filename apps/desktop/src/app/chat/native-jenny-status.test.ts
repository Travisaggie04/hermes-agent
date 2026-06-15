import { describe, expect, it } from 'vitest'

import { nativeJennyStatus } from './native-jenny-status'

describe('nativeJennyStatus', () => {
  it('asks for a project before presenting Jenny as ready', () => {
    expect(nativeJennyStatus({ gatewayOpen: true }).label).toBe('Pick a project')
  })

  it('shows gateway offline before bridge status', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: false,
        projectId: 'project-hermes',
        bridgeStatus: { last_response_at: '2026-06-15T00:00:00Z' }
      })
    ).toMatchObject({ label: 'Gateway offline', tone: 'warn' })
  })

  it('surfaces bridge errors as Jenny attention', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_error: 'Hermes responder failed' }
      })
    ).toMatchObject({ label: 'Jenny needs attention', tone: 'warn' })
  })

  it('does not surface no-pending responder noops as scary errors', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: {
          last_error: 'no matching pending Mission Control mailbox request',
          last_status: 'hermes_answer_noop',
          pending_count: 0,
          visible_pending_count: 0
        }
      })
    ).toMatchObject({
      detail: 'No project message is waiting for Jenny.',
      label: 'Jenny ready',
      tone: 'ok'
    })
  })

  it('shows Jenny working while the manual Hermes answer is running', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_status: 'hermes_answer_started', pending_count: 1, visible_pending_count: 1 }
      })
    ).toMatchObject({
      detail: 'Jenny is working on the latest project message.',
      label: 'Jenny working',
      tone: 'working'
    })
  })

  it('prioritizes visible pending messages', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { pending_count: 9, visible_pending_count: 2 }
      })
    ).toMatchObject({ detail: '2 messages waiting for Jenny.', label: 'Waiting for Jenny', tone: 'pending' })
  })

  it('shows reviewed-ready status after a reply when nothing is pending', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_response_request_id: 'req-1', pending_count: 0 }
      })
    ).toMatchObject({ label: 'Jenny replied', tone: 'ok' })
  })
})
