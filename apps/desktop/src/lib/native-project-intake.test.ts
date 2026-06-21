import { describe, expect, it, vi } from 'vitest'

import { jennyActionPolicyBriefRule } from './jenny-action-policy'
import {
  buildNativeProjectBriefCreatePayload,
  buildNativeProjectCreatePayload,
  createNativeProjectFromIntake,
  emptyNativeProjectIntake,
  NATIVE_PROJECT_DEFAULT_APPROVAL_RULES,
  NATIVE_PROJECT_DEFAULT_NEXT_LANE,
  NATIVE_PROJECT_REQUIRED_ERROR,
  nativeProjectIntakeList,
  nativeProjectSlug,
  parseNativeProjectIntake,
  validateNativeProjectIntake
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
    expect(parsed.approvalRules).toEqual([
      ...NATIVE_PROJECT_DEFAULT_APPROVAL_RULES,
      'Ask before payment changes'
    ])
    expect(parsed.approvalRules).toContain(jennyActionPolicyBriefRule())
    expect(parsed.policyDecision).toBe('ASK')
    expect(parsed.policyMatches).toEqual(['payment, checkout, or refund action', 'customer outreach or delivery'])
    expect(parsed.policyReview).toBe(
      'Action policy review: APPROVAL_GATED_LANE (ASK) payment, checkout, or refund action; customer outreach or delivery.'
    )
    expect(parsed.constraints).toEqual([
      'Action policy review: APPROVAL_GATED_LANE (ASK) payment, checkout, or refund action; customer outreach or delivery.',
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

  it('validates required native project fields before writing records', async () => {
    const validation = validateNativeProjectIntake(emptyNativeProjectIntake())
    const createProject = vi.fn()
    const createProjectBrief = vi.fn()

    await expect(
      createNativeProjectFromIntake(emptyNativeProjectIntake(), { createProject, createProjectBrief })
    ).resolves.toEqual({
      error: NATIVE_PROJECT_REQUIRED_ERROR,
      parsed: validation.parsed
    })
    expect(createProject).not.toHaveBeenCalled()
    expect(createProjectBrief).not.toHaveBeenCalled()
  })

  it('creates the native project and initial brief through one shared submit helper', async () => {
    const value = {
      ...emptyNativeProjectIntake(),
      approval: 'Ask before payment changes',
      evidence: 'passing tests',
      forbidden: 'payment mutation',
      goal: 'Make Jenny safer to use from native chat.',
      name: 'Jenny OS',
      source: 'Hermes repo',
      success: 'project sessions grouped'
    }
    const createProject = vi.fn(async () => ({
      project: {
        name: 'Jenny OS Live',
        project_id: 'project-jenny-os-live'
      }
    }))
    const createProjectBrief = vi.fn(async () => ({ stored: true }))

    await expect(createNativeProjectFromIntake(value, { createProject, createProjectBrief })).resolves.toMatchObject({
      projectId: 'project-jenny-os-live',
      projectName: 'Jenny OS Live'
    })
    expect(createProject).toHaveBeenCalledWith({
      current_goal: 'Make Jenny safer to use from native chat.',
      mistakes_guards: 'payment mutation',
      name: 'Jenny OS',
      next_recommended_lane: NATIVE_PROJECT_DEFAULT_NEXT_LANE,
      project_id: 'project-jenny-os',
      source_of_truth: 'Hermes repo',
      status: 'active'
    })
    expect(createProjectBrief).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Jenny OS Live initial brief',
        project_id: 'project-jenny-os-live'
      })
    )
  })
})
