import { describe, expect, it } from 'vitest'

import { coerceThinkingText, parseCommandDispatch, quickModelOptions, toRuntimeMessage } from './chat-runtime'

describe('coerceThinkingText', () => {
  it('strips streaming status prefixes from thinking deltas', () => {
    expect(coerceThinkingText("◉_◉ processing... checking the user's request")).toBe("checking the user's request")
    expect(coerceThinkingText('(¬‿¬) analyzing... reading the file')).toBe('reading the file')
  })

  it('drops empty thinking rewrite placeholder text', () => {
    expect(
      coerceThinkingText(
        "◉_◉ processing... I don't see any current rewritten thinking or next thinking to process. Could you provide the thinking content you'd like me to rewrite?"
      )
    ).toBe('')
  })
})

describe('quickModelOptions', () => {
  it('keeps OpenRouter visible while preserving explicit provider selection values', () => {
    const options = quickModelOptions(
      {
        provider: 'openai-codex',
        model: 'gpt-5.5',
        providers: [
          {
            slug: 'openai-codex',
            name: 'OpenAI Codex',
            is_current: true,
            models: ['gpt-5.5']
          },
          {
            slug: 'openrouter',
            name: 'OpenRouter',
            models: ['openai/gpt-5.5']
          }
        ]
      },
      'openai-codex',
      'gpt-5.5'
    )

    expect(options).toContainEqual({ provider: 'openai-codex', providerName: 'OpenAI Codex', model: 'gpt-5.5' })
    expect(options).toContainEqual({ provider: 'openrouter', providerName: 'OpenRouter', model: 'openai/gpt-5.5' })
  })
})

describe('parseCommandDispatch', () => {
  it('preserves send notices for native goal status rendering', () => {
    expect(
      parseCommandDispatch({
        message: '[Engineering goal kickoff]\nObjective:\nMake Jenny reliable.',
        notice: 'Goal set (20-turn budget): Make Jenny reliable.',
        type: 'send'
      })
    ).toEqual({
      message: '[Engineering goal kickoff]\nObjective:\nMake Jenny reliable.',
      notice: 'Goal set (20-turn budget): Make Jenny reliable.',
      type: 'send'
    })
  })
})

describe('toRuntimeMessage', () => {
  it('keeps hidden Jenny OS context out of native chat user bubbles', () => {
    const runtimeMessage = toRuntimeMessage({
      id: 'user-1',
      role: 'user',
      parts: [
        {
          type: 'text',
          text: [
            'Hidden Jenny OS project context:',
            'Project: Hermes / Mission Control',
            'Project ID: project-hermes-mission-control',
            'Visible chat rule: do not echo this hidden project context.',
            '',
            'test'
          ].join('\n')
        }
      ]
    })

    expect(runtimeMessage.content).toEqual([{ type: 'text', text: 'test' }])
  })

  it('keeps attached context compact when native chat renders a user message', () => {
    const runtimeMessage = toRuntimeMessage({
      id: 'user-2',
      role: 'user',
      parts: [
        {
          type: 'text',
          text:
            'what is this file\n\n--- Attached Context ---\n\n📄 @file:tsconfig.tsbuildinfo (981 tokens)\n```json\n{"root":["./src/main.tsx"]}\n```'
        }
      ]
    })

    expect(runtimeMessage.content).toEqual([{ type: 'text', text: '@file:tsconfig.tsbuildinfo\n\nwhat is this file' }])
  })
})
