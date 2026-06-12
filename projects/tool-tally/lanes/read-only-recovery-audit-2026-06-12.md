# Read-Only Tool & Tally Recovery Audit Lane - 2026-06-12

Project ID: `project-tool-tally`

## Objective

Create a safe recovery plan for Tool & Tally without turning on checkout,
customer delivery, outreach, or public/customer-facing behavior.

## Source Paths

- Recovery worktree: `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- Business OS notes: `/home/jenny/ai-ops-brain/business/tool-tally-review-packages`
- Historical/generated state:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-generated-state-20260530`
- Dirty inventory quarantine:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-dirty-inventories`

## Known Evidence

- Recovery status file:
  `operations/tooltally_restore_operating_capability_status_2026-06-06.md`
- Checkout was disabled in the last recovery status.
- Customer delivery was blocked in the last recovery status.
- Report dry-run failed because `weasyprint` was missing and paid-order job
  artifact naming did not match the quality agent expectation.
- Outreach prep existed in no-send mode, but contact-ready/sendable candidates
  were below threshold.
- The recovery worktree had existing uncommitted edits and local operation
  artifacts when observed.

## Read-Only Tasks

1. Confirm current repo branch, HEAD, dirty files, and untracked operation
   artifacts.
2. Read the restore status and identify which blockers are still current.
3. Verify the report-builder dependency issue and paid-order artifact naming
   mismatch.
4. Inspect checkout/worker guardrail docs without calling live payment routes.
5. Inspect no-send outreach readiness without sending or enabling anything.
6. Return a recovery order with gates for:
   - report engine,
   - website status,
   - checkout,
   - customer delivery,
   - outreach.

## Hard Stops

- No checkout enablement.
- No payment/Stripe write.
- No webhook invocation.
- No customer email, DM, text, ad, or outreach send.
- No customer delivery.
- No public launch/deploy.
- No Cloudflare setting or KV mutation.
- No secrets inspection or printing.

## Expected Return

- Current status.
- Dirty-worktree risk.
- Report-engine blocker list.
- Checkout/outreach/customer-delivery gate list.
- Next safe recovery lane.
