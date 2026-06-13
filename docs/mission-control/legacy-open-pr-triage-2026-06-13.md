# Legacy Open PR Triage - 2026-06-13

This is a read-only triage of older open GitHub PRs. It does not merge, close,
rebase, deploy, restart, or mutate live records.

## Recommendation

Treat the older open PRs as legacy backlog, not as current ready-to-merge work.

Do not merge any of them without a fresh accepted-live rebase, scope review,
CI run, and Mission Control challenge/deploy lane. Several are stacked on old
non-accepted bases, and PR #18 is currently dirty.

## Current Accepted Surface

Current accepted-live work has already moved through the newer Mission Control
project-room, Kanban, bridge, active-lanes, report-contract, and four-project
planning lanes. The older PRs predate that current operating surface and may
represent useful ideas, but not current source-of-truth implementation.

## Open PR Inventory

| PR | Title | State | Base | Merge state | Recommendation |
|---:|---|---|---|---|---|
| #18 | PR-J: Bound governance records endpoint | draft | `pr-base/v2026.5.29.2-mission-control-records` | DIRTY | Do not merge. Re-evaluate idea against current accepted-live records API if still needed. |
| #8 | PR6: Add read-only Mission Control lane dashboard | draft | `pr5-inert-autonomous-lane-runner-policy-model` | CLEAN | Do not merge directly. Likely superseded by current Project Rooms, Kanban, and active-lanes UI. Salvage only after diff review. |
| #7 | PR5: Add inert autonomous lane runner policy model | draft | `pr4-autonomous-lane-runner-spec-packaging` | CLEAN | Do not merge directly. Compare policy model to current autonomy hardening backlog before reuse. |
| #6 | PR4: Document autonomous lane runner architecture | open | `mission-control-os-stateful-foundation` | CLEAN | Do not merge directly. Salvage docs only if still consistent with current Level 0-5 autonomy model. |
| #5 | PR3b: Add gateway recovery and reliability hardening | draft | `pr-base/a34226d6d-mission-control-split` | CLEAN | Do not merge directly. Gateway reliability touches protected runtime behavior; requires fresh review and explicit gateway lane. |
| #4 | PR2: Add Mission Control state API, panels, and local MCP policy | draft | `pr-base/a34226d6d-mission-control-split` | CLEAN | Do not merge directly. Likely superseded by current Mission Control API/UI stack. Salvage specific tests/docs only. |
| #3 | Add OR1 start gate and read-only diagnostics | open | `pr-base/a34226d6d-or1-split` | CLEAN | Do not merge directly. Rebase and review diagnostics separately if useful. |
| #2 | Add optional external repo integrations and pilot docs | open | `longform-video-production-pipeline` | CLEAN | Do not merge directly. External integrations need current safety review and project-scoped context. |
| #1 | Gate approvals and Teams report release | open | `jenny/ops-center-dashboard` | CLEAN | Do not merge directly. Approval ideas may be useful, but the branch is older than the current accepted-live control plane. |

## Safe Salvage Process

For any legacy PR:

1. Create a new branch from `accepted-live/approval-safety-5ad8906`.
2. Cherry-pick or manually port only the specific file or concept needed.
3. Keep the new PR narrow and project-scoped.
4. Run fresh CI against accepted-live.
5. Require a short review that answers:
   - what is still useful,
   - what is superseded,
   - what protected surface it touches,
   - whether it needs deploy/gateway approval.
6. Merge only the fresh PR, not the old stacked PR.

## Protected Surfaces

Legacy PRs must stop for explicit approval if they touch:

- gateway restart or recovery behavior,
- dispatch/session-send,
- Waha/social posting,
- payment/checkout/customer outreach,
- model routing,
- workers/timers/daemons/cron,
- state database mutation,
- secrets,
- deploy/runtime switch,
- AcceptedBaselineRecord behavior.

## Next Safe Lane

If cleanup is desired, create a read-only legacy-PR closure lane:

- identify which PRs are fully superseded,
- extract any salvageable docs/tests into fresh accepted-live PRs,
- then close stale PRs with a clear comment only after Travis approves closure.

Do not close them automatically tonight.
