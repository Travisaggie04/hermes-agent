# Tonight Four-Project Safety Policy

This policy applies to the 2026-06-12 overnight four-project run.

## Allowed

- Create PRs.
- Review PRs.
- Merge low-risk UI, docs, planning, bridge, and non-live tooling PRs after
  review and green CI.
- Mission Control dashboard-only deploy/runtime switch if bounded and needed.
- Read-only audits and planning for Shorts, Long-form, and Tool & Tally.

## Forbidden Without Explicit Travis Approval

- Gateway restart.
- Dispatch or session-send.
- Waha sends.
- Social posting or live scheduling.
- Payment, checkout, charge, refund, or customer-facing commercial mutation.
- Customer outreach by email, text, DM, ads, or any external channel.
- Model routing changes.
- Hidden worker, timer, daemon, cron, or always-on automation.
- Secrets inspection or printing.
- Broad production mutation.

## Stop Rule

If a proposed lane touches any forbidden surface, stop and request explicit
approval before continuing.
