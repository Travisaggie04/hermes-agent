# Hermes Version Inventory - 2026-06-13

This is a read-only version inventory for Travis's laptop/Codex checkout and
Jenny's VPS runtimes. It does not approve an update, deploy, restart, runtime
switch, record mutation, dispatch/session-send, Waha action, or gateway change.

## Local Accepted-Live Checkout

- Branch: `accepted-live/approval-safety-5ad8906`
- Head: `dddb87696bc5caf4aa2aaa993c73a231d3ba2171`
- Description: `v2026.5.16-1486-gdddb87696`
- `pyproject.toml` package version: `0.16.0`
- `hermes_cli.__version__`: `0.16.0`
- `hermes_cli.__release_date__`: `2026.6.5`
- Desktop app package version in `apps/desktop/package.json`: `0.15.1`
- Root npm package version: `1.0.0`

## Public Repository Version Signals

The GitHub tags endpoint returned date-based tags. The newest observed tags
were:

| Tag | Commit |
| --- | --- |
| `v2026.5.16` | `a91a57fa5a13d516c38b07a141a9ce8a3daabeb0` |
| `v2026.5.7` | `498bfc7bc12a937621b4215312049b1000726df3` |
| `v2026.4.30` | `73bf3ab1b22314ed9dfecbb59242c03742fe72af` |
| `v2026.4.23` | `bf196a3fc0fd1f79353369e8732051db275c6276` |

`GET /repos/Travisaggie04/hermes-agent/releases/latest` returned HTTP `404`,
so there is no GitHub "latest release" object to trust as the update target.
The update source must be verified from the desktop updater/install channel or
from a specific reviewed branch/commit.

## VPS Runtime Inventory

These checks used the user service manager (`systemctl --user`) and did not
restart or switch either service.

| Service | State | Runtime | Head | Describe | Package |
| --- | --- | --- | --- | --- | --- |
| `hermes-dashboard.service` | active | `/home/jenny/.hermes/hermes-runtime-bridge-legacy-c1ef909` | `c1ef90992009e4ff4ed37ca360c3a698e46d53b7` | `v2026.5.29.2-145-gc1ef90992` | `0.16.0` |
| `hermes-gateway.service` | active | `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe` | `af1eafe23eb25eabd92496e0ea04db39e099acdf` | `v2026.5.29.2-111-gaf1eafe23` | `0.16.0` |

## Interpretation

- The desktop footer showing `v0.16.0` is consistent with the CLI/runtime
  package version, not necessarily the Electron desktop package version.
- The desktop updater may be using an installer/update channel that is separate
  from GitHub Releases. That channel still needs to be identified before
  changing laptop or VPS versions.
- The VPS dashboard is intentionally behind the current accepted-live branch
  after later docs/record work. That is not automatically an update problem:
  dashboard-only switch remains a separate deploy lane.
- The VPS gateway is intentionally older than the dashboard runtime. Updating
  or restarting the gateway is higher risk and should stay separate from
  dashboard-only work.

## Recommended Safe Update Sequence

1. Identify the desktop updater source and exact target version before clicking
   update.
2. Update the laptop desktop app first only if the updater source is trusted and
   the release notes do not imply gateway/runtime migration.
3. Smoke-check laptop Mission Control:
   - app opens,
   - Mission Control renders,
   - GitHub/Jenny bridge status renders,
   - dispatch/session-send remains disabled unless separately approved.
4. For the VPS, prepare a non-live runtime at the chosen target.
5. Validate the non-live runtime before any switch:
   - record store reads current and legacy records,
   - Mission Control assets contain expected markers,
   - dashboard starts and serves read-only status routes.
6. Switch `hermes-dashboard.service` only if the lane explicitly approves a
   dashboard-only runtime switch.
7. Do not restart or switch `hermes-gateway.service` without a separate gateway
   lane and explicit approval.
8. Append exactly one accepted-baseline record only after a successful
   dashboard validation and smoke check.

## Hard Stops

- No gateway restart in the version-readiness lane.
- No dispatch/session-send.
- No Waha/social posting/scheduler actions.
- No checkout/payment/customer/outreach changes.
- No hidden worker/timer/daemon enablement.
- No secrets or token file printing.
- No in-place mutation of the accepted runtime.

## Next Recommended Lane

Run a desktop updater-source inventory. The output should name the updater
manifest/source, the proposed desktop version, whether the update affects only
the Electron shell or also the Hermes runtime, and the rollback path before any
update is installed.
