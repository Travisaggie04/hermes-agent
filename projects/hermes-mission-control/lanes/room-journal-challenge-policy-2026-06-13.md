# Lane Packet - Mission Control Room, Journal, Challenge, And Tool Policy

Project ID: `project-hermes-mission-control`

Lane ID: `lane-hermes-room-journal-challenge-policy-2026-06-13`

## Objective

Make Jenny more reliable as an orchestration agent by strengthening the
Mission Control source-of-truth model before adding more autonomy.

## Research Finding Incorporated

The deep research recommendation argues against a large agent OS, free-form
multi-agent teams, or hidden autonomy right now. The safer path is a small
orchestration core with room-scoped specs, typed report contracts,
append-only events, challenge gates, tool allowlists, approval gates, and
regression checks.

## Scope

Build or plan the next safe PRs around:

- a Mission Control room contract,
- append-only journal/event schema,
- typed challenge-review contract with blocking verdicts,
- report/evidence contract completeness checks,
- tool policy manifest and approval stub surface,
- regression tests for stale state, wrong-lane authority, and missing evidence.

## Preferred Implementation Order

1. Add room contract docs/schemas:
   - room brief,
   - accepted facts,
   - specs,
   - decisions,
   - reports,
   - mailbox items,
   - append-only journal.
2. Add journal event schema and renderer/projection tests.
3. Add typed challenge-review categories:
   - wrong approach,
   - missing context,
   - protected surface,
   - scope split required,
   - questions required before lane draft.
4. Add report-contract completeness warnings.
5. Add tool policy manifest:
   - read-only,
   - analysis-only,
   - draft-only,
   - local mutation,
   - external mutation,
   - approval required.

## Allowed

- Docs, schemas, tests, UI warnings, read-only renderers.
- Low-risk Mission Control dashboard UI changes.
- Draft PRs and reviewed merges after CI passes.
- Dashboard-only runtime switch if needed and separately bounded.

## Forbidden Without Explicit New Approval

- Gateway restart or switch.
- Dispatch/session-send.
- Waha/social/payment/customer action.
- Hidden worker/timer/daemon/cron.
- Secrets access.
- Broad production mutation.

## Acceptance Evidence

- PR summary describes source-of-truth impact.
- Tests prove append-only records are not mutated.
- Challenge gate blocks missing or unsafe review states.
- Report-contract warnings appear without granting execution authority.
- Safety scan confirms no new dispatch, gateway, worker, timer, Waha, social,
  payment, or secret path.

## Win Condition

Mission Control can show why a project lane is safe or blocked from durable
artifacts, not from chat memory or stale summaries.
