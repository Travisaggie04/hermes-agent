import { describe, expect, it } from 'vitest'

import {
  buildNativeProjectBriefCreatePayload,
  buildNativeProjectCreatePayload,
  emptyNativeProjectIntake,
  NATIVE_PROJECT_DEFAULT_APPROVAL_RULES,
  NATIVE_PROJECT_DEFAULT_NEXT_LANE,
  nativeProjectIntakeList,
  nativeProjectSlug,
  parseNativeProjectIntake
} from './native-project-intake'

describe('native project intake helpers', () => {
  it('normalizes native project names and list fields consistently', () => {
    expect(nativeProjectSlug(' Tool & Tally / Checkout Recovery! ')).toBe('tool-tally-checkout-recovery')
    expect(nativeProjectSlug('')).toBe('project')
    expect(nativeProjectIntakeList('one, two\nthree\r\n\n')).toEqual(['one', 'two', 'three'])
  })

  it('builds the shared project and brief payloads for native chat project creation', () => {
    const parsed = parseNativeProjectIntake({
      ...emptyNativeProjectIntake(),
      approval: 'Ask before payment changes',
      evidence: 'passing tests\nmanual smoke',
      forbidden: 'payment mutation, outreach',
      goal: 'Make Jenny safer to use from native chat.',
      name: 'Jenny OS',
      source: 'Hermes repo',
      success: 'clean user messages\nproject sessions grouped'
    })

    expect(parsed.projectId).toBe('project-jenny-os')
    expect(parsed.approvalRules).toEqual([...NATIVE_PROJECT_DEFAULT_APPROVAL_RULES, 'Ask before payment changes'])
    expect(parsed.constraints).toEqual([
      'Evidence required: passing tests',
      'Evidence required: manual smoke',
      'Approval/stop rule: Ask before payment changes'
    ])

    expect(buildNativeProjectCreatePayload(parsed)).toEqual({
      current_goal: 'Make Jenny safer to use from native chat.',
      mistakes_guards: 'payment mutation; outreach',
      name: 'Jenny OS',
      next_recommended_lane: NATIVE_PROJECT_DEFAULT_NEXT_LANE,
      project_id: 'project-jenny-os',
      source_of_truth: 'Hermes repo',
      status: 'active'
    })

    expect(buildNativeProjectBriefCreatePayload(parsed, 'project-jenny-os', 'Jenny OS')).toEqual({
      approval_rules: parsed.approvalRules,
      constraints: parsed.constraints,
      forbidden_actions: ['payment mutation', 'outreach'],
      name: 'Jenny OS initial brief',
      outcome: 'Make Jenny safer to use from native chat.',
      project_id: 'project-jenny-os',
      source_of_truth: 'Hermes repo',
      status: 'active',
      success_criteria: ['clean user messages', 'project sessions grouped']
    })
  })
})
