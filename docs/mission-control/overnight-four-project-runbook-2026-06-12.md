# Overnight Four-Project Runbook - 2026-06-12

This runbook captures Travis's overnight operating plan for Mission Control,
Jenny, Codex, and the four active project domains. It is intentionally
conservative: Mission Control remains the source of truth, and risky live
actions stay gated.

## Global Goal

Coordinate tonight's four-project Mission Control planning run with:

- Hermes / Mission Control as the primary build lane.
- Short-form Videos as a read-only planning and audit lane.
- Long-form Videos as a read-only planning, research, and proof-design lane.
- Tool & Tally as a read-only recovery planning lane.

The work may continue overnight until Travis stops it.

## Global Permissions

Allowed tonight:

- Codex and Jenny may create PRs.
- Jenny may mark low-risk PRs ready after review and green CI.
- Low-risk UI, docs, planning, bridge, and non-live tooling PRs may be merged
  after review and green CI.
- Mission Control dashboard-only deploys or runtime switches are allowed if
  needed and bounded.
- Read-only audits, specs, runbooks, and project plans are allowed for all four
  projects.

Forbidden unless Travis explicitly approves later:

- Gateway restart.
- Dispatch or session-send.
- Waha or social send actions.
- Social posting or scheduling live posts.
- Customer outreach, email, SMS, DM, ads, or public launch actions.
- Payment, checkout enablement, charges, or customer-facing commercial changes.
- Model routing changes.
- Hidden worker, timer, daemon, cron, or always-on automation.
- Broad production mutation.
- Secrets inspection or printing.

## Operating Rules

1. Each project must remain scoped to its own project ID.
2. Each request must have a unique request ID.
3. Build work belongs primarily to Hermes / Mission Control.
4. The other three projects should return plans, evidence, and safe next lanes,
   not live actions.
5. Jenny should challenge vague or unsafe direction before drafting a lane.
6. No project may borrow authority from another project room.
7. Merge and deploy lanes must stay separate from planning or review lanes.
8. If any lane touches a protected surface, stop and ask for explicit approval.

Protected surfaces include gateway restart, dispatch, Waha, social accounts,
payment, checkout, customer outreach, production deploys, workers, timers,
model routing, secrets, and public/customer-facing changes.

## Project 1 - Hermes / Mission Control

Project ID: `project-hermes-mission-control`

Goal tonight:

Make as much progress as practical on Mission Control, the UI, and making Jenny
more stable, reliable, and autonomous as an orchestration agent above the other
agents.

Known problem:

Jenny started out-of-box, then became unstable as the system grew. The failure
pattern included regressions, split-brain behavior, weak orchestration, and
too much reliance on Travis manually copy/pasting between tools.

Desired morning outcome:

Visible, durable progress toward a robust Mission Control operating surface and
a safer Codex/Jenny bridge workflow.

Allowed:

- Low-risk UI improvements.
- Mission Control record and project-room hardening.
- Bridge hardening.
- Docs and runbooks.
- Tests and review gates.
- Dashboard-only deploy/runtime switch if needed and bounded.

Forbidden without explicit approval:

- Gateway restart.
- Direct dispatch/session-send.
- Hidden autonomous worker/timer.
- Waha, social posting, payment, customer outreach, or model routing changes.

First recommended lane:

Review PR #80, finish the manual GitHub bridge operator path, and then define
the next narrow Mission Control UI or bridge-hardening PR.

## Project 2 - Short-form Videos

Project ID: `project-shorts-video`

Goal tonight:

Plan improvements to the agentic short-form video generation pipeline so it can
produce better revenue-oriented content.

Current status:

The pipeline worked but quality is poor. The poster/scheduler worked before but
appears to have issues now. The 25-video queue for YouTube, Facebook, and
Instagram is empty or exhausted. TikTok developer approval was rejected and
needs a future fix.

Strategic direction:

Travis is not locked into explainers. The objective is revenue. The plan should
compare niches and formats by production feasibility, quality, monetization
potential, and ability to improve through feedback.

Desired morning outcome:

A clear audit plan, gap list, and practical 25-video queue strategy. No live
posting.

Allowed:

- Read-only audit of the current system.
- File, repo, docs, and config review.
- 25-video queue plan.
- Tooling and skill recommendations.
- Design for future autoresearch loops inspired by Karpathy-style continuous
  research, without enabling hidden timers tonight.

Forbidden:

- Posting or scheduling live posts.
- Social account mutation.
- TikTok developer/app approval changes.
- Social API sends.
- Hidden automation.
- Customer-facing or payment actions.
- Deploy/restart without explicit approval.

First recommended lane:

Run a read-only shorts pipeline audit and return the highest-ROI changes plus a
25-video concept queue plan.

## Project 3 - Long-form Videos

Project ID: `project-long-form-video`

Goal tonight:

Plan a high-quality agentic long-form video production approach that can earn
clicks and retention.

Current status:

Three previous attempts failed. Travis has a Windows laptop with an Nvidia 5080
and has explored or downloaded tools including Moho, DaVinci Resolve, Inkscape,
and Cavalry.

Strategic direction:

Travis is not locked into animation. The plan should challenge whether
animation is the right path and compare agentically feasible formats such as
animated stories, faceless explainers, documentary/explainer, character comedy,
educational, business, and finance/news.

Desired morning outcome:

A research-backed toolchain and method recommendation, a gap analysis from prior
failures, and one small proof plan. No full production attempt tonight.

Allowed:

- Read-only research.
- Local capability inventory if accessible.
- Toolchain comparison.
- Specs and proof-lane design.
- Plans for future autoresearch loops, without enabling hidden timers tonight.

Forbidden:

- Live posting.
- Account mutation.
- Paid purchases.
- Hidden worker/timer automation.
- External account/API changes.
- Deploy/restart/runtime switch without explicit approval.

First recommended lane:

Produce a toolchain and format decision memo that ranks options by feasibility,
quality, monetization, and automation risk.

## Project 4 - Tool & Tally

Project ID: `project-tool-tally`

Goal tonight:

Create a safe recovery plan for Tool & Tally, a website that generates reports
for customers' websites.

Current status:

The system was working before Jenny broke, but Travis shut it down. Everything
was live before, but checkout is currently turned off.

Critical component:

The report generation pipeline is the load-bearing system and had significant
work invested to produce good reports.

Desired morning outcome:

A good plan to get Tool & Tally back up and running safely, including the
report pipeline, website, checkout, and outreach recovery order.

Allowed:

- Read-only audit of repo, config, docs, and status.
- Report pipeline design review.
- Website, checkout, and outreach audit.
- Identify stale or broken parts.
- Write recovery plan and safety gates.
- PRs for docs, planning, or non-live checks.

Forbidden:

- Turning checkout back on.
- Payment or charge changes.
- Customer messages.
- Email, text, DM, ads, or outreach sends.
- Public launch changes.
- Customer-facing deploys without explicit approval.
- Secrets inspection or printing.

First recommended lane:

Run a read-only recovery audit and define safety gates for report generation,
checkout, and outreach before any live reactivation.

## Evidence Required By Morning

Each project should have:

- Latest status summary.
- Biggest blocker or uncertainty.
- Recommended next lane.
- Explicit forbidden actions.
- Evidence paths, PRs, or record IDs when available.

Hermes / Mission Control may also have:

- PRs created or merged if reviewed and green.
- Dashboard-only runtime switch if bounded and necessary.
- Updated bridge or UI evidence.

The other three projects should not have:

- Live posting.
- Payment or checkout changes.
- Outreach sends.
- Customer-facing mutations.
- Hidden automation.

## Initial Context Packs

`docs/mission-control/context-repo-structure-v1.md` defines the desired
token-efficient structure for project context:

- `projects/hermes-mission-control/current-state.md`
- `projects/shorts-video/current-state.md`
- `projects/long-form-video/current-state.md`
- `projects/tool-tally/current-state.md`
- `policies/tonight-four-project-safety.md`

This runbook starts that structure with current-state files based on Travis's
answers. These files are context anchors, not proof that the Shorts, Long-form,
or Tool & Tally implementation systems live in this repository.

Recommended next setup task:

- Locate the authoritative project paths for Shorts, Long-form, and Tool &
  Tally before attempting deeper audits.

Follow-up completed:

- `docs/mission-control/four-project-authority-inventory-2026-06-12.md`
  records the first authoritative path inventory and links each project to its
  safest next lane packet.
- `docs/mission-control/overnight-audit-findings-2026-06-12.md` records the
  first read-only findings from the Shorts queue, Long-form proof history, and
  Tool & Tally recovery state.
- `docs/mission-control/four-project-morning-status-2026-06-13.md` consolidates
  the current morning status, biggest blockers, next lanes, forbidden actions,
  and evidence paths for all four projects.
