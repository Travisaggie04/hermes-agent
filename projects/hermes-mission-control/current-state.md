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
