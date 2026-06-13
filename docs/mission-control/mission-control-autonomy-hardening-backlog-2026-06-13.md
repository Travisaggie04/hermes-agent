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

## Recommended Next Build Lanes

1. Add a Mission Control status badge for "merged but not deployed" versus
   "deployed and accepted".
2. Add report-contract completeness checks to show missing evidence fields.
3. Add Challenge Review categories so Jenny can challenge wrong approaches more
   consistently.
4. Add a project-scoped request ID display and copy button in Project Rooms.
5. Add a read-only bridge transcript view grouped by project and request ID.

## Morning Definition Of Done

A good morning result is not full autonomy. It is:

- four project lanes visible,
- project contexts isolated,
- latest plans/inventories accepted,
- bridge path usable without paste-by-Travis as the long-term direction,
- next engineering backlog clear,
- no protected action taken accidentally.
