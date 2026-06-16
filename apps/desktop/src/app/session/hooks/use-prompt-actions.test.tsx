import type { AppendMessage } from '@assistant-ui/react'
import { cleanup, render } from '@testing-library/react'
import type { MutableRefObject } from 'react'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ChatMessage } from '@/lib/chat-messages'
import {
  $messages,
  $sessions,
  setAwaitingResponse,
  setBusy,
  setSelectedMissionControlProject,
  setSessions
} from '@/store/session'
import type { SessionInfo } from '@/types/hermes'

import { usePromptActions } from './use-prompt-actions'

vi.mock('@/hermes', () => ({
  getProfiles: vi.fn(async () => ({ profiles: [] })),
  setApiRequestProfile: vi.fn(),
  transcribeAudio: vi.fn()
}))

// The active id the desktop holds is the *runtime* session id from
// session.create — deliberately distinct from the stored DB id here, because
// that mismatch is the bug: the REST renameSession endpoint resolves against
// the stored sessions table and 404s on a runtime id. session.title accepts
// the runtime id directly.
const RUNTIME_SESSION_ID = 'rt-abc123'

function sessionInfo(overrides: Partial<SessionInfo> = {}): SessionInfo {
  return {
    ended_at: null,
    id: RUNTIME_SESSION_ID,
    input_tokens: 0,
    is_active: true,
    last_active: 0,
    message_count: 3,
    model: null,
    output_tokens: 0,
    preview: null,
    source: null,
    started_at: 0,
    title: 'Old title',
    tool_call_count: 0,
    ...overrides
  }
}

interface HarnessHandle {
  editMessage: (message: AppendMessage) => Promise<void>
  reloadFromMessage: (parentId: string | null) => Promise<void>
  submitText: (text: string) => Promise<boolean>
}

function Harness({
  initialMessages = [],
  onReady,
  onState,
  refreshSessions,
  requestGateway
}: {
  initialMessages?: ChatMessage[]
  onReady: (handle: HarnessHandle) => void
  onState?: (state: { messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }) => void
  refreshSessions: () => Promise<void>
  requestGateway: <T>(method: string, params?: Record<string, unknown>) => Promise<T>
}) {
  const activeSessionIdRef: MutableRefObject<string | null> = { current: RUNTIME_SESSION_ID }
  const selectedStoredSessionIdRef: MutableRefObject<string | null> = { current: RUNTIME_SESSION_ID }
  const busyRef = { current: false }
  let currentState = { messages: initialMessages, busy: false, awaitingResponse: false } as never

  const actions = usePromptActions({
    activeSessionId: RUNTIME_SESSION_ID,
    activeSessionIdRef,
    branchCurrentSession: async () => true,
    busyRef,
    createBackendSessionForSend: async () => RUNTIME_SESSION_ID,
    handleSkinCommand: () => '',
    refreshSessions,
    requestGateway,
    selectedStoredSessionIdRef,
    startFreshSessionDraft: () => undefined,
    sttEnabled: false,
    updateSessionState: (_sessionId, updater) => {
      const state = updater(currentState)
      currentState = state as never
      onState?.(state as { messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean })
      return state
    }
  })

  useEffect(() => {
    onReady({
      editMessage: actions.editMessage,
      reloadFromMessage: actions.reloadFromMessage,
      submitText: actions.submitText
    })
  }, [actions.editMessage, actions.reloadFromMessage, actions.submitText, onReady])

  return null
}

describe('usePromptActions /title', () => {
  beforeEach(() => {
    setSessions(() => [sessionInfo()])
    setBusy(false)
    setAwaitingResponse(false)
  })

  afterEach(() => {
    cleanup()
    $messages.set([])
    setBusy(false)
    setAwaitingResponse(false)
    vi.restoreAllMocks()
    setSelectedMissionControlProject(null)
  })

  it('renames via the session.title RPC (with the runtime id), updates the sidebar store, and refreshes', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) =>
      (method === 'session.title' ? { pending: false, title: 'New title' } : {}) as never
    )

    let handle: HarnessHandle | null = null
    render(<Harness onReady={h => (handle = h)} refreshSessions={refreshSessions} requestGateway={requestGateway} />)

    await handle!.submitText('/title New title')

    // Routes through session.title with the runtime session id — NOT the slash
    // worker (slash.exec) and NOT the REST endpoint. This is the path that
    // resolves the runtime id and persists reliably across platforms.
    expect(requestGateway).toHaveBeenCalledWith('session.title', {
      session_id: RUNTIME_SESSION_ID,
      title: 'New title'
    })
    expect(requestGateway).not.toHaveBeenCalledWith('slash.exec', expect.anything())
    expect(refreshSessions).toHaveBeenCalledTimes(1)
    expect($sessions.get()[0]?.title).toBe('New title')
  })

  it('reports the queued state when the session row is not persisted yet', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) =>
      (method === 'session.title' ? { pending: true, title: 'Fresh chat' } : {}) as never
    )

    let handle: HarnessHandle | null = null
    render(<Harness onReady={h => (handle = h)} refreshSessions={refreshSessions} requestGateway={requestGateway} />)

    await handle!.submitText('/title Fresh chat')

    expect(requestGateway).toHaveBeenCalledWith('session.title', {
      session_id: RUNTIME_SESSION_ID,
      title: 'Fresh chat'
    })
    // Even when queued, the sidebar reflects the chosen title optimistically.
    expect(refreshSessions).toHaveBeenCalledTimes(1)
    expect($sessions.get()[0]?.title).toBe('Fresh chat')
  })

  it('falls through to the slash worker for a bare /title (show current title)', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async () => ({ output: 'Title: Old title' }) as never)

    let handle: HarnessHandle | null = null
    render(<Harness onReady={h => (handle = h)} refreshSessions={refreshSessions} requestGateway={requestGateway} />)

    await handle!.submitText('/title')

    expect(requestGateway).not.toHaveBeenCalledWith('session.title', expect.anything())
    expect(requestGateway).toHaveBeenCalledWith('slash.exec', expect.objectContaining({ command: 'title' }))
  })

  it('surfaces a rename error without touching the sidebar store', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'session.title') {
        throw new Error('Title too long')
      }

      return {} as never
    })

    let handle: HarnessHandle | null = null
    render(<Harness onReady={h => (handle = h)} refreshSessions={refreshSessions} requestGateway={requestGateway} />)

    await handle!.submitText('/title way too long title')

    expect(requestGateway).toHaveBeenCalledWith('session.title', expect.objectContaining({ title: 'way too long title' }))
    expect(refreshSessions).not.toHaveBeenCalled()
    expect($sessions.get()[0]?.title).toBe('Old title')
  })
})

describe('usePromptActions project harness', () => {
  beforeEach(() => {
    setSessions(() => [sessionInfo()])
    $messages.set([])
    setBusy(false)
    setAwaitingResponse(false)
    setSelectedMissionControlProject(null)
  })

  afterEach(() => {
    cleanup()
    $messages.set([])
    setBusy(false)
    setAwaitingResponse(false)
    vi.restoreAllMocks()
    setSelectedMissionControlProject(null)
  })

  it('sends hidden project context without showing it in the user message bubble', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (_method: string, _params?: Record<string, unknown>) => ({}) as never)
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.submitText('test')

    expect(requestGateway).toHaveBeenCalledWith('prompt.submit', {
      session_id: RUNTIME_SESSION_ID,
      text: expect.stringContaining('Hidden Jenny OS project context:')
    })
    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { session_id: string; text: string }]
      | undefined
    const sentText = promptSubmitCall?.[1].text ?? ''
    expect(sentText).toContain('Project: Hermes / Mission Control')
    expect(sentText).toContain('Project ID: project-hermes-mission-control')
    expect(sentText).toContain('Challenge vague, risky, or wrong-approach requests')
    expect(sentText).toContain('answer ordinary chat naturally and concisely')
    expect(sentText).toContain('Do not turn simple tests, greetings, or casual questions into formal spec reviews')
    expect(sentText).toContain('give short Codex-style status updates')
    expect(sentText).toContain('do not echo this hidden project context')
    expect(sentText.trim().endsWith('test')).toBe(true)

    const optimisticUser = states.flatMap(state => state.messages).find(message => message.role === 'user')
    expect(optimisticUser?.parts).toEqual([{ type: 'text', text: 'test' }])
  })

  it('shows a concise chat error when Jenny cannot reach the gateway', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'prompt.submit') {
        throw new Error("Error invoking remote method 'hermes:api': Error: connect ECONNREFUSED 100.115.125.111:9119")
      }

      return {} as never
    })
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.submitText('test')

    const assistantError = states.flatMap(state => state.messages).findLast(message => message.role === 'assistant' && message.error)
    expect(assistantError?.error).toBe('Jenny cannot reach the Hermes gateway. Reconnect the gateway, then retry from this chat.')
    expect(assistantError?.error).not.toContain('ECONNREFUSED')
    expect(assistantError?.error).not.toContain('100.115.125.111')
  })

  it('shows a concise chat error when the guarded bridge payload is too large', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'prompt.submit') {
        throw new Error("Error invoking remote method 'hermes:api': Error: bridge field is too large")
      }

      return {} as never
    })
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.submitText('test')

    const assistantError = states.flatMap(state => state.messages).findLast(message => message.role === 'assistant' && message.error)
    expect(assistantError?.error).toBe('Jenny could not process that message because it was too large. Send one smaller task and try again.')
    expect(assistantError?.error).not.toContain('bridge field')
  })

  it('shows a plain chat error when Jenny times out before replying', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'prompt.submit') {
        throw new Error(
          "Error invoking remote method 'hermes:api': Error: codex app-server startup failed: codex app-server method 'initialize' timed out after 10.0s"
        )
      }

      return {} as never
    })
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.submitText('test')

    const assistantError = states.flatMap(state => state.messages).findLast(message => message.role === 'assistant' && message.error)
    expect(assistantError?.error).toBe('Jenny failed before finishing. Retry once; if it fails again, open details.')
    expect(assistantError?.error).not.toContain('timed out')
    expect(assistantError?.error).not.toContain('app-server')
    expect(assistantError?.error).not.toContain('audit console')
  })

  it('keeps hidden project context when regenerating a project chat reply', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')
    const initialMessages: ChatMessage[] = [
      { id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'recheck the plan' }] },
      { id: 'assistant-1', role: 'assistant', parts: [{ type: 'text', text: 'old reply' }] }
    ]
    $messages.set(initialMessages)

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (_method: string, _params?: Record<string, unknown>) => ({}) as never)

    let handle: HarnessHandle | null = null
    render(
      <Harness
        initialMessages={initialMessages}
        onReady={h => (handle = h)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.reloadFromMessage('assistant-1')

    expect(requestGateway).toHaveBeenCalledWith('prompt.submit', {
      session_id: RUNTIME_SESSION_ID,
      text: expect.stringContaining('Hidden Jenny OS project context:'),
      truncate_before_user_ordinal: 0
    })
    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { session_id: string; text: string; truncate_before_user_ordinal?: number }]
      | undefined
    expect(promptSubmitCall?.[1].text).toContain('Project: Hermes / Mission Control')
    expect(promptSubmitCall?.[1].text.trim().endsWith('recheck the plan')).toBe(true)
  })

  it('keeps hidden project context when editing and resending a project chat message', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')
    const initialMessages: ChatMessage[] = [
      { id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'old request' }] },
      { id: 'assistant-1', role: 'assistant', parts: [{ type: 'text', text: 'old reply' }] }
    ]
    $messages.set(initialMessages)

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (_method: string, _params?: Record<string, unknown>) => ({}) as never)

    let handle: HarnessHandle | null = null
    render(
      <Harness
        initialMessages={initialMessages}
        onReady={h => (handle = h)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.editMessage({
      content: [{ type: 'text', text: 'edited request' }],
      role: 'user',
      sourceId: 'user-1'
    } as unknown as AppendMessage)

    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { session_id: string; text: string; truncate_before_user_ordinal?: number }]
      | undefined
    expect(promptSubmitCall?.[1].text).toContain('Hidden Jenny OS project context:')
    expect(promptSubmitCall?.[1].text).toContain('Project: Hermes / Mission Control')
    expect(promptSubmitCall?.[1].text.trim().endsWith('edited request')).toBe(true)
  })
})
