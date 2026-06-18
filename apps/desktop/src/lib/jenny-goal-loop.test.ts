import { describe, expect, it } from 'vitest'

import {
  JENNY_GOAL_LOOP_BLOCKED_AUDIT,
  JENNY_GOAL_LOOP_CHECKPOINTS,
  JENNY_GOAL_LOOP_COMPLETION_AUDIT,
  JENNY_GOAL_LOOP_ID,
  JENNY_GOAL_LOOP_PROGRESS_REPORT,
  JENNY_GOAL_LOOP_STOP_RULES,
  jennyHiddenGoalLoopContext
} from './jenny-goal-loop'

describe('Jenny desktop goal loop context', () => {
  it('centralizes long-running goal checkpoints', () => {
    expect(JENNY_GOAL_LOOP_ID).toBe('jenny_os_goal_loop_v1')
    expect(JENNY_GOAL_LOOP_CHECKPOINTS).toContain('state the active lane and current milestone before long work')
    expect(JENNY_GOAL_LOOP_CHECKPOINTS).toContain(
      'resume from the latest checkpoint after compaction, restart, or tool-call limits'
    )
    expect(JENNY_GOAL_LOOP_STOP_RULES).toContain('do not mark work complete until every explicit requirement has evidence')
    expect(JENNY_GOAL_LOOP_STOP_RULES).toContain(
      'do not mark work blocked unless the same blocker repeats and no safe progress remains'
    )
    expect(JENNY_GOAL_LOOP_PROGRESS_REPORT).toContain('completed items')
    expect(JENNY_GOAL_LOOP_COMPLETION_AUDIT).toContain('map every explicit requirement to current evidence')
    expect(JENNY_GOAL_LOOP_COMPLETION_AUDIT).toContain('treat missing, indirect, or stale evidence as incomplete')
    expect(JENNY_GOAL_LOOP_BLOCKED_AUDIT).toContain(
      'name the exact missing input, failing command, or external dependency'
    )
  })

  it('builds hidden context without visible command wording', () => {
    const context = jennyHiddenGoalLoopContext()

    expect(context).toContain('Goal loop: jenny_os_goal_loop_v1.')
    expect(context).toContain('Checkpoints:')
    expect(context).toContain('Reports:')
    expect(context).toContain('Complete only when:')
    expect(context).toContain('Blocked only when:')
    expect(context).toContain('Stop:')
    expect(context).not.toContain('[Engineering goal kickoff]')
    expect(context).not.toContain('Spec-first request for Jenny')
  })
})
