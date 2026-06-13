# Mission Control Recovery Status - 2026-06-13 Late

This is an operational status artifact for the Mission Control / Jenny recovery
lane. It is not approval for gateway restart, dispatch/session-send, Waha,
social posting, checkout/payment/customer actions, model routing changes,
hidden workers/timers/daemons, broad cleanup, or secrets access.

## Current Operating Decision

Mission Control / Jenny recovery is the only active build lane.

Paused until Jenny is stable:

- `project-shorts-video`
- `project-long-form-video`
- `project-tool-tally`
- `project-waha-work`

The paused projects remain visible as planning context only. Mission Control no
longer exposes paused-project queue buttons while the recovery lane is active.

## Accepted-Live Head

Latest accepted-live head after the current recovery UI sequence:

- `a1b8d3c2e476fd535bd02fa533050d0f31b9fba2`

## Completed PRs

| PR | Commit | Result |
|---:|---|---|
| #133 | `3580a33caf08ede16e55f9c08f4e0b7013a0df3d` | Desktop Mission Control shows all five real project rooms and hides diagnostic smoke/error bridge chatter from normal chat. |
| #134 | `f1823693dffdba833988717fb55ea51a77bfefce` | Desktop paused project rooms are read-only while Hermes / Mission Control remains the active recovery lane. |
| #135 | `7860e8d6a00648d4ea84e6e4b4d943a89cd8eddc` | Compact/phone project rooms match desktop paused-project behavior. |
| #136 | `83952716a2b69392dd216f614ad64b6732bf25ab` | Owner-facing wording simplified: `Message Jenny`, `About this project`, `Advanced controls`, and `Advanced status and reports`. |
| #137 | `a1b8d3c2e476fd535bd02fa533050d0f31b9fba2` | Paused-project queue/audit controls removed from desktop and compact surfaces. |

## Local Desktop Status

The local desktop app was rebuilt in place at PR #137:

- path:
  `C:\Users\Travis\Documents\Codex\2026-06-12\how-do-we-connect-you-to\work\hermes-agent\apps\desktop\release-bridge\win-unpacked\Hermes.exe`
- build stamp commit:
  `a1b8d3c2e476fd535bd02fa533050d0f31b9fba2`

Expected desktop behavior:

- five real projects visible,
- Hermes / Mission Control active,
- other four projects paused/read-only,
- normal conversation hides smoke/error diagnostics,
- primary controls are chat-like: message Jenny, send, run once, refresh,
- advanced guardrails remain collapsed behind advanced sections.

## Live Dashboard Status

Verified dashboard-only deployments completed through PR #136:

- current verified dashboard runtime after PR #136:
  `/home/jenny/.hermes/hermes-runtime-chat-polish-8395271`
- current verified dashboard head after PR #136:
  `83952716a2b69392dd216f614ad64b6732bf25ab`
- gateway runtime intentionally unchanged:
  `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe`

PR #137 dashboard runtime switch is still pending because direct Codex SSH hit a
Tailscale browser re-auth challenge, and the sandbox cannot read Travis's
private SSH key.

Fallback action already taken:

- queued a GitHub bridge request to Jenny on PR #79,
- request id:
  `codex-pr137-dashboard-deploy-20260613-225736`,
- request asks for dashboard-only runtime switch, no gateway restart, no
  dispatch/session-send, and exactly one `AcceptedBaselineRecord` only after
  successful validation.

## Validation Evidence

PR #136 validation:

- desktop Vitest on Jenny Linux: `23 passed`,
- desktop type-check: passed,
- targeted desktop ESLint: passed,
- compact page pytest: `12 passed`,
- Ruff: passed,
- GitHub CI: clean,
- dashboard-only runtime switch completed and smoked.

PR #137 validation:

- desktop Vitest on Jenny Linux: `23 passed`,
- desktop type-check: passed,
- targeted desktop ESLint: passed,
- compact page pytest: `12 passed`,
- Ruff: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

Local browser visual validation was attempted but blocked by the Windows
sandbox browser runtime:

- browser runtime failed to start with Windows sandbox process permissions.

## Remaining Blockers

1. Complete PR #137 dashboard-only runtime switch after SSH/Tailscale access is
   available or Jenny processes the GitHub bridge request.
2. Do not resume Tool & Tally, Shorts, Long-form, or Waha from Mission Control
   until Jenny/Mission Control recovery is stable enough to run project work
   through the new OS surface.
3. Keep older legacy PRs (#1-#8, #18) out of the active lane unless separately
   reviewed and salvaged onto fresh accepted-live branches.

## Next Recommended Lane

Primary next lane:

- finish the PR #137 dashboard-only runtime switch.

After that:

1. Add a clearer owner-facing "Jenny ready / waiting / blocked" indicator in
   the chat header.
2. Add a small "resume project" challenge gate later, so paused projects cannot
   restart without an explicit brief, challenge review, and approval reason.
3. Only after those are reliable, resume Tool & Tally first as a local-only
   report-engine fixture lane. Do not start checkout or outreach.

