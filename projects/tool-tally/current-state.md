# Tool & Tally Current State

Project ID: `project-tool-tally`

## Goal

Create a safe plan to bring Tool & Tally back online.

Tool & Tally is a website that generates reports for customers' websites. The
report generation pipeline is the critical component and had significant work
invested to produce good reports.

## Current Status

The system was working before Jenny broke, but Travis shut it down. Everything
was live before, but checkout is currently turned off.

## Recovery Areas

- Report generation pipeline.
- Website health.
- Checkout readiness.
- Outreach workflow recovery.

## Authoritative Paths

- Recovery worktree: `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- Business OS notes: `/home/jenny/ai-ops-brain/business/tool-tally-review-packages`
- Historical/generated state:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-generated-state-20260530`
- Dirty inventory quarantine:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-dirty-inventories`

Observed evidence:

- The recovery worktree had existing modified files and local operation
  artifacts when checked read-only.
- Last restore status kept checkout disabled, customer delivery blocked, and
  outreach in no-send mode.
- Report dry-run was blocked by missing `weasyprint` and paid-order artifact
  naming mismatch.

## Tonight's Lane

Read-only recovery planning lane.

Allowed tonight:

- Read-only audit of repo, config, docs, and status if authoritative paths are
  found.
- Report pipeline design review.
- Website, checkout, and outreach audit.
- Identify stale or broken parts.
- Write recovery plan and safety gates.
- PRs for docs, planning, or non-live checks.

Forbidden tonight:

- Turning checkout back on.
- Payment or charge changes.
- Customer messages.
- Email, text, DM, ads, or outreach sends.
- Public launch changes.
- Customer-facing deploys without explicit approval.
- Secrets inspection or printing.

## First Recommended Work

Start with
`projects/tool-tally/lanes/report-engine-fixture-recovery-2026-06-13.md`.
The report builder is protected: do not refactor, replace, simplify, or alter
report scoring/templates/artifact naming until a fixture/golden-output baseline
exists and a before/after diff proves the change is safe.

Use `docs/mission-control/tool-tally-recovery-plan-2026-06-12.md` as the current
recovery order. It keeps checkout, payment writes, customer delivery, and
outreach disabled until the local report-generation and operational-truth gates
pass.

Latest read-only inventory:

- `docs/mission-control/tool-tally-report-engine-inventory-2026-06-12.md`
- `docs/mission-control/tool-tally-report-builder-fixture-start-2026-06-13.md`

That inventory confirms the current recovery worktree is still focused on
paid-order-to-report-job conversion, report package building, PDF quality, and
quality-agent acceptance. The next safe implementation lane is local-only report
engine recovery against fixture data.
