# Four-Project Day Plan - 2026-06-13

This plan converts the morning research reports into actionable project lanes.
It is a planning and coordination artifact, not approval for live posting,
checkout, outreach, gateway changes, or hidden automation.

## Current Baseline

Authoritative branch:

- `accepted-live/approval-safety-5ad8906`

Current accepted-live head observed from Codex:

- `512d2f46d5b1be9bb8680578d6624ccbb15ad9e2`

Latest accepted dashboard runtime from the prior run:

- `/home/jenny/.hermes/hermes-runtime-report-contract-7b3b1ba`

Gateway runtime remains intentionally unchanged:

- `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe`

## Operating Decision

Use Hermes / Mission Control as the primary build lane. Treat Shorts,
Long-form Video, and Tool & Tally as bounded proof/audit lanes until their
respective safety gates pass.

The research supports this posture:

- Mission Control needs a stricter source-of-truth and challenge system before
  more autonomy.
- Shorts needs quality and monetization gates before volume or posting.
- Long-form needs a deterministic proof style before full character animation
  or full episodes.
- Tool & Tally needs report-engine proof before checkout or outreach.

## Project 1 - Hermes / Mission Control

Project ID: `project-hermes-mission-control`

### Finalized Goal

Make Jenny more reliable as a project orchestrator by improving typed state,
challenge behavior, evidence contracts, and tool policy.

### Today Lane

`projects/hermes-mission-control/lanes/room-journal-challenge-policy-2026-06-13.md`

### Plan

1. Define Mission Control room contract.
2. Add append-only journal/event schema.
3. Add typed challenge-review categories and blocking verdicts.
4. Add report-contract completeness warnings.
5. Add tool-policy manifest with approval gates.
6. Add regression checks for stale state, wrong-lane authority, missing
   challenge review, and missing evidence.

### Win Condition

Mission Control can prove why a lane is safe or blocked from durable
artifacts, not from chat memory.

## Project 2 - Short-form Videos

Project ID: `project-shorts-video`

### Finalized Goal

Create a revenue-oriented 25-video queue and quality/scheduler audit before
any live posting resumes.

### Today Lane

`projects/shorts-video/lanes/research-quality-scheduler-audit-2026-06-13.md`

### Plan

1. Audit Lane A and scheduler/poster in read-only or shadow mode.
2. Build 25-video queue as five lanes of five:
   buyer-intent demos, comparisons, before/after proofs, trend response with
   original angle, and credibility/personality shorts.
3. Add quality gate fields:
   hook, originality, monetization path, provenance, AI disclosure, platform
   fit, and CTA.
4. Design a manual-start research loop.
5. Keep TikTok implementation out of scope until developer approval recovery.

### Win Condition

The team knows the next 25 shorts to make and what scheduler safety gaps must
be fixed before live posting resumes.

## Project 3 - Long-form Videos

Project ID: `project-long-form-video`

### Finalized Goal

Prove a repeatable long-form visual system through a 10-15 second mechanism
explainer before attempting full episodes or character animation.

### Today Lane

`projects/long-form-video/lanes/mechanism-explainer-proof-2026-06-13.md`

### Plan

1. Commit to faceless documentary/explainer as the first production format.
2. Run local tool preflight.
3. Prepare or build one 10-15 second mechanism-explainer proof.
4. Use deterministic tools first:
   Resolve, Inkscape, FFmpeg/ffprobe, faster-whisper/WhisperX, Subtitle Edit.
5. Use ComfyUI/Wan/FramePack only as optional inserts.

### Win Condition

The proof shows whether the style can scale before the team spends effort on a
full long-form episode.

## Project 4 - Tool & Tally

Project ID: `project-tool-tally`

### Finalized Goal

Recover deterministic report generation before checkout, customer delivery, or
outreach resume.

### Today Lane

`projects/tool-tally/lanes/report-engine-fixture-recovery-2026-06-13.md`

### Plan

1. Keep checkout off.
2. Keep outreach no-send.
3. Inventory the report engine and renderer path.
4. Create pinned local/containerized report environment.
5. Build fixture corpus and artifact manifest.
6. Run local report package generation and QA gates.

### Win Condition

Tool & Tally can produce a deterministic local report proof pack with correct
artifact naming and reviewable PDF quality evidence.

## Work Order

1. Hermes / Mission Control room/journal/challenge/tool-policy lane.
2. Tool & Tally report-engine fixture recovery lane.
3. Shorts 25-video queue and scheduler shadow audit lane.
4. Long-form mechanism-explainer proof lane.

The reason Tool & Tally comes before video production is commercial risk: its
checkout/outreach recovery depends on report determinism, and current safety
gates keep all customer-facing actions blocked.

## Protected Actions

Follow:

- `policies/four-project-safe-work-policy-2026-06-13.md`

No lane may use this plan to authorize:

- gateway restart,
- dispatch/session-send,
- Waha/social posting,
- live scheduler activation,
- TikTok app changes,
- checkout enablement,
- payment writes,
- customer outreach,
- production deploy outside bounded dashboard-only Mission Control,
- hidden worker/timer/daemon/cron,
- secrets access.

## Coordination Prompt

Use this packet when asking Jenny to coordinate the day:

```text
Coordinate today using accepted-live as source of truth. Treat Hermes / Mission
Control as the primary build lane and Shorts, Long-form Video, and Tool & Tally
as bounded audit/proof lanes.

Start by reviewing the new 2026-06-13 four-project day plan and lane packets.
Recommend the first safe implementation PR for Hermes / Mission Control:
room contract, append-only journal schema, typed challenge-review gate,
report-contract completeness warnings, or tool-policy manifest.

For Shorts, Long-form, and Tool & Tally, do not perform live actions. Return
bounded next-lane packets only. Keep social posting, scheduling, TikTok app
changes, checkout, payment, customer outreach, gateway restart, dispatch,
Waha, workers, timers, daemons, cron, model routing, secrets, and broad
production mutation blocked.

Report back with: recommended first PR, safety concerns, tests/checks to run,
and any lane that should be split before work starts.
```
