import { QueryClient } from '@tanstack/react-query'
import { act, cleanup, render } from '@testing-library/react'
import type { MutableRefObject } from 'react'
import { useEffect, useRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChatMessage } from '@/lib/chat-messages'
import type { RpcEvent } from '@/types/hermes'

import type { ClientSessionState } from '../../types'

import { useMessageStream } from './use-message-stream'

vi.mock('@/lib/haptics', () => ({
  triggerHaptic: vi.fn()
}))

const SESSION_ID = 'session-usage-1'

interface HarnessHandle {
  handleGatewayEvent: (event: RpcEvent) => void
}

function baseState(): ClientSessionState {
  return {
    awaitingResponse: true,
    branch: '',
    busy: true,
    cwd: '',
    interrupted: false,
    messages: [
      {
        id: 'assistant-stream-1',
        pending: true,
        parts: [{ type: 'text', text: 'partial' }],
        role: 'assistant'
      } satisfies ChatMessage
    ],
    needsInput: false,
    pendingBranchGroup: null,
    sawAssistantPayload: true,
    storedSessionId: SESSION_ID,
    streamId: 'assistant-stream-1'
  }
}

function Harness({ onReady, onState }: { onReady: (handle: HarnessHandle) => void; onState: (state: ClientSessionState) => void }) {
  const activeSessionIdRef: MutableRefObject<string | null> = { current: SESSION_ID }
  const currentStateRef = useRef(baseState())

  const stream = useMessageStream({
    activeSessionIdRef,
    hydrateFromStoredSession: vi.fn(async () => undefined),
    queryClient: new QueryClient(),
    refreshHermesConfig: vi.fn(async () => undefined),
    refreshSessions: vi.fn(async () => undefined),
    updateSessionState: (_sessionId, updater) => {
      currentStateRef.current = updater(currentStateRef.current)
      onState(currentStateRef.current)

      return currentStateRef.current
    }
  })

  useEffect(() => {
    onReady({ handleGatewayEvent: stream.handleGatewayEvent })
  }, [onReady, stream.handleGatewayEvent])

  return null
}

describe('useMessageStream usage metadata', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('stores per-turn usage from message.complete instead of cumulative session usage', () => {
    const states: ClientSessionState[] = []
    let handle: HarnessHandle | null = null

    render(
      <Harness
        onReady={nextHandle => {
          handle = nextHandle
        }}
        onState={state => states.push(state)}
      />
    )

    act(() => {
      handle!.handleGatewayEvent({
        payload: {
          text: 'done',
          turn_usage: { calls: 1, input: 35, output: 10, total: 45 },
          usage: { calls: 7, input: 10_000, output: 2_000, total: 12_000 }
        },
        session_id: SESSION_ID,
        type: 'message.complete'
      })
    })

    const completed = states.at(-1)?.messages[0]

    expect(completed?.pending).toBe(false)
    expect(completed?.usage).toEqual({ calls: 1, input: 35, output: 10, total: 45 })
    expect(completed?.parts).toEqual([{ type: 'text', text: 'done' }])
  })
})
