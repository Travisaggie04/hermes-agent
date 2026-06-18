import type { AppendMessage } from '@assistant-ui/react'
import { cleanup, render, waitFor } from '@testing-library/react'
import type { MutableRefObject } from 'react'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createMissionControlSessionProjectLink } from '@/hermes'
import { type ChatMessage, chatMessageText } from '@/lib/chat-messages'
import { $notifications, clearNotifications } from '@/store/notifications'
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
  createMissionControlSessionProjectLink: vi.fn(async () => ({ ok: true })),
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
    clearNotifications()
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
      hidden_context: expect.stringContaining('Hidden Jenny OS project context:'),
      text: 'test'
    })
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith({
      cwd_snapshot: undefined,
      link_method: 'manual',
      linked_by: 'desktop',
      profile: undefined,
      project_id: 'project-hermes-mission-control',
      session_id: RUNTIME_SESSION_ID,
      source: 'desktop-native-chat',
      status: 'active',
      title_snapshot: 'test'
    })
    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { hidden_context?: string; session_id: string; text: string }]
      | undefined
    const sentText = promptSubmitCall?.[1].text ?? ''
    const hiddenContext = promptSubmitCall?.[1].hidden_context ?? ''
    expect(sentText).toBe('test')
    expect(sentText).not.toContain('Hidden Jenny OS project context:')
    expect(sentText).not.toContain('Project: Hermes / Mission Control')
    expect(hiddenContext).toContain('Project: Hermes / Mission Control')
    expect(hiddenContext).toContain('Project ID: project-hermes-mission-control')
    expect(hiddenContext).toContain('Challenge vague, risky, or wrong-approach requests')
    expect(hiddenContext).toContain('answer ordinary chat naturally and concisely')
    expect(hiddenContext).toContain('Do not turn simple tests, greetings, or casual questions into formal spec reviews')
    expect(hiddenContext).toContain('give short Codex-style status updates')
    expect(hiddenContext).toContain('Action policy: jenny_os_action_policy_v1.')
    expect(hiddenContext).toContain('ASK before:')
    expect(hiddenContext).toContain('gateway restart or gateway runtime switch')
    expect(hiddenContext).toContain('Goal loop: jenny_os_goal_loop_v1.')
    expect(hiddenContext).toContain('resume from the latest checkpoint after compaction, restart, or tool-call limits')
    expect(hiddenContext).toContain('do not mark work complete until every explicit requirement has evidence')
    expect(hiddenContext).toContain('Reports:')
    expect(hiddenContext).toContain('Complete only when:')
    expect(hiddenContext).toContain('Blocked only when:')
    expect(hiddenContext).toContain('map every explicit requirement to current evidence')
    expect(hiddenContext).toContain('name the exact missing input, failing command, or external dependency')
    expect(hiddenContext).not.toContain('Forbidden without separate explicit approval:')
    expect(hiddenContext).toContain('do not echo this hidden project context')

    const optimisticUser = states.flatMap(state => state.messages).find(message => message.role === 'user')
    expect(optimisticUser?.parts).toEqual([{ type: 'text', text: 'test' }])
  })

  it('queues one automatic Jenny reply request from normal project chat send', async () => {
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

    expect(requestGateway).toHaveBeenCalledTimes(1)
    expect(requestGateway).toHaveBeenCalledWith('prompt.submit', {
      session_id: RUNTIME_SESSION_ID,
      hidden_context: expect.stringContaining('Hidden Jenny OS project context:'),
      text: 'test'
    })

    const latestState = states[states.length - 1]

    expect(latestState).toMatchObject({
      busy: true,
      awaitingResponse: true
    })
    expect(latestState.messages.map(chatMessageText)).toEqual(['test'])
  })

  it('does not block Jenny replies if background project filing fails', async () => {
    setSelectedMissionControlProject('project-tool-tally', 'Tool & Tally')
    vi.mocked(createMissionControlSessionProjectLink).mockRejectedValueOnce(new Error('record store unavailable'))

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (_method: string, _params?: Record<string, unknown>) => ({}) as never)

    let handle: HarnessHandle | null = null
    render(<Harness onReady={h => (handle = h)} refreshSessions={refreshSessions} requestGateway={requestGateway} />)

    await handle!.submitText('keep going')

    expect(createMissionControlSessionProjectLink).toHaveBeenCalled()
    expect(requestGateway).toHaveBeenCalledWith('prompt.submit', {
      session_id: RUNTIME_SESSION_ID,
      hidden_context: expect.stringContaining('Project: Tool & Tally'),
      text: expect.stringContaining('keep going')
    })
    await waitFor(() => {
      expect($notifications.get()[0]).toMatchObject({
        kind: 'warning',
        message: 'Jenny can still reply. This chat may appear in Other chats instead of Tool & Tally.',
        title: 'Chat not filed yet'
      })
    })
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

  it('starts /goal without rendering the engineering kickoff as Travis visible text', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'slash.exec') {
        throw new Error('route through command.dispatch')
      }

      if (method === 'command.dispatch') {
        return {
          type: 'send',
          notice: 'Goal set (20-turn budget): Make Jenny reliable.',
          message: [
            '[Engineering goal kickoff]',
            'Objective:',
            'Make Jenny reliable.',
            '',
            'Operate as a senior engineering agent. Before broad implementation, turn this objective into a short working contract:',
            '- objective in plain English',
            '- evidence required to prove completion'
          ].join('\n')
        } as never
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

    await handle!.submitText('/goal Make Jenny reliable.')

    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { session_id: string; text: string }]
      | undefined
    expect(promptSubmitCall?.[1].text).toContain('[Engineering goal kickoff]')
    expect(promptSubmitCall?.[1].text).toContain('Objective:\nMake Jenny reliable.')

    const allMessages = states.flatMap(state => state.messages)
    expect(allMessages.filter(message => message.role === 'user')).toHaveLength(0)
    expect(allMessages.some(message => message.role === 'system' && chatMessageText(message).includes('Goal set'))).toBe(true)
    expect(allMessages.map(chatMessageText).join('\n')).not.toContain('Operate as a senior engineering agent')
  })

  it('shows the typed slash command instead of expanded send payloads', async () => {
    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async (method: string) => {
      if (method === 'slash.exec') {
        throw new Error('route through command.dispatch')
      }

      if (method === 'command.dispatch') {
        return {
          type: 'send',
          message:
            'Spec-first request for Jenny: Project: Hermes / Mission Control Request Travis is considering: test Current intake: Spec first. Allowed: read approved context. Forbidden: no direct session send.'
        } as never
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

    await handle!.submitText('/queue test')

    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { session_id: string; text: string }]
      | undefined
    expect(promptSubmitCall?.[1].text).toContain('Spec-first request for Jenny:')
    expect(promptSubmitCall?.[1].text).toContain('Request Travis is considering: test')

    const optimisticUser = states.flatMap(state => state.messages).find(message => message.role === 'user')
    expect(chatMessageText(optimisticUser!)).toBe('/queue test')
    expect(chatMessageText(optimisticUser!)).not.toContain('Spec-first request for Jenny')
    expect(chatMessageText(optimisticUser!)).not.toContain('Allowed: read approved context')
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
      hidden_context: expect.stringContaining('Hidden Jenny OS project context:'),
      text: 'recheck the plan',
      truncate_before_user_ordinal: 0
    })
    const promptSubmitCall = requestGateway.mock.calls.find(call => call[0] === 'prompt.submit') as
      | [string, { hidden_context?: string; session_id: string; text: string; truncate_before_user_ordinal?: number }]
      | undefined
    expect(promptSubmitCall?.[1].text).toBe('recheck the plan')
    expect(promptSubmitCall?.[1].hidden_context).toContain('Project: Hermes / Mission Control')
  })

  it('shows a chat retry error when regenerating a project reply fails', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')
    const initialMessages: ChatMessage[] = [
      { id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'recheck the plan' }] },
      { id: 'assistant-1', role: 'assistant', parts: [{ type: 'text', text: 'old reply' }] }
    ]
    $messages.set(initialMessages)

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async () => {
      throw new Error("Error invoking remote method 'hermes:api': Error: bridge field is too large")
    })
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        initialMessages={initialMessages}
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.reloadFromMessage('assistant-1')

    const assistantError = states.flatMap(state => state.messages).findLast(message => message.role === 'assistant' && message.error)
    expect(assistantError?.error).toBe('Jenny could not process that message because it was too large. Send one smaller task and try again.')
    expect(assistantError?.error).not.toContain('bridge field')
    expect(assistantError?.branchGroupId).toBe('branch:user-1')
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
      | [string, { hidden_context?: string; session_id: string; text: string; truncate_before_user_ordinal?: number }]
      | undefined
    expect(promptSubmitCall?.[1].text).toBe('edited request')
    expect(promptSubmitCall?.[1].hidden_context).toContain('Hidden Jenny OS project context:')
    expect(promptSubmitCall?.[1].hidden_context).toContain('Project: Hermes / Mission Control')
  })

  it('shows a chat retry error when editing and resending fails', async () => {
    setSelectedMissionControlProject('project-hermes-mission-control', 'Hermes / Mission Control')
    const initialMessages: ChatMessage[] = [
      { id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'old request' }] },
      { id: 'assistant-1', role: 'assistant', parts: [{ type: 'text', text: 'old reply' }] }
    ]
    $messages.set(initialMessages)

    const refreshSessions = vi.fn(async () => undefined)
    const requestGateway = vi.fn(async () => {
      throw new Error("Error invoking remote method 'hermes:api': Error: codex app-server startup failed")
    })
    const states: Array<{ messages: ChatMessage[]; busy: boolean; awaitingResponse: boolean }> = []

    let handle: HarnessHandle | null = null
    render(
      <Harness
        initialMessages={initialMessages}
        onReady={h => (handle = h)}
        onState={state => states.push(state)}
        refreshSessions={refreshSessions}
        requestGateway={requestGateway}
      />
    )

    await handle!.editMessage({
      content: [{ type: 'text', text: 'edited request' }],
      role: 'user',
      sourceId: 'user-1'
    } as unknown as AppendMessage)

    const assistantError = states.flatMap(state => state.messages).findLast(message => message.role === 'assistant' && message.error)
    expect(assistantError?.error).toBe('Jenny failed before finishing. Retry once; if it fails again, open details.')
    expect(assistantError?.error).not.toContain('app-server')
  })
})
