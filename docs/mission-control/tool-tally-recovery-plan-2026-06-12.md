# Tool & Tally Recovery Plan - 2026-06-12

This plan is for read-only recovery coordination. It does not approve checkout,
payments, customer delivery, outreach sends, deploys, worker starts, cron/timer
enablement, or public launch changes.

## Current Assessment

Tool & Tally should be treated as partially live but operationally gated.

Public pages responded from the VPS during read-only checks:

- `https://toolandtally.com/` redirected to `https://www.toolandtally.com/`
  and returned HTTP 200.
- `https://www.toolandtally.com/` returned HTTP 200.
- `https://www.toolandtally.com/request-website-checkup.html` returned HTTP
  200 after canonical redirect.
- `OPTIONS /api/report-request/start-payment` returned HTTP 204.

That means the recovery question is not "is the site reachable?" The recovery
question is whether the operating system can safely accept money, generate the
right report package, deliver it, and resume outreach without stale state or
customer-facing mistakes.

## Known Blockers

From the June 6 recovery status and read-only audit:

- checkout remained disabled,
- customer delivery remained blocked,
- no valid checkout request was posted,
- no Stripe write occurred,
- report generation failed because `weasyprint` was missing,
- paid-order job scaffolding and quality-agent inputs disagreed on artifact
  naming:
  - `source_order_snapshot.json`,
  - `source_request_snapshot.json`,
- outreach was no-send only and did not have enough contact-ready/sendable
  candidates,
- ops tables/dashboards were stale against known paid-order fulfillment
  classification,
- the recovery worktree already had modified files and local operation artifacts.

## Recovery Order

### 1. Freeze Live Mutation

Keep these disabled until all gates below pass:

- checkout,
- Stripe/payment writes,
- customer delivery,
- customer email/DM/text/outreach,
- launch/public marketing changes,
- workers/timers/cron,
- live report fulfillment.

Allowed actions:

- local tests,
- read-only website checks,
- local dry-runs with fixture data,
- docs and non-live PRs,
- status dashboards that do not mutate live state.

### 2. Preserve Dirty Worktree Evidence

Before touching Tool & Tally code, Jenny should create a read-only inventory of
the recovery worktree:

- branch,
- HEAD,
- modified files,
- untracked files,
- operation artifacts,
- last restore status,
- likely owner of each dirty change.

Do not clean, reset, or overwrite dirty files until that inventory is accepted.

Gate to pass:

- dirty changes are classified as intentional, generated artifact, stale
  operation output, or unknown.
- unknown changes are not overwritten.

### 3. Repair Local Report Generation First

The report engine is the load-bearing product. Checkout cannot be re-enabled if
paid report delivery is unreliable.

Required checks:

- confirm whether `weasyprint` is required, optional, or replaceable,
- document exact install/runtime dependency for PDF generation,
- reconcile `source_order_snapshot.json` vs `source_request_snapshot.json`,
- run a local-only paid-order fixture through the report builder,
- run the quality agent on the generated report package,
- capture artifact paths and QA results,
- verify no customer delivery path is called.

Gate to pass:

- one local-only paid-order fixture produces a complete report package,
- quality agent passes or returns a bounded blocker list,
- generated package includes all expected source snapshots,
- no Stripe/customer/outreach/live route is touched.

### 4. Rebuild Operational Truth

The ops tables/dashboards were stale against known paid-order closeout facts.
Do not rely on stale dashboards for launch decisions.

Required checks:

- rebuild local status tables from accepted closeout facts,
- mark which records are source-of-truth and which are derived,
- identify any paid-order states that cannot be reconciled,
- produce a "ready for checkout?" projection that defaults to false.

Gate to pass:

- no unresolved paid-order classification mismatch,
- no unknown delivery obligations,
- dashboard says checkout disabled until report fixture gate passes.

### 5. Checkout Dry-Run Gate

Only after report generation and operational truth pass:

- verify checkout configuration without secrets exposure,
- test non-writing route shape where possible,
- confirm webhook handling can be tested against fixtures,
- confirm failure states are safe and visible,
- confirm no accidental charge path is reachable from Mission Control.

Gate to pass:

- explicit Travis approval for any real payment/Stripe write,
- one fixture checkout event maps to a local report job without customer
  delivery,
- rollback/disable instructions are documented.

### 6. Outreach Recovery Gate

Outreach should remain no-send until report delivery is proven.

Required checks:

- inventory contact candidates,
- classify sendable vs not-sendable,
- verify source provenance,
- draft outreach templates only,
- verify unsubscribe/compliance posture,
- require explicit approval before any send.

Gate to pass:

- enough contact-ready candidates exist,
- no stale or scraped-low-confidence candidates are queued,
- every outbound template has a clear product promise that the report engine can
  actually fulfill,
- explicit Travis approval before first send.

## Next Safe Lane

Start with a local-only report engine recovery lane:

1. Inventory dirty Tool & Tally recovery worktree.
2. Reproduce the `weasyprint` / artifact-name blockers locally.
3. Fix or document the smallest report-generation blocker.
4. Produce one local fixture report package and quality-agent result.
5. Return a safety report.

Do not touch checkout, Stripe, customer delivery, or outreach sends in that
lane.

## Morning Definition Of Done

A good morning outcome is:

- Tool & Tally recovery order is documented,
- report-generation blocker is understood or narrowed,
- dirty worktree risk is inventoried,
- checkout remains disabled,
- outreach remains no-send,
- next safe implementation lane is clear.
