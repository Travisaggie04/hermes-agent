# Jenny OS Async Agent / Omnigent Integration Map - 2026-06-17

This map turns the chat-first Jenny OS direction into implementation checkpoints.
It is intentionally a planning artifact: no runtime behavior changes are made by
this document.

## Direction

Jenny OS should move toward the native Hermes chat surface:

- project-grouped chats are the primary workspace
- Mission Control is the advanced audit/recovery surface
- Travis's visible messages stay clean
- hidden project context and guardrails travel outside the visible chat bubble
- Jenny shows Codex-like status while working
- async/subagent work is visible and bounded, not hidden autonomy

## Upstream Hermes Async Agent Inventory

Compared against upstream Hermes at `5e01a5dbf1b7bc0144d9057be706da1ea9f065c3`.

| Area | Current Jenny OS branch | Upstream Hermes | Integration decision |
| --- | --- | --- | --- |
| Desktop Agents view | Present | Present with minor spinner/formatting changes | Keep current branch; merge small upstream UI polish only when useful. |
| Desktop subagent store | Present | Adds `child_session_id`/`sessionId` support | Port `sessionId` support so subagent rows can link to child sessions. |
| `tools/async_delegation.py` | Missing | Present | Port as the canonical backend for `delegate_task(background=true)`. |
| `delegate_task(background=true)` | Missing | Present | Port after tests; keep single-task only and bounded by config. |
| Async delegation tests | Missing | Present | Port focused tests before enabling the tool schema. |
| `send_message_tool.py` | Diverged | Diverged | Do not bulk replace; review only the specific async/session changes needed. |

## Omnigent Patterns To Borrow

Omnigent should remain a reference harness, not a replacement for Hermes.

Borrow these patterns conceptually:

- session-first project model: projects contain sessions; sessions are the unit
  of chat, status, and review
- policy vocabulary: central `ALLOW`, `ASK`, `DENY` decisions instead of
  scattered guard text
- orchestrator role: Jenny acts like a senior engineer who plans, delegates,
  reviews, and asks questions before broad implementation
- cross-review rule: risky implementation work should be reviewed by a distinct
  lane or agent before merge/deploy
- phone-first tests: compact views must have viewport tests for horizontal
  overflow and hidden technical detail

Do not borrow yet:

- wholesale Omnigent runtime/session architecture
- always-on collaboration server assumptions
- direct replacement of Hermes desktop chat
- new background workers or daemons

## PR Roadmap

### PR C - Native Project Chat Foundation

Make the native desktop chat feel like the main Jenny workspace:

- project selector in the normal chat experience
- sessions grouped under projects
- new project creation flow
- legacy sessions grouped under `Other chats`
- Mission Control presented as advanced/audit, not the primary workspace

### PR D - Clean Visible Messages

Keep Travis's visible chat bubble limited to the text he typed.

- inject project context, challenge gate, and safety rules as hidden metadata or
  sidecar context
- keep the full guarded packet auditable outside the visible message body
- test that sending `test` displays `test`, not the spec-first packet

### PR E - Automatic Jenny Reply Loop

Make chat behave like chat:

- sending a project message queues the guarded Jenny request
- one guarded reply attempt starts without a second button press
- UI shows queued, working, replied, failed, retry
- duplicate reply protection remains record-backed
- no daemon, cron, or always-on worker

### PR F - Async/Subagent Status

Use upstream Hermes async-agent primitives for visible work status:

- port `tools/async_delegation.py`
- port `delegate_task(background=true)` with single-task and capacity guards
- port `child_session_id` into the desktop subagent store
- show minimal chat status and put details in an Activity drawer

### PR G - Central Policy Guardrails

Begin replacing scattered safety copy with one policy evaluator:

- `ALLOW`: safe read/status/UI/record-backed action
- `ASK`: deploy, restart, runtime switch, gateway-affecting work
- `DENY`: hidden worker/timer, payment/social/outreach/Waha, secrets/state
  mutation without explicit approval

### PR H - Goal Mode Hardening

Make long-running Jenny engineering work resumable:

- checkpoints
- progress reports
- context-compaction continuation
- evidence-based done checks
- clear blocked/retry states

## Guardrails For All PRs

- no gateway restart or gateway runtime switch
- no Waha, social posting, payment, or outreach behavior
- no Tool & Tally report-builder changes
- no hidden worker, timer, daemon, or cron
- no local LLM routing integration
- prefer small PRs with focused tests
- rebuild local `release-bridge` only after desktop changes are merged

## Immediate Next Step

After this map lands, start PR C with the smallest native chat slice:

1. make project selection more prominent in the existing chat path
2. preserve current session behavior
3. keep legacy/unfiled chats collapsed under `Other chats`
4. add tests proving the project-focused sidebar still behaves after reload
