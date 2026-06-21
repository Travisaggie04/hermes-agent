export const JENNY_ACTION_POLICY_ID = 'jenny_os_action_policy_v1'

export type JennyActionPolicyDecision = 'ALLOW' | 'ASK' | 'DENY'
export type JennyActionPolicyLaneState = 'APPROVAL_GATED_LANE' | 'APPROVED_SAFE_LANE' | 'BLOCKED_DANGEROUS_LANE'

export interface JennyActionPolicyRule {
  readonly decision: JennyActionPolicyDecision
  readonly laneState: JennyActionPolicyLaneState
  readonly summary: string
  readonly examples: readonly string[]
}

export interface JennyActionPolicyEvaluation {
  readonly decision: JennyActionPolicyDecision
  readonly laneState: JennyActionPolicyLaneState
  readonly matches: readonly string[]
  readonly rule: JennyActionPolicyRule
}

const JENNY_ACTION_POLICY_LANE_STATE_BY_DECISION: Record<JennyActionPolicyDecision, JennyActionPolicyLaneState> = {
  ALLOW: 'APPROVED_SAFE_LANE',
  ASK: 'APPROVAL_GATED_LANE',
  DENY: 'BLOCKED_DANGEROUS_LANE'
}

export const JENNY_ACTION_POLICY_RULES = [
  {
    decision: 'ALLOW',
    laneState: 'APPROVED_SAFE_LANE',
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
    laneState: 'APPROVAL_GATED_LANE',
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
    laneState: 'BLOCKED_DANGEROUS_LANE',
    summary: 'Shortcut requests that weaken Jenny OS reliability are not allowed',
    examples: ['broad or unlimited approval', 'disable or bypass guardrails', 'skip review, tests, or evidence']
  }
] as const satisfies readonly JennyActionPolicyRule[]

const JENNY_ACTION_POLICY_PRECEDENCE: readonly JennyActionPolicyDecision[] = ['DENY', 'ASK', 'ALLOW']

const JENNY_ACTION_POLICY_MATCHERS = [
  {
    decision: 'DENY',
    example: 'broad or unlimited approval',
    patterns: [/\b(?:broad|blanket|unlimited)\s+approval\b/i, /\bapprove\s+(?:all|everything|anything)\b/i]
  },
  {
    decision: 'DENY',
    example: 'disable or bypass guardrails',
    patterns: [
      /\b(?:disable|bypass|skip|remove)\s+(?:the\s+)?guardrails?\b/i,
      /\bwithout\s+(?:approval|permission|review|tests|evidence)\b/i
    ]
  },
  {
    decision: 'DENY',
    example: 'skip review, tests, or evidence',
    patterns: [/\bskip\s+(?:review|tests?|evidence)\b/i]
  },
  {
    decision: 'ASK',
    example: 'gateway restart or gateway runtime switch',
    patterns: [/\bgateway\s+(?:restart|switch|runtime)\b/i, /\brestart\s+(?:the\s+)?gateway\b/i]
  },
  {
    decision: 'ASK',
    example: 'live runtime switch',
    patterns: [/\b(?:live|production|dashboard)\s+runtime\s+switch\b/i, /\bruntime\s+switch\b/i]
  },
  {
    decision: 'ASK',
    example: 'deploy or service restart',
    patterns: [/\bdeploy\b/i, /\bservice\s+restart\b/i, /\brestart\s+(?:service|server|app|runtime)\b/i]
  },
  {
    decision: 'ASK',
    example: 'payment, checkout, or refund action',
    patterns: [/\b(?:payment|checkout|refund|stripe|paid order)\b/i]
  },
  {
    decision: 'ASK',
    example: 'customer outreach or delivery',
    patterns: [/\b(?:customer\s+)?(?:outreach|delivery|email|sms|dm)\b/i]
  },
  {
    decision: 'ASK',
    example: 'Waha, WhatsApp, social posting, or publishing',
    patterns: [/\b(?:waha|whatsapp|social\s+post(?:ing)?|post\s+to\s+social|public\s+post|publish(?:ing)?)\b/i]
  },
  {
    decision: 'ASK',
    example: 'hidden worker, timer, daemon, cron, scheduler, or always-on loop',
    patterns: [
      /\b(?:hidden|background)\s+(?:worker|timer|daemon|loop)\b/i,
      /\b(?:daemon|cron|scheduler|always-on)\b/i
    ]
  },
  {
    decision: 'ASK',
    example: 'secrets, state.db, config, or live record mutation',
    patterns: [
      /\b(?:inspect|read|view|dump|print|show|expose|rotate|change|edit|write|delete|wipe|mutate)\s+(?:\w+\s+){0,3}(?:secrets?|tokens?|state\.db|config|live records?)\b/i,
      /\b(?:secrets?|tokens?)\s+(?:inspection|dump|exposure|rotation|change)\b/i,
      /\b(?:state\.db|config|live records?|records?)\s+(?:mutation|edit|write|delete|wipe|change)\b/i,
      /\bstate\s+(?:deletion|delete|wipe|reset)\b/i
    ]
  },
  {
    decision: 'ASK',
    example: 'local LLM or model routing change',
    patterns: [/\b(?:local\s+llm|model routing|routing change)\b/i]
  },
  {
    decision: 'ASK',
    example: 'Tool & Tally report-builder, checkout, or outreach change',
    patterns: [/\btool\s*&\s*tally\b/i, /\breport-builder\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'read approved context',
    patterns: [/\bread\s+approved\s+context\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'inspect status',
    patterns: [/\binspect\s+status\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'plan a bounded lane',
    patterns: [/\bplan\s+(?:a\s+)?bounded\s+lane\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'create a draft PR',
    patterns: [/\b(?:create|open)\s+(?:a\s+)?draft\s+pr\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'run targeted tests',
    patterns: [/\brun\s+targeted\s+tests?\b/i]
  },
  {
    decision: 'ALLOW',
    example: 'report evidence',
    patterns: [/\breport\s+evidence\b/i]
  }
] as const satisfies readonly {
  readonly decision: JennyActionPolicyDecision
  readonly example: string
  readonly patterns: readonly RegExp[]
}[]

function examplesForDecision(decision: JennyActionPolicyDecision): readonly string[] {
  return JENNY_ACTION_POLICY_RULES.find(rule => rule.decision === decision)?.examples ?? []
}

export const JENNY_ALLOWED_ACTION_EXAMPLES = examplesForDecision('ALLOW')

export const JENNY_PROTECTED_ACTION_SUMMARIES = examplesForDecision('ASK')

export const JENNY_DENIED_SHORTCUT_SUMMARIES = examplesForDecision('DENY')

export function jennyActionPolicyLaneState(decision: JennyActionPolicyDecision): JennyActionPolicyLaneState {
  return JENNY_ACTION_POLICY_LANE_STATE_BY_DECISION[decision]
}

export function jennyActionPolicyDecisionSummary(): string {
  return JENNY_ACTION_POLICY_RULES.map(
    rule => `${rule.laneState} (${rule.decision}): ${rule.summary} (${rule.examples.join('; ')})`
  ).join('\n')
}

export function jennyActionPolicyBriefRule(): string {
  return `Jenny must apply ${JENNY_ACTION_POLICY_ID}: ${jennyActionPolicyDecisionSummary()}`
}

export function jennyActionPolicyForText(value: string): JennyActionPolicyEvaluation {
  const matchesByDecision = new Map<JennyActionPolicyDecision, string[]>()
  const text = value.trim()

  if (text) {
    for (const matcher of JENNY_ACTION_POLICY_MATCHERS) {
      if (!matcher.patterns.some(pattern => pattern.test(text))) {
        continue
      }

      const matches = matchesByDecision.get(matcher.decision) ?? []

      if (!matches.includes(matcher.example)) {
        matches.push(matcher.example)
      }

      matchesByDecision.set(matcher.decision, matches)
    }
  }

  const decision = JENNY_ACTION_POLICY_PRECEDENCE.find(item => (matchesByDecision.get(item)?.length ?? 0) > 0) ?? 'ALLOW'
  const rule = JENNY_ACTION_POLICY_RULES.find(item => item.decision === decision) ?? JENNY_ACTION_POLICY_RULES[0]

  return {
    decision,
    laneState: jennyActionPolicyLaneState(decision),
    matches: matchesByDecision.get(decision) ?? [],
    rule
  }
}

export function jennyActionPolicyReviewConstraint(evaluation: JennyActionPolicyEvaluation): string {
  if (evaluation.decision === 'ALLOW') {
    return `Action policy review: ${evaluation.laneState} (ALLOW) ${evaluation.rule.summary}.`
  }

  const target = evaluation.matches.length ? evaluation.matches.join('; ') : evaluation.rule.examples.join('; ')

  return `Action policy review: ${evaluation.laneState} (${evaluation.decision}) ${target}.`
}

export function jennyHiddenActionPolicyContext(): string {
  return [
    `Action policy: ${JENNY_ACTION_POLICY_ID}.`,
    `APPROVED_SAFE_LANE (ALLOW): ${JENNY_ALLOWED_ACTION_EXAMPLES.join(', ')}.`,
    `APPROVAL_GATED_LANE (ASK before): ${JENNY_PROTECTED_ACTION_SUMMARIES.join('; ')}.`,
    `BLOCKED_DANGEROUS_LANE (DENY): ${JENNY_DENIED_SHORTCUT_SUMMARIES.join('; ')}.`
  ].join('\n')
}
