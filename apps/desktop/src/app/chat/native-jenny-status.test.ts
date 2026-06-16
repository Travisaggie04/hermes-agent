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
      summary: 'Background status unavailable',
      tone: 'ok'
    })
  })

  it('surfaces bridge record errors as Jenny attention', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_error: 'Hermes responder failed' }
      })
    ).toMatchObject({ detail: 'Hermes responder failed', label: 'Jenny needs attention', summary: 'Check details and retry', tone: 'warn' })
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
    ).toMatchObject({ label: 'Jenny ready', summary: 'Ready', tone: 'ok' })
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
      summary: 'Ready',
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
      summary: 'Working',
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
      summary: 'Working',
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
    ).toMatchObject({ detail: '2 messages waiting for Jenny.', label: 'Waiting for Jenny', summary: '2 waiting', tone: 'pending' })
  })

  it('shows reviewed-ready status after a reply when nothing is pending', () => {
    expect(
      nativeJennyStatus({
        gatewayOpen: true,
        projectId: 'project-hermes',
        bridgeStatus: { last_response_request_id: 'req-1', pending_count: 0 }
      })
    ).toMatchObject({ label: 'Jenny replied', summary: 'Reply ready', tone: 'ok' })
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
      summary: 'Ready',
      tone: 'ok'
    })
  })
})
