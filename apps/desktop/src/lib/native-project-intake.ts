import type { MissionControlProjectBriefCreatePayload, MissionControlProjectCreatePayload } from '@/hermes'
import {
  jennyActionPolicyBriefRule,
  jennyActionPolicyForText,
  jennyActionPolicyReviewConstraint,
  type JennyActionPolicyDecision
} from '@/lib/jenny-action-policy'

export interface NativeProjectIntakeValue {
  approval: string
  evidence: string
  forbidden: string
  goal: string
  name: string
  source: string
  success: string
}

export interface NativeProjectIntakeParsed {
  approval: string[]
  approvalRules: string[]
  constraints: string[]
  evidence: string[]
  forbidden: string[]
  goal: string
  name: string
  policyDecision: JennyActionPolicyDecision
  policyMatches: string[]
  policyReview: string
  projectId: string
  source: string
  success: string[]
}

export interface NativeProjectCreateDependencies {
  createProject: (
    payload: MissionControlProjectCreatePayload
  ) => Promise<{ project: { name?: null | string; project_id?: null | string } }>
  createProjectBrief: (payload: MissionControlProjectBriefCreatePayload) => Promise<unknown>
}

export interface NativeProjectCreateResult {
  parsed: NativeProjectIntakeParsed
  projectId: string
  projectName: string
}

export interface NativeProjectIntakeValidation {
  error: string
  parsed: NativeProjectIntakeParsed
}

export const NATIVE_PROJECT_REQUIRED_ERROR = 'Project name and goal are required.'

export const NATIVE_PROJECT_DEFAULT_APPROVAL_RULES = [
  'Jenny must challenge vague, risky, or wrong-approach requests before implementation.',
  'Jenny must define evidence, tests, rollback/stop conditions, and approval needs before broad work.',
  jennyActionPolicyBriefRule()
] as const

export const NATIVE_PROJECT_DEFAULT_NEXT_LANE = 'Start with a spec-first project setup review.'

export function emptyNativeProjectIntake(): NativeProjectIntakeValue {
  return {
    approval: '',
    evidence: '',
    forbidden: '',
    goal: '',
    name: '',
    source: '',
    success: ''
  }
}

export function nativeProjectSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'project'
}

export function nativeProjectIntakeList(value: string): string[] {
  return value.split(/\r?\n|,/).map(item => item.trim()).filter(Boolean)
}

export function parseNativeProjectIntake(value: NativeProjectIntakeValue): NativeProjectIntakeParsed {
  const name = value.name.trim()
  const goal = value.goal.trim()
  const source = value.source.trim()
  const success = nativeProjectIntakeList(value.success)
  const forbidden = nativeProjectIntakeList(value.forbidden)
  const evidence = nativeProjectIntakeList(value.evidence)
  const approval = nativeProjectIntakeList(value.approval)
  const policyEvaluation = jennyActionPolicyForText(
    [goal, source, success.join('\n'), approval.join('\n'), forbidden.join('\n')].filter(Boolean).join('\n')
  )
  const policyReview = jennyActionPolicyReviewConstraint(policyEvaluation)
  const approvalRules = [...NATIVE_PROJECT_DEFAULT_APPROVAL_RULES, ...approval]
  const constraints = [
    ...(policyEvaluation.decision === 'ALLOW' ? [] : [policyReview]),
    ...evidence.map(item => `Evidence required: ${item}`),
    ...approval.map(item => `Approval/stop rule: ${item}`)
  ]

  return {
    approval,
    approvalRules,
    constraints,
    evidence,
    forbidden,
    goal,
    name,
    policyDecision: policyEvaluation.decision,
    policyMatches: [...policyEvaluation.matches],
    policyReview,
    projectId: `project-${nativeProjectSlug(name)}`,
    source,
    success
  }
}

export function validateNativeProjectIntake(value: NativeProjectIntakeValue): NativeProjectIntakeValidation {
  const parsed = parseNativeProjectIntake(value)

  return {
    error: parsed.name && parsed.goal ? '' : NATIVE_PROJECT_REQUIRED_ERROR,
    parsed
  }
}

export function buildNativeProjectCreatePayload(parsed: NativeProjectIntakeParsed): MissionControlProjectCreatePayload {
  return {
    current_goal: parsed.goal,
    mistakes_guards: parsed.forbidden.join('; '),
    name: parsed.name,
    next_recommended_lane: NATIVE_PROJECT_DEFAULT_NEXT_LANE,
    project_id: parsed.projectId,
    source_of_truth: parsed.source,
    status: 'active'
  }
}

export function buildNativeProjectBriefCreatePayload(
  parsed: NativeProjectIntakeParsed,
  projectId: string,
  projectName: string
): MissionControlProjectBriefCreatePayload {
  return {
    approval_rules: parsed.approvalRules,
    constraints: parsed.constraints,
    forbidden_actions: parsed.forbidden,
    name: `${projectName} initial brief`,
    outcome: parsed.goal,
    project_id: projectId,
    source_of_truth: parsed.source,
    status: 'active',
    success_criteria: parsed.success
  }
}

export async function createNativeProjectFromIntake(
  value: NativeProjectIntakeValue,
  dependencies: NativeProjectCreateDependencies
): Promise<NativeProjectCreateResult | { error: string; parsed: NativeProjectIntakeParsed }> {
  const validation = validateNativeProjectIntake(value)

  if (validation.error) {
    return validation
  }

  const project = await dependencies.createProject(buildNativeProjectCreatePayload(validation.parsed))
  const projectId = project.project.project_id || validation.parsed.projectId
  const projectName = project.project.name || validation.parsed.name

  await dependencies.createProjectBrief(buildNativeProjectBriefCreatePayload(validation.parsed, projectId, projectName))

  return {
    parsed: validation.parsed,
    projectId,
    projectName
  }
}
