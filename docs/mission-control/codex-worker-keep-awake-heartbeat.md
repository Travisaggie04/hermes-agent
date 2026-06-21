# Codex worker keep-awake and heartbeat path

This is the approved safe design for waking the Main Laptop Codex worker when Jenny needs help.

## Safety boundary

This path is **operator-started** and **manual handoff only**.

It must not enable:

- `worker_dispatch`
- `session_send`
- queue mutation
- Waha / social / payment actions
- model-routing changes
- timers, cron, daemon, autostart, or automatic code execution
- live runtime restart/switch/deploy
- secret inspection or output

A fresh heartbeat only means the laptop Codex worker is available for a copyable/manual packet. It is not permission to execute automatically.

## Operator commands

From the Main Laptop WSL shell:

```bash
jenny-worker-awake on
jenny-worker-awake status
jenny-worker-awake off
```

`on` keeps the laptop awake and starts the operator-visible worker tmux session. `off` stops the worker watcher and releases the keep-awake hold.

## Heartbeat loop

When an operator wants Mission Control to show Codex as online, run the heartbeat loop from a Hermes checkout:

```bash
python scripts/codex_worker_heartbeat_loop.py \
  --mission-control-url <dashboard-api-url>
```

The script also accepts `HERMES_MISSION_CONTROL_URL` so the URL does not need to be repeated:

```bash
export HERMES_MISSION_CONTROL_URL=<dashboard-api-url>
python scripts/codex_worker_heartbeat_loop.py
```

If the dashboard requires a session token, put it in the environment variable `HERMES_MISSION_CONTROL_TOKEN`. The script uses the `X-Hermes-Session-Token` header and never prints the token.

For a one-shot smoke or test:

```bash
python scripts/codex_worker_heartbeat_loop.py \
  --mission-control-url <dashboard-api-url> \
  --once
```

For a dry run that does not contact Mission Control:

```bash
python scripts/codex_worker_heartbeat_loop.py \
  --mission-control-url http://127.0.0.1:9119 \
  --once \
  --dry-run
```

## Record semantics

The heartbeat loop appends `WorkerNodeRunRecord` records with:

```text
presence_status: online
smoke_status: heartbeat_loop_ok
worker_dispatch_enabled: false
max_concurrent_read_only_lanes: 1
max_concurrent_mutation_lanes: 0
```

Mission Control treats the record as online only while `last_heartbeat_at` is fresh. The freshness window is 15 minutes. If the heartbeat goes stale, Mission Control shows the worker as stale/offline for readiness purposes.

Smoke states such as `reachable_manual_smoke_ok` belong in `smoke_status`, not `presence_status`. `presence_status` is restricted to `online` or `offline`.

## Operator decision packet

- **Option A — manual keep-awake only:** safest, lowest automation. Operator runs `jenny-worker-awake on/off`; Jenny may prepare manual packets.
- **Option B — WSL background job with heartbeat:** recommended next step. Operator starts a visible WSL/tmux heartbeat loop for dinner/overnight work. Dispatch remains disabled.
- **Option C — fully automatic Jenny-to-Codex dispatch:** future lane only. Requires separate approval, hard global resource/concurrency guards, CI-reviewed implementation, and explicit worker dispatch enablement.

Recommendation: use **Option B** next for overnight/dinner-time work, but keep automatic dispatch disabled until a separate approval.
