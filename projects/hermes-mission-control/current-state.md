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

Review and finish the manual GitHub bridge operator path, then choose the next
narrow Mission Control UI or bridge-hardening PR.
