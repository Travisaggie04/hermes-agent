import { describe, expect, it } from 'vitest'

import {
  JENNY_ACTION_POLICY_ID,
  JENNY_ALLOWED_ACTION_EXAMPLES,
  JENNY_DENIED_SHORTCUT_SUMMARIES,
  JENNY_PROTECTED_ACTION_SUMMARIES,
  jennyHiddenActionPolicyContext
} from './jenny-action-policy'

describe('Jenny desktop action policy context', () => {
  it('centralizes the native chat hidden policy vocabulary', () => {
    expect(JENNY_ACTION_POLICY_ID).toBe('jenny_os_action_policy_v1')
    expect(JENNY_ALLOWED_ACTION_EXAMPLES).toContain('run targeted tests')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('gateway restart or gateway runtime switch')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('Waha, WhatsApp, social posting, or publishing')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('local LLM or model routing change')
    expect(JENNY_DENIED_SHORTCUT_SUMMARIES).toContain('broad or unlimited approval')
  })

  it('builds hidden context without visible user-message wording', () => {
    const context = jennyHiddenActionPolicyContext()

    expect(context).toContain('Action policy: jenny_os_action_policy_v1.')
    expect(context).toContain('Protected actions require separate explicit approval:')
    expect(context).toContain('Denied shortcuts:')
    expect(context).not.toContain('Spec-first request for Jenny')
    expect(context).not.toContain('Request Travis is considering')
  })
})
