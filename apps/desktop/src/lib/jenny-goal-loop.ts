export const JENNY_GOAL_LOOP_ID = 'jenny_os_goal_loop_v1'

export const JENNY_GOAL_LOOP_CHECKPOINTS = [
  'state the active lane and current milestone before long work',
  'report meaningful progress after completed checkpoints',
  'record evidence, tests, PRs, and runtime/build state before claiming completion',
  'resume from the latest checkpoint after compaction, restart, or tool-call limits'
] as const

export const JENNY_GOAL_LOOP_STOP_RULES = [
  'do not mark work complete until every explicit requirement has evidence',
  'do not mark work blocked unless the same blocker repeats and no safe progress remains',
  'do not start protected actions without the shared action policy approval path',
  'do not replace Travis visible chat with hidden harness text'
] as const

export function jennyHiddenGoalLoopContext(): string {
  return [
    `Goal loop: ${JENNY_GOAL_LOOP_ID}.`,
    `Checkpoint rules: ${JENNY_GOAL_LOOP_CHECKPOINTS.join('; ')}.`,
    `Stop rules: ${JENNY_GOAL_LOOP_STOP_RULES.join('; ')}.`
  ].join('\n')
}
