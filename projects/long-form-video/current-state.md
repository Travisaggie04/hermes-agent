# Long-form Videos Current State

Project ID: `project-long-form-video`

## Goal

Find a high-quality, agentically producible long-form video method that can get
clicks, hold attention, and make money.

## Current Status

Three previous attempts at long-form video generation failed. Travis has a
Windows laptop with an Nvidia 5080 and has explored tools including Moho,
DaVinci Resolve, Inkscape, and Cavalry.

Travis is not locked into animated content. The chosen format should be based
on agentic feasibility, quality, monetization potential, and repeatability.

## Candidate Directions

- Animated stories.
- Faceless explainers.
- Documentary/explainer videos.
- Character comedy.
- Educational videos.
- Business or finance/news content.

## Authoritative Paths

- Shared implementation repo: `/home/jenny/wt/agentic-video-channel-factory`
- Long-form notes: `/home/jenny/ai-ops-brain/social-video/the-signal-room/long-form`
- Historical worktrees: `/home/jenny/wt/signal-room-longform-*`
- Historical review packages:
  `/home/jenny/wt/agentic-video-channel-factory/review-packages/signal-room-longform-*`

Observed evidence:

- The current pipeline registry says long-form is separate and not completed.
- Long-form must get its own quality lock, metadata contract, queue ledger,
  backlog rules, and scheduler before any automation.

## Tonight's Lane

Read-only planning, research, and proof-design lane.

Allowed tonight:

- Research and compare long-form formats.
- Compare toolchains.
- Inventory local capabilities if accessible.
- Create a proof plan.
- Design future autoresearch loops without enabling hidden timers tonight.

Forbidden tonight:

- Live posting.
- Account mutations.
- Paid purchases.
- Hidden worker/timer automation.
- External account or API changes.
- Deploy/restart/runtime switch without explicit approval.

## First Recommended Work

Run `projects/long-form-video/lanes/read-only-decision-memo-2026-06-12.md` and
return a toolchain and format decision memo ranked by feasibility, quality,
monetization, and automation risk.

Use `docs/mission-control/video-production-decision-memo-2026-06-12.md` as the
current decision memo. It recommends choosing one 10-15 second adult animated
Signal Room mechanism proof first, with a faceless mechanism explainer as the
fallback if local rigging blocks.

Use `docs/mission-control/long-form-proof-plan-2026-06-12.md` as the concrete
proof lane. It defines pass/fail criteria for the 10-15 second proof and keeps
full episode production, publishing, scheduling, and hidden automation disabled.

## 2026-06-13 Inventory Update

See `docs/mission-control/long-form-proof-inventory-2026-06-13.md`.

The latest read-only inventory found useful historical proof assets for the
adult animated fee-machine direction, including rig-selection, Moho compositing,
and HyperFrames scaffold packages. It also found that the historical 349-second
mixed-media proof had serious OCR/safe-area and freeze/silence warnings, which
supports keeping the next lane to a 10-15 second proof instead of restarting
full long-form production.

Observed local Windows tool state from Codex: DaVinci Resolve, Inkscape, and
Cavalry exist in standard Program Files paths, but ffmpeg/ffprobe/Python are not
on PATH from this shell, and Blender/Moho were not found in standard install
paths. The next safe lane is a local tool preflight plus adult character rig
acting gate before any render attempt.
