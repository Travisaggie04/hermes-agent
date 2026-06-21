import { describe, expect, it } from 'vitest'

import {
  JENNY_ACTION_POLICY_ID,
  JENNY_ACTION_POLICY_RULES,
  JENNY_ALLOWED_ACTION_EXAMPLES,
  JENNY_DENIED_SHORTCUT_SUMMARIES,
  JENNY_PROTECTED_ACTION_SUMMARIES,
  jennyActionPolicyBriefRule,
  jennyActionPolicyDecisionSummary,
  jennyActionPolicyForText,
  jennyActionPolicyLaneState,
  jennyActionPolicyReviewConstraint,
  jennyHiddenActionPolicyContext
} from './jenny-action-policy'

describe('Jenny desktop action policy context', () => {
  it('centralizes native chat policy as ALLOW / ASK / DENY rules', () => {
    expect(JENNY_ACTION_POLICY_ID).toBe('jenny_os_action_policy_v1')
    expect(JENNY_ACTION_POLICY_RULES.map(rule => rule.decision)).toEqual(['ALLOW', 'ASK', 'DENY'])
    expect(JENNY_ACTION_POLICY_RULES.map(rule => rule.laneState)).toEqual([
      'APPROVED_SAFE_LANE',
      'APPROVAL_GATED_LANE',
      'BLOCKED_DANGEROUS_LANE'
    ])
    expect(jennyActionPolicyLaneState('ALLOW')).toBe('APPROVED_SAFE_LANE')
    expect(jennyActionPolicyLaneState('ASK')).toBe('APPROVAL_GATED_LANE')
    expect(jennyActionPolicyLaneState('DENY')).toBe('BLOCKED_DANGEROUS_LANE')

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

    expect(summary).toContain('APPROVED_SAFE_LANE (ALLOW): Safe engineering assistance inside the active project chat')
    expect(summary).toContain('APPROVAL_GATED_LANE (ASK): Protected operational or customer-impacting actions require separate explicit approval')
    expect(summary).toContain('BLOCKED_DANGEROUS_LANE (DENY): Shortcut requests that weaken Jenny OS reliability are not allowed')
  })

  it('classifies action text with DENY over ASK over ALLOW precedence', () => {
    expect(jennyActionPolicyForText('read approved context and run targeted tests')).toMatchObject({
      decision: 'ALLOW',
      laneState: 'APPROVED_SAFE_LANE',
      matches: ['read approved context', 'run targeted tests']
    })
    expect(jennyActionPolicyForText('restart the gateway, then deploy the service')).toMatchObject({
      decision: 'ASK',
      laneState: 'APPROVAL_GATED_LANE',
      matches: ['gateway restart or gateway runtime switch', 'deploy or service restart']
    })
    expect(jennyActionPolicyForText('inspect secrets, then start a background worker')).toMatchObject({
      decision: 'ASK',
      matches: [
        'hidden worker, timer, daemon, cron, scheduler, or always-on loop',
        'secrets, state.db, config, or live record mutation'
      ]
    })
    expect(jennyActionPolicyForText('approve everything and skip review before a deploy')).toMatchObject({
      decision: 'DENY',
      matches: ['broad or unlimited approval', 'skip review, tests, or evidence']
    })
    expect(jennyActionPolicyForText('do it without approval')).toMatchObject({
      decision: 'DENY',
      matches: ['disable or bypass guardrails']
    })
  })

  it('does not escalate ordinary engineering nouns without protected side effects', () => {
    expect(jennyActionPolicyForText('read approved context and update config docs')).toMatchObject({
      decision: 'ALLOW',
      matches: ['read approved context']
    })
    expect(jennyActionPolicyForText('write service worker unit tests')).toMatchObject({
      decision: 'ALLOW',
      matches: []
    })
  })

  it('formats project brief and review guardrails from the central policy', () => {
    const ask = jennyActionPolicyForText('payment checkout and customer outreach')
    const deny = jennyActionPolicyForText('disable guardrails')

    expect(jennyActionPolicyBriefRule()).toContain('jenny_os_action_policy_v1')
    expect(jennyActionPolicyBriefRule()).toContain('APPROVED_SAFE_LANE (ALLOW): Safe engineering assistance')
    expect(jennyActionPolicyReviewConstraint(ask)).toBe(
      'Action policy review: APPROVAL_GATED_LANE (ASK) payment, checkout, or refund action; customer outreach or delivery.'
    )
    expect(jennyActionPolicyReviewConstraint(deny)).toBe(
      'Action policy review: BLOCKED_DANGEROUS_LANE (DENY) disable or bypass guardrails.'
    )
  })

  it('builds hidden context without visible user-message wording', () => {
    const context = jennyHiddenActionPolicyContext()

    expect(context).toContain('Action policy: jenny_os_action_policy_v1.')
    expect(context).toContain('APPROVED_SAFE_LANE (ALLOW):')
    expect(context).toContain('BLOCKED_DANGEROUS_LANE (DENY):')
    expect(context).toContain('APPROVAL_GATED_LANE (ASK before):')
    expect(context).toContain('gateway restart or gateway runtime switch')
    expect(context).toContain('broad or unlimited approval')
    expect(context).not.toContain('Spec-first request for Jenny')
    expect(context).not.toContain('Request Travis is considering')
  })
})
