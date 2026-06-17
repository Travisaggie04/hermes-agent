import { describe, expect, it } from 'vitest'

import {
  JENNY_ACTION_POLICY_ID,
  JENNY_ACTION_POLICY_RULES,
  JENNY_ALLOWED_ACTION_EXAMPLES,
  JENNY_DENIED_SHORTCUT_SUMMARIES,
  JENNY_PROTECTED_ACTION_SUMMARIES,
  jennyActionPolicyDecisionSummary,
  jennyHiddenActionPolicyContext
} from './jenny-action-policy'

describe('Jenny desktop action policy context', () => {
  it('centralizes native chat policy as ALLOW / ASK / DENY rules', () => {
    expect(JENNY_ACTION_POLICY_ID).toBe('jenny_os_action_policy_v1')
    expect(JENNY_ACTION_POLICY_RULES.map(rule => rule.decision)).toEqual(['ALLOW', 'ASK', 'DENY'])

    expect(JENNY_ACTION_POLICY_RULES.find(rule => rule.decision === 'ALLOW')?.examples).toEqual(
      JENNY_ALLOWED_ACTION_EXAMPLES
    )
    expect(JENNY_ACTION_POLICY_RULES.find(rule => rule.decision === 'ASK')?.examples).toEqual(
      JENNY_PROTECTED_ACTION_SUMMARIES
    )
    expect(JENNY_ACTION_POLICY_RULES.find(rule => rule.decision === 'DENY')?.examples).toEqual(
      JENNY_DENIED_SHORTCUT_SUMMARIES
    )

    expect(JENNY_ALLOWED_ACTION_EXAMPLES).toContain('run targeted tests')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('gateway restart or gateway runtime switch')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('Waha, WhatsApp, social posting, or publishing')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('hidden worker, timer, daemon, cron, scheduler, or always-on loop')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('Tool & Tally report-builder, checkout, or outreach change')
    expect(JENNY_PROTECTED_ACTION_SUMMARIES).toContain('local LLM or model routing change')
    expect(JENNY_DENIED_SHORTCUT_SUMMARIES).toContain('broad or unlimited approval')
  })

  it('summarizes the shared policy decisions for hidden Jenny context', () => {
    const summary = jennyActionPolicyDecisionSummary()

    expect(summary).toContain('ALLOW: Safe engineering assistance inside the active project chat')
    expect(summary).toContain('ASK: Protected operational or customer-impacting actions require separate explicit approval')
    expect(summary).toContain('DENY: Shortcut requests that weaken Jenny OS reliability are not allowed')
  })

  it('builds hidden context without visible user-message wording', () => {
    const context = jennyHiddenActionPolicyContext()

    expect(context).toContain('Action policy: jenny_os_action_policy_v1.')
    expect(context).toContain('Policy decisions:')
    expect(context).toContain('ALLOW:')
    expect(context).toContain('ASK:')
    expect(context).toContain('DENY:')
    expect(context).toContain('Protected actions require separate explicit approval:')
    expect(context).toContain('Denied shortcuts:')
    expect(context).not.toContain('Spec-first request for Jenny')
    expect(context).not.toContain('Request Travis is considering')
  })
})
