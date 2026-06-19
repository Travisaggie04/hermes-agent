import { describe, expect, it } from 'vitest'

import { nativeJennyStatus } from './native-jenny-status'

const TRANSPORT_WORDING_RE = /bridge|mailbox|mission control status|audit console/i
const SECOND_ACTION_WORDING_RE = /get response|run jenny|ask jenny|queue for jenny|tap run|click run/i
const NOW_MS = Date.parse('2026-06-16T20:00:00Z')
const RECENT_STATUS_AT = '2026-06-16T19:59:45Z'
const STALE_STATUS_AT = '2026-06-16T19:58:00Z'

function expectCleanVisibleStatus(status: ReturnType<typeof nativeJennyStatus>) {
  expect(status.detail).not.toMatch(TRANSPORT_WORDING_RE)
  expect(status.label).not.toMatch(TRANSPORT_WORDING_RE)
  expect(status.summary).not.toMatch(TRANSPORT_WORDING_RE)
  expect(status.detail).not.toMatch(SECOND_ACTION_WORDING_RE)
  expect(status.label).not.toMatch(SECOND_ACTION_WORDING_RE)
  expect(status.summary).not.toMatch(SECOND_ACTION_WORDING_RE)
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

  it('warns when Jenny project manual controls are not confirmed', () => {
    const status = nativeJennyStatus({
      bridgeStatus: { manual_start_only: false, pending_count: 0, visible_pending_count: 0 },
      gatewayOpen: true,
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: 'Jenny project safety check needs attention because manual controls are not confirmed. Normal chat can continue, but project automation must stay off until reviewed.',
      label: 'Jenny safety check',
      summary: 'Review safety check',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
  })

  it('warns before normal ready or queued states when live automation flags are present', () => {
    const status = nativeJennyStatus({
      bridgeStatus: {
        last_status: 'hermes_answer_completed',
        manual_start_only: true,
        pending_count: 0,
        visible_pending_count: 0,
        would_execute: true
      },
      gatewayOpen: true,
      projectId: 'project-hermes',
      replyAttemptStatus: 'queued'
    })

    expect(status).toMatchObject({
      detail: 'Jenny project safety check needs attention because live automation controls are not confirmed off. Normal chat can continue, but project automation must stay off until reviewed.',
      label: 'Jenny safety check',
      summary: 'Review safety check',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
  })

  it('treats send-to-Jenny bridge status as unsafe for native project automation', () => {
    const status = nativeJennyStatus({
      bridgeStatus: {
        manual_start_only: true,
        pending_count: 0,
        send_to_jenny_enabled: true,
        visible_pending_count: 0
      },
      gatewayOpen: true,
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: 'Jenny project safety check needs attention because live automation controls are not confirmed off. Normal chat can continue, but project automation must stay off until reviewed.',
      label: 'Jenny safety check',
      summary: 'Review safety check',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
  })

  it('treats malformed truthy bridge automation flags as unsafe', () => {
    const status = nativeJennyStatus({
      bridgeStatus: {
        manual_start_only: true,
        pending_count: 0,
        visible_pending_count: 0,
        worker_dispatch_enabled: 1 as unknown as boolean
      },
      gatewayOpen: true,
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: 'Jenny project safety check needs attention because live automation controls are not confirmed off. Normal chat can continue, but project automation must stay off until reviewed.',
      label: 'Jenny safety check',
      summary: 'Review safety check',
      tone: 'warn'
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
      nowMs: NOW_MS,
      bridgeStatus: {
        last_poll_at: RECENT_STATUS_AT,
        last_status: 'hermes_answer_started',
        pending_count: 1,
        visible_pending_count: 1
      }
    })

    expect(status).toMatchObject({
      detail: 'Jenny is working on the latest project message. Progress appears in this chat.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
    expectCleanVisibleStatus(status)
  })

  it('does not show stale answer-started records as active work', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      nowMs: NOW_MS,
      bridgeStatus: {
        last_poll_at: STALE_STATUS_AT,
        last_status: 'hermes_answer_started',
        pending_count: 1,
        visible_pending_count: 1
      }
    })

    expect(status).toMatchObject({
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
    })
    expectCleanVisibleStatus(status)
  })

  it('does not show stale completed watch polls as active work', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      nowMs: NOW_MS,
      bridgeStatus: {
        foreground_watch_running: true,
        last_poll_at: STALE_STATUS_AT,
        last_status: 'watch_poll_completed',
        pending_count: 0,
        visible_pending_count: 0
      }
    })

    expect(status).toMatchObject({
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
    })
    expectCleanVisibleStatus(status)
  })

  it('uses explicit native reply attempts before inferred running state', () => {
    expect(
      nativeJennyStatus({
        activeTurnRunning: true,
        awaitingResponse: false,
        gatewayOpen: true,
        projectId: 'project-hermes',
        replyAttemptStatus: 'queued'
      })
    ).toMatchObject({
      detail: 'Your message was sent. Jenny will reply here.',
      label: 'Jenny queued',
      summary: 'Waiting for Jenny',
      tone: 'pending'
    })

    expect(
      nativeJennyStatus({
        activeTurnRunning: false,
        gatewayOpen: true,
        projectId: 'project-hermes',
        replyAttemptStatus: 'working'
      })
    ).toMatchObject({
      detail: 'Jenny is working. Progress and the final reply appear here.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
  })

  it('uses explicit native reply completion before stale bridge status', () => {
    expect(
      nativeJennyStatus({
        bridgeStatus: { last_error: 'stale bridge field is too large' },
        gatewayOpen: true,
        projectId: 'project-hermes',
        replyAttemptStatus: 'replied'
      })
    ).toMatchObject({
      detail: 'Jenny replied. Review the latest answer before relying on it.',
      label: 'Jenny replied',
      summary: 'Review latest reply',
      tone: 'ok'
    })
  })

  it('uses explicit native reply failure before stale bridge status', () => {
    const status = nativeJennyStatus({
      bridgeStatus: {
        last_response_at: '2026-06-16T19:59:55Z',
        last_response_request_id: 'old-reply',
        last_status: 'replied',
        pending_count: 0,
        visible_pending_count: 0
      },
      gatewayOpen: true,
      latestChatReplied: true,
      projectId: 'project-hermes',
      replyAttemptError: 'Error invoking remote method: Error: app-server startup failed',
      replyAttemptStatus: 'failed'
    })

    expect(status).toMatchObject({
      detail: 'Jenny failed before finishing a reply. Retry once, and open details if it fails again.',
      label: 'Jenny failed',
      summary: 'Retry available',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
  })

  it('shows a fresh foreground watch poll as active work', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      nowMs: NOW_MS,
      bridgeStatus: {
        foreground_watch_running: true,
        last_poll_at: RECENT_STATUS_AT,
        last_status: 'watch_poll_completed',
        pending_count: 0,
        visible_pending_count: 0
      }
    })

    expect(status).toMatchObject({
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
    expectCleanVisibleStatus(status)
  })

  it('shows Jenny queued while native chat is waiting for the first reply update', () => {
    expect(
      nativeJennyStatus({
        activeTurnRunning: true,
        awaitingResponse: true,
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { pending_count: 0, visible_pending_count: 0 }
      })
    ).toMatchObject({
      detail: 'Your message was sent. Jenny will reply here.',
      label: 'Jenny queued',
      summary: 'Waiting for Jenny',
      tone: 'pending'
    })
  })

  it('shows Jenny working while the active native chat turn is running after the first reply update', () => {
    expect(
      nativeJennyStatus({
        activeTurnRunning: true,
        awaitingResponse: false,
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { pending_count: 0, visible_pending_count: 0 }
      })
    ).toMatchObject({
      detail: 'Jenny is working. Progress and the final reply appear here.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
  })

  it('shows Jenny working while native subagents are active even if the main turn is quiet', () => {
    const status = nativeJennyStatus({
      bridgeStatus: { pending_count: 0, visible_pending_count: 0 },
      gatewayOpen: true,
      liveSubagentCount: 2,
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: '2 Jenny subtasks are running. Progress and the final reply appear here.',
      label: 'Jenny working',
      summary: 'Progress appears here',
      tone: 'working'
    })
    expectCleanVisibleStatus(status)
  })

  it('lets the latest native chat error drive the status before background bridge records', () => {
    const status = nativeJennyStatus({
      bridgeStatus: {
        last_response_at: '2026-06-16T19:59:55Z',
        last_response_request_id: 'old-reply',
        last_status: 'replied',
        pending_count: 0,
        visible_pending_count: 0
      },
      gatewayOpen: true,
      latestChatError: 'Error invoking remote method: Error: app-server startup failed',
      projectId: 'project-hermes'
    })

    expect(status).toMatchObject({
      detail: 'Jenny failed before finishing a reply. Retry once, and open details if it fails again.',
      label: 'Jenny failed',
      summary: 'Retry available',
      tone: 'warn'
    })
    expectCleanVisibleStatus(status)
  })

  it('does not let older queued project messages block normal native chat', () => {
    const status = nativeJennyStatus({
      gatewayOpen: true,
      projectId: 'project-hermes',
      bridgeStatus: { pending_count: 9, visible_pending_count: 2 }
    })

    expect(status).toMatchObject({
      detail: 'Jenny has 2 older queued project messages, but this chat is ready. Send a message here and Jenny will reply in this project chat.',
      label: 'Jenny ready',
      summary: 'Send a message',
      tone: 'ok'
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

  it('shows reviewed-ready status from the latest native chat reply before background bridge records', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        latestChatReplied: true,
        projectId: 'project-hermes',
        bridgeStatus: {
          last_error: 'stale bridge field is too large',
          pending_count: 0,
          visible_pending_count: 0
        }
      })
    ).toMatchObject({
      detail: 'Jenny replied. Review the latest answer before relying on it.',
      label: 'Jenny replied',
      summary: 'Review latest reply',
      tone: 'ok'
    })
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
