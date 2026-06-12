# Overnight Audit Findings - 2026-06-12

This document records read-only findings gathered during the overnight
four-project run. It is evidence for planning only. It does not approve live
posting, checkout, outreach, deploys, restarts, dispatch, workers, timers, or
customer-facing mutation.

## Mission Control / Hermes

Current state:

- PR #80 merged the manual GitHub bridge operator command path.
- PR #81 merged the overnight four-project runbook and context packs.
- PR #82 was opened as a docs-only follow-up for authoritative project paths and
  safe lane packets.
- The live GitHub bridge poll path works through the current dashboard runtime:
  `/home/jenny/.hermes/hermes-runtime-github-bridge-mailbox-944411a`.

Decision:

- No dashboard runtime switch is required for PR #81 or PR #82 because both are
  docs/context-only.
- PR #80's newer helper command is useful, but the older manual poll path is
  enough for tonight. A runtime refresh for the helper can wait unless bridge
  operator friction becomes the main blocker.

Next safe build lane:

- Add Mission Control visibility for four-project lane state after the context
  records are accepted.
- Keep all bridge actions manual-start and foreground-only.

## Short-Form Videos

Authority:

- `/home/jenny/wt/agentic-video-channel-factory`
- `/home/jenny/ai-ops-brain/social-video/signal-room`

Read-only checks run:

- Inspected `runtime/social_queue_state.json`.
- Ran `python3 tools/social_queue_status.py --state runtime/social_queue_state.json`.
- Ran `python3 tools/social_queue_lane_a_audit.py --packages-root review-packages`.
- Ran `python3 tools/social_queue_lane_a_backfill_plan.py --packages-root review-packages`.
- Read the Lane A registry, social publishing automation foundation, and allowed
  production path docs.

Queue status observed:

- Queue ledger exists at `runtime/social_queue_state.json`.
- Candidate queue records found: 138.
- Status counts:
  - `posted`: 67
  - `disabled_waiting_approval`: 25
  - `scheduled`: 24
  - `queued`: 20
  - `manually_removed_from_dashboard`: 2
- Platform counts:
  - YouTube: 50
  - Facebook: 38
  - Instagram: 25
  - TikTok: 25

Status reporter result:

- YouTube:
  - `queued_count`: 20
  - `posted_count`: 30
  - `missing_slots_to_reach_25`: 25
- Facebook:
  - `scheduled_count`: 24
  - `posted_count`: 12
  - `missing_slots_to_reach_25`: 25
- Instagram:
  - `posted_count`: 25
  - `missing_slots_to_reach_25`: 25
- TikTok:
  - `disabled_waiting_approval`: expected mode
  - `missing_slots_to_reach_25`: 25

Lane A eligibility:

- `scanned_package_count`: 202
- `eligible_count`: 50
- `rejected_count`: 152
- `already_eligible_count`: 50
- `backfill_candidate_count`: 7
- `regenerate_recommended_count`: 127
- `blocked_review_only_count`: 18

Main rejection patterns:

- Missing explicit Lane A marker.
- Missing `SIGNAL_ROOM_PRODUCTION_QUALITY_LOCK.json`.
- Missing human psychology gate fields.
- Quality lock FPS below 59.
- Review-only or not-for-scheduling markers.

Planning conclusion:

- The queue problem is not a simple lack of files. There are eligible packages,
  but the next-five-day platform slots are empty from the status reporter's
  perspective, and many historical packages correctly fail the current Lane A
  gate.
- Do not loosen Lane A gates. The safe fix is a read-only queue reconciliation
  and refill plan that uses eligible packages first, then regenerates new Lane A
  packages for the missing slate.

Recommended next Shorts lane:

- Produce a queue reconciliation plan:
  - why YouTube shows 20 queued but still 25 missing next-five-day slots,
  - why Facebook has 24 scheduled but still 25 missing next-five-day slots,
  - whether eligible packages are stale, outside the target date window, or
    blocked by platform policy,
  - which seven packages are backfill candidates,
  - which new Lane A topics should be generated for the next 25-package slate.

## Long-Form Videos

Authority:

- `/home/jenny/wt/agentic-video-channel-factory`
- `/home/jenny/ai-ops-brain/social-video/the-signal-room/long-form`
- `/home/jenny/wt/signal-room-longform-*`

Read-only evidence:

- The pipeline registry says long-form is separate and not completed.
- Long-form needs its own quality lock, metadata contract, queue ledger, backlog
  rules, and scheduler before automation.
- Historical proof packages exist for pacing/realism, rural air service, and
  several long-form topics.

Useful proof evidence:

- `longform-pacing-realism-sample-2026-05-11` tested slower narration,
  section pauses, EQ, compression, loudness normalization, and lower music.
- `signal-room-longform-rural-air-service-polished-v1-2026-05-12` produced a
  367-second private review candidate with improved moving modules and direct
  narration.
- `signal-room-adult-character-rig-selection-2026-05-28` selected CC0
  Quaternius adult character candidates and identified Blender/Moho as the next
  machine-dependent pass.
- `signal-room-moho-character-fee-machine-proof-2026-05-28` proved Moho
  transparent character frames can composite over deterministic mechanism
  animation, but did not prove final brand art, facial acting, lip sync, custom
  adult style, reusable bones, or mouth switches.

Strategic split:

- Adult animated Signal Room explainers are the strongest continuity path from
  existing work.
- The "Impossible Footage" direction may be more clickable and visually broad,
  but it is still framed as Shorts-first with 3-6 minute long-form only after
  style/topic proof.

Planning conclusion:

- Do not attempt a full long-form episode next. The next proof should answer one
  production question:
  - either character acting/rig feasibility for adult animated explainers,
  - or a Shorts-first visual/topic proof for Impossible Footage.
- The adult animated path has better existing guardrails and direct continuity.
  Impossible Footage may have better hook potential, but needs stricter
  "reconstruction, not fake footage" rules.

Recommended next Long-form lane:

- Make a decision memo that compares:
  - adult animated Signal Room explainers,
  - Impossible Footage,
  - faceless/documentary explainers,
  - business/finance/news videos.
- Recommend one 10-15 second proof, not a full episode.

## Tool & Tally

Authority:

- `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- `/home/jenny/ai-ops-brain/business/tool-tally-review-packages`
- `/home/jenny/ai-ops-brain/quarantine/tooltally-generated-state-20260530`

Read-only checks run:

- Read `operations/tooltally_restore_operating_capability_status_2026-06-06.md`.
- Inspected recovery worktree status.
- Checked public website routes from the VPS with passive HTTP HEAD/OPTIONS only.

Worktree state observed:

- Branch:
  `fix/tooltally-delivery-review-dry-run-qa...origin/fix/tooltally-delivery-review-dry-run-qa`
- Modified files were present:
  - `qa/check_pdf_blank_sparse_pages.py`
  - `reports/builders/build_tvic_report_package.py`
  - `scripts/build_paid_request_with_locked_tvic_builder.py`
  - `scripts/create_tooltally_report_job_from_paid_order.py`
  - `scripts/run_tooltally_report_quality_agent.py`
- Local operation artifacts were present.

Public route checks:

- `https://toolandtally.com/` resolved to `https://www.toolandtally.com/` with
  HTTP 200 from the VPS.
- `https://www.toolandtally.com/` returned HTTP 200 from the VPS.
- `https://www.toolandtally.com/request-website-checkup.html` returned HTTP 200
  after canonical redirect.
- `OPTIONS https://www.toolandtally.com/api/report-request/start-payment`
  returned HTTP 204.

Known recovery blockers from the June 6 status:

- Checkout remained disabled.
- Customer delivery remained blocked.
- No valid checkout request was posted.
- No Stripe write occurred.
- Report generation failed because `weasyprint` was missing.
- Paid-order job scaffold and quality-agent expected filenames were misaligned:
  `source_order_snapshot.json` vs `source_request_snapshot.json`.
- Outreach was available only in no-send mode, with insufficient
  contact-ready/sendable candidates.
- Ops tables/dashboards were stale against known paid-order fulfillment
  classification.

Planning conclusion:

- Tool & Tally is not "offline"; public pages respond. The risk is operational
  correctness: checkout, report generation, paid-order classification, customer
  delivery, and outreach gates.
- The next safe lane is not launch. It is a local-only recovery audit that
  reconciles report-engine dependencies and stale state.

Recommended next Tool & Tally lane:

- Start with the report engine:
  - reproduce the `weasyprint` blocker,
  - fix or document the paid-order artifact name mismatch,
  - regenerate local-only dashboard/table status from known closeout facts,
  - keep checkout, delivery, and outreach disabled.

## Overnight Priority Order

1. Mission Control: accept the authority inventory and keep Codex/Jenny bridge
   stable.
2. Tool & Tally: report engine recovery plan, because checkout cannot reopen
   safely until the report pipeline is trustworthy.
3. Shorts: queue reconciliation and next 25-package slate planning.
4. Long-form: choose one proof path instead of restarting a full production
   attempt.

This order favors reliability before revenue actions. It avoids the failure
pattern where Jenny tries to make visible progress by touching live surfaces
before the underlying system is safe.
