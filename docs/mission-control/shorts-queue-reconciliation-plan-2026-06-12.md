# Shorts Queue Reconciliation Plan - 2026-06-12

This plan is for read-only queue recovery. It does not approve posting,
scheduling, platform API sends, TikTok approval changes, workers, timers,
daemons, or live account mutation.

## Current Evidence

Authoritative paths:

- implementation repo: `/home/jenny/wt/agentic-video-channel-factory`
- queue ledger: `/home/jenny/wt/agentic-video-channel-factory/runtime/social_queue_state.json`
- review packages: `/home/jenny/wt/agentic-video-channel-factory/review-packages`

Read-only audit found:

- 138 candidate queue records,
- 67 posted,
- 25 disabled waiting approval,
- 24 scheduled,
- 20 queued,
- 2 manually removed from dashboard.

Platform counts:

- YouTube: 50,
- Facebook: 38,
- Instagram: 25,
- TikTok: 25.

Status reporter result:

- YouTube: 20 queued, 30 posted, 25 missing slots to reach next-five-day slate,
- Facebook: 24 scheduled, 12 posted, 25 missing slots,
- Instagram: 25 posted, 25 missing slots,
- TikTok: disabled waiting approval, 25 missing slots.

Lane A package audit:

- 202 packages scanned,
- 50 eligible,
- 152 rejected,
- 7 backfill candidates,
- 127 regenerate recommended,
- 18 blocked review-only.

## Interpretation

The queue is not simply empty. It is out of operational alignment.

The status reporter's "missing slots" likely means existing queued/scheduled
records do not satisfy the current next-five-day platform slate rules. Possible
causes:

- records are outside the target date window,
- platform-specific schedule windows are stale,
- eligible packages are not mapped to the next slate,
- platform policy disabled a surface,
- dashboard and ledger use different source-of-truth assumptions,
- old packages fail newer Lane A gates.

Do not loosen the Lane A quality gate to fill volume. The queue should be
reconciled against the gate, then refilled.

## Reconciliation Steps

### 1. Snapshot State

Create a read-only packet containing:

- ledger path and file hash,
- queue record counts by platform/status/date,
- scheduler window assumptions,
- current Lane A package count,
- dashboard status reporter output.

Gate:

- packet is evidence-only,
- no queue file writes,
- no scheduler writes,
- no platform API calls.

### 2. Explain Missing Slots

For each platform, classify every record into:

- posted historical,
- valid future scheduled,
- future queued but not scheduled,
- queued outside target window,
- stale package,
- blocked by platform gate,
- invalid package link,
- duplicate/removed.

Expected questions to answer:

- why YouTube has 20 queued but 25 missing next-five-day slots,
- why Facebook has 24 scheduled but 25 missing slots,
- whether Instagram has no future slate despite 25 posted,
- whether TikTok records are intentionally disabled only.

Gate:

- no schedule changes,
- no queue mutation,
- platform state is described, not modified.

### 3. Backfill Candidate Review

Inspect the 7 backfill candidates first.

For each candidate, return:

- package id/path,
- platform fit,
- title/hook,
- quality lock status,
- missing fields,
- whether it can be queued unchanged,
- whether it needs regeneration,
- risk reason if rejected.

Gate:

- backfill candidates are recommendations only,
- no package promotion,
- no queue write.

### 4. Review-Only Package Triage

Inspect the 18 review-only packages only after the 7 backfill candidates.

Classify them:

- promote after metadata repair,
- regenerate from concept,
- keep review-only,
- discard.

Gate:

- review-only packages do not become scheduled packages without a new quality
  lock and explicit approval.

### 5. New 25-Video Slate

If the current eligible/backfill pool cannot fill the next slate, generate a
planning-only slate:

- 5 repeatable formats,
- 5 topics per format,
- one original thesis per topic,
- one source/evidence requirement,
- one visual beat,
- one platform-specific note,
- no direct scheduling.

Recommended format families:

1. The hidden mechanism.
2. Bad advice teardown.
3. Before/after proof.
4. Tiny business autopsy.
5. Impossible but true, framed as factual explanation or reconstruction.

Gate:

- slate is concepts only until a Lane A package is generated and reviewed.

## Quality Bar

Every proposed package must have:

- explicit original thesis,
- non-generic hook,
- source/evidence anchor,
- quality lock,
- human psychology gate fields,
- clean captions,
- platform-safe metadata,
- no TikTok path unless approval is restored.

## Autoresearch Integration

Start with manual-start research reports:

- collect platform performance metrics,
- label each video by format/topic/hook/visual type,
- compare performance by platform,
- recommend next slate changes.

Do not add timers or always-on research jobs yet. Autoresearch can become a
scheduled system only after Mission Control has visible run records, stop
controls, budget/cost limits, and explicit approval gates.

## Next Safe Lane

Run a read-only queue reconciliation packet:

1. classify all current queue records against the next-five-day slate,
2. list the 7 backfill candidates,
3. explain the 25 missing slots per platform,
4. draft the 25-video slate concepts,
5. return a no-mutation report.

No posting, scheduling, queue mutation, TikTok action, or platform API write.

## Morning Definition Of Done

A good outcome is:

- current queue mismatch explained,
- backfill candidates ranked,
- 25-video slate drafted,
- quality gates preserved,
- no live platform mutation performed.
