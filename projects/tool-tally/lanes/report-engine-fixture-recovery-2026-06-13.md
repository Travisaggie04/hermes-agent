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
- identify the renderer and dependency path,
- create or verify a pinned report environment,
- build fixture corpus,
- normalize artifact naming,
- generate report packages locally,
- add report QA checks.

## Recommended Recovery Order

1. Keep checkout off and outreach no-send.
2. Containerize or otherwise pin report dependencies:
   - Python,
   - WeasyPrint,
   - fonts,
   - Pango/HarfBuzz dependencies,
   - browser dependencies if screenshots are needed.
3. Build local fixtures:
   - sample site data,
   - screenshots,
   - expected audit outputs,
   - expected artifact names,
   - expected report metadata.
4. Separate browser evidence capture from PDF rendering.
5. Add report manifest per run:
   - fixture ID,
   - order ID,
   - customer slug,
   - artifact type,
   - expected filename,
   - content hash.
6. Add QA gates:
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
- Sandbox design review without live activation.

## Forbidden Without Explicit New Approval

- Turning checkout on.
- Payment writes, charges, refunds, or customer delivery.
- Customer outreach sends.
- Production deploy.
- Public launch changes.
- Secrets inspection or printing.

## Acceptance Evidence

- Fixture-based report dry-run result.
- Artifact manifest proof.
- PDF quality checks.
- Explicit blockers if WeasyPrint or naming still fails.
- Next lane recommendation for sandbox checkout or no-send outreach only after
  report proof passes.

## Win Condition

Tool & Tally can produce a deterministic report proof pack locally, making the
future checkout/outreach recovery path safe and evidence-based.
