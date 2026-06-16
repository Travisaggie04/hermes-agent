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

  it('keeps native chat usable when only background bridge status is unavailable', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        queryError: new Error('connect ECONNREFUSED 100.115.125.111:9119')
      })
    ).toMatchObject({
      detail: 'Send a message here; Jenny will reply in this project chat. Background Mission Control status is unavailable.',
      label: 'Jenny ready',
      summary: 'Chat still works',
      tone: 'ok'
    })
  })

  it('summarizes bridge record errors as Jenny attention without raw backend wording', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_error: 'Hermes responder failed' }
      })
    ).toMatchObject({
      detail: 'Jenny failed before finishing a reply. Retry once, and review the audit console if it fails again.',
      label: 'Jenny needs attention',
      summary: 'Check details and retry',
      tone: 'warn'
    })
  })

  it('turns bridge size failures into an actionable native chat message', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { last_error: 'bridge field is too large' }
    })

    expect(status).toMatchObject({
      detail: 'Jenny could not process that message because it was too large. Send a shorter request or split it into one smaller task.',
      label: 'Jenny needs attention',
      tone: 'warn'
    })
    expect(status.detail).not.toContain('bridge field')
  })

  it('turns gateway connection failures into an actionable native chat message', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { last_error: 'Error invoking remote method: connect ECONNREFUSED 100.115.125.111:9119' }
    })

    expect(status).toMatchObject({
      detail: 'Jenny could not reach the Hermes gateway. Check the gateway connection, then retry from this chat.',
      label: 'Jenny needs attention',
      tone: 'warn'
    })
    expect(status.detail).not.toContain('ECONNREFUSED')
  })

  it('does not let background-only bridge errors dominate the native chat status', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: {
          background_pending_count: 3,
          last_error: 'bridge field is too large',
          pending_count: 3,
          visible_pending_count: 0
        }
      })
    ).toMatchObject({ label: 'Jenny ready', summary: 'Send a message', tone: 'ok' })
  })

  it('does not surface stale bridge errors after a newer Jenny reply', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: {
          last_error: 'old bridge error',
          last_poll_at: '2026-06-15T00:00:00Z',
          last_response_at: '2026-06-15T00:00:05Z',
          last_response_request_id: 'req-1',
          pending_count: 0,
          visible_pending_count: 0
        }
      })
    ).toMatchObject({ label: 'Jenny replied', tone: 'ok' })
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
      summary: 'Send a message',
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
      summary: 'Progress appears here',
      tone: 'working'
    })
  })

  it('shows Jenny working while the active native chat turn is running', () => {
    expect(
      nativeJennyStatus({
        activeTurnRunning: true,
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { pending_count: 0, visible_pending_count: 0 }
      })
    ).toMatchObject({
      detail: 'Jenny is working on this chat. Progress and the final reply appear here.',
      label: 'Jenny working',
      summary: 'Progress appears here',
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
    ).toMatchObject({
      detail: 'Jenny has 2 messages waiting. The reply will appear in this chat.',
      label: 'Waiting for Jenny',
      summary: 'Reply will appear here',
      tone: 'pending'
    })
  })

  it('shows reviewed-ready status after a reply when nothing is pending', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_response_request_id: 'req-1', pending_count: 0 }
      })
    ).toMatchObject({ label: 'Jenny replied', summary: 'Review latest reply', tone: 'ok' })
  })

  it('makes the ready state explain that normal chat sends to Jenny', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { pending_count: 0, visible_pending_count: 0 }
      })
    ).toMatchObject({
      detail: 'Send a message here; Jenny will reply in this project chat.',
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
    })
  })
})
