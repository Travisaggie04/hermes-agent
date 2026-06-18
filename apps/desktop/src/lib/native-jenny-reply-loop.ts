import type { ChatMessage, NativeJennyReplyAttempt, NativeJennyReplyAttemptStatus } from '@/lib/chat-messages'

export interface NativeJennyReplyAttemptSummary extends NativeJennyReplyAttempt {
  messageId: string
}

const IN_FLIGHT_REPLY_STATUSES = new Set<NativeJennyReplyAttemptStatus>(['queued', 'working'])

export function nativeJennyReplyAttempt(
  status: NativeJennyReplyAttemptStatus = 'queued',
  error?: string,
  nowMs = Date.now()
): NativeJennyReplyAttempt {
  const trimmedError = error?.trim()

  return {
    status,
    updatedAt: nowMs,
    ...(trimmedError && { error: trimmedError })
  }
}

export function withNativeJennyReplyAttempt(
  message: ChatMessage,
  status: NativeJennyReplyAttemptStatus = 'queued',
  error?: string,
  nowMs = Date.now()
): ChatMessage {
  if (message.role !== 'user') {
    return message
  }

  return {
    ...message,
    nativeJennyReplyAttempt: nativeJennyReplyAttempt(status, error, nowMs)
  }
}

export function latestNativeJennyReplyAttempt(
  messages: readonly ChatMessage[]
): NativeJennyReplyAttemptSummary | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]

    if (message.hidden) {
      continue
    }

    if (message.role !== 'user') {
      continue
    }

    const attempt = message.nativeJennyReplyAttempt

    return attempt ? { ...attempt, messageId: message.id } : null
  }

  return null
}

export function setNativeJennyReplyAttemptForUser(
  messages: readonly ChatMessage[],
  userMessageId: string,
  status: NativeJennyReplyAttemptStatus = 'queued',
  error?: string,
  nowMs = Date.now()
): ChatMessage[] {
  let changed = false
  const next = messages.map(message => {
    if (message.id !== userMessageId || message.role !== 'user') {
      return message
    }

    changed = true

    return withNativeJennyReplyAttempt(message, status, error, nowMs)
  })

  return changed ? next : [...messages]
}

export function updateLatestNativeJennyReplyAttempt(
  messages: readonly ChatMessage[],
  status: NativeJennyReplyAttemptStatus,
  error?: string,
  nowMs = Date.now()
): ChatMessage[] {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]

    if (message.hidden) {
      continue
    }

    if (message.role !== 'user') {
      continue
    }

    const attempt = message.nativeJennyReplyAttempt

    if (!attempt || (status !== 'queued' && !IN_FLIGHT_REPLY_STATUSES.has(attempt.status))) {
      return messages as ChatMessage[]
    }

    const trimmedError = error?.trim()

    if (attempt.status === status && (attempt.error ?? '') === (trimmedError ?? '')) {
      return messages as ChatMessage[]
    }

    const next = [...messages]
    next[index] = withNativeJennyReplyAttempt(message, status, trimmedError, nowMs)

    return next
  }

  return messages as ChatMessage[]
}
