# Four-Project Authority Inventory - 2026-06-12

This inventory records the best-known source paths for the overnight
four-project run. It is a routing aid for Mission Control and Jenny; it is not
permission to mutate any protected surface.

## Global Safety

Allowed tonight:

- Mission Control / Hermes docs, UI, bridge, and non-live tooling work.
- Read-only audits for Shorts, Long-form, and Tool & Tally.
- Low-risk PRs after review and green CI.
- Bounded dashboard-only runtime switches when needed.

Forbidden without a separate explicit approval:

- Gateway restart.
- Dispatch or session-send.
- Waha or social sends.
- Live posting or live scheduling.
- Checkout/payment/customer delivery/customer outreach.
- Model routing changes.
- Hidden worker, timer, daemon, cron, or always-on automation.
- Secrets inspection or printing.

## Hermes / Mission Control

Project ID: `project-hermes-mission-control`

Authority paths:

- Local Codex working repo:
  `C:\Users\Travis\Documents\Codex\2026-06-12\how-do-we-connect-you-to\work\hermes-agent`
- Accepted-live branch:
  `accepted-live/approval-safety-5ad8906`
- Live dashboard runtime observed before this inventory:
  `/home/jenny/.hermes/hermes-runtime-github-bridge-mailbox-944411a`
- Live gateway runtime observed before this inventory:
  `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe`
- GitHub bridge mailbox transport:
  PR #79 conversation thread in `Travisaggie04/hermes-agent`

Current evidence:

- PR #80 merged: manual GitHub bridge operator commands.
- PR #81 merged: overnight four-project runbook and context packs.
- A dashboard runtime switch is not required for PR #81 because it is docs-only.
- PR #80 is CLI/operator-path work; the older live runtime can still poll the
  bridge with the pre-existing command, but it does not contain the newer
  `notify-jenny-now` helper until a future bounded runtime refresh.

Recommended next lane:

- Build a Mission Control status/readiness surface that makes the four project
  lanes visible without enabling execution.
- Keep bridge work manual-start and foreground-only until Travis approves a
  stronger autonomy level.

## Short-Form Videos

Project ID: `project-shorts-video`

Authority paths:

- Primary implementation repo:
  `/home/jenny/wt/agentic-video-channel-factory`
- Strategy/ops brain:
  `/home/jenny/ai-ops-brain/social-video/signal-room`
- Important review packages:
  `/home/jenny/wt/agentic-video-channel-factory/review-packages`
- Queue/runtime state:
  `/home/jenny/wt/agentic-video-channel-factory/runtime`

Current evidence:

- Repo status observed read-only:
  `main...origin/main [ahead 32]` with untracked `runtime/`.
- `README.md` defines the system as a reliability-first video channel control
  plane with SQLite state, manifest files, deterministic drafts, QA checklists,
  and dry-run publish packages.
- `docs/signal-room-pipeline-registry.md` says Lane A is the only approved
  short-form production pipeline.
- `docs/signal-room-social-publishing-automation.md` says queue automation is
  intentionally non-posting and uses a local ledger.
- `tools/SIGNAL_ROOM_ALLOWED_PRODUCTION_PATH.md` says the active Shorts path is
  Lane A / new-tools Shorts stack only.
- Distribution notes say YouTube is canonical, Meta/Instagram readiness was
  verified in the past, Facebook queue growth is paused, and TikTok remains
  disabled waiting approval.

Important constraint:

- Do not loosen Lane A gates just to refill the queue. If no eligible packages
  exist, plan a backfill or regeneration lane rather than bypassing quality
  locks.

Recommended next lane:

- Read-only Shorts audit:
  - inspect Lane A package eligibility,
  - inspect queue ledger health,
  - identify why the 25-video queue is empty or exhausted,
  - produce a new 25-concept slate strategy,
  - recommend quality improvements and future autoresearch design,
  - perform no posting, scheduling, token readout, or account mutation.

## Long-Form Videos

Project ID: `project-long-form-video`

Authority paths:

- Shared implementation repo:
  `/home/jenny/wt/agentic-video-channel-factory`
- Long-form working notes:
  `/home/jenny/ai-ops-brain/social-video/the-signal-room/long-form`
- Historical long-form worktrees:
  `/home/jenny/wt/signal-room-longform-*`
- Historical review packages:
  `/home/jenny/wt/agentic-video-channel-factory/review-packages/signal-room-longform-*`

Current evidence:

- `docs/signal-room-pipeline-registry.md` states the long-form pipeline is
  separate and not completed yet.
- The same registry says long-form needs its own quality lock, metadata
  contract, queue ledger, backlog rules, and scheduler before automation.
- Prior attempts exist in multiple `signal-room-longform-*` worktrees and
  review packages.

Recommended next lane:

- Read-only long-form decision memo:
  - summarize why prior long-form attempts failed,
  - compare animated stories, faceless explainers, documentary/explainer,
    character-driven formats, business/finance/news, and impossible-footage
    style concepts,
  - rank by agentic feasibility, monetization, quality, and repeatability,
  - recommend one small proof lane,
  - do not upload, schedule, purchase software, mutate accounts, or start
    hidden workers.

## Tool & Tally

Project ID: `project-tool-tally`

Authority paths:

- Best current recovery worktree:
  `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- Business OS notes:
  `/home/jenny/ai-ops-brain/business/tool-tally-review-packages`
- Quarantined/generated historical state:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-generated-state-20260530`
- Dirty inventory quarantine:
  `/home/jenny/ai-ops-brain/quarantine/tooltally-dirty-inventories`

Current evidence:

- The recovery worktree is not clean. Observed modified files:
  - `qa/check_pdf_blank_sparse_pages.py`
  - `reports/builders/build_tvic_report_package.py`
  - `scripts/build_paid_request_with_locked_tvic_builder.py`
  - `scripts/create_tooltally_report_job_from_paid_order.py`
  - `scripts/run_tooltally_report_quality_agent.py`
- The recovery worktree also has local operation artifact folders.
- `operations/tooltally_restore_operating_capability_status_2026-06-06.md`
  says the website was reachable, checkout remained disabled, webhook was not
  invoked, no checkout/payment was created, and customer delivery remained
  blocked.
- Report generation was blocked by missing `weasyprint` and a
  `source_order_snapshot.json` vs `source_request_snapshot.json` mismatch.
- Outreach prep exists in no-send mode, but contact-ready/sendable candidates
  were insufficient and all real-send flags remained false.

Important constraint:

- Treat this as a recovery audit lane until Jenny accounts for the dirty
  worktree and current live flags. Do not turn checkout on, do not send
  outreach, do not deliver reports, and do not deploy customer-facing changes.

Recommended next lane:

- Read-only Tool & Tally recovery audit:
  - confirm current branch, dirty files, and intended owner of existing edits,
  - verify report-builder dependency gap,
  - verify paid-order artifact naming mismatch,
  - inspect stale ops-table/dashboard classification,
  - inspect no-send outreach readiness,
  - produce a recovery order with gates for report engine, checkout, and
    outreach.

## Open Questions

- Whether `/home/jenny/wt/agentic-video-channel-factory` should be treated as
  one shared implementation repo for both Shorts and Long-form, or split into
  project-specific branches/worktrees before new changes.
- Whether Tool & Tally's dirty recovery worktree should become the accepted
  recovery baseline or be recreated from a clean origin/main worktree with the
  known fixes reapplied.
- Whether the PR #80 bridge helper should be deployed to a new dashboard/runtime
  worktree even though the current bridge poll path already works.
