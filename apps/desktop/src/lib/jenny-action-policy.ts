export const JENNY_ACTION_POLICY_ID = 'jenny_os_action_policy_v1'

export type JennyActionPolicyDecision = 'ALLOW' | 'ASK' | 'DENY'

export interface JennyActionPolicyRule {
  readonly decision: JennyActionPolicyDecision
  readonly summary: string
  readonly examples: readonly string[]
}

export const JENNY_ACTION_POLICY_RULES = [
  {
    decision: 'ALLOW',
    summary: 'Safe engineering assistance inside the active project chat',
    examples: [
      'read approved context',
      'inspect status',
      'plan a bounded lane',
      'create a draft PR',
      'run targeted tests',
      'report evidence'
    ]
  },
  {
    decision: 'ASK',
    summary: 'Protected operational or customer-impacting actions require separate explicit approval',
    examples: [
      'gateway restart or gateway runtime switch',
      'live runtime switch',
      'deploy or service restart',
      'payment, checkout, or refund action',
      'customer outreach or delivery',
      'Waha, WhatsApp, social posting, or publishing',
      'hidden worker, timer, daemon, cron, scheduler, or always-on loop',
      'secrets, state.db, config, or live record mutation',
      'local LLM or model routing change',
      'Tool & Tally report-builder, checkout, or outreach change'
    ]
  },
  {
    decision: 'DENY',
    summary: 'Shortcut requests that weaken Jenny OS reliability are not allowed',
    examples: ['broad or unlimited approval', 'disable or bypass guardrails', 'skip review, tests, or evidence']
  }
] as const satisfies readonly JennyActionPolicyRule[]

function examplesForDecision(decision: JennyActionPolicyDecision): readonly string[] {
  return JENNY_ACTION_POLICY_RULES.find(rule => rule.decision === decision)?.examples ?? []
}

export const JENNY_ALLOWED_ACTION_EXAMPLES = examplesForDecision('ALLOW')

export const JENNY_PROTECTED_ACTION_SUMMARIES = examplesForDecision('ASK')

export const JENNY_DENIED_SHORTCUT_SUMMARIES = examplesForDecision('DENY')

export function jennyActionPolicyDecisionSummary(): string {
  return JENNY_ACTION_POLICY_RULES.map(rule => `${rule.decision}: ${rule.summary} (${rule.examples.join('; ')})`).join('\n')
}

export function jennyHiddenActionPolicyContext(): string {
  return [
    `Action policy: ${JENNY_ACTION_POLICY_ID}.`,
    `ALLOW: ${JENNY_ALLOWED_ACTION_EXAMPLES.join(', ')}.`,
    `ASK before: ${JENNY_PROTECTED_ACTION_SUMMARIES.join('; ')}.`,
    `DENY: ${JENNY_DENIED_SHORTCUT_SUMMARIES.join('; ')}.`
  ].join('\n')
}
