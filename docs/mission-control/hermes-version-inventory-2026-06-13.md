# Hermes Version Inventory - 2026-06-13

This is a read-only version inventory for Travis's laptop/Codex checkout,
the legacy laptop Hermes worker node, and Jenny's VPS runtimes. It does not
approve an update, deploy, restart, runtime switch, laptop worker-node trigger,
record mutation, dispatch/session-send, Waha action, or gateway change.

Update 2026-06-20: the Mission Control update contract distinguishes three
separate lanes: VPS dashboard/gateway runtime updates, external desktop app
self-updates, and laptop Codex worker-node readiness/update posture. The
legacy laptop Hermes worker-node path is deprecated and is not an executor
path. Codex worker-node dispatch remains disabled unless a separate explicit
operator approval and fresh readiness record enable a manual handoff.

## Local Accepted-Live Checkout

- Branch: `accepted-live/approval-safety-5ad8906`
- Head after PR #110: `de4e0c7926f3a9e64b130d4cb5f643f22d69032c`
- Head after PR #106: `98eca98f4f83a14a77a03972c24108591cf27261`
- Description after PR #106: `v2026.5.16-1489-g98eca98f4`
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
The update source must be verified from the VPS-triggered worker-node
updater/install channel or from a specific reviewed branch/commit.

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
- A current accepted-live branch or dashboard/gateway live runtime update does
  not update the native laptop desktop app shown in the footer. That footer
  belongs to the installed desktop app updater path and stays external/manual.
- Codex worker-node readiness/update posture is tracked separately from the
  desktop app updater. Presence, heartbeat, capabilities, blockers, and report
  contract readiness must be clear before any manual handoff. Worker dispatch
  remains disabled by default.
- Travis clarified that the laptop Hermes install had been used as a worker
  node and that the VPS historically triggered laptop Hermes updates. That path
  remains useful historical context, but the current plan is to retire the
  worker-node autostart and use Codex as the optional laptop engineering worker.
- The VPS dashboard is intentionally behind the current accepted-live branch
  after later docs/record work. That is not automatically an update problem:
  dashboard-only switch remains a separate deploy lane.
- The VPS gateway is intentionally older than the dashboard runtime. Updating
  or restarting the gateway is higher risk and should stay separate from
  dashboard-only work.

## Recommended Safe Update Sequence

1. Inventory the current VPS dashboard and gateway runtime paths, heads,
   rollback path, package versions, and service state.
2. Inventory Codex worker-node presence, heartbeat, capabilities, blockers,
   and report contract readiness. Do not trigger a worker-node update or
   dispatch.
3. Keep external desktop app self-update and any laptop Codex worker-node
   update as separate explicit/manual lanes.
4. Prepare non-live VPS dashboard and gateway runtimes at the chosen target.
5. Validate the non-live runtimes before any switch:
   - record store reads current and legacy records,
   - Mission Control assets contain expected markers,
   - dashboard starts and serves read-only status routes,
   - gateway imports and starts in the prepared runtime when gateway work is
     included.
6. Switch/restart dashboard and gateway only through the approved live-ops lane.
7. Smoke-check dashboard and gateway routes after the switch.
8. Append exactly one accepted-baseline record only after successful approved
   dashboard/gateway validation and smoke checks.

## Hard Stops

- No gateway restart in the version-readiness lane.
- No external desktop app update trigger in the runtime-readiness lane.
- No Codex worker-node update or dispatch trigger in the runtime-readiness lane.
- No dispatch/session-send.
- No Waha/social posting/scheduler actions.
- No checkout/payment/customer/outreach changes.
- No hidden worker/timer/daemon enablement.
- No secrets or token file printing.
- No in-place mutation of the accepted runtime.

## Next Recommended Lane

Run a read-only runtime and worker-node readiness inventory. The output should
name dashboard/gateway runtime paths and heads, rollback paths, Codex
worker-node presence/heartbeat/capabilities/blockers, and the exact separate
approval needed before any live runtime switch, baseline append, external
desktop update, or worker-node update is triggered.
