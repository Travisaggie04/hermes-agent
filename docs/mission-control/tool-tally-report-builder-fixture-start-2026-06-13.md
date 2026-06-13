# Tool & Tally Report Builder Fixture Start - 2026-06-13

This is a read-only start note for the Tool & Tally report-engine fixture
recovery lane. It does not approve checkout, payment writes, customer delivery,
outreach sends, production deploys, worker/timer starts, live report
fulfillment, or report-builder rewrites.

## Worktree Inspected

- Path: `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- Branch: `fix/tooltally-delivery-review-dry-run-qa`
- HEAD: `098e816 fix(tooltally): repair delivery review dry-run QA`
- Status: dirty recovery worktree with local operation artifacts.

Modified files observed:

- `qa/check_pdf_blank_sparse_pages.py`
- `reports/builders/build_tvic_report_package.py`
- `scripts/build_paid_request_with_locked_tvic_builder.py`
- `scripts/create_tooltally_report_job_from_paid_order.py`
- `scripts/run_tooltally_report_quality_agent.py`

Untracked local operation artifacts observed:

- `operations/tooltally_report_engine_dry_run_20260605T173227Z/`
- `operations/tooltally_report_engine_local_fixture_20260605T173402Z/`
- `operations/tooltally_restore_dry_run_2026-06-06/`
- `operations/tooltally_restore_operating_capability_status_2026-06-06.md`

## Report Builder Guardrail

The report builder is protected. Do not refactor, replace, simplify, or alter
report scoring, section ordering, template copy, or artifact naming until the
fixture/golden-output baseline exists and a before/after output diff proves the
change is safe.

Current protected builder path:

- `reports/builders/build_tvic_report_package.py`

Important existing signal:

- `reports/industry_profiles/tvic_industry_profile_seeds_2026-05-15.json`
  already says not to wire profile seeds into `build_tvic_report_package.py`
  until a baseline report QA / montage comparison plan is run.

## Existing Fixture Evidence

Known local fake paid-order fixture:

- `operations/tooltally_report_engine_local_fixture_20260605T173402Z/fake_paid_order_queue_v0_1.csv`

Fixture row summary:

- request: `ttrq_local_fixture_20260606`
- package: `level_1_website_checkup`
- business: `Riverview Roofing Example`
- URL: `https://example.invalid/riverview-roofing`
- status: `paid_queued`
- stripe mode: `test_mock_local_only`
- auto email: `false`
- customer delivery: `false`
- note: local fake paid-order fixture only; do not email, deliver, or call live
  services.

Existing test surface:

- `tests/test_tooltally_report_engine_local_dry_run.py`
- `tests/test_tooltally_paid_order_to_report_job.py`
- `tests/test_tooltally_report_quality_agent.py`

Existing status report said the safe gate had previously run with these local
checks passing, but the current shell could not rerun them because system Python
does not have `pytest` and this worktree has no `.venv` or `venv` visible.

## Current Known Blockers

From the restore status and read-only inspection:

1. The report-builder runtime is not reproducible in the current shell because
   `weasyprint`/test dependencies are not available.
2. The paid-order report scaffold and quality-agent expected filename had a
   mismatch in prior status:
   - produced: `source_order_snapshot.json`
   - expected: `source_request_snapshot.json`
3. Checkout remains blocked and must stay blocked until fixture report
   generation, manifest proof, and QA gates pass.
4. Outreach remains no-send and should stay separate from report-builder
   fixture recovery.

## Next Safe Implementation Slice

Jenny should run this as a local-only Tool & Tally fixture lane:

1. Create or locate a pinned local Python environment for the Tool & Tally
   recovery worktree.
2. Install only the report-builder/test dependencies needed for local fixture
   generation and pytest; do not touch production services.
3. Run the focused fixture tests:
   - `tests/test_tooltally_report_engine_local_dry_run.py`
   - `tests/test_tooltally_paid_order_to_report_job.py`
   - `tests/test_tooltally_report_quality_agent.py`
4. Reproduce the local fake paid-order fixture through the locked TVIC builder.
5. Capture a golden-output baseline:
   - manifest,
   - generated HTML/PDF paths,
   - PDF text assertions,
   - page count,
   - artifact names,
   - quality-agent result.
6. If the scaffold naming mismatch still exists, fix only that specific
   mismatch and capture the before/after fixture diff.
7. Stop before checkout, customer delivery, or outreach.

## Safety Confirmation

This inspection performed:

- no report-builder code changes,
- no checkout/payment/customer action,
- no outreach send,
- no live report delivery,
- no production deploy,
- no worker/timer start,
- no environment/package install,
- no secrets inspection or printing.
