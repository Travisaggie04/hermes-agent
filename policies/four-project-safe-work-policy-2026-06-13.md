# Four-Project Safe Work Policy - 2026-06-13

This policy applies to the current four-project recovery and planning run.
It supersedes the overnight policy for new 2026-06-13 work, while keeping the
same protected-surface boundaries.

## Purpose

Codex may coordinate the overall run. Jenny may perform bounded repo/runtime
checks, review low-risk PRs, and prepare safe follow-up lanes. Mission Control
is the operating surface and source-of-truth view.

## Allowed

- Create branches, commits, and draft PRs.
- Review PRs and CI.
- Merge low-risk docs, planning, schema, tests, and UI PRs after review and
  green CI.
- Perform Mission Control dashboard-only deploy/runtime switches when bounded
  and needed.
- Run read-only audits for Shorts, Long-form Video, and Tool & Tally.
- Create local fixtures, dry-runs, schemas, tests, docs, and report packets.
- Use GitHub bridge/mailbox messages as context transport.

## Allowed With Care

- Local repo mutations in non-live worktrees.
- Test-only fixture generation.
- Dashboard UI changes that do not add execution authority.
- Manual-start bridge checks that do not dispatch sessions or start workers.

## Forbidden Without Explicit New Approval

- Gateway restart or gateway runtime switch.
- Dispatch, session-send, or Waha action.
- Social posting, live scheduling, social API sends, or account mutation.
- TikTok developer/app changes.
- Checkout enablement, payment writes, charges, refunds, or customer-facing
  commercial mutation.
- Customer outreach by email, text, DM, ads, or any external channel.
- Production deploys outside bounded Mission Control dashboard-only updates.
- Model routing changes.
- Hidden worker, timer, daemon, cron, retry scheduler, or always-on poller.
- Secrets inspection, printing, copying, or transport.
- Broad cleanup or production mutation unrelated to the current lane.

## Stop Rules

Stop and request explicit approval if a lane:

- touches a forbidden surface,
- cannot name its project ID,
- lacks a brief or challenge-review basis,
- lacks allowed actions, forbidden actions, and stop conditions,
- cannot produce an evidence packet,
- would make irreversible or customer-facing changes.

## Reporting Contract

Every lane report must include:

- project ID,
- request ID or lane ID,
- scope completed,
- changed files or evidence paths,
- checks/tests run,
- protected surfaces not touched,
- remaining risks/blockers,
- next recommended lane.
