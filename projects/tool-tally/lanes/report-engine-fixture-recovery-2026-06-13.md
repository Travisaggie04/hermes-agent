# Lane Packet - Tool & Tally Report Engine Fixture Recovery

Project ID: `project-tool-tally`

Lane ID: `lane-tool-tally-report-engine-fixture-recovery-2026-06-13`

## Objective

Recover Tool & Tally by stabilizing deterministic report generation before
checkout, customer delivery, or outreach resume.

## Research Finding Incorporated

The Tool & Tally research identifies report generation as the first-class
product surface. Checkout and outreach should remain disabled until the report
engine can produce deterministic fixture-based proof packs.

## Scope

Local-only recovery work:

- inventory the current report engine,
- preserve current report-builder behavior until fixture evidence exists,
- identify the renderer and dependency path,
- create or verify a pinned report environment,
- build fixture corpus,
- normalize artifact naming,
- generate report packages locally,
- add report QA checks.

## Recommended Recovery Order

1. Keep checkout off and outreach no-send.
2. Treat the report builder as protected:
   - do not refactor, replace, or simplify report-builder logic before a
     fixture/golden-output baseline exists,
   - do not change scoring, section ordering, template copy, or artifact naming
     without a before/after fixture diff,
   - preserve existing report quality behavior unless a failing fixture proves a
     specific correction is needed.
3. Inventory the current report-builder path and all inputs/outputs:
   - builder scripts,
   - templates,
   - scoring/ranking logic,
   - browser-capture inputs,
   - PDF/rendering dependencies,
   - historical sample reports,
   - local operation artifacts.
4. Containerize or otherwise pin report dependencies:
   - Python,
   - WeasyPrint,
   - fonts,
   - Pango/HarfBuzz dependencies,
   - browser dependencies if screenshots are needed.
5. Build local fixtures:
   - sample site data,
   - screenshots,
   - expected audit outputs,
   - expected artifact names,
   - expected report metadata.
6. Add at least one golden-output proof:
   - known fixture input,
   - expected manifest,
   - expected PDF/text assertions,
   - expected artifact names,
   - allowed nondeterministic fields documented explicitly.
7. Separate browser evidence capture from PDF rendering.
8. Add report manifest per run:
   - fixture ID,
   - order ID,
   - customer slug,
   - artifact type,
   - expected filename,
   - content hash.
9. Add QA gates:
   - HTML preview check,
   - visual diff,
   - PDF extracted text,
   - page count,
   - artifact naming proof,
   - failure-mode tests.

## Recommended Tool Direction

- Browser capture/audit: Playwright.
- Accessibility: axe-core.
- Lab performance: Lighthouse CI or Unlighthouse.
- Field data: CrUX API.
- Deep outside-in check: WebPageTest when needed.
- PDF rendering: WeasyPrint primary, Playwright PDF fallback only.
- PDF inspection: pypdf/pdfplumber.
- No-send email QA later: Mailpit.

## Allowed

- Read-only repo audit.
- Local fixture creation.
- Local report dry-runs.
- Tests and docs.
- Minimal report-builder fixes only after a fixture proves the defect and the
  before/after output diff is captured.
- Sandbox design review without live activation.

## Forbidden Without Explicit New Approval

- Broad report-builder rewrite or template redesign.
- Report scoring, section order, copy, or artifact naming changes without
  fixture/golden-output evidence.
- Turning checkout on.
- Payment writes, charges, refunds, or customer delivery.
- Customer outreach sends.
- Production deploy.
- Public launch changes.
- Secrets inspection or printing.

## Acceptance Evidence

- Report-builder inventory with exact source files and runtime dependencies.
- At least one fixture/golden-output baseline.
- Fixture-based report dry-run result.
- Before/after diff for any report-builder behavior change.
- Artifact manifest proof.
- PDF quality checks.
- Explicit blockers if WeasyPrint or naming still fails.
- Next lane recommendation for sandbox checkout or no-send outreach only after
  report proof passes.

## Win Condition

Tool & Tally can produce a deterministic report proof pack locally, making the
future checkout/outreach recovery path safe and evidence-based.
