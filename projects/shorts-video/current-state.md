# Short-form Videos Current State

Project ID: `project-shorts-video`

## Goal

Improve the agentic short-form video generation pipeline so it can create
income-producing content.

## Current Status

The system was working but quality is poor. The poster/scheduler worked before
but now appears to have issues. The 25-video queue for YouTube, Facebook, and
Instagram is empty or exhausted. TikTok developer approval was rejected and
needs a future fix.

The current niche is explainers, but Travis is not locked into that. The real
goal is to find a format and pipeline that can make money.

## Platforms

- YouTube
- Facebook
- Instagram
- TikTok, pending future developer approval recovery

## Authoritative Paths

- Implementation repo: `/home/jenny/wt/agentic-video-channel-factory`
- Strategy/ops notes: `/home/jenny/ai-ops-brain/social-video/signal-room`
- Review packages: `/home/jenny/wt/agentic-video-channel-factory/review-packages`
- Queue/runtime state: `/home/jenny/wt/agentic-video-channel-factory/runtime`

Observed evidence:

- The implementation repo was `main...origin/main [ahead 32]` with untracked
  `runtime/` when checked read-only.
- Lane A is the only approved short-form production pipeline.
- Facebook queue growth is paused in the current social automation docs.
- TikTok remains disabled pending approval recovery.

## Tonight's Lane

Read-only planning and audit lane.

Allowed tonight:

- Review current system design if authoritative paths are found.
- Identify quality and reliability gaps.
- Plan a 25-video queue.
- Recommend tools, skills, and software to improve output quality.
- Design a future autoresearch loop inspired by Karpathy-style continuous
  research, without enabling hidden timers tonight.

Forbidden tonight:

- Posting or scheduling live posts.
- Social account mutation.
- TikTok developer/app approval changes.
- Social API sends.
- Customer-facing actions.
- Payments.
- Hidden automation.
- Deploy/restart without explicit approval.

## First Recommended Work

Run `projects/shorts-video/lanes/read-only-audit-2026-06-12.md` and return a
read-only pipeline audit plus a 25-video concept queue strategy.

Use `docs/mission-control/video-production-decision-memo-2026-06-12.md` as the
current toolchain and policy decision memo. It recommends a Shorts-first quality
engine, not raw volume, because platform monetization policy rewards original,
non-repetitive content.

Use `docs/mission-control/shorts-queue-reconciliation-plan-2026-06-12.md` as
the current queue recovery plan. It keeps posting, scheduling, platform API
sends, TikTok changes, and queue mutation disabled while explaining the current
missing-slot mismatch and drafting the next 25-video slate.
