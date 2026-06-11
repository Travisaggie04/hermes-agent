import { describe, expect, it } from 'vitest'

import {
  displayModelName,
  formatModelStatusLabel,
  formatProviderModelLabel,
  providerModelPickerNotice,
  reasoningEffortLabel
} from './model-status-label'

describe('model-status-label', () => {
  it('formats display names consistently', () => {
    expect(displayModelName('anthropic/claude-opus-4.8-fast')).toBe('Opus 4.8')
    expect(displayModelName('openai/gpt-5.5')).toBe('GPT-5.5')
  })

  it('renders provider-qualified labels so OpenAI Codex and OpenRouter are distinct', () => {
    expect(formatProviderModelLabel('OpenAI Codex', 'openai-codex', 'gpt-5.5')).toBe('OpenAI Codex · GPT-5.5')
    expect(formatProviderModelLabel('OpenRouter', 'openrouter', 'openai/gpt-5.5')).toBe(
      'OpenRouter · openai/gpt-5.5'
    )
  })

  it('adds an explicit OpenRouter aggregator notice without warning direct OpenAI Codex rows', () => {
    expect(providerModelPickerNotice('openrouter')).toContain('OpenRouter aggregator')
    expect(providerModelPickerNotice('openai-codex')).toBe('')
  })

  it('maps reasoning effort to compact labels', () => {
    expect(reasoningEffortLabel('high')).toBe('High')
    expect(reasoningEffortLabel('xhigh')).toBe('Max')
    expect(reasoningEffortLabel('')).toBe('')
  })

  it('appends fast + effort session state to the status label', () => {
    expect(formatModelStatusLabel('openai/gpt-5.5', { fastMode: true, reasoningEffort: 'high' })).toBe(
      'GPT-5.5 · Fast High'
    )
  })

  it('always surfaces the effort (default medium) so the level is visible', () => {
    expect(formatModelStatusLabel('openai/gpt-5.5', { reasoningEffort: 'medium' })).toBe('GPT-5.5 · Med')
    expect(formatModelStatusLabel('openai/gpt-5.5')).toBe('GPT-5.5 · Med')
  })

  it('returns just the placeholder name when there is no model', () => {
    expect(formatModelStatusLabel('')).toBe('No model')
  })
})
