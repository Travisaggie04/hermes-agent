# Jenny Engineering Orchestrator Runbook - 2026-06-19

This runbook explains the code-side Mission Control direction for Travis.
Jenny is the orchestrator and report reviewer. Codex on the laptop is a
supervised engineering worker node with its own engineering hardness.

The preferred model posture for this lane is ChatGPT 5.5 extra high, or the
strongest available reasoning mode. Larger architectural chunks are preferred
when they stay reviewable, tested, and reversible.

## Roles

- Travis is the operator. Mission Control should explain state in plain
  language and make the next safe action obvious.
- Jenny is the orchestrator. Jenny can inspect state, prepare bounded work
  packets, review reports, challenge unsafe requests, and recommend the next
  lane.
- Codex on the laptop is a worker node. It may receive bounded work packets and
  return structured reports, but it still enforces its own repository,
  worktree, test, secret, approval, and live-operation safeguards.
- Mission Control is the control plane. It shows projects, sessions,
  approvals, runs, reports, provenance, bridge status, blocked reasons, child
  runs, worker-node runs, and next safe actions.

Jenny must not treat Codex as an uncontrolled executor. Codex must not treat a
Jenny packet as permission to bypass Codex safety checks.

## Routes

- `/jenny-mobile` is the phone Jenny mobile chat route.
  It may create a visible manual bridge request and ask Jenny for one foreground
  reply, but it must fail closed and disable send/retry controls unless the
  GitHub bridge status confirms manual-only mode with `would_execute`,
  dispatch, execution, session-send, worker-dispatch, worker, timer, daemon,
  Discord automation, and model-routing flags off.
- `/mission-control-compact` is the old compact Mission Control route.
  Its compact chat controls follow the same manual-only bridge rule; the
  manual report/challenge/lane draft buttons are separate record actions and
  remain visibly guarded.
  Its compact health dashboard also treats any true execution lock on the
  operator decision packet, readiness summary, worker presence, result
  ingestion, report completion, or next-safe-action summary as a red health
  issue instead of implying the lane is safe.
- Desktop Mission Control is the advanced audit and recovery surface.
  Any GitHub bridge write button there follows the same fail-closed status
  check before creating a bridge request.
- Jenny and GitHub bridge status payloads explicitly report session-send and
  worker-dispatch as disabled, so control surfaces can fail closed on those
  backend flags instead of guessing.
- Mission Control plugin status and preview payloads inherit a base inert flag
  set with `would_execute`, execution, dispatch, session-send, and
  worker-dispatch all false by default.
- The Desktop Jenny project chat uses normal chat submission, so it remains
  usable, but its status pill warns when backend safety status reports live
  dispatch, execution, session-send, worker, timer, daemon, Discord automation,
  or model-routing flags.
- Desktop Jenny activity panels are status-only. They warn instead of showing
  async agents as ready if execution, dispatch, session-send, send-to-Jenny,
  worker-dispatch, worker, timer, daemon, model-routing, or trusted-execution
  flags are on.

## Runtime Provenance

Runtime provenance answers one question: can Mission Control prove that source,
accepted baseline, dashboard runtime, gateway runtime, rollback runtime, dirty
state, and dispatch state are safe enough for autonomy?

Important statuses:

- `CLEAN_AND_ALIGNED`: the only clean state for autonomy previews.
- `SOURCE_DEFAULT_DRIFT`: source HEAD and the default branch HEAD do not match,
  so Jenny cannot prove it is reviewing the current default source truth.
- `SOURCE_CURRENT_BUT_BASELINE_STALE`: source moved after the accepted runtime.
  If Mission Control sees merged PRs after the accepted baseline, it names
  those PRs as explicit provenance blockers until a new accepted baseline is
  created through a separately approved live reconciliation lane.
- `DASHBOARD_GATEWAY_DRIFT`: dashboard and gateway do not agree.
- `GATEWAY_UNTRUSTED`: gateway runtime cannot be trusted.
- `DIRTY_RUNTIME`: runtime has dirty or untracked files.
- `BROKEN_GIT_METADATA`: runtime git metadata is missing or broken.
- `ROLLBACK_STALE`: rollback no longer matches the expected safe fallback.
- `BLOCKED_UNSAFE_FOR_AUTONOMY`: Mission Control must not treat autonomy as
  available.

If provenance is not clean, Jenny may still explain what is wrong, but work
stays blocked or preview-only.

## Why Baseline, Gateway, And Dirty State Block Autonomy

- A stale `AcceptedBaselineRecord` means the accepted runtime does not prove the
  current source is safe.
- Source/default HEAD drift means Mission Control cannot prove the source truth
  came from the current default branch.
- Broken gateway git metadata means Mission Control cannot prove what code the
  gateway is serving.
- Dirty runtime files mean a live runtime has unreviewed changes that did not
  come from a clean PR path.
- Missing runtime paths mean Mission Control cannot verify the runtime it is
  being asked to trust.

These states block autonomy because Jenny must not act from uncertain source
truth.

## Preview-Only

Preview-only means Mission Control may calculate eligibility, build a work
packet preview, and show blocked reasons. It does not execute the work.

All current execution scaffolding must remain disabled:

- `would_execute: false`
- `execution_enabled: false`
- `dispatch_enabled: false`
- `session_send_enabled: false`
- `worker_dispatch_enabled: false`

## Supervised Read-Only Autonomy

Read-only autonomy is only a preview today. It requires clean provenance, an
exact unexpired approval, an unconsumed one-time scope, no active mutation
lane, a valid read-only run, report inbox readiness, and no write-capable
bridge or tool path.

Blocked examples:

- stale baseline
- dirty runtime
- broken gateway metadata
- broad or wildcard scope
- expired or consumed approval
- active mutation lane
- write-capable bridge
- commit, PR creation, deploy, restart, runtime switch, queue, worker, timer,
  daemon, Waha, social, payment, or model-routing capability
- delegation, async agent, process registry, send-message, file-operation,
  shell, patch, or `send_to_jenny` paths, even if a caller labels the path
  read-only
- Hermes responder toolsets that include `file`, `terminal`,
  `code_execution`, `delegation`, `kanban`, `messaging`, `browser`, or
  `debugging`; these are not safe read-only executors

Current state target: blocked or preview-ready, never execution-ready.

## Scoped PR Creation

Scoped PR creation is also preview-only. It is meant for a future bounded lane
where Jenny can prepare a PR packet and Codex can implement under its own
engineering checks.

Scoped PR preview requires:

- clean runtime provenance
- exact approved scope
- explicit files or directories
- at most one active mutation lane
- no merge
- no deploy
- no restart
- no runtime switch
- report/result contract
- tests required
- human review required

Current state target: blocked or preview-ready, never execution-ready.

## Laptop Codex Worker Node

The laptop Codex worker-node model tracks:

- parent run ID
- worker-node run ID
- worker identity
- worker host label, usually `laptop-codex`
- assigned objective
- assigned packet summary
- allowed and forbidden actions
- status
- blocked reasons
- report ID
- report contract status
- report review status
- presence status
- last seen timestamp
- worker version and capability summary
- stop/cancel semantics

The laptop can be offline. Mission Control must show that honestly. Jenny may
prepare instructions and review reports, but worker dispatch remains disabled.
Worker-node readiness now requires append-only evidence that the laptop Codex
worker is explicitly online and recently seen. Missing, unrecognized, offline,
or stale presence records block the worker-node lane. This is record-based
truth only; Mission Control does not ping the laptop or activate a worker.
Every worker-node packet also requires a report contract with tests/checks and
human review, because laptop Codex is an engineering worker node and Jenny
must receive verifiable evidence before depending on the result.

Current state target: preview-ready tracking, not execution-ready.

## Child-Agent Tracking

Child-agent records track planned delegation without enabling live delegation.
They show parent run, child run, agent identity, objective, status, failure
reason, report linkage, dependencies, and stop/cancel state.

Child-agent records are display-only and not trusted for execution.

## Reports

Jenny should not mark work done just because a worker says it is done. The
report should answer the contract:

- what changed
- what evidence proves it
- what tests ran
- what risks remain
- what is blocked
- what the next safe action is

Reports are append-only. A later report can supersede or correct an earlier
one, but it should not overwrite history.

Mission Control projects approval and run lifecycle summaries from append-only
records. The approval lifecycle row shows available, pending, and expired
approvals. Approval gaps call out duplicate approvals, consumed approvals, and
runs tied to unavailable approval records. The run lifecycle row shows active,
terminal, and stop/cancel runs. Run gaps call out duplicate runs, terminal runs
without reports, stale report links, and the one-active-mutation-lane rule.

Mission Control now projects a report lifecycle summary from append-only
records. The report lifecycle row shows open, reviewed, and terminal report
counts. The report gaps row shows duplicate report IDs, overwrite conflicts,
completed runs with no report, and stale run-to-report links. An overwrite
conflict means the same report ID was appended more than once with changed
identity or review fields; Jenny must treat that report chain as quarantined
until Travis reviews the append-only history. A report link mismatch means the
report exists, but its own run ID points to a different run than the child or
worker record that references it; even an accepted report stays blocked until
that lineage is reviewed. The report review blockers row lists the exact report
or run IDs Jenny must review before treating the work as closed.

Mission Control also projects a report review queue for Jenny. This queue puts
worker-node reports, child-agent reports, duplicate report records, and missing
required reports into a manual review order. It also counts linked reports whose
own run ID points at a different parent, child, or worker record, because an
accepted-but-mismatched report is still unsafe to rely on. The top report review
row tells Travis what Jenny should read first and why. The queue is advisory and
display-only; it does not write review records, contact Codex, dispatch work, or
mark a report accepted.

Mission Control also checks report contract completeness. A report should have
summary, result, risks or blockers, evidence, tests, next lane, and safety
confirmation. Missing fields stay as manual Jenny review blockers; the
projection does not accept, reject, or mutate the report.

Child-agent and laptop Codex worker-node rows also join against `ReportRecord`
when possible. A worker row can therefore show whether the referenced report
was found and whether Jenny has reviewed, accepted, rejected, or superseded it.
Missing or unreviewed linked reports remain display-only blockers; they do not
enable worker dispatch or execution.

Mission Control also projects a next-safe-action summary from the same backend
truth. This row tells Travis the first manual review step Jenny should take,
such as reviewing provenance, approval, run, report, worker-node, child-agent,
or tool-permission blockers. The projection is advisory only: it is
display-only, not stored as an approval, and keeps work execution, bridge
sending, and worker-node dispatch disabled.

The operator decision packet is the plain-language rollup for Travis. It
combines runtime provenance, readiness, the next safe action, the report review
queue, worker instruction availability, child instruction availability, and the
hard locks into one advisory packet. It is not an approval and is not an
execution command; it tells Jenny and Travis what to review next. It also
rolls up report-link mismatches by unique report and by review surface, so
Jenny can see whether the queue, ingestion check, completion path, or
stop/cancel control found lineage that must be reviewed before handoff.

The orchestration readiness summary rolls the backend gates into three plain
states: supervised read-only autonomy, scoped PR creation, and laptop Codex
worker-node. A state may be blocked or preview-ready, but this lane still keeps
execution-ready false. Travis should treat preview-ready as "safe to prepare a
manual packet for review," not "safe to run automatically."

The worker-node instruction preview turns the latest laptop Codex worker record
into a manual handoff prompt. It states the worker, objective, allowed actions,
hard forbidden actions, Codex's own engineering safety-hardness contract, and
the report contract. It is useful copy for Jenny or Travis to review, but it
does not contact the laptop, start a worker, or enable execution. It also
blocks the next worker instruction when the linked worker report is missing,
still needs Jenny review, is linked to the wrong run, or the worker record
carries a failure reason. Jenny must review the report before issuing another
worker packet.
Mission Control distinguishes "preview available" from "handoff ready" so a
visible worker packet is not mistaken for permission to send it.

The execution mode classification is the early "what kind of work is this?"
row. It only classifies the requested lane as read-only preview, scoped PR
preview, laptop Codex worker-node preview, higher-risk blocked, or unknown
blocked. Deploy, restart, runtime switch, merge, Waha/social/payment,
model-routing, queue mutation, timers, live dispatch, session-send, and worker
dispatch markers remain blocked and require a separate future approval. This
classification is not a work packet and still keeps all execution flags false.

The execution packet preview is the canonical bounded work-packet view. It
wraps the active approval, run, scope, report contract, and worker-node
contract into one advisory packet. It may say blocked or preview-ready, but it
always keeps `would_execute`, `execution_enabled`, `dispatch_enabled`,
`session_send_enabled`, and `worker_dispatch_enabled` false. A worker-node
packet also requires explicit online worker presence before it can be
preview-ready, and its worker-node contract carries the same Codex
engineering safety-hardness requirement as the manual handoff prompt.

The orchestration run graph joins parent runs, child-agent runs, laptop Codex
worker-node runs, and reports into one display-only lineage view. Missing
parent runs, missing report IDs, stale report links, and reports tied to
unknown run IDs remain blockers until Jenny can review or repair the append-only
records.

The stop/cancel control row reviews any stopping, stopped, or cancelled parent,
child-agent, or laptop Codex worker-node run. A stopped or cancelled item still
needs a stop reason, a linked final report, and Jenny review before another
instruction depends on it. If the final report exists but its own run ID points
at a different run, child run, or worker-node run, the item stays blocked as a
report-link mismatch. A stopping item remains blocked until a human confirms
the stop state. This is only a review surface; it does not send stop signals,
cancel work, dispatch agents, or mutate records.

The result ingestion contract checks whether a report is safe for Jenny to
rely on. It requires append-only consistency, linkage to a parent/child/worker
run, an accepted redaction status, no forbidden raw metadata keys such as
tokens, transcripts, raw logs, local paths, or API responses, and an explicit
safety confirmation. It never accepts or rewrites the report; it only tells
Travis which reports are ready for manual review and which need repair.

The report completion path checks terminal run, child-run, and laptop Codex
worker-node records before Jenny treats work as closed. A completed, failed,
blocked, stopped, or cancelled item must have a linked report that is accepted,
contract-complete, redacted, metadata-safe, and safety-confirmed. A report that
is only reviewed can inform Jenny, but it still blocks completion until Jenny
or Travis explicitly accepts it. The projection never closes a run or accepts a
report; it only shows whether the evidence chain is complete enough for Jenny
and Travis to review.

The child-agent instruction preview mirrors the laptop Codex worker preview for
planned delegation. It gives Jenny a manual prompt with child-agent identity,
objective, allowed actions, forbidden actions, and report requirements. It does
not start delegation, send a session, mutate records, or enable dispatch.
Mission Control also separates child-agent "preview available" from "handoff
ready" so an unresolved child report or blocker cannot be mistaken for a safe
next delegation instruction.

## Mission Control Reading Guide

- Runtime provenance: source and runtime trust.
- Read-only autonomy: whether a read-only lane could be preview-ready.
- Scoped PR lane: whether a bounded PR packet could be preview-ready.
- Bridge permission: whether the bridge is manual-only, read-only safe,
  write-capable, or unknown-blocked.
- Execution mode: whether the requested lane is read-only, scoped PR,
  worker-node preview, or blocked as higher-risk/unknown before any packet is
  considered.
- Child-agent status: planned delegation state.
- Laptop Codex worker-node: worker host, assignment, blocked reasons, and
  report status.
- Worker presence: whether the latest laptop Codex worker record proves
  online, recently seen presence; unknown, offline, or stale presence blocks
  readiness.
- Lifecycle projection: latest-by-ID approvals, runs, and reports from
  append-only records.
- Approval lifecycle: available, pending, expired, consumed, rejected, missing,
  and unavailable approval chains.
- Run lifecycle: active, terminal, stop/cancel, mutation-lane, and missing
  report chains.
- Report lifecycle: report inbox/review state, duplicate IDs, overwrite
  conflicts, missing reports, stale report links, and exact review blockers.
- Report review queue: Jenny's prioritized manual review list, including top
  report, reason, missing report links, mismatched report links, and
  worker/child report context.
- Result ingestion: whether reports are linked, redacted, metadata-safe, and
  include a safety confirmation before Jenny relies on them; mismatched report
  links stay blocked.
- Report completion: whether terminal run, child, and worker-node records have
  linked, reviewed, contract-complete, ingestion-safe reports before closure,
  including mismatched-link blockers.
- Report contract compliance: whether reports include required result fields
  before Jenny accepts or relies on them.
- Stop/cancel control: whether stopping, stopped, or cancelled runs have a
  reason, final report, Jenny review, and matching final-report lineage.
- Next safe action: the highest-priority manual review or preview-preparation
  step; it does not enable execution.
- Operator decision packet: a plain-language packet for Travis showing state,
  whether approval is required, next instruction, top report review, blockers,
  and hard locks.
- Orchestration readiness: blocked or preview-ready state for supervised
  read-only autonomy, scoped PR creation, and laptop Codex worker-node.
- Worker instruction preview: a manual Codex handoff prompt with objective,
  allowed actions, forbidden actions, and report requirements.
- Execution packet preview: the bounded work-packet contract for Jenny and
  Travis to review; it is not a dispatch or approval.
- Orchestration run graph: parent/child/worker/report lineage and any missing
  parent or report-link blockers.
- Child instruction preview: a manual child-agent delegation prompt and report
  contract; it does not activate delegation.

If a row says blocked, Travis should read the blocker first instead of trying
to force the action.

## Still Forbidden

Until separately approved, do not use this lane for:

- live deploy
- restart
- runtime switch
- appending `AcceptedBaselineRecord`
- live state database mutation
- live config mutation
- live record mutation
- live operational endpoint calls
- worker dispatch
- session sending
- Waha, social, payment, model-routing, queue, worker, timer, or daemon
  activation
- secrets inspection or output
- PR merge
- operational reconciliation of gateway, dashboard, or baseline
- `9121 /api/status` as a gate

## Future Live Reconciliation

Live operational reconciliation remains a separate approval lane. Before it can
be considered, Mission Control must already prove:

- clean runtime provenance
- exact accepted baseline truth
- dashboard and gateway truth
- rollback truth
- zero unsafe active lanes
- explicit approval and report contract
- tests and review gates
- a manual recovery path

## Audit After Code Changes

After each code-side change:

1. Check git status and branch.
2. Confirm no unrelated dirty files were touched.
3. Run focused tests for the changed boundary.
4. Run broader checks when the change touches shared contracts.
5. Confirm Mission Control still shows disabled execution, dispatch, session
   sending, and worker dispatch.
   Phone and compact routes must also fail closed on `would_execute`,
   dispatch, execution, session-send, worker-dispatch, worker, timer, daemon,
   Discord automation, and model-routing flags.
6. Confirm no secrets or raw private paths were added to docs, tests, or UI.
7. Commit coherent chunks and keep the PR reviewable.
