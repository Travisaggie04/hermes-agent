import { describe, expect, it } from 'vitest'

import source from './use-message-stream.ts?raw'

describe('useMessageStream native Jenny reply loop wiring', () => {
  it('moves reply attempts from working to replied or failed through stream events', () => {
    expect(source).toContain("import { updateLatestNativeJennyReplyAttempt } from '@/lib/native-jenny-reply-loop'")
    expect(source).toContain("messages: updateLatestNativeJennyReplyAttempt(nextMessages, 'working')")
    expect(source).toContain("completionError ? 'failed' : 'replied'")
    expect(source).toContain("const prev = updateLatestNativeJennyReplyAttempt(state.messages, 'failed', errorMessage)")
  })
})
