# Hermes / Mission Control Current State

Project ID: `project-hermes-mission-control`

## Goal

Make Mission Control the primary operating surface for Travis on laptop and
phone, replacing Discord as the main place to manage Jenny/Hermes project work.

## Current Problem

Jenny started as an out-of-the-box Hermes agent and became unstable as the
system grew. Observed problems include regressions, split-brain behavior,
manual copy/paste between tools, weak orchestration, and insufficient challenge
of unclear or unsafe asks.

Travis is not a coder. Jenny must act as a strong engineering operator and
reviewer, not just accept non-technical direction.

## Current Direction

Mission Control should provide:

- Project rooms.
- Project-specific context.
- Challenge review before lane drafting.
- Approval and rollback awareness.
- Bridge communication between Codex and Jenny.
- Clear separation between planning, review, deploy, and live-action lanes.

## Authoritative Paths

- Local Codex working repo:
  `C:\Users\Travis\Documents\Codex\2026-06-12\how-do-we-connect-you-to\work\hermes-agent`
- Accepted-live branch: `accepted-live/approval-safety-5ad8906`
- Live dashboard runtime observed before this context update:
  `/home/jenny/.hermes/hermes-runtime-github-bridge-mailbox-944411a`
- Live gateway runtime observed before this context update:
  `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe`
- GitHub bridge mailbox transport: PR #79 conversation thread.
- Laptop Hermes role: worker node. Travis clarified that the VPS historically
  triggered laptop Hermes updates, so laptop updates must be treated as a
  worker-node update trigger with separate inventory, rollback, and approval.
- Native desktop footer version/build is a separate installed app signal. A
  current accepted-live branch or dashboard-only runtime switch does not update
  the laptop footer version; that requires the separate worker-node update lane.

## Tonight's Lane

Primary build lane.

Allowed tonight:

- Low-risk Mission Control UI improvements.
- Bridge hardening.
- Documentation and context-pack setup.
- PRs reviewed with green CI.
- Dashboard-only deploy/runtime switch if needed and bounded.

Forbidden without explicit approval:

- Gateway restart.
- Laptop worker-node update trigger.
- Dispatch or session-send.
- Waha or social posting.
- Payment, checkout, customer outreach, or model routing changes.
- Hidden worker, timer, daemon, or broad production mutation.

## First Recommended Work

Build the next narrow Mission Control UI or bridge-hardening PR after preserving
the four-project authority inventory and lane packets.

## 2026-06-13 Hardening Update

See
`docs/mission-control/mission-control-autonomy-hardening-backlog-2026-06-13.md`.

The latest hardening backlog defines staged gates for making Jenny more
autonomous: unambiguous state, stronger challenge behavior, lane isolation,
PR/deploy discipline, manual bridge reliability, and only then limited
execution. The key decision is that "more autonomous" means better records,
visibility, and stop conditions first; direct execution remains gated.

## 2026-06-13 Legacy PR Triage

See `docs/mission-control/legacy-open-pr-triage-2026-06-13.md`.

Older open PRs #1-#8 and #18 should be treated as legacy backlog, not current
ready-to-merge work. They are based on old stacked branches or old pre-current
Mission Control foundations. Salvage useful ideas only through fresh branches
from accepted-live, with current CI and protected-surface review.

## 2026-06-13 Late Recovery UI Status

See
`docs/mission-control/mission-control-recovery-status-2026-06-13-late.md`.

The current recovery UI sequence makes Mission Control / Jenny recovery the only
active lane, keeps the other real projects visible but read-only, simplifies the
workspace toward a project chat, and removes paused-project queue controls until
Jenny is stable enough to resume project work through the new OS surface.

## 2026-06-14 Early Recovery Update

The recovery status document now tracks accepted-live through PR #156. Current
local desktop `release-bridge` is rebuilt and validated at
`366a35a071d2c8d51d577df093fd5a7bd48da0c4`.

The remaining visible gap is the bounded dashboard-only runtime switch on the
VPS so phone/web surfaces catch up to the current accepted-live Mission Control
UI. That request is queued to Jenny through the GitHub bridge. Gateway restart,
laptop worker-node update, dispatch/session-send, Waha/social/payment/customer
actions, workers/timers/daemons, and broad cleanup remain out of scope.

PR #153 also hides Codex/operator bridge packets from the owner-facing project
chat, so Mission Control should continue moving toward a clean project chat
surface while retaining technical guardrails behind advanced controls.

PR #155 removes mojibake-prone Unicode separators from owner-facing Mission
Control desktop/phone text. PR #156 hardens the GitHub bridge parser so escaped
fenced JSON packets can still be read instead of silently stalling the
Codex/Jenny handoff.
