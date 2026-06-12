# Tool & Tally Report Engine Inventory - 2026-06-12

This is a read-only inventory of the Tool & Tally recovery worktree and named
evidence paths. It does not approve checkout, Stripe/payment writes, customer
delivery, outreach sends, public launch changes, deploys, worker/timer starts,
or dirty-worktree cleanup.

## Recovery Worktree

Path:

- `/home/jenny/wt/tooltally-restore-operating-capability-20260606`

Observed state:

- branch: `fix/tooltally-delivery-review-dry-run-qa`
- head: `098e8161cf093d8270b15291d7238c64d502e521`
- tracking: `origin/fix/tooltally-delivery-review-dry-run-qa`

Tracked modified files:

- `qa/check_pdf_blank_sparse_pages.py`
- `reports/builders/build_tvic_report_package.py`
- `scripts/build_paid_request_with_locked_tvic_builder.py`
- `scripts/create_tooltally_report_job_from_paid_order.py`
- `scripts/run_tooltally_report_quality_agent.py`

Untracked operation artifacts:

- `operations/tooltally_report_engine_dry_run_20260605T173227Z/`
- `operations/tooltally_report_engine_local_fixture_20260605T173402Z/`
- `operations/tooltally_restore_dry_run_2026-06-06/`
- `operations/tooltally_restore_operating_capability_status_2026-06-06.md`

## Current Blocker Evidence

The recovery worktree still points at the same load-bearing area described in
the recovery plan: paid-order-to-report-job conversion, report package building,
PDF quality, and quality-agent acceptance.

Important references found read-only:

- `operations/tooltally_restore_operating_capability_status_2026-06-06.md`
- `operations/tooltally_restore_dry_run_2026-06-06/fake_paid_order_queue_v0_1.csv`
- `operations/tooltally_report_engine_local_fixture_20260605T173402Z/fake_paid_order_queue_v0_1.csv`
- `operations/tooltally_report_engine_local_fixture_20260605T173402Z/report_draft_jobs/ttrpt_local_fixture_20260606_riverview-roofing-example/source_order_snapshot.json`
- `tests/test_tooltally_report_engine_local_dry_run.py`
- `scripts/run_tooltally_report_quality_agent.py`
- `scripts/create_tooltally_report_job_from_paid_order.py`

The quality agent currently expects both:

- `source_request_snapshot.json`
- `source_order_snapshot.json`

That confirms the previously recorded artifact-name mismatch is still central
to the recovery lane and should be resolved before checkout/customer delivery
is reconsidered.

## Existing Review Packages

Existing business review package evidence exists outside the worktree:

- `/home/jenny/ai-ops-brain/business/tool-tally-review-packages/afford-a-rooter-paid-rehearsal-20260515/`

Notable files:

- `ADAPTER_BUILD_RESULT.json`
- `JOB_REHEARSAL_RESULT.json`
- `SHA256_MANIFEST.json`
- `tvic_builder_evidence_packet.json`
- `level1_website_checkup.pdf`
- `level2_detailed_analysis.pdf`
- `level2_fix_plan_addon.pdf`
- `level3_monthly_checkup.pdf`

These are useful as known-good-or-prior proof artifacts, but they should not be
treated as proof that the current recovery worktree can fulfill a new paid order.

## Dirty Inventory Quarantine

Existing dirty-inventory quarantine exists:

- `/home/jenny/ai-ops-brain/quarantine/tooltally-dirty-inventories/`

Useful files include:

- `tooltally_dirty_inventory_20260530-164329.txt`
- `high_risk_dirty_files_20260530-164329.txt`
- `unknown_travis_review_required_20260530-164329.txt`
- `outreach_state_scripts_20260530-164329.txt`
- `worker_analytics_leftovers_20260530-164329.txt`
- `tooltally_public_site_package_plan_20260530.txt`

Before changing Tool & Tally code, Jenny should compare the current dirty files
against this quarantine so intentional recovery edits are not overwritten and
unknown changes are not silently normalized.

## Next Safe Implementation Lane

Run a local-only report-engine recovery lane in the Tool & Tally worktree:

1. Re-read `operations/tooltally_restore_operating_capability_status_2026-06-06.md`.
2. Classify each current modified file as intentional recovery work, generated
   artifact adjustment, stale operation output, or unknown.
3. Reproduce the local fixture report job using the existing fake paid-order
   queue only.
4. Reconcile `source_request_snapshot.json` and `source_order_snapshot.json`
   so the builder and quality agent agree.
5. Confirm whether `weasyprint` is required, optional, or replaceable in the
   current fixture path.
6. Run the quality agent on one local fixture package.
7. Return changed files, artifact paths, test output, blockers, and safety
   confirmation.

Hard stops remain:

- no checkout enablement,
- no Stripe/payment write,
- no customer delivery,
- no outreach send,
- no Cloudflare/public launch mutation,
- no worker/timer/cron enablement,
- no secrets inspection or printing,
- no dirty-worktree cleanup until the inventory is accepted.

