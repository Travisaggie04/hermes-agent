import { describe, expect, it } from 'vitest'

import { buildModelSwitchCommand } from './use-model-controls'

describe('buildModelSwitchCommand', () => {
  it('selects OpenAI Codex GPT-5.5 with provider=openai-codex', () => {
    expect(
      buildModelSwitchCommand({ provider: 'openai-codex', model: 'gpt-5.5', persistGlobal: false })
    ).toBe('/model gpt-5.5 --provider openai-codex')
  })

  it('selects OpenRouter models with provider=openrouter explicitly', () => {
    expect(
      buildModelSwitchCommand({ provider: 'openrouter', model: 'openai/gpt-5.5', persistGlobal: true })
    ).toBe('/model openai/gpt-5.5 --provider openrouter --global')
  })
})
