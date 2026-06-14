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

- `58853d442654e69014fa4fbc95e3bd837cd87fe6`

## Completed PRs

| PR | Commit | Result |
|---:|---|---|
| #133 | `3580a33caf08ede16e55f9c08f4e0b7013a0df3d` | Desktop Mission Control shows all five real project rooms and hides diagnostic smoke/error bridge chatter from normal chat. |
| #134 | `f1823693dffdba833988717fb55ea51a77bfefce` | Desktop paused project rooms are read-only while Hermes / Mission Control remains the active recovery lane. |
| #135 | `7860e8d6a00648d4ea84e6e4b4d943a89cd8eddc` | Compact/phone project rooms match desktop paused-project behavior. |
| #136 | `83952716a2b69392dd216f614ad64b6732bf25ab` | Owner-facing wording simplified: `Message Jenny`, `About this project`, `Advanced controls`, and `Advanced status and reports`. |
| #137 | `a1b8d3c2e476fd535bd02fa533050d0f31b9fba2` | Paused-project queue/audit controls removed from desktop and compact surfaces. |
| #139 | `594a2ebba641f9430e27647f69bcbd1c5f310989` | Adds an owner-facing Jenny chat readiness chip for watching, waiting, replied, ready, and needs-attention states. |
| #141 | `112361b51aa5803436208886a75180539308cbe3` | Keeps all five project rooms visible even when backend project records are partially projected. Existing records still override canonical project anchors. |
| #142 | `82e142577f54d3cd3e2a728b33ac78827cb775cc` | Renames the owner-facing one-shot bridge action from `Run Jenny once` to `Get Jenny reply`. |
| #143 | `4c674cb868d396b39b78a92b99db2cf193010133` | Adds plain owner-facing copy explaining that desktop can be current while phone/web waits for a safe dashboard-only update. |
| #144 | `b41e5a7957834805fbcc6c2026da2ab957b0fdda` | Refreshes this Mission Control recovery status handoff. |
| #145 | `b7835fc9fcc79a8deafa23ed01dc7e8930873ea6` | Adds paused-project resume requirements so paused work cannot resume without brief, challenge review, allowed/forbidden actions, and Travis approval. |
| #146 | `bf140807bfbe5efbf74b7c519821e69aad49ad1f` | Adds packaged desktop validation for Jenny Workspace and the five project anchors. |
| #147 | `feb34a1ba8228f309b391a598844e313f7c4b7ee` | Routes Hermes update and storage cleanup lane buttons through the GitHub Jenny mailbox instead of the old local-only bridge. |
| #148 | `2d5c4c608b2a03411d4961325e14e2228db486de` | Keeps the desktop app single-instance so a second launch focuses the existing Hermes window instead of opening a duplicate. |
| #149 | `c98b553c8f0640965dc810c5c2c4df92fc62692f` | Makes compact/phone previous-session cards open the real chat resume route. |
| #150 | `854a5bbee8769c1c1b51e0eb45da9e1c1516ad91` | Fixes desktop package validation so an explicit `release-bridge` root is validated in place without rebuilding into the default `release` folder. |
| #151 | `f0ce9ca5125c42137fb0ac5f9985369d983d746b` | Hides additional bridge-smoke diagnostics such as `Bridge works` and `success smoke reached` from normal project chat. |
| #152 | `8dd5c3e38a85cf535e6475152c582e63245b6855` | Refreshes this recovery status and the Hermes / Mission Control current-state handoff. |
| #153 | `58853d442654e69014fa4fbc95e3bd837cd87fe6` | Hides operator bridge packets such as Codex deploy/review requests from the owner-facing project chat. |

## Local Desktop Status

The local desktop app was rebuilt in place at PR #153:

- path:
  `C:\Users\Travis\Documents\Codex\2026-06-12\how-do-we-connect-you-to\work\hermes-agent\apps\desktop\release-bridge\win-unpacked\Hermes.exe`
- latest build stamp commit:
  `58853d442654e69014fa4fbc95e3bd837cd87fe6`

Expected desktop behavior:

- five real projects visible,
- Hermes / Mission Control active,
- other four projects paused/read-only,
- normal conversation hides smoke/error diagnostics and bridge-smoke
  confirmation chatter,
- operator bridge packets from Codex deploy/review coordination are hidden
  from the owner-facing chat,
- primary controls are chat-like: message Jenny, send, get Jenny reply, refresh,
- five project-room anchors remain visible even if the backend temporarily
  returns only Hermes / Mission Control,
- if accepted-live is ahead of the served dashboard, desktop shows plain
  update-lag copy instead of requiring Travis to interpret commit IDs,
- advanced guardrails remain collapsed behind advanced sections.

## Live Dashboard Status

Verified dashboard-only deployments completed through PR #136:

- current verified dashboard runtime after PR #136:
  `/home/jenny/.hermes/hermes-runtime-chat-polish-8395271`
- current verified dashboard head after PR #136:
  `83952716a2b69392dd216f614ad64b6732bf25ab`
- gateway runtime intentionally unchanged:
  `/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe`

PR #137/#139/#141/#142/#143/#145/#146/#147/#148/#149/#150/#151/#152/#153
dashboard runtime switch is still pending. Codex
fixed host-key verification with a repo-local known-hosts entry matching the
previously accepted VPS fingerprint, but direct SSH still hits a Tailscale
browser re-auth challenge.

Fallback action already taken:

- queued a GitHub bridge request to Jenny on PR #79,
- superseding request id:
  `codex-pr153-dashboard-deploy-structured-20260614-001`,
- supersedes earlier request:
  `codex-pr152-dashboard-deploy-structured-20260614-001`,
- request asks for dashboard-only runtime switch to
  `58853d442654e69014fa4fbc95e3bd837cd87fe6`, no gateway restart, no
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

PR #139 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #141 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #142 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #143 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #145 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean.

PR #146 validation:

- packaged desktop validator path added and validated,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #147 validation:

- local desktop type-check: passed,
- targeted desktop ESLint: passed,
- Python compile for touched backend files: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #148 validation:

- desktop platform tests: passed,
- desktop type-check: passed,
- targeted desktop ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #149 validation:

- `npx tsc -b web`: passed,
- targeted compact static test: passed,
- targeted web ESLint: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #150 validation:

- `HERMES_DESKTOP_RELEASE_ROOT=apps/desktop/release-bridge npm run test:desktop -- validate`: passed,
- `node --check apps/desktop/scripts/test-desktop.mjs`: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #151 validation:

- local desktop type-check: passed,
- targeted desktop and compact ESLint: passed,
- Python compile for compact static tests: passed,
- static diagnostic marker check: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

PR #152 validation:

- docs-only diff,
- `git diff --check`: passed,
- GitHub CI: clean.

PR #153 validation:

- local desktop type-check: passed,
- targeted desktop and compact ESLint: passed,
- Python compile for compact static tests: passed,
- static operator-bridge marker coverage: passed,
- GitHub CI: clean,
- local desktop app rebuilt in place.

Local browser visual validation was attempted but blocked by the Windows
sandbox browser runtime:

- browser runtime failed to start with Windows sandbox process permissions.

## Remaining Blockers

1. Complete latest accepted-live dashboard-only runtime switch after
   SSH/Tailscale access is available or Jenny processes the GitHub bridge
   request.
2. Do not resume Tool & Tally, Shorts, Long-form, or Waha from Mission Control
   until Jenny/Mission Control recovery is stable enough to run project work
   through the new OS surface.
3. Keep older legacy PRs (#1-#8, #18) out of the active lane unless separately
   reviewed and salvaged onto fresh accepted-live branches.

## Next Recommended Lane

Primary next lane:

- finish the latest accepted-live dashboard-only runtime switch to
  `58853d442654e69014fa4fbc95e3bd837cd87fe6`.

After that:

1. Keep the owner-facing chat clean of bridge/operator packets while preserving
   normal Travis/Jenny messages.
2. Add the next small Jenny Workspace reliability affordance only if it keeps
   guardrails in the background for a non-coder operator.
3. Do not resume Tool & Tally, Shorts, Long-form, or Waha until Travis
   explicitly resumes them after Jenny/Mission Control is stable.

