import { beforeEach, describe, expect, it } from 'vitest'

import type { ComposerAttachment } from './composer'
import {
  $queuedPromptsBySession,
  clearQueuedPromptFailure,
  clearQueuedPrompts,
  dequeueQueuedPrompt,
  enqueueQueuedPrompt,
  getQueuedPrompts,
  markQueuedPromptFailed,
  removeQueuedPrompt,
  removeQueuedPromptAttachment,
  shouldAutoDrainOnSettle,
  updateQueuedPrompt,
  updateQueuedPromptText
} from './composer-queue'

const SESSION_KEY = 'session-abc'
const QUEUE_STORAGE_KEY = 'hermes.desktop.composerQueue.v1'

function attachment(id: string, kind: ComposerAttachment['kind'] = 'file'): ComposerAttachment {
  return {
    id,
    kind,
    label: id,
    refText: `@file:${id}`
  }
}

describe('composer queue store', () => {
  beforeEach(() => {
    window.localStorage.removeItem(QUEUE_STORAGE_KEY)
    $queuedPromptsBySession.set({})
  })

  it('queues prompts in FIFO order', () => {
    enqueueQueuedPrompt(SESSION_KEY, { attachments: [], text: 'first' })
    enqueueQueuedPrompt(SESSION_KEY, { attachments: [], text: 'second' })

    expect(dequeueQueuedPrompt(SESSION_KEY)?.text).toBe('first')
    expect(dequeueQueuedPrompt(SESSION_KEY)?.text).toBe('second')
    expect(dequeueQueuedPrompt(SESSION_KEY)).toBeNull()
  })

  it('clones attachments when queueing', () => {
    const source = [attachment('a-1')]
    const queued = enqueueQueuedPrompt(SESSION_KEY, { attachments: source, text: 'check clones' })

    expect(queued).not.toBeNull()
    expect(getQueuedPrompts(SESSION_KEY)[0]?.attachments[0]).toEqual(source[0])
    expect(getQueuedPrompts(SESSION_KEY)[0]?.attachments[0]).not.toBe(source[0])
  })

  it('updates and removes queued entries by id', () => {
    const first = enqueueQueuedPrompt(SESSION_KEY, { attachments: [], text: 'draft one' })
    const second = enqueueQueuedPrompt(SESSION_KEY, { attachments: [], text: 'draft two' })

    expect(first).not.toBeNull()
    expect(second).not.toBeNull()

    expect(updateQueuedPromptText(SESSION_KEY, first!.id, 'draft one edited')).toBe(true)
    expect(getQueuedPrompts(SESSION_KEY).map(entry => entry.text)).toEqual(['draft one edited', 'draft two'])

    expect(removeQueuedPrompt(SESSION_KEY, first!.id)).toBe(true)
    expect(getQueuedPrompts(SESSION_KEY).map(entry => entry.text)).toEqual(['draft two'])
  })

  it('updates queued text and attachment snapshot', () => {
    const first = enqueueQueuedPrompt(SESSION_KEY, { attachments: [attachment('f-1')], text: 'draft one' })
    const editedAttachments = [attachment('f-2'), attachment('f-3', 'image')]

    expect(first).not.toBeNull()
    expect(
      updateQueuedPrompt(SESSION_KEY, first!.id, {
        attachments: editedAttachments,
        text: 'edited text'
      })
    ).toBe(true)

    const queue = getQueuedPrompts(SESSION_KEY)
    expect(queue[0]?.text).toBe('edited text')
    expect(queue[0]?.attachments).toEqual(editedAttachments)
    expect(queue[0]?.attachments[0]).not.toBe(editedAttachments[0])
  })

  it('marks failed queued sends and clears failure state on retry or edit', () => {
    const entry = enqueueQueuedPrompt(SESSION_KEY, { attachments: [attachment('img-1', 'image')], text: 'look' })

    expect(entry).not.toBeNull()
    expect(markQueuedPromptFailed(SESSION_KEY, entry!.id, 'Image attach failed: file does not exist.')).toBe(true)
    expect(getQueuedPrompts(SESSION_KEY)[0]).toMatchObject({
      failureReason: 'Image attach failed: file does not exist.',
      status: 'failed'
    })
    expect(getQueuedPrompts(SESSION_KEY)[0]?.failedAt).toEqual(expect.any(Number))

    expect(clearQueuedPromptFailure(SESSION_KEY, entry!.id)).toBe(true)
    expect(getQueuedPrompts(SESSION_KEY)[0]).toMatchObject({ status: 'queued' })
    expect(getQueuedPrompts(SESSION_KEY)[0]?.failureReason).toBeUndefined()
    expect(getQueuedPrompts(SESSION_KEY)[0]?.failedAt).toBeUndefined()

    expect(markQueuedPromptFailed(SESSION_KEY, entry!.id, 'failed again')).toBe(true)
    expect(updateQueuedPromptText(SESSION_KEY, entry!.id, 'look again')).toBe(true)
    expect(getQueuedPrompts(SESSION_KEY)[0]).toMatchObject({ status: 'queued', text: 'look again' })
    expect(getQueuedPrompts(SESSION_KEY)[0]?.failureReason).toBeUndefined()
  })

  it('removes a stale attachment from a failed queued prompt', () => {
    const entry = enqueueQueuedPrompt(SESSION_KEY, {
      attachments: [attachment('img-1', 'image'), attachment('f-1')],
      text: 'use the remaining context'
    })

    expect(entry).not.toBeNull()
    expect(markQueuedPromptFailed(SESSION_KEY, entry!.id, 'missing image')).toBe(true)
    expect(removeQueuedPromptAttachment(SESSION_KEY, entry!.id, 'img-1')).toBe(true)

    const queue = getQueuedPrompts(SESSION_KEY)
    expect(queue[0]?.text).toBe('use the remaining context')
    expect(queue[0]?.attachments.map(item => item.id)).toEqual(['f-1'])
    expect(queue[0]?.status).toBe('queued')
    expect(queue[0]?.failureReason).toBeUndefined()
  })

  it('clears queue state for a session', () => {
    enqueueQueuedPrompt(SESSION_KEY, { attachments: [attachment('img-1', 'image')], text: 'queued' })

    clearQueuedPrompts(SESSION_KEY)

    expect(getQueuedPrompts(SESSION_KEY)).toEqual([])
    expect($queuedPromptsBySession.get()[SESSION_KEY]).toBeUndefined()
    expect(window.localStorage.getItem(QUEUE_STORAGE_KEY)).toBeNull()
  })

  it('persists queue entries into local storage', () => {
    enqueueQueuedPrompt(SESSION_KEY, { attachments: [], text: 'persist me' })

    const raw = window.localStorage.getItem(QUEUE_STORAGE_KEY)
    expect(raw).toBeTruthy()

    const parsed = JSON.parse(String(raw)) as Record<string, { text: string }[]>
    expect(parsed[SESSION_KEY]?.[0]?.text).toBe('persist me')
  })
})

describe('shouldAutoDrainOnSettle', () => {
  const base = { isBusy: false, queueLength: 1, userInterrupted: false, wasBusy: true }

  it('drains the next queued prompt when a turn completes naturally', () => {
    expect(shouldAutoDrainOnSettle(base)).toBe(true)
  })

  it('does NOT drain when the user explicitly interrupted (Stop button)', () => {
    // Regression: previously the Stop button "never worked" because cancelling
    // a turn flipped busy → false and the queue immediately re-fired its head.
    expect(shouldAutoDrainOnSettle({ ...base, userInterrupted: true })).toBe(false)
  })

  it('does not drain when the queue is empty', () => {
    expect(shouldAutoDrainOnSettle({ ...base, queueLength: 0 })).toBe(false)
  })

  it('does not drain when interrupted even if the queue is also empty', () => {
    expect(shouldAutoDrainOnSettle({ ...base, queueLength: 0, userInterrupted: true })).toBe(false)
  })

  it('ignores steady busy state (no true → false transition)', () => {
    expect(shouldAutoDrainOnSettle({ ...base, isBusy: true })).toBe(false)
  })

  it('ignores busy entry (false → true, not a settle)', () => {
    expect(shouldAutoDrainOnSettle({ ...base, isBusy: true, wasBusy: false })).toBe(false)
  })

  it('ignores steady idle state (was not busy)', () => {
    expect(shouldAutoDrainOnSettle({ ...base, wasBusy: false })).toBe(false)
  })
})
