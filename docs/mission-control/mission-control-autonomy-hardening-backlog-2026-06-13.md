# Mission Control Autonomy Hardening Backlog - 2026-06-13

This backlog converts the broad goal "make Jenny more autonomous" into staged
engineering gates. It is intentionally conservative: better autonomy means more
visible state, better challenge behavior, and tighter stop conditions before it
means more execution.

## Current Position

Mission Control now has the core shape of an operating surface:

- project rooms,
- project briefs,
- challenge reviews,
- read-only lane drafts,
- project Kanban,
- bridge records,
- manual-start bridge relay status,
- GitHub bridge mailbox,
- four-project active-lanes surface.

The remaining reliability risk is not the absence of buttons. The risk is
letting Jenny take action before Mission Control can prove which project,
which lane, which authority level, which rollback path, and which report
contract apply.

## Autonomy Principle

Jenny should gain autonomy only when each new action is:

1. scoped to one project,
2. backed by a brief and challenge review,
3. represented by an append-only lane/request record,
4. visible in Mission Control before and after work,
5. reversible or explicitly accepted as irreversible,
6. reported with evidence,
7. blocked automatically when it touches protected surfaces.

## Phase 1 - Make State Unambiguous

Goal: eliminate split-brain and stale-runtime confusion.

Build/verify:

- Mission Control shows accepted dashboard runtime, gateway runtime, rollback
  runtime, accepted head, and stale warnings in one compact status stack.
- Every project card shows latest brief, latest challenge review, latest lane
  draft, latest report, and whether the data is missing/stale.
- Active Lanes shows the four overnight projects without blending contexts.
- Project room request packets include request ID, project ID, allowed actions,
  forbidden actions, and stop conditions.

Definition of done:

- Travis can open laptop or phone and tell which project needs attention
  without reading Discord history.

## Phase 2 - Improve Challenge Quality

Goal: Jenny must challenge wrong or vague requests before work starts.

Build/verify:

- Challenge Review records require explicit fields for:
  - wrong-approach concern,
  - missing-context concern,
  - protected-surface concern,
  - scope-splitting recommendation,
  - minimum questions before lane drafting.
- Mission Control highlights `needs_spec_first`, `needs_clarification`, and
  unsafe reviews before any lane-draft action.
- Project rooms make the "safe next lane" more prominent than the raw user
  request.

Definition of done:

- A vague request like "fix the video pipeline" produces questions and a
  bounded audit lane, not a broad implementation lane.

## Phase 3 - Lane Isolation And Evidence Contracts

Goal: one lane cannot borrow authority from another project.

Build/verify:

- Lane Request records include:
  - project ID,
  - request ID,
  - authority level,
  - allowed action list,
  - forbidden action list,
  - stop conditions,
  - required report format,
  - evidence paths expected.
- Reports must link changed files, checks run, risks, and next lane.
- Mission Control flags reports that do not answer the lane contract.

Definition of done:

- A Tool & Tally recovery audit cannot accidentally authorize checkout,
  payment, outreach, or customer-facing changes.

## Phase 4 - PR And Deploy Discipline

Goal: make code work repeatable without relying on Travis as a programmer.

Build/verify:

- PR lanes are separate from review lanes and deploy lanes.
- PR summary must state scope, validation, and protected surfaces not touched.
- Deploy lanes must show:
  - accepted-live head,
  - new runtime path,
  - rollback runtime path,
  - dashboard/gateway restart scope,
  - smoke checks,
  - exactly one AcceptedBaselineRecord after success.
- Mission Control should show "ready to merge", "merged but not deployed",
  and "deployed/accepted" as different states.

Definition of done:

- Jenny can safely manage low-risk docs/UI PRs while refusing broad deploy or
  gateway changes without an explicit lane.

## Phase 5 - Manual Bridge Reliability

Goal: Codex and Jenny can exchange work packets without Travis copy/paste.

Build/verify:

- GitHub mailbox request and response records dedupe by request ID and issue.
- Foreground watch mode is bounded and visibly manual-start only.
- Bridge status panel shows pending count, last poll, last response, last
  error, and worker/timer/daemon disabled flags.
- No bridge message is trusted for execution unless it becomes a lane record
  with the normal challenge and approval gates.

Definition of done:

- Codex can send a bounded request and receive Jenny's response through the
  mailbox, while Mission Control still treats it as context, not authority.

## Phase 6 - Limited Autonomy

Goal: add execution only after the record loop is reliable.

## Phase 6A - Goal Mode Engineering Loop

Goal: make `/goal` safe for long engineering tasks Travis can let run while
Jenny remains auditable and interruptible.

Current baseline:

- `/goal` already persists a standing goal per session.
- A judge checks each completed turn and decides whether to continue.
- The loop has turn budgets plus pause, resume, status, and clear controls.
- Gateway continuation emits goal status updates and chains the next turn only
  after the current turn releases the running guard.

Build/verify before relying on it for real overnight work:

- Goal kickoff should convert broad user text into a visible engineering
  contract: objective, scope, explicit non-goals, protected surfaces, expected
  evidence, stop conditions, and user approvals needed.
- Each continuation should carry forward the latest plan state, completed
  checklist, evidence gathered, open risks, and next smallest action instead
  of only saying "continue working."
- The status stream should show concise Codex-style progress: planning,
  running checks, editing files, waiting on CI, blocked, or complete.
- Goal completion should require evidence against the contract, not just a
  confident summary.
- Blocked states should stop the loop with the exact missing input, failing
  command, or external dependency.
- The loop must keep respecting Mission Control protected surfaces:
  no gateway restart, deploy, dispatch/session-send, Waha/social/payment,
  checkout/outreach, hidden worker/timer/daemon, model routing, secrets, or
  live record deletion without a separate approved lane.
- Long goal runs should leave a compact final report suitable for Mission
  Control records: changed files, tests/checks, PRs, live/deployed state,
  residual risks, rollback path, and recommended next lane.

Definition of done:

- Travis can start a bounded engineering goal, walk away, and return to a
  clear status trail showing what Jenny did, what evidence proves it, what
  remains blocked, and whether any human approval is needed.

Candidate Level 2/3 actions:

- read-only repo audit,
- docs/context PR,
- low-risk UI PR,
- test-only bugfix PR,
- dashboard-only runtime switch after accepted deploy lane.

Still forbidden without separate explicit approval:

- gateway restart,
- dispatch/session-send,
- Waha/social posting,
- payment/checkout,
- customer outreach,
- model routing,
- hidden worker/timer/daemon,
- broad production mutation,
- secrets inspection or printing.

Definition of done:

- Jenny performs small PR lanes with evidence, and Mission Control shows every
  stage before any action can become live.

## Phase 6B - Local Model Helper Deferred

Goal: keep local LM Studio/Qwen experiments out of the active Jenny control
loop until the core desktop and phone orchestration path is stable.

Decision:

- Do not integrate a local laptop model into Mission Control, Jenny bridge
  routing, PR review, deploy decisions, or `/goal` continuations right now.
- Treat local model smoke results as lab notes only, not authority.
- If revisited later, the local model may only act as an advisory helper for
  low-risk summaries, request classification, draft challenge questions, and
  evidence checklist suggestions.

Requirements before any future integration:

- The helper must be manually enabled, project-scoped, and visibly labeled as
  advisory.
- Qwen-style prompts must use `/no_think` or an equivalent budget control when
  needed.
- Structured output must use schema validation; raw JSON prompting is not
  sufficient.
- Codex or Jenny must validate every helper output before it affects a lane.
- The helper must never approve PRs, merge, deploy, restart services, dispatch
  sessions, route models, mutate records, or touch protected surfaces.
- The helper must not run as a hidden worker, timer, daemon, or automatic
  background loop.

Definition of done before revisiting:

- Travis can use the normal Hermes desktop chat and phone surface for Jenny
  without relying on Discord or a local-model workaround.

## Recommended Next Build Lanes

1. Add a Mission Control status badge for "merged but not deployed" versus
   "deployed and accepted".
2. Add report-contract completeness checks to show missing evidence fields.
3. Add Challenge Review categories so Jenny can challenge wrong approaches more
   consistently.
4. Add a project-scoped request ID display and copy button in Project Rooms.
5. Add a read-only bridge transcript view grouped by project and request ID.
6. Harden `/goal` into the long-task engineering loop described in Phase 6A.
7. Revisit the local model helper only after Phase 6A and the native Jenny chat
   path are stable.

## Morning Definition Of Done

A good morning result is not full autonomy. It is:

- four project lanes visible,
- project contexts isolated,
- latest plans/inventories accepted,
- bridge path usable without paste-by-Travis as the long-term direction,
- next engineering backlog clear,
- no protected action taken accidentally.
