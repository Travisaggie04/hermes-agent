# Hermes Mission Control OS Discovery and Runbook

Date: 2026-06-01

## Goal

Mission Control OS should turn the current Hermes dashboard into a safe local
control plane for Travis/Jenny operations. It should make project state,
worker results, approval gates, and next prompts visible without relying on
Discord copy/paste, but it must not become autonomous computer use or a broad
remote-control surface.

This pass is discovery and architecture only. No dashboard rewrite, public
exposure, autonomous mouse/keyboard/browser control, email sending, publishing,
payment activation, customer outreach, destructive action, or always-on worker
is in scope.

## Current Status Board

The dashboard is a React/Vite frontend served by `hermes_cli/web_server.py`
through FastAPI/Uvicorn. `web/src/App.tsx` routes the landing page to
`/mission-control`, and `web/src/pages/MissionControlPage.tsx` already provides
the first Mission Control surface.

Current dashboard pages include:

- Mission Control: project cards, status-file links, daily drivers, approval
  counts, gateway status, active automation, recent sessions, social platform
  local status, and safe prompt templates.
- Approvals: standing gates plus dynamic approval records under
  `$HERMES_HOME/state/ops-center/approval-inbox.json`.
- Ops Runs: read-only ledger combining recent Hermes sessions and cron jobs.
- Sessions, Analytics, Models, Logs, Cron, Skills, Plugins, Profiles, Config,
  Keys, Docs, and optional Chat.

The dashboard data flow is mostly poll-based. Mission Control, Approvals, and
Ops Runs call `api.getStatus`, `api.getCronJobs("all")`, `api.getSessions`,
`api.getOpsApprovalSummary`, `api.getOpsApprovals`,
`api.getOpsApprovalAudit`, `api.getOpsActionRegistryStatus`,
`api.getOpsMemoryStatus`, and local social-status endpoints on a 30 second
interval. The general status page has a faster refresh path.

Private-access assumptions:

- `hermes dashboard` binds to `127.0.0.1` by default.
- FastAPI middleware rejects unexpected Host headers for loopback binds.
- Most `/api/*` routes require an ephemeral per-process
  `X-Hermes-Session-Token`; only a small public read-only list is exempt.
- CORS is limited to localhost origins.
- Binding to `0.0.0.0` requires `--insecure` and remains unsuitable for public
  exposure because the dashboard can inspect and mutate local config/secrets.
- Docker/s6 can supervise the dashboard only when `HERMES_DASHBOARD` is truthy;
  otherwise the service slot exits and is not restarted.

## Current Hermes API Capabilities

There are two relevant API surfaces.

The dashboard REST API in `hermes_cli/web_server.py` provides:

- Health/status: `GET /api/status`.
- Session access: `GET /api/sessions`, session search, message history, latest
  descendant, and delete.
- Logs and analytics: `GET /api/logs`, `/api/analytics/*`.
- Cron/job state and mutation: list, create, update, pause, resume, trigger,
  delete under `/api/cron/jobs`.
- Ops state: approvals, approval audit, summary, fixed action registry,
  memory status, local social platform status, and manual social status writes
  under `/api/ops/*`.
- Embedded TUI: `/api/pty` WebSocket when launched with `--tui`; this is the
  real `hermes --tui`, not a React chat rewrite.

The gateway API server in `gateway/platforms/api_server.py` provides an
OpenAI-compatible local backend:

- `POST /v1/chat/completions`.
- `POST /v1/responses`, response retrieval, and response deletion.
- `GET /v1/models`, `GET /v1/capabilities`.
- Runs API: `POST /v1/runs`, `GET /v1/runs/{run_id}`,
  `GET /v1/runs/{run_id}/events`, `POST /v1/runs/{run_id}/approval`, and
  `POST /v1/runs/{run_id}/stop`.
- Health: `GET /health` and `GET /health/detailed`.
- Jobs API under `/api/jobs`.

The API server defaults to `127.0.0.1:8642`, uses bearer auth from
`API_SERVER_KEY`, requires a key for non-loopback binds, and does not enable
browser CORS unless explicitly configured.

## Existing Queue, Audit, Approval, and Artifact Patterns

Approval gate:

- `hermes_cli/ops_approvals.py` is profile-local JSON/JSONL storage.
- It records decisions only by default. Approving a request sets
  `execution_allowed` to false and generates a Jenny command for the normal
  chat/tool flow.
- Audit events append to
  `$HERMES_HOME/state/ops-center/approval-audit.jsonl`.
- Allowed risk labels include Read-only, Draft-only, Local-build,
  Live-service, Money/customer, Credential/auth, Destructive, and Security
  boundary.

Fixed action registry:

- `hermes_cli/ops_actions.py` exposes exactly one fixed action today:
  `read_only_status_probe`.
- Execution is disabled by default through `ops_center.action_execution_enabled`
  and `ops_center.allowed_actions` in `DEFAULT_CONFIG`.
- Even when enabled, the only executable path returns gateway/dashboard status
  metadata and writes only audit-log events.
- Arbitrary commands, gateway restart, cron mutation, credential change,
  public/payment action, and messaging outreach are blocked classes.

Laptop SSH Capability:

- Capability name: `laptop_ssh_read_only_inspection`.
- Default state: disabled until preflight-approved.
- Purpose: preserve the approved private route for laptop-local files so Jenny
  does not conclude a laptop file is unavailable merely because it is absent
  from the VPS filesystem.
- Locality trigger phrases: "my laptop", "Downloads", "Windows Downloads",
  "MSI laptop", "TRAVIS-MSI", and known laptop paths such as
  `C:\Users\Travis\Downloads\`.
- Approved route:
  - SSH alias: `main-laptop`
  - Hostname: `travis-msi.taila00f3c.ts.net`
  - User: `travis`
  - Remote machine: `TRAVIS-MSI`
  - Remote home: `C:\Users\Travis`
  - Downloads path: `C:\Users\Travis\Downloads\`
  - Agent OS pack: `C:\Users\Travis\Downloads\agent-os-pack\` and
    `C:\Users\Travis\Downloads\agent-os-pack.7z`
- Required locality behavior:
  - First classify whether the requested file is expected on the VPS, the
    laptop, OneDrive/rclone, or an unknown source.
  - Check current local/VPS paths only if relevant to that classification.
  - If not found locally and likely on the laptop, consider this approved SSH
    route.
  - If SSH fails, report the exact failure and do not claim the file does not
    exist globally.
- Allowed modes: read-only existence checks, directory listing, file metadata,
  and checksum checks within the approved path.
- Blocked modes: copy, delete, move, extract, execute, install, broad recursive
  inventory, secret reading or printing, unrelated personal-file inspection,
  and any mutation of laptop files or settings.
- Approval requirements: before using SSH, state the alias or host, target
  path, exact read-only Windows command or commands, that no secrets will be
  printed, and that no files will be modified, copied, deleted, extracted, or
  run. Require approval unless an active approval slice already grants that
  exact read-only laptop inspection.
- Safe Windows command patterns: bounded `cmd /c if exist ...` existence
  checks, bounded `cmd /c dir ...` listings for the approved path,
  PowerShell `Get-Item` metadata reads for exact approved paths, and
  PowerShell `Get-FileHash` checksum reads for exact approved files.
- Forbidden command patterns: `copy`, `xcopy`, `robocopy`, `move`, `del`,
  `erase`, `rmdir`, archive extraction, installers, script execution, broad
  recursive `dir /s` inventory, commands that read `.env`, private keys,
  browser profiles, credentials, tokens, SSH keys, or unrelated personal file
  contents.
- Privacy constraints: never print SSH keys, tokens, credentials, `.env`
  contents, private keys, browser profile data, or unrelated personal file
  contents.

Task queue and worker output:

- Hermes Kanban is the existing durable task queue. The shared board lives
  under the Hermes root, with optional per-board SQLite DBs under
  `<root>/kanban/boards/<slug>/`.
- Task states include triage, todo, scheduled, ready, running, blocked,
  review, done, and archived.
- Worker runs write structured summaries, metadata, comments, events,
  heartbeats, and per-task logs.
- The Kanban dashboard plugin reads `task_events`, task runs, comments,
  latest summaries, diagnostics, and worker logs. It can also receive live
  updates over its authenticated WebSocket.
- Worker handoffs are expected to use structured `summary` and `metadata`
  fields. Review-required work is intentionally blocked for human review.

Status artifacts:

- Mission Control currently links to AI Ops Brain `PROJECT_STATUS.md` files
  for project state and uses local JSON snapshots for social status.
- Good future Mission Control state should continue to be file/DB-backed,
  inspectable, and append-audited instead of hidden in transient chat.

## Desired Control Plane

Mission Control should become an operator console with four lanes:

1. Observe: read status files, sessions, logs, cron state, Kanban tasks, worker
   results, approval gates, and audit logs.
2. Decide: create or update approval proposals and next Codex prompts without
   executing risky work.
3. Queue: save bounded prompts or Kanban tasks for later execution by the
   correct Hermes profile.
4. Notify: send lightweight notifications to Discord/WhatsApp when something
   needs Travis, but keep the actual state and controls in Hermes.

Mission Control operations also need a lane lock before action. Jenny should
classify the active lane, explicitly allowed actions, forbidden adjacent lanes,
other-thread/chat exclusions, and the approval slice required before crossing
lanes. Context from a neighboring lane may be recorded as risk/background, but
it must not authorize work outside the current lane. A documentation-only lane
stays documentation-only; a read-only inventory lane stays read-only; a
stop-state lane permits no cleanup or forward progress; and a cleanup/revert
lane may touch only the named cleanup target.

## Task Control Envelope T2 Design Model

T2 is a design/specification model for future Mission Control task routing. It
does not implement enforcement, command parsing, preflight checks, approval
records, dashboard UI, MCP tools, runtime behavior, feature flags, or
persistence migrations. Any code that consumes this model belongs to a later
reviewed implementation slice.

The Task Control Envelope is the normalized control packet Mission Control
should place around a bounded Jenny/Codex task before the task is started,
queued, or handed to a future approval surface. Its action fields must use only
the G1 canonical action categories from
`docs/design/goal_contract_approval_slice_g1_20260602.md`.

Proposed envelope schema:

```yaml
schema: mission_control.task_control_envelope.v1
task:
  id: string
  title: string
  source: string
  source_ref: string
  created_at: string
  created_by: string
repo:
  path: string
  branch: string
  head: string
mode:
  active_mode: string
  preset: string
  allowed_actions: [string]
  forbidden_actions: [string]
  checkpoints: [string]
lane_lock:
  active_lane: string
  explicitly_allowed_actions: [string]
  explicitly_forbidden_actions: [string]
  adjacent_context_not_authority: [string]
  other_thread_workstreams_excluded: [string]
  approval_slice_required_before_crossing: string
capabilities:
  required: [string]
  optional: [string]
  blocked: [string]
  registry_snapshot_ref: string
file_locality:
  requested_paths: [string]
  expected_locations: [string]
  resolver_decision: string
dirty_worktree:
  status: string
  allowed_dirty_paths: [string]
  unrelated_dirty_paths: [string]
  checkpoint_on_unrelated_dirty_files: string
evidence:
  required_cards: [string]
  produced_cards: [string]
relationships:
  mission_brief_ref: string
  g1_spec_ref: string
  g2_goal_contract_ref: string
  w1b_artifact_metadata_ref: string
  w1c_artifact_browser_ref: string
  g3_approval_slice_ref: string
```

The schema is intentionally declarative. `allowed_actions`,
`forbidden_actions`, `explicitly_allowed_actions`, and
`explicitly_forbidden_actions` are category lists, not executable commands.
They must be drawn from the G1 action category set:
`discuss`, `plan`, `inspect_repo`, `read_files`, `search_files`, `edit_files`,
`run_focused_tests`, `run_broad_tests`, `run_build`, `run_lint`,
`run_dev_server`, `browser_qa`, `install_dependencies`, `change_config`,
`touch_secrets`, `commit`, `push`, `open_pr`, `deploy`, `restart_service`,
`public_bind`, `oauth_connector`, `external_network`, and `destructive_git`.

### Active Mode Defaults

Active Mode is the future per-task posture selected from the G1 preset names.
Mode defaults define the starting category allowance, but the Task Control
Envelope can narrow them further for a specific task. It cannot widen them
without a later approval slice.

| Active Mode | Default allowed G1 action categories | Default checkpoint posture |
|---|---|---|
| `discussion-only` | `discuss`, `plan` | `stop_after_plan`, `stop_on_scope_expansion` |
| `inspection-only` | `discuss`, `plan`, `inspect_repo`, `read_files`, `search_files` | `stop_after_inspection_report`, `stop_on_scope_expansion` |
| `implement-slice` | `discuss`, `plan`, `inspect_repo`, `read_files`, `search_files`, `edit_files`, `run_focused_tests`, `run_build`, `run_lint`, `browser_qa` | `stop_after_implementation_report`, `stop_after_validation_report`, `stop_on_validation_failure`, `stop_on_scope_expansion` |
| `commit-only` | `discuss`, `inspect_repo`, `read_files`, `search_files`, `run_focused_tests`, `run_build`, `run_lint`, `commit` | `stop_after_local_commit_report`, `stop_on_unrelated_dirty_files` |
| `local-smoke-test` | `discuss`, `inspect_repo`, `read_files`, `search_files`, `run_focused_tests`, `run_build`, `run_lint`, `run_dev_server`, `browser_qa` | `stop_after_validation_report`, `stop_on_validation_failure` |
| `stop-state-only` | `discuss`, `inspect_repo`, `read_files`, `search_files` | `stop_after_status_report`, `stop_on_scope_expansion` |

The default denied posture is every G1 category not listed for the active mode.
Task-specific forbidden actions should still be recorded explicitly when the
operator names them, because an explicit denial is more useful to reviewers than
an implied omission.

### Checkpoint Mapping

T2 uses the G1 checkpoint vocabulary as event labels for future task control,
not the current filesystem checkpoint manager. The checkpoint labels map to
Mission Control moments:

- `stop_after_status_report`: stop after reporting current state; no cleanup or
  forward progress.
- `stop_after_plan`: stop after a proposed plan or task split.
- `stop_after_inspection_report`: stop after local read-only findings.
- `stop_after_implementation_report`: stop after documentation/code edits are
  summarized, before validation expansion.
- `stop_after_validation_report`: stop after the allowed focused validation is
  reported.
- `stop_after_local_commit_report`: stop after a local commit summary, before
  any `push` or `open_pr`.
- `stop_on_scope_expansion`: stop when satisfying the task would require a G1
  category not allowed by the envelope.
- `stop_on_validation_failure`: stop and report when allowed validation fails.
- `stop_on_unrelated_dirty_files`: stop when unrelated dirty files affect the
  requested work.
- `stop_on_dependency_change_needed`: stop when `install_dependencies` is
  needed but not already allowed.
- `stop_on_restart_or_deploy_needed`: stop when `restart_service` or `deploy`
  is needed but not already allowed.
- `stop_on_user_message_conflict`: stop when a newer user message conflicts
  with the active envelope.

### Transition Rules

T2 transitions are conservative:

- A task may move to a narrower mode without approval.
- A task may not add any new G1 action category unless a future G3 Approval
  Slice or equivalent user approval explicitly allows that category.
- A task may not cross from `read_files` or `search_files` into `edit_files`
  without the active envelope allowing `edit_files`.
- A task may not cross from `edit_files` into `commit`, `push`, `deploy`, or
  `restart_service` unless those categories are explicitly allowed.
- A task may not use `touch_secrets`, `oauth_connector`, `external_network`,
  `public_bind`, or `destructive_git` unless the active envelope explicitly
  allows the category and the capability state is compatible.
- If W1C or G3 does not exist in the checkout, the transition must stop at the
  design boundary rather than pretending an implementation surface is present.

### Evidence Cards

Evidence Cards are small review records attached to the envelope. They are
designed for future dashboard/API rendering and should be safe to display
without exposing secrets. A card should include:

- `card_id`
- `kind`
- `summary`
- `source_ref`
- `action_categories`
- `files_or_artifacts`
- `commands_run`
- `result`
- `redaction_notes`
- `created_at`

The `action_categories` field must contain only G1 action categories. Example
card kinds include repo-state, diff-summary, validation, secret-scan,
dirty-worktree, file-locality, capability-state, and reviewer-verdict. These
are display kinds, not action names and not execution authority.

Evidence Cards relate to W1B by pointing at artifact metadata instead of
embedding large artifacts. W1C may later browse the cards and linked artifacts,
but W1C is not present in this checkout unless it is reimplemented in a later
slice.

### File Locality Resolver

The File Locality Resolver is a future preflight/read model that classifies
where requested files are expected to live before any file access occurs. It
should record:

- requested path or path hint
- expected location, such as repo checkout, Hermes profile state, AI Ops Brain,
  laptop-local path, OneDrive/rclone-backed path, or unknown
- allowed G1 categories for the lookup
- forbidden G1 categories for the lookup
- exact stop checkpoint if the file is not available in the allowed locality

The resolver must not turn a missing local file into authority for
`external_network`, `oauth_connector`, `touch_secrets`, or laptop/OneDrive
inspection. Those categories require explicit envelope permission and a
compatible capability state. In this T3 docs-only slice, laptop SSH, OneDrive,
rclone, and external access remain forbidden.

### Dirty Worktree Gate

The Dirty Worktree Gate is a future pre-edit and pre-commit control. It should
capture branch, HEAD, dirty file list, which dirty paths belong to the current
task, and which paths are unrelated. If unrelated dirty files are present and
the task would need `edit_files`, `commit`, or `destructive_git`, the envelope
should trigger `stop_on_unrelated_dirty_files`.

The gate is not a cleanup instruction. It must never authorize deleting,
reverting, formatting, or committing unrelated files. Cleanup/revert remains a
separate active lane with its own envelope.

### Lane Lock

Lane Lock is the operator-facing summary of the envelope. It should be produced
before action and repeated in the final handoff for bounded lane work. It
records the active lane, explicitly allowed actions, explicitly forbidden
actions, adjacent context that must not be acted on, excluded workstreams, and
the approval slice required before crossing lanes.

Lane Lock is stricter than Active Mode. Active Mode supplies default category
sets; Lane Lock binds the actual task. If the user says "documentation-only",
Lane Lock must limit `edit_files` to documentation files and deny disallowed
G1 categories such as `run_focused_tests`, `run_broad_tests`, `deploy`,
`restart_service`, `external_network`, and any other forbidden G1 category
named in the prompt. Runtime behavior and UI changes remain out of scope unless
a later envelope names them and grants the matching G1 categories.

### Capability Registry Integration

The future Capability Registry should describe what the current checkout,
profile, host, and approval context can safely do. It should not grant action
authority by itself. The Task Control Envelope remains the task-specific
authority boundary.

Capability records should include a stable capability name, state, source,
required G1 action categories, denied G1 action categories, locality limits,
secret-redaction posture, audit requirements, and expiry. Suggested states are
`absent`, `available`, `disabled`, `blocked`, `requires_approval`, and
`approved_for_slice`. A capability in `available` state still cannot be used
unless the envelope allows the matching G1 category.

Mission Control should use registry snapshots to populate Evidence Cards and
to explain why a requested transition is blocked. For example, a laptop-local
file resolver capability may be known, but a task whose envelope forbids
`external_network` must still stop before using it.

### Related Specs and Surfaces

- Phase 1A Mission Briefs: provide human-facing objective, scope, constraints,
  and verification expectations that can seed a Task Control Envelope.
- G1 Goal Contract spec constants: provide the canonical action categories,
  presets, checkpoint labels, approval states, source fields, and policy values
  used by T2. T2 must not add new action categories.
- G2 Goal Contract records: future persisted goal-contract records should store
  or reference the envelope so the agent and dashboard agree on task boundaries.
- W1B Artifact metadata endpoint: should provide artifact references for
  Evidence Cards, worker results, validation logs, and packet previews without
  embedding large or sensitive content in the envelope.
- W1C Artifact Browser UI: future browser surface for Evidence Cards and
  artifacts. W1C is reconciled as not present in this checkout unless it is
  reimplemented later.
- G3 Approval Slice records: future approval records that may allow an envelope
  transition, category expansion, or capability use. T2 only points to the
  approval slice requirement; it does not create or enforce G3 records.

Discord should become notification-only because it is a poor source of truth:
thread rollover loses context, copy/paste relays waste Codex turns, and
important state is hard to query. Discord can still announce "approval needed",
"worker blocked", or "new result ready", with a link or identifier pointing
back to dashboard/API state.

## Recommended Architecture

Keep the existing dashboard and add narrow read models before write tools:

- Source-of-truth layer:
  - AI Ops Brain status files for human-readable project state.
  - Kanban DB for durable task/work queue and worker results.
  - SessionDB for Hermes conversations/tool traces.
  - Cron job store for scheduled work.
  - Ops approval JSON/JSONL for decision records and audit.
  - Local ops snapshots for social/platform readiness.
- Backend read facade:
  - Add small `/api/mission-control/*` routes only when aggregation starts to
    duplicate frontend logic or must be shared with MCP.
  - Prefer read-only aggregate endpoints first:
    `status`, `open-tasks`, `latest-worker-results`, `repo-status`,
    `approval-gates`, and `recent-audit-log`.
- Dashboard:
  - Extend the existing Mission Control, Approvals, Ops Runs, and Kanban
    plugin surfaces.
  - Do not rebuild the primary chat transcript/composer in React; embedded
    chat remains the real TUI.
- Execution:
  - Use Hermes API server runs or Kanban worker dispatch for agent work.
  - Use `POST /v1/runs`, run polling, SSE events, approval resolution, and
    stop support instead of screen control.
  - Do not add mouse/keyboard/browser-control automation.

## Future ChatGPT OAuth/MCP Bridge

Hermes already has MCP server infrastructure:

- `mcp_serve.py` runs a FastMCP stdio server for messaging/channel bridge
  tools.
- `agent/transports/hermes_tools_mcp_server.py` exposes a curated subset of
  Hermes tools to Codex via stdio MCP.
- `tools/mcp_tool.py`, `tools/mcp_oauth.py`, and
  `tools/mcp_oauth_manager.py` implement MCP client support and OAuth 2.1 PKCE
  token storage/recovery for outbound MCP servers.

The future ChatGPT bridge should be a new narrow MCP server, not an expansion
of the current broad messaging bridge and not a public dashboard. Recommended
shape:

- Add `mission_control_mcp_server.py` or a `hermes_cli/mission_control_mcp.py`
  module that uses FastMCP and calls the same read facade used by the
  dashboard.
- Start with stdio/local transport for development. Add remote HTTP/SSE only
  after OAuth, scope checks, rate limits, audit logging, and deployment
  isolation are reviewed.
- Use OAuth as an access boundary for ChatGPT, but never pass Hermes secrets,
  API keys, cookies, or dashboard session tokens through MCP tool results.
- Store bridge OAuth tokens under profile-local Hermes auth/token storage with
  0o600 files and the existing secure-parent-dir pattern.
- Scope the bridge to Mission Control tools only. It should not inherit the
  broad Hermes tool registry, terminal, browser, file mutation, email, or
  publishing tools.

Safe first MCP tools:

- `get_project_status`
- `get_open_tasks`
- `get_latest_worker_results`
- `get_repo_status`
- `get_approval_gates`
- `get_recent_audit_log`
- `save_next_codex_prompt`
- `import_worker_result`
- `pause_future_outreach`
- `block_all_sends`

The last four are writes, but should be local-control writes only:
append/save a prompt packet, import a worker-result artifact into local state,
or set local block flags. They must not send, publish, delete, launch, pay,
or run a broad Codex session.

Blocked MCP tools/actions:

- `send_email`
- `publish_video`
- `activate_payment`
- `delete_files`
- `run_unbounded_codex`
- `autonomous_computer_use`
- `start_bulk_outreach`
- Any arbitrary shell, dashboard token reveal, OAuth token reveal, API key
  reveal, browser/mouse/keyboard control, credential mutation, public launch,
  payment activation, customer outreach, or destructive filesystem action.

## Approval Gates

Keep current default posture:

- Read-only and dry-run by default.
- Fixed named actions only; no free-form command execution.
- Dashboard approval records remain decision records, not direct execution
  authority.
- Execution stays disabled unless `ops_center.action_execution_enabled` is true
  and the exact fixed action appears in `ops_center.allowed_actions`.
- Expiring approvals and risk labels remain mandatory.
- High-risk classes require exact Travis approval in current context:
  live-service restart, customer/money/public action, credential/auth change,
  destructive change, and security-boundary change.

For the MCP bridge, every write-capable tool should:

- Validate project/profile/scope.
- Write an append-only audit record.
- Return a dry-run preview unless explicitly told to save a local-only packet.
- Refuse execution if the target maps to a blocked action class.

## Audit Logging

Use append-only JSONL for bridge actions, modelled after
`approval-audit.jsonl`. Minimum event fields:

- `timestamp`
- `actor`
- `surface` (`dashboard`, `mcp`, `chatgpt`, `cron`, or `kanban`)
- `tool`
- `project`
- `profile`
- `target`
- `dry_run`
- `result`
- `source_ref`

Never log secrets, OAuth tokens, API keys, cookies, raw Authorization headers,
or dashboard session tokens. Redact previews before audit when source text may
contain credentials.

## Codex-Usage Minimization Strategy

Current waste pattern:

- Codex is being used as a relay between Discord threads, project status files,
  dashboard state, and worker results.
- Codex turns are spent summarizing state that should already be queryable.
- Codex is asked to produce next prompts manually because there is no durable
  prompt queue/control-plane packet.

Mission Control should replace that with:

- Dashboard state cards sourced from status files, Kanban, sessions, cron,
  approvals, and audit logs.
- A prompt packet queue that saves "next Codex prompt" artifacts without
  starting Codex.
- Worker results imported once into local state, then visible to dashboard and
  ChatGPT through read-only APIs.
- ChatGPT oversight through MCP reads: it can ask "what is blocked?" or "what
  should Codex do next?" without Codex being the summarizer.
- Codex reserved for bounded implementation prompts with exact repo, branch,
  task, constraints, and verification commands.

## Phased Rollout

Phase 0: Discovery and runbook

- Document existing dashboard/API/queue/approval/MCP surfaces.
- Do not add broad UI or execution tools.

Phase 1: Read-only aggregation

- Add a backend Mission Control read facade if needed.
- Aggregate project status, open tasks, latest worker results, repo status,
  approval gates, and recent audit logs.
- Keep the dashboard local-only and token-gated.

Phase 2: Local packet writes

- Add local-only `save_next_codex_prompt` and `import_worker_result`.
- Add `pause_future_outreach` and `block_all_sends` as local block-flag writes
  with audit records.
- Add tests for validation, redaction, and blocked classes.

### Phase 2 Implementation Note

Phase 2 adds a dashboard-token-gated local packet store under
`$HERMES_HOME/state/mission-control/packets/`. Packets are file-per-packet JSON
artifacts for operator review and later dashboard/MCP visibility. They are not
execution requests, queue dispatches, Hermes runs, worker starts, emails,
publishing jobs, payment actions, browser controls, or production mutations.

Supported packet writes:

- `codex_prompt`: saves a bounded next Codex/Jenny prompt for later human
  review.
- `worker_result`: imports pasted worker/Jenny/Codex result text as untrusted
  data and extracts display-only metadata such as repo, branch, commits,
  changed files, tests, risks, and next prompt text.
- `block_flag`: records local advisory flags such as `block_all_sends` or
  `pause_future_outreach`. No global enforcement hook exists yet, so these are
  advisory-only packets until a reviewed local state hook is added.

Every packet is forced to `dry_run: true`, `review_required: true`, and
`trusted_for_execution: false`, regardless of request payload. Packet payloads,
previews, and audit records are recursively redacted before storage. Imported
worker text remains inert data; dangerous command-like strings may be preserved
for review after redaction, but they are never transformed into runnable
actions.

Packet audit events append to
`$HERMES_HOME/state/mission-control/packet-audit.jsonl`. Creation and rejection
events record packet kind, project, safety posture, result, warnings, actor, and
surface without raw secrets, dashboard tokens, OAuth tokens, cookies, API keys,
SMTP/Gmail credentials, payment/customer credentials, or Authorization headers.

This reduces Discord/Codex relay usage by making next prompts and worker
handoffs durable local state. ChatGPT or the dashboard can later read the
packet queue directly instead of asking Codex to summarize copied thread state.

The next phase should add dashboard UI integration for listing packets,
reviewing imported worker results, and copying approved next prompts. It should
not add MCP/OAuth or execution tools yet.

Phase 3: Dashboard packet UI

- List Mission Control packets in the dashboard.
- Review packet details, warnings, source refs, approval gates, and worker
  metadata.
- Copy prompt/preview text only; do not add execution controls.

Phase 4: ChatGPT MCP bridge, local/stdout first

- Expose the narrow Mission Control tools through a dedicated FastMCP server.
- Use stdio/local development first; no public endpoint.
- Add OAuth only when remote transport is necessary and reviewed.

### Phase 4 Implementation Note

Phase 4 adds a dedicated local/stdout Mission Control MCP scaffold in
`hermes_cli/mission_control_mcp.py`. This is a narrow bridge for future
ChatGPT/Hermes integration, not a public endpoint and not a general Hermes tool
export. The module can list its tool manifest with:

```bash
python -m hermes_cli.mission_control_mcp --list-tools
```

The command prints local discovery metadata only. It does not start a remote
server, does not run tools, and does not expose dashboard session tokens,
OAuth tokens, API keys, cookies, SMTP/Gmail credentials, payment/customer
credentials, Authorization headers, or credential values.

Existing Hermes MCP patterns found:

- `mcp_serve.py` uses FastMCP over stdio for messaging/channel bridge tools.
- `agent/transports/hermes_tools_mcp_server.py` uses FastMCP over stdio to
  expose a curated Hermes subset to Codex subprocesses.
- `tools/mcp_tool.py` is the outbound MCP client layer for stdio, SSE, and
  Streamable HTTP servers.
- `tools/mcp_oauth.py` and `tools/mcp_oauth_manager.py` implement OAuth 2.1
  PKCE and secure profile-local token storage for outbound MCP clients.

Recommended local/stdout bridge shape:

- Keep `hermes_cli/mission_control_mcp.py` as a separate FastMCP server module
  with stdio as the only supported transport in this phase.
- Call `hermes_cli.mission_control` read helpers and packet helpers directly,
  so dashboard REST auth/session tokens are not needed.
- Return redacted structured data with explicit safety metadata:
  `dry_run=true`, `review_required=true`, `trusted_for_execution=false`,
  `local_only=true`, and `executes_or_dispatches=false`.
- Keep write tools local-packet-only. Packet writes save/audit JSON review
  artifacts and never dispatch the packet.

This bridge is separate from the broad Hermes tool registry because Mission
Control is an operator-control surface, not an agent capability dump. It must
not inherit terminal, browser, file mutation, email, publishing, payment,
credential, worker, Codex-run, Hermes-run, or arbitrary shell tools from the
general registry.

OAuth and remote transport are deferred because they require a separate
security review: scopes, token lifecycle, storage permissions, audit logs, rate
limits, host binding, reverse-proxy behavior, incident recovery, and explicit
rules for what a remote ChatGPT client may read or write. Until that review is
complete, the bridge remains local/stdout only.

Safe Phase 4 tools:

- Read-only: `get_project_status`, `get_open_tasks`,
  `get_latest_worker_results`, `get_repo_status`, `get_approval_gates`,
  `get_recent_audit_log`, `list_mission_packets`, and `get_mission_packet`.
- Local packet writes: `save_next_codex_prompt`, `import_worker_result`, and
  `save_block_flag_packet`.

Blocked tools/actions remain absent from the MCP registry:

- `send_email`, `publish_video`, `activate_payment`, `delete_files`,
  `run_unbounded_codex`, `run_codex`, `start_codex`, `start_worker`,
  `start_hermes_run`, `autonomous_computer_use`, `browser_control`,
  `mouse_control`, `keyboard_control`, `start_bulk_outreach`,
  `arbitrary_shell`, `reveal_secret`, and `update_credentials`.

Test strategy:

- Unit-test the Mission Control MCP registry and `--list-tools` manifest.
- Assert only approved tools are discoverable and blocked tools are absent.
- Assert read tools return redacted structured data or controlled warnings.
- Assert packet write tools create only local packets, preserve safety flags,
  append audit records, and keep worker result text untrusted display data.
- Assert malformed input returns controlled redacted errors.

Future ChatGPT path:

```text
ChatGPT -> local/stdio or future OAuth MCP bridge -> narrow Mission Control tools -> Hermes dashboard/API state
```

This phase does not connect ChatGPT yet. It makes the local tool contract
concrete so future integration can avoid using Codex as a relay for status,
worker-result, and next-prompt state.

Phase 5 remote OAuth/security review prerequisites:

- Threat model remote ChatGPT access and define exact read/write scopes.
- Choose transport and binding rules; no public route until reviewed.
- Add OAuth client/server flow, token storage permissions, token revocation,
  audit events, and rate limits.
- Reconfirm no broad Hermes registry, terminal, browser control, credential
  reveal, send/publish/payment/delete, Codex-run, Hermes-run, or worker-start
  path is exposed.

Phase 5: OAuth-protected remote bridge

Phase 5 is a planning/security-review phase only. The remote security review is
documented in
`docs/design/hermes_mission_control_mcp_remote_security_review_20260601.md`.
It defines the threat model, scope matrix, OAuth/token plan,
audit/rate-limit plan, binding/proxy rules, rollback plan, and Phase 6 test
plan required before any remote MCP transport, OAuth implementation, public
endpoint, or ChatGPT connector work begins.

The reviewed initial posture keeps local/stdout as the safe default. Read-only
Mission Control tools may be eligible first after future controls exist.
Packet-write tools remain local-only/deferred for remote use until a later
review. The dashboard stays private and must not become the remote MCP
surface.

Phase 6: Inert remote MCP policy/schema tests

- Encode the Phase 5 scope matrix as static policy metadata only.
- Keep every future remote tool disabled by default.
- Keep packet-write tools local-only and non-dispatching.
- Test that blocked tool names/classes cannot enter the policy.
- Do not add OAuth, remote transport, public routes, ChatGPT connection, or
  execution paths.

Phase 7: Local MCP client E2E validation

- Validate the existing local/stdout bridge from a local MCP client.
- Keep the test local and inert; do not expose remote transport.
- Exercise `--list-tools`, representative read-only calls, and local
  packet-write calls inside isolated test state.
- Keep remote policy disabled and aligned with the local MCP allowlist.
- Never add autonomous computer-use or real browser/mouse/keyboard control.

Phase 8: Local operator diagnostics or pause

- Prefer a local-only runbook/troubleshooting note and, if needed, an inert
  read-only diagnostic command.
- Phase 8 runbook:
  `docs/design/hermes_mission_control_mcp_local_diagnostics_runbook_20260601.md`.
- Keep local/stdout as the only bridge surface and keep remote policy disabled.
- Do not begin remote OAuth, public endpoint, or ChatGPT connector work without
  a separate implementation plan.

## Next Implementation Prompt

Do not start this yet. Use this when ready for the next small implementation
pass:

```text
Repo: /home/jenny/.hermes/hermes-context-routing-deploy-20260530

Goal:
Implement Phase 1 of Hermes Mission Control OS as a read-only backend facade.
Do not build broad UI and do not add execution tools.

Tasks:
1. Read AGENTS.md and docs/design/hermes_mission_control_os_20260601.md.
2. Add a small read-only Mission Control aggregation module and dashboard API
   routes only if they reduce duplicated frontend logic.
3. First endpoints should be read-only and token-gated:
   - GET /api/mission-control/project-status
   - GET /api/mission-control/open-tasks
   - GET /api/mission-control/latest-worker-results
   - GET /api/mission-control/repo-status
   - GET /api/mission-control/approval-gates
   - GET /api/mission-control/recent-audit-log
4. Use existing sources: AI Ops Brain status paths where already listed,
   hermes_cli.kanban_db read helpers, SessionDB/dashboard sessions,
   ApprovalStore, and existing status/log readers.
5. Do not expose secrets, dashboard session tokens, OAuth tokens, API keys,
   cookies, file mutation, terminal, browser control, email, publishing,
   payment, outreach, or destructive actions.
6. Add focused tests for redaction, read-only behavior, missing source files,
   and route auth.
7. Run the focused pytest targets and report changed files, validations,
   risks, and next prompt.
```
