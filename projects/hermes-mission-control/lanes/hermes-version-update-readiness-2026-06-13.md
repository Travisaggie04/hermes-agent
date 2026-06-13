# Hermes Version Update Readiness Lane - 2026-06-13

## Purpose

Prepare a safe Hermes update path for Travis's laptop and Jenny's VPS without
mixing version changes into Mission Control record/schema work.

## Current Evidence

- Accepted-live head after today's planning and room-journal work:
  `8d16650d3282cae9d47a155a6ae9e43c2e28165f`.
- Local package version in `pyproject.toml`: `0.16.0`.
- Desktop UI observed by Travis still displays `v0.16.0`.
- Public repository tags are date-based; newest tag observed by API:
  `v2026.5.16`.
- GitHub Releases API returned no `latest` release object for this repo, so
  the update source must be verified from the updater/install path rather than
  assuming a GitHub Release.

## Scope

Inventory and update:

- Travis laptop desktop app.
- Jenny VPS Hermes runtime / dashboard runtime.
- Installed CLI/runtime version metadata.
- Update channel/source used by the desktop updater.

## Safe Sequence

1. Inventory current versions before changing anything:
   - laptop desktop app version,
   - laptop CLI/runtime version,
   - VPS dashboard runtime head/path,
   - VPS gateway runtime head/path,
   - installed package version in the active runtime,
   - available upstream updater target.
2. Identify update source:
   - desktop updater manifest or installer source,
   - repo tag/commit if updater maps to Git tags,
   - package/index source if updater maps to package distribution.
3. Update laptop first if the desktop updater is the lowest-risk path.
4. Smoke-check laptop Mission Control:
   - app opens,
   - Mission Control loads,
   - bridge status still visible,
   - no dispatch/session-send enabled unexpectedly.
5. Prepare a non-live VPS runtime at the chosen update target.
6. Validate the non-live runtime before switching:
   - dashboard starts locally,
   - bridge/status endpoints work,
   - record store reads legacy and current record shapes,
   - Mission Control assets contain expected markers.
7. If needed, switch dashboard runtime only.
8. Do not restart or switch gateway without a separate explicit gateway lane.
9. Append exactly one `AcceptedBaselineRecord` only after successful validation.

## Hard Stops

- No gateway restart in this lane.
- No dispatch/session-send.
- No Waha/social posting/scheduler actions.
- No checkout/payment/customer/outreach changes.
- No hidden worker/timer/daemon enablement.
- No secret printing.
- No in-place mutation of the current accepted runtime.

## Required Checks

- Desktop: app version, Mission Control render, bridge status render.
- VPS: `hermes-dashboard.service` active after any dashboard-only switch.
- VPS: `hermes-gateway.service` remains unchanged unless a later gateway lane
  explicitly approves it.
- Record store: read succeeds against live records.
- Rollback: previous dashboard runtime path and head are captured before switch.

## Recommended Next Prompt

Ask Jenny to run a read-only version inventory first:

```text
Run a read-only Hermes version inventory lane. Do not update, deploy, restart,
switch runtimes, mutate records, dispatch/session-send, use Waha, or print
secrets. Report laptop/desktop update target if visible from repo/updater
metadata, VPS dashboard runtime path/head, gateway runtime path/head, active
package version, available repo tags or updater manifest target, and the safest
separate update sequence. If any update would require gateway restart, mark it
as a separate blocked lane.
```

