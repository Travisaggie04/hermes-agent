import { describe, expect, it } from 'vitest'

import { nativeJennyStatus } from './native-jenny-status'

const TRANSPORT_WORDING_RE = /bridge|mailbox|mission control status|audit console/i

function expectCleanVisibleStatus(status: ReturnType<typeof nativeJennyStatus>) {
  expect(status.detail).not.toMatch(TRANSPORT_WORDING_RE)
  expect(status.label).not.toMatch(TRANSPORT_WORDING_RE)
  expect(status.summary).not.toMatch(TRANSPORT_WORDING_RE)
}

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
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      queryError: new Error('connect ECONNREFUSED 100.115.125.111:9119')
    })

    expect(status).toMatchObject({
      detail: 'Send a message here; Jenny will reply in this project chat. Background status is unavailable.',
      label: 'Jenny ready',
      summary: 'Chat still works',
      tone: 'ok'
    })
    expectCleanVisibleStatus(status)
  })

  it('summarizes bridge record errors as Jenny attention without raw backend wording', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { last_error: 'Hermes responder failed' }
    })

    expect(status).toMatchObject({
      detail: 'Jenny failed before finishing a reply. Retry once, and open details if it fails again.',
      label: 'Jenny needs attention',
      summary: 'Check details and retry',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
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
    expectCleanVisibleStatus(status)
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
    expectCleanVisibleStatus(status)
  })

  it('maps unknown backend errors to plain chat language', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { last_error: 'unclassified transport failure' }
    })

    expect(status).toMatchObject({
      detail: 'Jenny had trouble finishing that message. Retry once, or open details.',
      label: 'Jenny needs attention',
      summary: 'Check details and retry',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
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
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { last_status: 'hermes_answer_started', pending_count: 1, visible_pending_count: 1 }
    })

    expect(status).toMatchObject({
      detail: 'Jenny is working on the latest project message.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
    expectCleanVisibleStatus(status)
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
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { pending_count: 9, visible_pending_count: 2 }
    })

    expect(status).toMatchObject({
      detail: 'Jenny has 2 messages waiting. The reply will appear in this chat.',
      label: 'Waiting for Jenny',
      summary: 'Reply will appear here',
      tone: 'pending'
    })
    expectCleanVisibleStatus(status)
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
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { pending_count: 0, visible_pending_count: 0 }
    })

    expect(status).toMatchObject({
      detail: 'Send a message here; Jenny will reply in this project chat.',
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
    })
    expectCleanVisibleStatus(status)
  })

  it('uses plain Jenny wording while status is loading', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      loading: true,
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: 'Checking Jenny.',
      label: 'Checking Jenny',
      summary: 'Checking',
      tone: 'idle'
    })
    expectCleanVisibleStatus(status)
  })
})
