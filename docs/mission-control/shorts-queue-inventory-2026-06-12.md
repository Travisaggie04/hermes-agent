# Shorts Queue Inventory - 2026-06-12

This is a read-only inventory of the Signal Room short-form video queue and
Lane A package pool. It does not approve posting, scheduling, platform API
writes, TikTok developer/app changes, queue mutation, worker/timer/daemon
enablement, or social account changes.

## Implementation Repo

Path:

- `/home/jenny/wt/agentic-video-channel-factory`

Observed state:

- branch: `main`
- head: `b9226f4f0f4eb18689194ed746eb400a649c3d27`
- status: `main...origin/main [ahead 32]`
- runtime directory: untracked

Important implication:

- The repo contains substantial local unreconciled work. Do not reset, clean, or
  overwrite it before a separate dirty-worktree inventory is accepted.

## Queue Ledger

Path:

- `/home/jenny/wt/agentic-video-channel-factory/runtime/social_queue_state.json`

Observed hash:

- `5200fbefe3c126c9497464d47eb68992e0f646c3483b9e6e89f8256ddd8699b3`

Observed top-level state:

- queue record count: `138`
- platform counts:
  - YouTube: `50`
  - Facebook: `38`
  - Instagram: `25`
  - TikTok: `25`

The direct JSON count sees status as `unknown` because the useful operational
state is encoded in record fields consumed by the queue tools. Use the repo
tools as the source of interpretation.

## Read-Only Tooling

Confirmed read-only or dry-run commands:

```bash
python3 tools/social_queue_status.py \
  --state runtime/social_queue_state.json \
  --start-date 2026-06-13 \
  --days 5 \
  --attention-only
```

```bash
python3 tools/social_queue_lane_a_audit.py \
  --packages-root review-packages \
  --json
```

```bash
python3 tools/social_queue_lane_a_backfill_plan.py \
  --packages-root review-packages \
  --json
```

```bash
python3 tools/social_queue_reconcile.py \
  --packages-root review-packages \
  --state runtime/social_queue_state.json \
  --start-date 2026-06-13 \
  --days 5
```

Do not pass `--write` to `social_queue_reconcile.py` until a separate approval
lane authorizes queue mutation.

## Lane A Package Audit

Read-only Lane A audit result:

- scanned package count: `202`
- eligible count: `50`
- rejected count: `152`

Read-only backfill planner result:

- scanned package count: `202`
- already eligible count: `50`
- backfill candidate count: `7`
- regenerate recommended count: `127`
- blocked review-only count: `18`

Top missing fields are dominated by missing Lane A and human psychology gates:

- `Lane A marker`: `152`
- `human_psychology_gate.*`: `140`
- `quality_lock.human_psychology_hook_gate_passed`: `140`
- several visual/readability quality-lock fields: `133+`

This confirms the current blocker is not just queue volume. Most packages fail
the newer quality and human-psychology gates.

## Reconciliation Dry Run

Read-only dry run:

```bash
python3 tools/social_queue_reconcile.py \
  --packages-root review-packages \
  --state runtime/social_queue_state.json \
  --start-date 2026-06-13 \
  --days 5
```

Observed result:

- `dry_run`: `true`
- target days: `5`
- slots per day: `5`
- target per platform: `25`
- created count: `100`
- created by platform:
  - YouTube: `25`
  - Facebook: `25`
  - Instagram: `25`
  - TikTok: `25`

First proposed YouTube records used existing backlog packages such as:

- `The Bank Text Wanted the Callback`
- `The Crypto Profit Started in a Chat`
- `The Marketplace Deposit Was the Test`
- `The Delivery Fee Was the Bait`
- `The Emergency Asked for Gift Cards`

Interpretation:

- The next-five-day slate can be filled in dry-run from package evidence, but
  writing the ledger would be a queue mutation and remains blocked.
- TikTok proposals are not actionable until developer approval is recovered.
- YouTube/Facebook/Instagram should be reviewed first as the non-TikTok path.

## Attention Output

`social_queue_status.py --attention-only` primarily surfaced TikTok records in
`disabled_waiting_approval` state, with target post times from May 31 to June 3.

That confirms TikTok is stale and intentionally disabled, not merely empty.

## Next Safe Lane

Run a no-write Shorts queue reconciliation packet:

1. Save the read-only status, Lane A audit, backfill plan, and reconcile dry-run
   outputs into a review package.
2. Review the 7 backfill candidates first.
3. Separate the non-TikTok slate from TikTok-disabled proposals.
4. Draft a 25-video concept slate for non-TikTok production if package quality
   is insufficient.
5. Return a recommendation for which packages can be rebuilt into Lane A.

Hard stops:

- no `--write`,
- no queue file mutation,
- no posting or scheduling,
- no social platform API writes,
- no TikTok approval/developer action,
- no worker/timer/daemon enablement,
- no credential inspection or printing.

