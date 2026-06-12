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

Run a read-only recovery audit and define safety gates for report generation,
checkout, and outreach before any live reactivation.
