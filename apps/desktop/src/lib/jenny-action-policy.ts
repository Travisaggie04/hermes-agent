export const JENNY_ACTION_POLICY_ID = 'jenny_os_action_policy_v1'

export const JENNY_ALLOWED_ACTION_EXAMPLES = [
  'read approved context',
  'inspect status',
  'plan a bounded lane',
  'create a draft PR',
  'run targeted tests',
  'report evidence'
] as const

export const JENNY_PROTECTED_ACTION_SUMMARIES = [
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
] as const

export const JENNY_DENIED_SHORTCUT_SUMMARIES = [
  'broad or unlimited approval',
  'disable or bypass guardrails',
  'skip review, tests, or evidence'
] as const

export function jennyHiddenActionPolicyContext(): string {
  return [
    `Action policy: ${JENNY_ACTION_POLICY_ID}.`,
    `Allowed by default: ${JENNY_ALLOWED_ACTION_EXAMPLES.join(', ')}.`,
    `Protected actions require separate explicit approval: ${JENNY_PROTECTED_ACTION_SUMMARIES.join('; ')}.`,
    `Denied shortcuts: ${JENNY_DENIED_SHORTCUT_SUMMARIES.join('; ')}.`
  ].join('\n')
}
