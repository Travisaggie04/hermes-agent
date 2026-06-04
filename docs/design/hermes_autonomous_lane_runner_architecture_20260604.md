# Hermes Autonomous Lane Runner Architecture

Date: 2026-06-04

## Purpose

This document specifies a future autonomous lane runner for Hermes Mission
Control. The lane runner should reduce copy/paste control blocks and make
Hermes manage Jenny/Codex work safely by turning each bounded task into a
machine-checkable Task Control Envelope, enforcing lane boundaries at every
high-risk step, and producing compact evidence before any completion claim.

This is a design document only. It does not implement runtime enforcement,
tool-call interception, file-write guards, dashboard behavior, tests, commits,
deployment behavior, or production execution wiring.

## Problem Statement

Current bounded work relies on humans repeatedly copying control blocks into
Discord or chat. That keeps Travis in the loop, but it is fragile:

- Control blocks can be omitted, shortened, or interpreted from stale context.
- Workers can drift into adjacent lanes such as testing, cleanup, deploy, or
  remote inspection after a narrow documentation or inventory request.
- Dirty worktrees and wrong worktrees are found late, after edits or tests.
- Evidence for "done", "safe", "docs-only", or "ready to commit" is scattered
  across chat logs instead of attached to the task.
- Token-heavy context loading can pull in unrelated files, generated artifacts,
  sibling worktrees, or quarantined paths.

The autonomous lane runner should make Hermes the coordinator for this safety
protocol. Jenny remains the bounded coding worker, but Hermes owns the task
packet, approval posture, guard decisions, evidence records, and dashboard
state.

## Source Of Truth: Task Control Envelope

The Task Control Envelope is the single source of truth for a running lane. Chat
history, thread names, prior approvals, dashboard hints, and worker memory may
provide background, but they do not authorize actions outside the active
envelope.

Minimum envelope fields:

```yaml
schema: mission_control.task_control_envelope.v1
task:
  id: string
  title: string
  source: string
  created_at: string
repo:
  path: string
  branch: string
  head: string | null
lane:
  active_lane: string
  mode: string
  allowed_actions: [string]
  forbidden_actions: [string]
  other_threads_excluded: [string]
  stop_condition: string
approval:
  tier: auto | semi_auto | manual
  slice_id: string
  expires_at: string | null
paths:
  allowed_write_paths: [string]
  forbidden_paths: [string]
  quarantined_path_denylist: [string]
  allowed_dirty_paths: [string]
context:
  max_context_files: integer
  max_context_bytes: integer
  generated_file_patterns: [string]
  parent_scan_allowed: boolean
evidence:
  required_cards: [string]
  produced_cards: [string]
```

Envelope action names should use the same canonical action vocabulary as the
Goal Contract / Approval Slice work: discuss, plan, inspect_repo, read_files,
search_files, edit_files, run_focused_tests, run_broad_tests, run_build,
run_lint, run_dev_server, browser_qa, install_dependencies, change_config,
touch_secrets, commit, push, open_pr, deploy, restart_service, public_bind,
oauth_connector, external_network, and destructive_git.

The envelope must be immutable once a lane starts. Any expansion requires a new
approval slice or a new envelope revision with a fresh Start Gate.

## Lane State Machine

The lane runner should model each task as an explicit state machine:

```text
created
  -> start_gate_pending
  -> blocked_start_gate | ready
ready
  -> context_loading
  -> blocked_context | running
running
  -> awaiting_approval | blocked_guard | validating | completing
validating
  -> blocked_validation | completing
completing
  -> completed | blocked_completion
awaiting_approval
  -> ready | stopped
blocked_*
  -> stopped | awaiting_approval
```

State rules:

- `created`: envelope exists but has not been checked.
- `start_gate_pending`: only operating instructions, envelope data, and
  locality/status checks are allowed.
- `blocked_start_gate`: path, branch, HEAD, dirty-state, mode, or approval
  conflicts prevent work.
- `ready`: the lane can perform only actions explicitly allowed by the
  envelope.
- `context_loading`: context is being selected under path, token, and generated
  file constraints.
- `blocked_context`: required context is unavailable without crossing a
  forbidden path or action category.
- `running`: tool calls and file reads/writes are guarded by the active
  envelope.
- `awaiting_approval`: the requested next action needs a higher approval tier
  or a new slice.
- `blocked_guard`: Tool Guard rejected a tool call, write, test, git, remote,
  or deploy action.
- `validating`: only envelope-approved verification actions may run.
- `blocked_validation`: allowed validation failed or required validation cannot
  run.
- `completing`: Evidence Cards and final state are checked before handoff.
- `completed`: final report produced; no further actions without a new
  envelope.
- `stopped`: lane is intentionally ended or blocked for user decision.

## Approval Tiers

The lane runner should support three approval tiers.

| Tier | Meaning | Allowed examples | Must stop before |
|---|---|---|---|
| `auto` | Hermes may proceed without asking when the envelope and guards pass. | discussion, planning, read-only status, docs-only edits to named files | tests, dependency changes, commits, remotes, deploys, secrets |
| `semi_auto` | Hermes may perform low-risk local work, but must checkpoint before validation or external effects. | narrow code/docs edits, focused local tests when explicitly allowed | broad tests, commits, pushes, restarts, deploys, secrets |
| `manual` | A human approval slice is required for each named high-impact action. | commit-only, push, deploy, restart, OAuth, public bind, destructive git | any action not named in the manual slice |

Tiers are ceilings, not defaults. A manual tier does not allow every manual
action; it only allows the exact action categories and paths named in the
envelope.

## Start Gate Responsibilities

The Start Gate is the first enforcement point. It should run before context
loading, editing, tests, cleanup, commits, remote probes, restarts, or deploys.

Responsibilities:

- Validate that required envelope fields are present.
- Confirm actual path, git root, branch, and optional HEAD match the envelope.
- Read `git status --short --branch --untracked-files=all`.
- Allow only exact dirty paths listed by the envelope.
- Block dirty files in forbidden or quarantined paths.
- Confirm active lane, mode, allowed actions, forbidden actions, excluded
  workstreams, and stop condition are non-empty and consistent.
- Create or update a Start Gate Evidence Card.
- Produce a PASS/BLOCKED decision before any lane work begins.

The Start Gate should be pure and read-only. It must not clean, stage, revert,
switch branches, install dependencies, run tests, or repair state.

## Tool Guard Responsibilities

The Tool Guard is the per-action runtime boundary for the lane runner. It
should evaluate every tool call against the active envelope before the call is
allowed.

Responsibilities:

- Map each tool call to canonical action categories.
- Check tool action categories against `allowed_actions` and
  `forbidden_actions`.
- Enforce path allowlists, write allowlists, generated-file restrictions, and
  quarantined path denylist.
- Block parent-directory scans that could cross into sibling or quarantined
  worktrees.
- Require manual approval for secrets, OAuth, public binds, destructive git,
  pushes, deploys, and service restarts.
- Require a validation checkpoint before completion when the envelope requires
  evidence.
- Record allow/block decisions as Evidence Cards when useful for audit.

Tool Guard decisions should be deterministic and explainable: given an envelope
and a proposed tool action, the validator should return allow/block plus
specific reasons.

## Evidence Card Schema

Evidence Cards are compact proof records attached to a lane. They should be
bounded, redacted, and display-safe.

```yaml
schema: mission_control.evidence_card.v1
card_id: string
task_id: string
kind: start_gate | guard_decision | diff_summary | validation | secret_scan | completion | blocked
claim: string
repo_path: string
branch: string
head: string
action_categories: [string]
commands_or_sources:
  - label: string
    command: string | null
    source_path: string | null
observed_output_summary: string
files_inspected: [string]
files_changed: [string]
result: pass | blocked | fail | skipped
redaction_notes: string
limitations: string
created_at: string
```

Evidence Cards must not embed large command logs, secrets, full generated
artifacts, raw tokens, or unrelated context. They point to bounded summaries
and artifact metadata instead.

## Dashboard State Card And UI Panels

The dashboard should show lane state without becoming a second execution
surface. It should help Travis see whether Jenny is safe to continue.

Recommended panels:

- Active Envelope Card: task id, lane, mode, approval tier, stop condition,
  allowed actions, forbidden actions, excluded threads.
- Start Gate Panel: path, branch, HEAD, dirty files, allowed dirty files,
  PASS/BLOCKED decision, timestamp.
- Lane State Panel: current state, last transition, next permitted actions,
  pending approval request if any.
- Tool Guard Panel: most recent allowed and blocked decisions with reasons.
- Evidence Cards Panel: cards grouped by kind with pass/fail/skipped status.
- Path Safety Panel: allowed write paths, forbidden paths, quarantined denylist,
  generated file patterns, parent-scan posture.
- Usage Panel: context file count, bytes loaded, token budget estimate, and
  skipped context due to budget or generated-file rules.
- Completion Panel: changed files, verification performed, skipped checks,
  residual risks, and whether a later commit-only slice is safe.

The dashboard may display and request approvals, but execution authority should
still come from the active envelope and approval slice.

## Token And Usage Conservative Context Rules

Context loading should preserve tokens and avoid accidental scope expansion.

Rules:

- Load the envelope, nearest operating instructions, and explicitly named files
  before broader search.
- Prefer file names, headings, schemas, and short excerpts over whole large
  files.
- Never load generated website/API artifacts unless they are explicitly in the
  allowed context list.
- Apply `max_context_files` and `max_context_bytes` from the envelope.
- Summarize prior Evidence Cards instead of replaying full logs.
- Stop when required context would exceed the envelope budget.
- Do not traverse parent directories to find sibling worktrees or unrelated
  files unless `parent_scan_allowed` is true and the target path is explicitly
  in scope.
- Treat quarantined paths as denylisted even for read-only context unless the
  envelope explicitly names a quarantine-inspection lane.

## Quarantined Path Denylist And Parent-Scan Prevention

The lane runner should maintain an envelope-level path denylist. Example
patterns:

```yaml
quarantined_path_denylist:
  - "**/QUARANTINED_DO_NOT_USE_*"
  - "**/.hub/quarantine/**"
  - "**/quarantine/**"
  - "**/*.old.*"
```

Parent-scan prevention should block context loaders and search tools from
walking above the required repo root, then discovering sibling worktrees,
backup checkouts, generated website artifacts, or quarantine folders. If a task
needs another worktree, it must use a new envelope whose repo path names that
worktree directly.

For file writes, denylist matches should be hard blocks. For file reads,
denylist matches should be blocks unless the active lane is explicitly a
quarantine or security inspection lane.

## Enforcement Points

The future runner should enforce the active envelope at these points:

- Before lane start: validate envelope, approval tier, path, branch, HEAD, and
  dirty state through Start Gate.
- Before context load: enforce path scope, generated-file rules, token limits,
  parent-scan prevention, and quarantined denylist.
- Before tool call: classify the action category and check approval tier,
  allowed actions, forbidden actions, and path scope.
- Before file write: require `edit_files`, check write allowlist, block
  generated files and quarantined paths, and reject writes outside repo root.
- Before tests: require the exact test category allowed by the envelope; stop
  when broad tests, dev servers, or browser QA would exceed the slice.
- Before git, remote, or deploy: require manual approval for commit, push,
  open_pr, deploy, restart_service, public_bind, external_network, or
  destructive_git.
- Before completion: require Evidence Cards for start gate, diff scope,
  verification or skipped verification, secret scan when text changed, and
  final status.

## First Implementation Slice

The first implementation slice should be limited to schema plus pure validators
only.

Allowed scope for that slice:

- Define Task Control Envelope and Evidence Card schema objects.
- Define canonical lane states, action categories, approval tiers, and
  transition validation.
- Add pure validation functions that accept data structures and return
  structured PASS/BLOCKED/ERROR decisions.
- Add pure path-safety validators for allowed paths, forbidden paths,
  quarantined denylist, generated file patterns, and parent-scan prevention.
- Add tests for validators.

Explicitly out of scope for the first slice:

- No production execution wiring.
- No model/tool interception.
- No file-write hooks.
- No dashboard UI.
- No gateway/Discord behavior changes.
- No CLI commands.
- No persistence migrations.
- No tests that run real tools, git mutations, network calls, deploys, or
  restarts.

## Tests Required

The implementation slice should include focused unit tests for:

- Missing required envelope fields block lane start.
- Wrong repo path, wrong branch, and wrong HEAD block Start Gate validation.
- Dirty files are allowed only when they exactly match allowed dirty paths.
- Dirty files in forbidden or quarantined paths block validation.
- Action categories outside allowed actions block tool validation.
- Explicit forbidden actions override otherwise allowed categories.
- Auto, semi-auto, and manual approval tiers gate the expected categories.
- Parent-scan attempts above repo root are rejected.
- Generated files are skipped or blocked unless explicitly allowed.
- Evidence Card records reject oversized logs and secret-like values.
- State transitions reject invalid jumps and require approval where needed.

Tests should be pure unit tests. They should not modify the real worktree, call
remote systems, run production tools, or depend on the live dashboard.

## Risks And Stop Conditions

Risks:

- Overly broad default actions could turn the runner into an unsafe automation
  surface.
- Path matching bugs could allow writes into generated files, sibling
  worktrees, or quarantined directories.
- Dashboard approval buttons could be mistaken for authority if they are not
  tied to envelope revisions.
- Evidence Cards could leak secrets if summaries are not redacted and bounded.
- Token-conservative context loading could omit relevant instructions if
  priority rules are wrong.
- Pure validators could drift from runtime behavior if later wiring bypasses
  them.

Stop conditions:

- Any required envelope field is missing or contradictory.
- Actual path, repo root, branch, or expected HEAD differs from the envelope.
- Dirty files exist outside explicitly allowed dirty paths.
- Any requested action requires a forbidden action category.
- Any tool call, context load, or file write touches a quarantined path.
- Any parent scan would leave the required repo root.
- Tests, git, remote access, deployment, restart, secrets, or cleanup are
  needed but not named in the approval slice.
- Evidence needed for completion cannot be produced within the allowed lane.

## Non-Enforcement Statement

This document is a specification artifact. It records the intended architecture
for a later implementation slice. It does not change Hermes production
behavior, add runtime guards, run tests, touch quarantined worktrees, modify
generated website files, commit, push, deploy, restart services, or perform
remote access.
