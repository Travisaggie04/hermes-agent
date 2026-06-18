import { describe, expect, it } from 'vitest'

import type { ChatMessage } from '@/lib/chat-messages'

import {
  latestNativeJennyReplyAttempt,
  setNativeJennyReplyAttemptForUser,
  updateLatestNativeJennyReplyAttempt,
  withNativeJennyReplyAttempt
} from './native-jenny-reply-loop'

const user = (id: string, text = id): ChatMessage => ({
  id,
  role: 'user',
  parts: [{ type: 'text', text }]
})

const assistant = (id: string, text = id): ChatMessage => ({
  id,
  role: 'assistant',
  parts: [{ type: 'text', text }]
})

describe('native Jenny reply loop helpers', () => {
  it('marks user messages with an out-of-band queued reply attempt', () => {
    const marked = withNativeJennyReplyAttempt(user('u1', 'test'), 'queued', undefined, 100)

    expect(marked.nativeJennyReplyAttempt).toEqual({ status: 'queued', updatedAt: 100 })
    expect(marked.parts).toEqual([{ type: 'text', text: 'test' }])
  })

  it('reads the latest marked user attempt through trailing assistant messages', () => {
    const messages = [
      withNativeJennyReplyAttempt(user('older'), 'failed', 'old failure', 100),
      assistant('a1'),
      withNativeJennyReplyAttempt(user('latest'), 'working', undefined, 200),
      assistant('a2', 'partial')
    ]

    expect(latestNativeJennyReplyAttempt(messages)).toEqual({
      messageId: 'latest',
      status: 'working',
      updatedAt: 200
    })
  })

  it('does not let an older marked attempt drive status after a newer unmarked user turn', () => {
    const messages = [withNativeJennyReplyAttempt(user('project'), 'working', undefined, 100), user('normal')]

    expect(latestNativeJennyReplyAttempt(messages)).toBeNull()
    expect(updateLatestNativeJennyReplyAttempt(messages, 'failed', 'late error', 200)).toBe(messages)
  })

  it('moves the latest in-flight attempt through working, replied, and failed states', () => {
    const queued = [withNativeJennyReplyAttempt(user('u1'), 'queued', undefined, 100)]
    const working = updateLatestNativeJennyReplyAttempt(queued, 'working', undefined, 200)
    const replied = updateLatestNativeJennyReplyAttempt(working, 'replied', undefined, 300)
    const failed = updateLatestNativeJennyReplyAttempt(queued, 'failed', 'gateway offline', 400)

    expect(latestNativeJennyReplyAttempt(working)).toMatchObject({ messageId: 'u1', status: 'working' })
    expect(latestNativeJennyReplyAttempt(replied)).toMatchObject({ messageId: 'u1', status: 'replied' })
    expect(latestNativeJennyReplyAttempt(failed)).toMatchObject({
      error: 'gateway offline',
      messageId: 'u1',
      status: 'failed'
    })
  })

  it('does not rewrite a terminal replied attempt when a later retry helper reports failure', () => {
    const replied = [withNativeJennyReplyAttempt(user('u1'), 'replied', undefined, 100)]

    expect(updateLatestNativeJennyReplyAttempt(replied, 'failed', 'late failure', 200)).toBe(replied)
    expect(latestNativeJennyReplyAttempt(replied)).toMatchObject({ messageId: 'u1', status: 'replied' })
  })

  it('can requeue one existing user message for retry or edit flows', () => {
    const messages = [user('u1'), assistant('a1'), user('u2')]
    const next = setNativeJennyReplyAttemptForUser(messages, 'u1', 'queued', undefined, 500)

    expect(next).not.toBe(messages)
    expect(next[0].nativeJennyReplyAttempt).toEqual({ status: 'queued', updatedAt: 500 })
    expect(next[2].nativeJennyReplyAttempt).toBeUndefined()
  })
})
