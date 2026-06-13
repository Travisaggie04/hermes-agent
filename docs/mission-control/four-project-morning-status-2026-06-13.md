# Four-Project Morning Status - 2026-06-13

This is the consolidated status artifact for the overnight four-project
Mission Control planning run. It is a handoff document, not an approval to
post, charge, deploy gateway code, contact customers, enable workers/timers, or
mutate production systems.

## Global Runtime Status

Current source-of-truth status after the follow-up PRs:

- accepted-live branch head:
  `90309f6c841378eaa4d08170ee0b2b94f42d25ac`
- latest merged PR: #107, docs-only laptop Hermes worker-node update path
  clarification.
- live dashboard runtime for PR #106/#107: not verified from Codex after merge.
- deploy request status: queued to Jenny through the GitHub bridge on PR #79.
- direct Codex SSH status: blocked by sandbox access to Travis's private key
  and Tailscale approval, so Codex did not perform a runtime switch.

Dashboard-only runtime switches were used for visible Mission Control UI work.
Gateway was not restarted or switched.

## PRs Completed During This Run

| PR | Result | Purpose |
|---:|---|---|
| #89 | merged | Ignore local desktop release artifacts. |
| #90 | merged | Overnight Mission Control handoff. |
| #91 | merged and dashboard-deployed | Four-project active-lanes surface. |
| #92 | merged | Tool & Tally report-engine inventory. |
| #93 | merged | Shorts queue inventory. |
| #94 | merged | Long-form proof inventory. |
| #95 | merged | Mission Control autonomy hardening backlog. |
| #96 | merged and dashboard-deployed | Report-contract visibility in Mission Control UI. |
| #97 | merged | Legacy open PR triage. |
| #98 | merged | Four-project morning status. |
| #99 | merged | Four-project day plan and lane packets. |
| #100 | closed | Superseded legacy-record compatibility PR. |
| #101 | merged | Mission Control room journal records. |
| #102 | merged | Legacy Mission Control record-line compatibility. |
| #103 | merged | Hermes version update readiness lane. |
| #104 | merged | Hermes version inventory and Tool & Tally report-builder guardrail. |
| #105 | merged | Typed challenge-review categories and blocking verdicts. |
| #106 | merged; dashboard deploy queued | Guarded Hermes update lane button for desktop/compact Mission Control. |
| #107 | merged | Laptop Hermes worker-node update-path clarification. |

## Protected Actions Not Taken

- no gateway restart,
- no dispatch/session-send,
- no Waha or social posting,
- no social scheduler write,
- no payment/checkout/customer action,
- no customer outreach send,
- no model routing change,
- no hidden worker/timer/daemon/cron enablement,
- no secrets inspection or printing,
- no broad production mutation.

## Project 1 - Hermes / Mission Control

Project ID: `project-hermes-mission-control`

Latest status:

- Mission Control now has project rooms, Kanban, active-lanes, bridge status,
  GitHub mailbox status, report-contract visibility, typed challenge-review
  categories, room journal records, and a guarded Hermes update lane button in
  accepted-live.
- The guarded update lane button queues an append-only Jenny bridge request; it
  does not update the laptop worker node, switch runtimes, restart gateway, or
  dispatch/send sessions.
- Travis clarified that the laptop Hermes install is a worker node and that the
  VPS historically triggered laptop Hermes updates. Laptop worker-node update
  is now a separate explicit approval lane.
- The live dashboard runtime has not yet been verified as switched to PR
  #106/#107 from Codex.

Biggest blocker / uncertainty:

- Jenny should not receive more direct execution authority until challenge
  quality, lane isolation, and report-contract evidence are stronger.
- Older open PRs #1-#8 and #18 are legacy backlog and should not be merged
  directly.
- Codex can post GitHub bridge requests, but Jenny has not yet replied to the
  dashboard deploy request for PR #106/#107. Direct Codex SSH to the VPS is
  blocked from this sandbox.

Recommended next lane:

- Complete the bounded dashboard-only runtime switch for accepted-live
  `90309f6c841378eaa4d08170ee0b2b94f42d25ac` so PR #106 is visible, without
  touching gateway or triggering the laptop worker-node update.
- Then build the next Mission Control guardrail: "merged but not deployed"
  versus "deployed and accepted" status, or report-contract completeness
  warnings.
- If cleaning old PRs, run a separate legacy-PR closure/salvage lane.

Forbidden actions:

- gateway restart,
- dispatch/session-send,
- Waha/social/payment/customer actions,
- hidden worker/timer/daemon,
- secrets access,
- broad production mutation.

Evidence:

- `docs/mission-control/mission-control-autonomy-hardening-backlog-2026-06-13.md`
- `docs/mission-control/legacy-open-pr-triage-2026-06-13.md`
- `projects/hermes-mission-control/lanes/hermes-version-update-readiness-2026-06-13.md`
- PR #91, #95, #96, #97, #101, #105, #106, #107

## Project 2 - Short-form Videos

Project ID: `project-shorts-video`

Latest status:

- Authoritative repo:
  `/home/jenny/wt/agentic-video-channel-factory`
- Repo was observed as `main...origin/main [ahead 32]` with untracked
  `runtime/`.
- Queue ledger has 138 records.
- Lane A scan found 50 eligible packages out of 202 scanned.
- No-write reconciler dry-run could fill 100 next-five-day records across
  YouTube, Facebook, Instagram, and TikTok, but TikTok remains blocked by
  developer approval.

Biggest blocker / uncertainty:

- Quality remains the main blocker. Filling queue slots without Lane A quality
  evidence risks low-value, repetitive, or policy-weak content.
- Posting/scheduler reliability still needs review, but no live social write
  should happen before the queue quality plan is accepted.

Recommended next lane:

- Run a read-only quality and scheduler audit focused on the 25-video queue:
  confirm which Lane A packages are actually usable for YouTube, Facebook, and
  Instagram first; keep TikTok out until approval is fixed.

Forbidden actions:

- posting,
- scheduling live posts,
- social API sends,
- TikTok developer/app changes,
- queue mutation without a separate approved write lane,
- hidden research/posting timers.

Evidence:

- `docs/mission-control/shorts-queue-inventory-2026-06-12.md`
- `docs/mission-control/shorts-queue-reconciliation-plan-2026-06-12.md`
- `docs/mission-control/video-production-decision-memo-2026-06-12.md`
- PR #93

## Project 3 - Long-form Videos

Project ID: `project-long-form-video`

Latest status:

- Authoritative repo:
  `/home/jenny/wt/agentic-video-channel-factory`
- Long-form pipeline is explicitly not production-approved in the pipeline
  registry.
- Useful proof assets exist for:
  - adult character rig selection,
  - Moho character fee-machine compositing,
  - HyperFrames fee-machine V2 scaffold,
  - historical mixed-media long-form QA.
- Local Windows tool inventory found DaVinci Resolve, Inkscape, and Cavalry in
  standard paths, but ffmpeg/ffprobe/Python were not on PATH from the Codex
  shell, and Blender/Moho were not found in standard install paths.

Biggest blocker / uncertainty:

- The adult character rig acting gate has not passed.
- The historical 349-second mixed-media proof had serious OCR/safe-area and
  freeze/silence warnings, so full long-form production should not restart yet.

Recommended next lane:

- Local-only tool preflight plus adult character rig acting gate.
- Only after that passes, run one 10-15 second fee-machine proof, not a full
  episode.

Forbidden actions:

- live posting,
- account mutation,
- paid purchases,
- full episode production,
- scheduler/queue automation,
- hidden worker/timer.

Evidence:

- `docs/mission-control/long-form-proof-inventory-2026-06-13.md`
- `docs/mission-control/long-form-proof-plan-2026-06-12.md`
- `docs/mission-control/video-production-decision-memo-2026-06-12.md`
- PR #94

## Project 4 - Tool & Tally

Project ID: `project-tool-tally`

Latest status:

- Authoritative recovery worktree:
  `/home/jenny/wt/tooltally-restore-operating-capability-20260606`
- Recovery worktree had pre-existing modified files and local operation
  artifacts when checked read-only.
- Checkout remains off.
- Customer delivery remains blocked.
- Outreach remains no-send.
- Current report-engine focus is paid-order-to-report-job conversion, report
  package building, PDF quality, and quality-agent acceptance.

Biggest blocker / uncertainty:

- Report dry-run was blocked by missing `weasyprint` and paid-order artifact
  naming mismatch.
- Until local report generation passes against fixture data, checkout and
  outreach should remain disabled.

Recommended next lane:

- Local-only Tool & Tally report-engine recovery against fixture data:
  install/verify local render dependencies, normalize paid-order artifact
  naming, generate a report package, run PDF quality checks, and produce a
  no-customer evidence packet.

Forbidden actions:

- turning checkout back on,
- payment writes,
- customer delivery,
- email/text/DM/outreach sends,
- public launch changes,
- customer-facing deploys,
- secrets inspection.

Evidence:

- `docs/mission-control/tool-tally-report-engine-inventory-2026-06-12.md`
- `docs/mission-control/tool-tally-recovery-plan-2026-06-12.md`
- PR #92

## Legacy PR Status

Open legacy PRs still exist:

- #1, #2, #3, #4, #5, #6, #7, #8, #18

Current guidance:

- Do not merge directly.
- Treat as legacy backlog.
- Rebase/salvage useful pieces only through fresh accepted-live branches.
- Do not close automatically without Travis approval.

Evidence:

- `docs/mission-control/legacy-open-pr-triage-2026-06-13.md`

## Next Best Work Order

1. Hermes / Mission Control:
   complete dashboard-only deploy of accepted-live, then add merged/deployed
   status and report-contract completeness warnings.
2. Tool & Tally:
   local-only report-engine fixture recovery.
3. Shorts:
   Lane A quality audit and non-TikTok 25-video queue plan.
4. Long-form:
   local tool preflight and adult rig acting gate.

Do not start live publishing, checkout, outreach, or hidden automation from
this handoff.
