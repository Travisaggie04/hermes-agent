import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchJSON } from "@/lib/api";
import { cn } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const WORKSPACE_STATUS_URL = "/api/plugins/mission-control-governance/workspace-status";
const WORKSPACE_PROJECTS_URL = "/api/plugins/mission-control-governance/workspace/projects";
const WORKSPACE_PROJECT_BRIEFS_URL = "/api/plugins/mission-control-governance/workspace/project-briefs";
const WORKSPACE_CHALLENGE_REVIEWS_URL = "/api/plugins/mission-control-governance/workspace/challenge-reviews";
const WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL = "/api/plugins/mission-control-governance/workspace/challenge-reviews/create";
const WORKSPACE_LANE_REQUESTS_URL = "/api/plugins/mission-control-governance/workspace/lane-requests";
const WORKSPACE_LANE_REQUESTS_CREATE_URL = "/api/plugins/mission-control-governance/workspace/lane-requests/create";
const WORKSPACE_REPORTS_URL = "/api/plugins/mission-control-governance/workspace/reports";
const WORKSPACE_REPORTS_CREATE_URL = "/api/plugins/mission-control-governance/workspace/reports/create";
const WORKSPACE_JENNY_BRIDGE_OUTBOX_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox";
const WORKSPACE_JENNY_BRIDGE_INBOX_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/inbox";
const WORKSPACE_JENNY_BRIDGE_POLLER_STATUS_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/poller-status";
const WORKSPACE_JENNY_REPLY_REVIEWS_URL = "/api/plugins/mission-control-governance/workspace/jenny-reply-reviews";
const WORKSPACE_JENNY_REPLY_REVIEWS_CREATE_URL = "/api/plugins/mission-control-governance/workspace/jenny-reply-reviews/create";
const WORKSPACE_GITHUB_BRIDGE_STATUS_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/status";
const WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/outbox/create";
const WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once";
const WORKSPACE_PROJECT_STATE_URL = "/api/plugins/mission-control-governance/workspace/project-state";
const WORKSPACE_PROFILE_MEMORY_STORAGE_URL = "/api/plugins/mission-control-governance/workspace/profile-memory-storage";
const MODEL_INFO_URL = "/api/model/info";
const MODEL_OPTIONS_URL = "/api/model/options";
const COMPACT_JENNY_MESSAGE_LIMIT = 1900;
const COMPACT_RUN_EFFORTS = [
  { label: "Minimal", value: "minimal" },
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Extra high", value: "xhigh" },
] as const;

const REAL_PROJECT_IDS = [
  "project-hermes-mission-control",
  "project-long-form-video",
  "project-shorts-video",
  "project-tool-tally",
  "project-waha-work",
] as const;
const HERMES_PROJECT_ID = "project-hermes-mission-control";
const HERMES_UPDATE_LANE_REQUEST = [
  "Start a safe Hermes update readiness lane for the VPS and laptop Hermes worker node.",
  "Inventory the existing VPS-triggered laptop worker-node update path and current installed versions first.",
  "Treat the native laptop desktop app bottom-bar version as a separate installed worker-node version; accepted-live merges and dashboard-only deploys do not update that installed app.",
  "Prepare a non-live VPS dashboard runtime at accepted-live and validate it before any dashboard-only switch.",
  "Keep gateway update as a separate explicit lane.",
  "Do not trigger the laptop worker-node update automatically, restart/switch gateway, dispatch, send sessions, use Waha/social/payment/customer actions, enable new background workers/timers/daemons/cron, or inspect/print secrets.",
].join(" ");
const HERMES_STORAGE_CLEANUP_LANE_REQUEST = [
  "Start a safe Hermes storage cleanup lane for the VPS, with a target of about 50% disk usage when practical.",
  "Inventory VPS disk usage, large runtime/worktree/cache/build artifacts, logs, backup/snapshot directories, and Mission Control record growth before cleanup.",
  "Create a timestamped dry-run manifest before deleting anything; include exact paths, protected paths, expected GiB recovered, and rollback risk.",
  "Preserve the current dashboard runtime, gateway runtime, shared runtime venv, latest rollback runtime, records, secrets, service files, live app data, dirty project worktrees, and report-builder/customer/payment/outreach data.",
  "With explicit cleanup approval, safe candidates may include clean stale Hermes runtime worktrees, clean stale review worktrees, old caches, old build outputs, and obsolete logs.",
  "Measure df -h and top du consumers before and after each cleanup pass; stop when the VPS is near 50% usage or remaining candidates are risky.",
  "Prefer moving review artifacts or exports to connected long-term storage when useful: OneDrive travis_Littleton@msn.com, Family Hub secondary storage, or the 5TB Google Drive.",
  "Keep laptop cleanup advisory-only unless Travis separately approves worker-node cleanup.",
  "Do not touch dirty worktrees, Tool & Tally report-builder data, records/config/state.db, secrets, current/rollback runtimes, gateway, dispatch, session send, Waha/social/payment/customer actions, workers/timers/daemons/cron, or laptop cleanup without separate approval.",
].join(" ");

const REAL_PROJECT_NAMES = [
  "Hermes / Mission Control",
  "Long-form Video",
  "Shorts Video",
  "Tool & Tally",
  "Waha Work",
] as const;

const CANONICAL_REAL_PROJECTS: ProjectRecord[] = [
  {
    current_goal: "Make Jenny OS native chat the primary workspace while Mission Control stays audit/recovery.",
    name: "Hermes / Mission Control",
    next_recommended_lane: "Continue the Jenny OS native chat recovery lane.",
    project_id: "project-hermes-mission-control",
    source_of_truth: "Mission Control recovery records",
    status: "Active recovery lane",
  },
  {
    current_goal: "Paused until Jenny/Mission Control is stable.",
    name: "Long-form Video",
    next_recommended_lane: "Resume with a read-only toolchain/proof plan after Jenny is stable.",
    project_id: "project-long-form-video",
    source_of_truth: "Mission Control project anchor",
    status: "Paused",
  },
  {
    current_goal: "Paused until Jenny/Mission Control is stable.",
    name: "Shorts Video",
    next_recommended_lane: "Resume with a read-only queue/status audit after Jenny is stable.",
    project_id: "project-shorts-video",
    source_of_truth: "Mission Control project anchor",
    status: "Paused",
  },
  {
    current_goal: "Paused until Jenny/Mission Control is stable.",
    name: "Tool & Tally",
    next_recommended_lane: "Resume with report-engine fixture recovery before checkout or outreach.",
    project_id: "project-tool-tally",
    source_of_truth: "Mission Control project anchor",
    status: "Paused",
  },
  {
    current_goal: "Paused until Jenny/Mission Control is stable.",
    name: "Waha Work",
    next_recommended_lane: "Resume only after isolated Waha approval gates are clear.",
    project_id: "project-waha-work",
    source_of_truth: "Mission Control project anchor",
    status: "Paused",
  },
];

const ACTIVE_OS_PROJECT_IDS = [HERMES_PROJECT_ID];

const PAUSED_PROJECT_IDS = [
  "project-shorts-video",
  "project-long-form-video",
  "project-tool-tally",
  "project-waha-work",
];

const PROJECT_LANE_GUIDANCE: Record<string, string> = {
  "project-hermes-mission-control":
    "Mission Control workspace validation or a narrow Desktop/dashboard PR. Keep manual-copy/display-only unless Travis approves execution.",
  "project-long-form-video":
    "Long-form video toolchain/status proof. Protect the adult animated/vector explainer lane and avoid avatar/static-card regressions.",
  "project-shorts-video":
    "Shorts video topic/research/review packet. No posting, paid rendering, or account changes without a separate gate.",
  "project-tool-tally":
    "Tool & Tally read-only launch/hardening packet. No payment, customer delivery, outreach, public intake, or deploy without approval.",
  "project-waha-work":
    "Waha owner-side inspection handoff. Keep Waha context isolated and mark numbers/findings review-only until Travis approves.",
};

interface WrappedRecord<T> {
  record?: T;
}

interface ProjectRecord {
  current_goal?: string;
  latest_report_summary?: string;
  latest_result?: string;
  mistakes_guards?: string;
  name: string;
  next_recommended_lane?: string;
  project_id: string;
  source_of_truth?: string;
  status?: string;
}

interface LaneRequestRecord {
  objective?: string;
  project_id?: string;
  status?: string;
  title?: string;
}

interface ProjectBriefRecord {
  approval_rules?: string[];
  constraints?: string[];
  outcome?: string;
  project_id?: string;
  status?: string;
  success_criteria?: string[];
}

interface ChallengeReviewRecord {
  blocking_verdicts?: string[];
  challenge_categories?: string[];
  concerns?: string[];
  decision_state?: string;
  project_id?: string;
  questions?: string[];
  recommended_path?: string;
  request_summary?: string;
  required_approvals?: string[];
  status?: string;
  suggested_lane_title?: string;
}

interface ReportRecord {
  blockers?: string[];
  changed_files?: string[];
  metadata?: { artifact_links?: string[]; [key: string]: unknown };
  project_id?: string;
  result?: string;
  risks?: string[];
  summary?: string;
  tests?: string[];
  next_recommended_lane?: string;
}

interface JennyBridgeRequestRecord {
  ack_key?: string;
  bridge_state?: string;
  created_at?: string;
  has_response?: boolean;
  message: string;
  metadata?: Record<string, unknown>;
  project_id?: string;
  request_id?: string;
  status?: string;
  target_agent?: string;
}

interface JennyBridgeResponseRecord {
  created_at?: string;
  message: string;
  project_id?: string;
  request_id?: string;
  responder?: string;
  response_id?: string;
  status?: string;
}

interface JennyReplyReviewRecord {
  created_at?: string;
  decision?: string;
  note?: string;
  project_id?: string;
  request_id?: string;
  response_id?: string;
  review_id?: string;
  reviewer?: string;
}

interface JennyBridgePollerStatus {
  dispatch_enabled?: boolean;
  execution_enabled?: boolean;
  last_error?: string;
  last_poll_at?: string;
  last_response_at?: string;
  last_response_request_id?: string;
  last_status?: string;
  manual_start_only?: boolean;
  pending_count?: number;
  session_send_enabled?: boolean;
  timer_enabled?: boolean;
  worker_enabled?: boolean;
}

interface GitHubBridgeStatus {
  daemon_enabled?: boolean;
  discord_automation_enabled?: boolean;
  dispatch_enabled?: boolean;
  execution_enabled?: boolean;
  last_error?: string;
  last_poll_at?: string;
  last_response_at?: string;
  last_response_request_id?: string;
  last_status?: string;
  manual_start_only?: boolean;
  mode?: string;
  foreground_watch_supported?: boolean;
  foreground_watch_running?: boolean;
  model_routing_enabled?: boolean;
  pending_count?: number;
  visible_pending_count?: number;
  background_pending_count?: number;
  pending_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  visible_pending_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  recent_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  response_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  send_to_jenny_enabled?: boolean;
  session_send_enabled?: boolean;
  status_records?: Array<WrappedRecord<GitHubBridgeMailboxStatusRecord> | GitHubBridgeMailboxStatusRecord>;
  timer_enabled?: boolean;
  worker_dispatch_enabled?: boolean;
  would_execute?: boolean;
  worker_enabled?: boolean;
}

interface CompactBridgeSafety {
  reasons: string[];
  safe: boolean;
}

interface GitHubBridgeMailboxStatusRecord {
  created_at?: string;
  handled_request_id?: string;
  last_error?: string;
  mode?: string;
  pending_count?: number;
  status?: string;
  status_id?: string;
}

interface GitHubBridgeMessageRecord {
  created_at?: string;
  from_agent?: string;
  github_comment_id?: string;
  message: string;
  metadata?: Record<string, unknown>;
  project_id?: string;
  request_id?: string;
  status?: string;
  to_agent?: string;
}

interface ProjectStateRecord {
  artifact_links?: string[];
  blockers?: string[];
  current_goal?: string;
  has_real_report?: boolean;
  latest_activity_at?: string;
  latest_activity_source?: string;
  latest_jenny_report?: ReportRecord;
  latest_lane_objective?: string;
  latest_lane_title?: string;
  latest_report_summary?: string;
  latest_result?: string;
  missing_state_fields?: string[];
  next_recommended_lane?: string;
  project_id?: string;
  report_contract?: {
    complete?: boolean;
    display_only?: boolean;
    missing_fields?: string[];
    required_fields?: string[];
    state?: string;
    trusted_for_execution?: boolean;
  };
  recent_sessions?: ProjectSessionRecord[];
  risks?: string[];
  risks_blockers?: string[];
  status?: string;
}

interface ProjectSessionRecord {
  cwd_snapshot?: string;
  linked_project_id?: string;
  profile?: string;
  session_id?: string;
  source?: string;
  title?: string;
}

interface WorkspaceStatus {
  accepted_baseline?: { head?: string; runtime_path?: string };
  approval_lifecycle?: CompactExecutionLockSource & {
    available_approval_ids?: string[];
    blocked?: boolean;
    blocked_reasons?: string[];
    consumed_approval_ids?: string[];
    duplicate_approval_ids?: string[];
    expired_approval_ids?: string[];
    pending_approval_ids?: string[];
    rejected_or_cancelled_approval_ids?: string[];
    runs_missing_approval_id?: string[];
    runs_with_missing_approval_record?: Record<string, string>;
    runs_with_unavailable_approval?: Record<string, string>;
  };
  child_agent_instruction_preview?: CompactExecutionLockSource & {
    agent_identity?: string;
    available?: boolean;
    blocked?: boolean;
    blocked_reasons?: string[];
    child_run_id?: string;
    manual_handoff_only?: boolean;
    manual_handoff_prompt?: string;
    objective?: string;
    ready_for_handoff?: boolean;
    report_id?: string;
    report_link_status?: string;
    report_review_status?: string;
  };
  child_agent_orchestration?: CompactExecutionLockSource & {
    active_count?: number;
    active_runs?: Array<Record<string, unknown>>;
    blocked_reasons?: string[];
    latest_by_id?: Record<string, Record<string, unknown>>;
  };
  deployment_gap?: { accepted_live_head?: string; dashboard_deploy_needed?: boolean; deployed_head?: string; latest_merged_pr?: string; state?: string };
  execution_mode_classification?: CompactExecutionLockSource & {
    blocked?: boolean;
    blocked_reasons?: string[];
    mode_family?: string;
    preview_ready?: boolean;
    warnings?: string[];
  };
  execution_packet_preview?: CompactExecutionLockSource & {
    blocked_reasons?: string[];
    eligible?: boolean;
    packet?: CompactExecutionLockSource & {
      mode?: string;
      worker_node_contract?: CompactExecutionLockSource & {
        codex_safety_hardness_required?: boolean;
        manual_handoff_only?: boolean;
        worker_host_label?: string;
        worker_identity?: string;
      };
    };
    warnings?: string[];
  };
  hard_boundary_contract?: CompactExecutionLockSource & {
    blocked?: boolean;
    blocked_reasons?: string[];
    execution_ready?: boolean;
    forbidden_action_count?: number;
    forbidden_actions?: string[];
    live_flag_violation_count?: number;
    live_flag_violations?: string[];
    live_operations_enabled?: boolean;
    live_operations_goal?: boolean;
    plain_language_summary?: string;
    separate_approval_action_count?: number;
    separate_approval_actions?: string[];
    separate_approval_required?: boolean;
    state?: string;
  };
  lane?: { active_lane_count?: number };
  next_safe_actions?: {
    action_count?: number;
    blocked?: boolean;
    blocked_reasons?: string[];
    dispatch_enabled?: boolean;
    display_only?: boolean;
    execution_enabled?: boolean;
    primary_action_label?: string;
    session_send_enabled?: boolean;
    would_execute?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
  };
  operator_decision_packet?: {
    blocked?: boolean;
    blocked_reasons?: string[];
    dispatch_enabled?: boolean;
    display_only?: boolean;
    execution_lock_blocked_reasons?: string[];
    execution_enabled?: boolean;
    jenny_review_required?: boolean;
    next_safe_action_label?: string;
    plain_language_summary?: string;
    recommended_operator_instruction?: string;
    session_send_enabled?: boolean;
    state?: string;
    would_dispatch?: boolean;
    would_execute?: boolean;
    would_session_send?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
  };
  orchestration_readiness?: {
    blocked_reasons?: string[];
    dispatch_enabled?: boolean;
    execution_enabled?: boolean;
    execution_ready?: boolean;
    session_send_enabled?: boolean;
    states?: {
      laptop_codex_worker_node?: string;
      scoped_pr_creation?: string;
      supervised_read_only_autonomy?: string;
    };
    would_execute?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
  };
  orchestration_run_graph?: CompactExecutionLockSource & {
    blocked?: boolean;
    blocked_reasons?: string[];
    child_run_node_count?: number;
    edge_count?: number;
    node_count?: number;
    report_node_count?: number;
    run_node_count?: number;
    worker_node_run_count?: number;
  };
  report_completion_path?: {
    blocked?: boolean;
    blocked_completion_count?: number;
    blocked_reasons?: string[];
    completion_ready_count?: number;
    dispatch_enabled?: boolean;
    execution_enabled?: boolean;
    session_send_enabled?: boolean;
    terminal_item_count?: number;
    would_execute?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
  };
  report_lifecycle?: CompactExecutionLockSource & {
    blocked?: boolean;
    blocked_reasons?: string[];
    duplicate_report_ids?: string[];
    open_report_ids?: string[];
    report_overwrite_conflict_count?: number;
    report_overwrite_conflict_ids?: string[];
    report_overwrite_conflicts?: Record<string, string[]>;
    reviewed_report_ids?: string[];
    runs_missing_report?: string[];
    runs_with_missing_linked_report_ids?: Record<string, string[]>;
    terminal_report_ids?: string[];
  };
  result_ingestion_contract?: {
    blocked?: boolean;
    blocked_reasons?: string[];
    blocked_report_count?: number;
    dispatch_enabled?: boolean;
    execution_enabled?: boolean;
    ingestion_ready_count?: number;
    report_count?: number;
    session_send_enabled?: boolean;
    would_execute?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
  };
  run_lifecycle?: CompactExecutionLockSource & {
    active_mutation_lane_count?: number;
    active_mutation_run_ids?: string[];
    active_run_ids?: string[];
    blocked?: boolean;
    blocked_reasons?: string[];
    duplicate_run_ids?: string[];
    one_active_mutation_lane_rule_passed?: boolean;
    stop_cancel_run_ids?: string[];
    terminal_run_ids?: string[];
    terminal_runs_missing_report?: string[];
    terminal_runs_with_missing_linked_report_ids?: Record<string, string[]>;
  };
  runtime_worktree_guard?: { decision_state?: string };
  safety?: { dispatch_in_gateway?: boolean; model_routing_enabled?: boolean };
  stale_context?: { warnings?: string[] };
  worker_node_presence?: {
    blocked?: boolean;
    blocked_reasons?: string[];
    dispatch_enabled?: boolean;
    execution_enabled?: boolean;
    online?: boolean;
    presence_state?: string;
    session_send_enabled?: boolean;
    would_execute?: boolean;
    worker_dispatch_enabled?: boolean;
    worker_enabled?: boolean;
    worker_host_label?: string;
    worker_run_id?: string;
  };
  worker_node_instruction_preview?: CompactExecutionLockSource & {
    available?: boolean;
    blocked_reasons?: string[];
    manual_handoff_only?: boolean;
    manual_handoff_prompt?: string;
    ready_for_handoff?: boolean;
    worker_host_label?: string;
  };
}

interface MemoryFileLevel {
  bytes?: number;
  chars?: number;
  error?: string;
  exists?: boolean;
  limit_chars?: number;
  lines?: number;
  path?: string;
  percent_used?: number;
}

interface ProfileMountUsage {
  error?: string;
  free_bytes?: number;
  path?: string;
  percent_used?: number;
  total_bytes?: number;
  used_bytes?: number;
}

interface ProfileStorageLevel {
  bytes?: number;
  components?: Record<string, ProfileStorageLevel>;
  error?: string;
  exists?: boolean;
  path?: string;
  scope?: string;
}

interface ProfileMemoryStorageRecord {
  data?: ProfileStorageLevel;
  home?: string;
  memory?: MemoryFileLevel;
  mount?: ProfileMountUsage;
  profile?: string;
  recall_file_bytes?: number;
  total_bytes?: number;
  user?: MemoryFileLevel;
}

interface ProfileMemoryStorage {
  errors?: Array<{ profile?: string; error?: string }>;
  profile_count?: number;
  profiles?: ProfileMemoryStorageRecord[];
  stored?: boolean;
  total_bytes?: number;
  total_memory_bytes?: number;
  total_profile_data_bytes?: number;
  total_recall_file_bytes?: number;
  total_user_bytes?: number;
}

interface CompactModelInfo {
  model?: string;
  provider?: string;
}

interface CompactModelOptionProvider {
  models?: string[];
  name?: string;
  slug: string;
}

interface CompactModelOptions {
  model?: string;
  provider?: string;
  providers?: CompactModelOptionProvider[];
}

interface CompactRunSettings {
  effort: string;
  model: string;
  provider: string;
}

interface CompactSnapshot {
  challengeReviews: ChallengeReviewRecord[];
  jennyBridgeRequests: JennyBridgeRequestRecord[];
  jennyBridgeResponses: JennyBridgeResponseRecord[];
  jennyReplyReviews: JennyReplyReviewRecord[];
  jennyBridgePollerStatus: JennyBridgePollerStatus;
  githubBridgeStatus: GitHubBridgeStatus;
  laneRequests: LaneRequestRecord[];
  memoryStorage: ProfileMemoryStorage;
  projectBriefs: ProjectBriefRecord[];
  projectStates: ProjectStateRecord[];
  projects: ProjectRecord[];
  reports: ReportRecord[];
  workspaceStatus: WorkspaceStatus;
}

interface ProjectViewModel {
  artifactLinks: string;
  blockers: string;
  currentGoal: string;
  freshness: string;
  latestActivity: string;
  latestLane: string;
  latestLaneRequest?: LaneRequestRecord;
  latestReport: string;
  latestResult: string;
  missingFields: string;
  nextLane: string;
  projectBrief?: ProjectBriefRecord;
  projectState?: ProjectStateRecord;
  project: ProjectRecord;
  reportContract: string;
  report?: ReportRecord;
  readinessDetail: string;
  readinessLabel: string;
  challengeReview?: ChallengeReviewRecord;
  risks: string;
  status: string;
}

type ProjectKanbanColumnId =
  | "intake"
  | "needs-clarification"
  | "challenge-review"
  | "lane-draft"
  | "awaiting-approval"
  | "active"
  | "evidence-review"
  | "accepted"
  | "blocked-rollback";

interface ProjectKanbanColumn {
  description: string;
  id: ProjectKanbanColumnId;
  title: string;
}

const PROJECT_KANBAN_COLUMNS: ProjectKanbanColumn[] = [
  { id: "intake", title: "Intake", description: "Needs a project brief or source-of-truth anchor." },
  { id: "needs-clarification", title: "Needs Clarification", description: "Jenny should question the request or approach." },
  { id: "challenge-review", title: "Challenge Review", description: "Waiting for Jenny's challenge gate." },
  { id: "lane-draft", title: "Lane Draft", description: "Clear challenge exists; draft the bounded lane." },
  { id: "awaiting-approval", title: "Awaiting Approval", description: "Drafted or approval-needed work waits on Travis." },
  { id: "active", title: "Active", description: "Approved work in progress; watch stop conditions." },
  { id: "evidence-review", title: "Evidence Review", description: "Review report, files, checks, and risks." },
  { id: "accepted", title: "Accepted", description: "Accepted result or completed lane." },
  { id: "blocked-rollback", title: "Blocked / Rollback", description: "Unsafe, blocked, or rollback-aware work." },
];

interface ReportFormState {
  artifactLinks: string;
  changedFiles: string;
  nextRecommendedLane: string;
  projectId: string;
  result: string;
  risks: string;
  summary: string;
}

const EMPTY_REPORT_FORM: ReportFormState = {
  artifactLinks: "",
  changedFiles: "",
  nextRecommendedLane: "",
  projectId: "",
  result: "",
  risks: "",
  summary: "",
};

function unwrapRecords<T>(items: Array<WrappedRecord<T> | T> | undefined): T[] {
  if (!Array.isArray(items)) return [];
  return items.map(item => ("record" in Object(item) ? (item as WrappedRecord<T>).record : item)).filter(Boolean) as T[];
}

function text(value: string | undefined, fallback: string): string {
  return value && value.trim() ? value.trim() : fallback;
}

function listText(values: string[] | undefined, fallback: string): string {
  return Array.isArray(values) && values.length ? values.filter(Boolean).join("; ") : fallback;
}

function compactText(value: string | string[] | undefined, maxChars: number): string {
  const raw = Array.isArray(value) ? value.filter(Boolean).join("; ") : value ?? "";
  const normalized = raw.replace(/\s+/g, " ").trim();
  return normalized.length > maxChars ? `${normalized.slice(0, Math.max(0, maxChars - 3)).trim()}...` : normalized;
}

function stripHiddenJennyOsContext(value: string): string {
  if (!/^Hidden Jenny OS project context:/i.test(value.trimStart())) {
    return value;
  }

  const rest = value.trimStart().replace(/^Hidden Jenny OS project context:[ \t]*\r?\n/i, "");
  const blankSeparator = rest.match(/\r?\n[ \t]*\r?\n/);

  if (blankSeparator?.index !== undefined) {
    return rest.slice(blankSeparator.index + blankSeparator[0].length).trimStart();
  }

  const lines = rest.split(/\r?\n/);
  const visibleRuleIndex = lines.findIndex(line => /^Visible chat rule:/i.test(line.trim()));

  if (visibleRuleIndex >= 0) {
    return lines.slice(visibleRuleIndex + 1).join("\n").trimStart();
  }

  return "";
}

function projectRequestPreview(value: string, maxChars: number): string {
  const visibleValue = stripHiddenJennyOsContext(value);
  const normalized = visibleValue.replace(/\s+/g, " ").trim();

  if (!normalized && /^Hidden Jenny OS project context:/i.test(value.trimStart())) {
    return "Project message";
  }

  const specFirstRequestMatch = normalized.match(
    /^Spec-first request for Jenny:\s*Project:\s*.+?\s+Request Travis is considering:\s*([\s\S]*?)(?=\s+Current intake:|$)/i,
  );
  const projectRoomRequestMatch = normalized.match(
    /^Project room request:\s*(?:.+?\s+)?Request:\s*([\s\S]*?)(?=\s+(?:Request intake:|Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i,
  );
  const requestMatch = normalized.match(
    /(?:^|[\s/])Request:\s*([\s\S]*?)(?=\s+(?:Request intake:|Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i,
  );
  const inlineRequestMatch = normalized.match(
    /^[\w &/-]+ Request:\s*([\s\S]*?)(?=\s+(?:Current brief:|Request intake:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i,
  );
  const fallbackMatch = normalized.match(
    /^(.+?)\s+(?=Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)/i,
  );
  const candidate = specFirstRequestMatch?.[1] ?? projectRoomRequestMatch?.[1] ?? requestMatch?.[1] ?? inlineRequestMatch?.[1] ?? fallbackMatch?.[1] ?? visibleValue;
  return compactText(candidate, maxChars);
}

function ownerVisibleJennyReply(value: string): string {
  const normalized = value.replace(/\r\n/g, "\n").trim();
  const lower = normalized.toLowerCase();
  const technicalJennyReply = [
    "session_id:",
    "preflight",
    "safety confirmation",
    "no live github/ci/runtime check",
    "stale-runtime confusion",
    "i treated this as a read-only",
    "i did not deploy",
    "do not deploy",
    "do not resume tool",
  ].some(marker => lower.includes(marker));

  if (!technicalJennyReply) {
    return value;
  }

  const recommendationMatch = normalized.match(
    /(?:^|\n)\s*recommendation\s*\n([\s\S]*?)(?=\n\s*(?:risks?|safety confirmation|validation|evidence|blockers?|approval|$))/i,
  );
  const candidate = recommendationMatch?.[1] ?? "";
  const cleanedRecommendation = compactText(candidate.replace(/^\s*[-*]\s*/gm, "").replace(/\n+/g, " "), 220);

  if (cleanedRecommendation) {
    return `Jenny replied with a guarded status update. Recommendation: ${cleanedRecommendation}`;
  }

  return "Jenny replied with a guarded status update. Open Review reply for evidence, risks, and safety details.";
}

function chatRequestText(value: string): string {
  return projectRequestPreview(value, 1200);
}

function cleanChatDisplayMessage(metadata: Record<string, unknown> | undefined, fallback: string, maxChars: number): string {
  const userMessage = typeof metadata?.user_message === "string" ? metadata.user_message.trim() : "";
  return compactText(userMessage || projectRequestPreview(fallback, maxChars), maxChars);
}

function chatStatusLabel(value: string | undefined): string {
  switch (value) {
    case "queued":
      return "sent";
    case "replied":
      return "replied";
    case "retry_requested":
      return "retry requested";
    case "response_appended":
      return "reply received";
    default:
      return value || "sent";
  }
}

interface JennyReplyContract {
  label: string;
  tone: "complete" | "missing";
}

function jennyReplyContract(value: string): JennyReplyContract {
  const lower = value.toLowerCase();
  const checks = [
    { label: "recommendation", present: /\b(recommend|recommendation|next safe lane|next lane|next step)\b/.test(lower) },
    { label: "evidence", present: /\b(evidence|validation|validated|test|tests|checked|verified|pass|ci)\b/.test(lower) },
    { label: "risks", present: /\b(risk|risks|blocker|blockers|remaining risk)\b/.test(lower) },
    { label: "approval/rollback", present: /\b(approval|approved|rollback|required approval|approval needed|roll back)\b/.test(lower) },
    { label: "safety", present: /\b(safety|forbidden|no deploy|no dispatch|guard|gated)\b/.test(lower) },
  ];
  const missing = checks.filter(check => !check.present).map(check => check.label);
  const matched = checks.length - missing.length;

  if (!missing.length) {
    return { label: `Reply quality ${matched}/${checks.length}: complete`, tone: "complete" };
  }

  return {
    label: `Reply quality ${matched}/${checks.length}: missing ${missing.join(", ")}`,
    tone: "missing",
  };
}

function buildJennyReplyReviewPrompt(action: "accept" | "evidence" | "safer-plan", projectName: string, reply: string): string {
  const replyPreview = compactText(reply, 500);

  if (action === "accept") {
    return [
      `Review this Jenny reply for ${projectName}.`,
      "If it is complete, convert it into a concise accepted-result summary with evidence, risks/blockers, tests/checks, and the next safe lane.",
      "If it is not complete, say exactly what is missing before Travis relies on it.",
      "",
      `Jenny reply: ${replyPreview}`,
    ].join("\n");
  }

  if (action === "evidence") {
    return [
      `The last Jenny reply for ${projectName} needs stronger evidence.`,
      "Reply with the exact files, commands, checks, PR/CI status, runtime status, and remaining risks that prove or disprove the recommendation.",
      "Do not take action. Report evidence only.",
      "",
      `Jenny reply: ${replyPreview}`,
    ].join("\n");
  }

  return [
    `Challenge the last Jenny reply for ${projectName} like a senior engineer.`,
    "Identify unsafe assumptions, missing approvals, wrong approach risk, rollback concerns, and the smallest safer next lane.",
    "Do not implement or trigger live actions.",
    "",
    `Jenny reply: ${replyPreview}`,
  ].join("\n");
}

type JennyReplyReviewDecision = "accepted" | "needs_evidence" | "needs_safer_plan";

interface ProjectChatMessage {
  body: string;
  displayBody?: string;
  id: string;
  meta: string;
  speaker: "Jenny" | "You";
  time?: string;
}

function jennyReplyReviewDecisionLabel(decision: string | undefined): string {
  switch (decision) {
    case "accepted":
      return "Reviewed: accepted";
    case "needs_evidence":
      return "Reviewed: needs evidence";
    case "needs_safer_plan":
      return "Reviewed: needs safer plan";
    default:
      return "Not reviewed yet";
  }
}

function latestReplyReviewByResponseId(reviews: JennyReplyReviewRecord[]): Map<string, JennyReplyReviewRecord> {
  const map = new Map<string, JennyReplyReviewRecord>();
  for (const review of reviews) {
    if (review.response_id) {
      map.set(review.response_id, review);
    }
  }
  return map;
}

function latestReviewedJennyReply(
  chatMessages: ProjectChatMessage[],
  reviewsByResponseId: Map<string, JennyReplyReviewRecord>,
): JennyReplyReviewRecord | null {
  for (const chat of [...chatMessages].reverse()) {
    if (chat.speaker !== "Jenny") {
      continue;
    }
    const review = reviewsByResponseId.get(chat.id);
    if (review) {
      return review;
    }
  }
  return null;
}

function latestJennyReply(chatMessages: ProjectChatMessage[]): ProjectChatMessage | null {
  for (const chat of [...chatMessages].reverse()) {
    if (chat.speaker === "Jenny") {
      return chat;
    }
  }
  return null;
}

function jennyReplyReviewStatus(review: JennyReplyReviewRecord | null): { detail: string; label: string; nextStep: string | null; tone: "accepted" | "blocked" | "none" | "warn" } {
  if (!review) {
    return {
      detail: "No Jenny reply has been accepted or challenged yet.",
      label: "Reply not reviewed",
      nextStep: null,
      tone: "none",
    };
  }

  if (review.decision === "accepted") {
    return {
      detail: "Travis accepted the latest reviewed Jenny reply. Continue with the next bounded lane.",
      label: "Reply accepted",
      nextStep: null,
      tone: "accepted",
    };
  }

  if (review.decision === "needs_evidence") {
    return {
      detail: "Travis marked the latest reviewed Jenny reply as needing stronger evidence.",
      label: "Needs evidence",
      nextStep: "Ask Jenny for exact files, commands, checks, CI/runtime status, and remaining risks before relying on that reply.",
      tone: "warn",
    };
  }

  if (review.decision === "needs_safer_plan") {
    return {
      detail: "Travis marked the latest reviewed Jenny reply as needing a safer plan.",
      label: "Needs safer plan",
      nextStep: "Challenge Jenny for unsafe assumptions, missing approvals, rollback concerns, and the smallest safer next lane.",
      tone: "blocked",
    };
  }

  return {
    detail: "The latest reply review decision is unknown. Treat the reply as not accepted.",
    label: "Review unclear",
    nextStep: "Ask Jenny to restate the evidence, risks, and next safe lane before proceeding.",
    tone: "warn",
  };
}

function latestJennyOutcomeStatus(
  latestReply: ProjectChatMessage | null,
  review: JennyReplyReviewRecord | null,
): { detail: string; label: string; nextStep: string; reviewLabel: string; tone: "accepted" | "blocked" | "none" | "warn" } {
  if (!latestReply) {
    return {
      detail: "No Jenny reply is available for this project yet.",
      label: "Waiting for Jenny",
      nextStep: "Send one bounded project message, then get one Jenny reply.",
      reviewLabel: "No reply yet",
      tone: "none",
    };
  }

  const contract = jennyReplyContract(latestReply.body);
  const reviewStatus = jennyReplyReviewStatus(review);

  if (!review) {
    return {
      detail: "Jenny replied, but this latest reply has not been accepted or challenged yet.",
      label: "Review before relying",
      nextStep: "Use the reply review buttons: accept only if evidence is clear, otherwise ask for evidence or challenge the plan.",
      reviewLabel: contract.label,
      tone: contract.tone === "complete" ? "warn" : "blocked",
    };
  }

  if (review.decision === "accepted") {
    return {
      detail: "The latest Jenny reply was accepted and can be used as context for the next bounded lane.",
      label: "Usable as context",
      nextStep: "Continue with one bounded follow-up request.",
      reviewLabel: reviewStatus.label,
      tone: "accepted",
    };
  }

  return {
    detail: reviewStatus.detail,
    label: reviewStatus.tone === "blocked" ? "Do not proceed" : "Do not rely yet",
    nextStep: reviewStatus.nextStep ?? "Ask Jenny to restate evidence, risks, and the next safe lane.",
    reviewLabel: reviewStatus.label,
    tone: reviewStatus.tone,
  };
}

function jennyReplyReviewStatusClass(tone: "accepted" | "blocked" | "none" | "warn"): string {
  switch (tone) {
    case "accepted":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
    case "blocked":
      return "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300";
    case "warn":
      return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
    default:
      return "border-[#f3ebda]/10 bg-[#15101a]/60 text-[#a59783]";
  }
}

interface JennyRunProgress {
  detail: string;
  phase: "complete" | "error" | "queued" | "starting" | "waiting";
}

type JennyWorkSessionStepState = "active" | "blocked" | "done" | "idle";

interface JennyWorkSessionStep {
  detail: string;
  label: string;
  state: JennyWorkSessionStepState;
}

interface JennyLiveStatusItem {
  label: string;
  value: string;
}

function jennyRunProgressCopy(progress: JennyRunProgress | null, elapsedSeconds: number): { detail: string; label: string } {
  if (!progress) {
    return {
      detail: "Jenny is standing by.",
      label: "Standing by",
    };
  }

  if (progress.phase === "queued") {
    return {
      detail: progress.detail || "Sent. Waiting for Jenny to start.",
      label: "Sent",
    };
  }
  if (progress.phase === "complete") {
    return {
      detail: progress.detail || "Jenny replied.",
      label: "Jenny replied",
    };
  }
  if (progress.phase === "error") {
    return {
      detail: progress.detail || "Jenny hit a guarded error. No hidden action was treated as successful.",
      label: "Needs attention",
    };
  }

  return {
    detail: `${progress.detail || "Jenny is working on one guarded reply."} Elapsed ${elapsedSeconds}s.`,
    label: progress.phase === "starting" ? "Starting Jenny" : "Jenny is working",
  };
}

function jennyLiveStatusItems({
  elapsedSeconds,
  latestUserMessage,
  pendingCount,
  progress,
  responseCount,
  statusLabel,
}: {
  elapsedSeconds: number;
  latestUserMessage: string;
  pendingCount: number;
  progress: JennyRunProgress | null;
  responseCount: number;
  statusLabel: string;
}): JennyLiveStatusItem[] {
  const phase = progress?.phase
    ? progress.phase.replaceAll("_", " ")
    : pendingCount
      ? "waiting"
      : responseCount
        ? "replied"
        : "ready";

  return [
    { label: "Current phase", value: statusLabel || phase },
    { label: "Last sent", value: latestUserMessage || "No message sent yet" },
    { label: "Reply state", value: pendingCount ? `${pendingCount} waiting` : responseCount ? `${responseCount} received` : "No reply yet" },
    { label: "Elapsed", value: isJennyRunActive(progress) ? `${elapsedSeconds}s` : "not running" },
  ];
}

function isJennyRunActive(progress: JennyRunProgress | null): boolean {
  return progress?.phase === "starting" || progress?.phase === "waiting";
}

function recordBackedJennyRunProgress(
  statusRecords: GitHubBridgeMailboxStatusRecord[],
  bridgeMessages: GitHubBridgeMessageRecord[],
  projectId: string,
): JennyRunProgress | null {
  const projectRequestIds = new Set(
    bridgeMessages
      .filter(message => message.project_id === projectId)
      .map(message => message.request_id)
      .filter(Boolean),
  );

  for (const record of [...statusRecords].reverse()) {
    if (record.handled_request_id && projectRequestIds.size && !projectRequestIds.has(record.handled_request_id)) {
      continue;
    }
    switch (record.status) {
      case "hermes_answer_started":
        return {
          detail: "Jenny is working on the latest project message. This status is restored from the bridge audit trail.",
          phase: "waiting",
        };
      case "hermes_answer_completed":
      case "response_appended":
        return {
          detail: "Jenny replied to the latest project message. Review the response before relying on it.",
          phase: "complete",
        };
      case "hermes_answer_error":
        return {
          detail: record.last_error || "Jenny hit a guarded error. No hidden action was treated as successful.",
          phase: "error",
        };
      case "message_posted":
        return {
          detail: "Sent. Waiting for Jenny to start.",
          phase: "queued",
        };
      default:
        break;
    }
  }

  return null;
}

function jennyWorkSessionSteps({
  hasError,
  hasRunnablePendingMessage,
  pendingCount,
  progress,
  replyReviewTone,
  responseCount,
}: {
  hasError: boolean;
  hasRunnablePendingMessage: boolean;
  pendingCount: number;
  progress: JennyRunProgress | null;
  replyReviewTone: "accepted" | "blocked" | "none" | "warn";
  responseCount: number;
}): JennyWorkSessionStep[] {
  const activeRun = isJennyRunActive(progress);
  const hasReply = responseCount > 0 || progress?.phase === "complete" || replyReviewTone !== "none";
  const queued = pendingCount > 0 || hasRunnablePendingMessage || Boolean(progress);

  return [
    {
      detail: queued ? "Message is in Jenny mailbox." : "Write and send one bounded message.",
      label: "Queued",
      state: hasError ? "blocked" : queued && !activeRun && !hasReply ? "active" : queued || hasReply ? "done" : "idle",
    },
    {
      detail: activeRun ? "One guarded reply is running." : hasReply ? "Jenny run finished." : "Send a message to start one guarded reply.",
      label: "Jenny working",
      state: hasError ? "blocked" : activeRun ? "active" : hasReply ? "done" : "idle",
    },
    {
      detail: hasReply ? "Latest reply is available." : "No reply yet.",
      label: "Reply received",
      state: hasError ? "blocked" : hasReply ? "done" : "idle",
    },
    {
      detail: replyReviewTone === "accepted"
        ? "Reply accepted; send the next bounded message."
        : replyReviewTone === "blocked" || replyReviewTone === "warn"
          ? "Review asks Jenny for stronger evidence or a safer plan."
          : hasReply
            ? "Review the reply before relying on it."
            : "Waiting for a reply to review.",
      label: "Review next",
      state: replyReviewTone === "accepted"
        ? "done"
        : replyReviewTone === "blocked" || replyReviewTone === "warn"
          ? "blocked"
          : hasReply
            ? "active"
            : "idle",
    },
  ];
}

function jennyActivityLabel(status: string | undefined): string {
  switch (status) {
    case "hermes_answer_started":
      return "Jenny is thinking";
    case "hermes_answer_completed":
      return "Jenny replied";
    case "hermes_answer_error":
      return "Jenny hit an error";
    case "hermes_answer_noop":
      return "No pending message";
    case "poll_completed":
    case "watch_poll_completed":
      return "Mailbox checked";
    case "poll_error":
    case "watch_poll_error":
      return "Mailbox check failed";
    default:
      return status?.replaceAll("_", " ") || "Idle";
  }
}

function jennyActivityDetail(record: GitHubBridgeMailboxStatusRecord): string {
  if (record.last_error) {
    if (isNoPendingBridgeError(record.last_error)) {
      return "No message is waiting for Jenny.";
    }
    return record.last_error;
  }
  if (record.handled_request_id) {
    return `request ${record.handled_request_id}`;
  }
  if (typeof record.pending_count === "number") {
    return `${record.pending_count} pending`;
  }
  return record.mode || "manual bridge";
}

function jennyActivityItems(status: GitHubBridgeStatus): GitHubBridgeMailboxStatusRecord[] {
  return unwrapRecords(status.status_records).slice(-4).reverse();
}

function pendingJennyMessageCount(requests: JennyBridgeRequestRecord[], responses: JennyBridgeResponseRecord[]): number {
  const repliedRequestIds = new Set(responses.map(response => response.request_id).filter(Boolean));
  return requests.filter(request => {
    const state = request.bridge_state ?? request.status ?? "queued";
    return state !== "replied" && !(request.request_id && repliedRequestIds.has(request.request_id));
  }).length;
}

function latestPendingGitHubBridgeMessage(messages: GitHubBridgeMessageRecord[]): GitHubBridgeMessageRecord | null {
  const repliedRequestIds = new Set(
    messages
      .filter(message => message.from_agent === "jenny")
      .map(message => message.request_id)
      .filter(Boolean),
  );
  const pending = messages.filter(message =>
    message.to_agent === "jenny" &&
    ["queued", "retry_requested"].includes(message.status ?? "") &&
    !repliedRequestIds.has(message.request_id),
  );
  return pending.length ? pending[pending.length - 1] : null;
}

function uniqueGitHubBridgeMessages(messages: GitHubBridgeMessageRecord[]): GitHubBridgeMessageRecord[] {
  const seen = new Set<string>();
  return messages.filter(message => {
    const key = [
      message.request_id ?? "",
      message.from_agent ?? "",
      message.to_agent ?? "",
      message.status ?? "",
      message.github_comment_id ?? "",
      message.created_at ?? "",
    ].join(":");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function timestampValue(value?: string): number {
  const time = Date.parse(value ?? "");
  return Number.isFinite(time) ? time : 0;
}

function latestJennyReplyTimestamp(
  responses: JennyBridgeResponseRecord[],
  githubMessages: GitHubBridgeMessageRecord[],
): number {
  const responseTimes = responses.map(response => timestampValue(response.created_at));
  const githubReplyTimes = githubMessages
    .filter(message => message.from_agent === "jenny")
    .map(message => timestampValue(message.created_at));

  return Math.max(0, ...responseTimes, ...githubReplyTimes);
}

function isCurrentAfterReply(createdAt: string | undefined, latestReplyAt: number): boolean {
  if (!latestReplyAt) {
    return true;
  }

  const created = timestampValue(createdAt);
  return !created || created > latestReplyAt;
}

function isDiagnosticChatMessage(message?: string): boolean {
  const text = (message ?? "").toLowerCase();
  return [
    "codex app-server startup failed",
    "desktop phone bridge",
    "error guard",
    "failure guarded",
    "local error",
    "mission control two process",
    "reply with one sentence",
    "success smoke reached",
    "bridge works",
    "smoke",
  ].some(marker => text.includes(marker));
}

function isOperatorBridgeMessage(message: GitHubBridgeMessageRecord): boolean {
  const fromAgent = message.from_agent?.toLowerCase() ?? "";
  const requestId = message.request_id?.toLowerCase() ?? "";
  const text = message.message?.toLowerCase() ?? "";
  return fromAgent === "codex" ||
    requestId.startsWith("codex-") ||
    text.includes("bounded dashboard-only deploy check") ||
    text.includes("review pr #");
}

function visibleCurrentGitHubBridgeMessagesForProject(
  messages: GitHubBridgeMessageRecord[],
  projectId: string,
): GitHubBridgeMessageRecord[] {
  const visibleMessages = uniqueGitHubBridgeMessages(messages)
    .filter(message => message.project_id === projectId)
    .filter(message => !isDiagnosticChatMessage(message.message) && !isOperatorBridgeMessage(message));
  const latestReplyAt = latestJennyReplyTimestamp([], visibleMessages);
  return visibleMessages.filter(message => isCurrentAfterReply(message.created_at, latestReplyAt));
}

function latestVisiblePendingGitHubBridgeMessageForProject(
  messages: GitHubBridgeMessageRecord[],
  projectId: string,
): GitHubBridgeMessageRecord | null {
  return latestPendingGitHubBridgeMessage(visibleCurrentGitHubBridgeMessagesForProject(messages, projectId));
}

function latestGitHubBridgeReplyForRequest(
  status: GitHubBridgeStatus | undefined,
  requestId: string | undefined,
): GitHubBridgeMessageRecord | null {
  if (!requestId) {
    return null;
  }

  const replies = uniqueGitHubBridgeMessages([
    ...unwrapRecords(status?.response_messages),
    ...unwrapRecords(status?.recent_messages),
  ]).filter(message => message.request_id === requestId && message.from_agent === "jenny");

  return replies.length ? replies[replies.length - 1] : null;
}

function bridgeRequestId(): string {
  const fallback = Math.random().toString(16).slice(2, 14);
  return `mission-control-chat-${globalThis.crypto?.randomUUID?.() ?? fallback}`;
}

function isNoPendingBridgeError(value: unknown): boolean {
  const text = String(value ?? "").toLowerCase();
  return text.includes("no matching pending") || text.includes("no pending message") || text.includes("no pending request");
}

function hasGitHubBridgeSignal(status: GitHubBridgeStatus): boolean {
  return Boolean(
    status.last_error ||
    status.last_status ||
    status.last_poll_at ||
    status.last_response_at ||
    status.last_response_request_id ||
    status.mode ||
    status.foreground_watch_supported !== undefined ||
    status.foreground_watch_running !== undefined ||
    status.pending_count !== undefined ||
    status.visible_pending_count !== undefined ||
    unwrapRecords(status.pending_messages).length ||
    unwrapRecords(status.visible_pending_messages).length ||
    unwrapRecords(status.recent_messages).length ||
    unwrapRecords(status.response_messages).length ||
    unwrapRecords(status.status_records).length,
  );
}

function normalizedBridgeError(bridgeStatus: JennyBridgePollerStatus, githubBridgeStatus: GitHubBridgeStatus): string {
  const githubError = String(githubBridgeStatus.last_error || "");
  if (githubError && !isNoPendingBridgeError(githubError)) {
    return githubError;
  }
  const legacyError = String(bridgeStatus.last_error || "");
  if (!legacyError || isNoPendingBridgeError(legacyError)) {
    return "";
  }
  return hasGitHubBridgeSignal(githubBridgeStatus) ? "" : legacyError;
}

function compactGitHubBridgeSafety(status: GitHubBridgeStatus | undefined, workspaceStatus?: WorkspaceStatus): CompactBridgeSafety {
  const reasons: string[] = [];
  if (!status) {
    reasons.push("GitHub bridge status not loaded");
  } else {
    if (status.manual_start_only !== true) reasons.push("manual_start_only is not confirmed");
    const liveFlags: Array<[keyof GitHubBridgeStatus, string]> = [
      ["dispatch_enabled", "dispatch_enabled must remain false"],
      ["execution_enabled", "execution_enabled must remain false"],
      ["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"],
      ["session_send_enabled", "session_send_enabled must remain false"],
      ["worker_dispatch_enabled", "worker_dispatch_enabled must remain false"],
      ["would_execute", "would_execute must remain false"],
      ["worker_enabled", "worker_enabled must remain false"],
      ["timer_enabled", "timer_enabled must remain false"],
      ["daemon_enabled", "daemon_enabled must remain false"],
      ["discord_automation_enabled", "discord_automation_enabled must remain false"],
      ["model_routing_enabled", "model_routing_enabled must remain false"],
    ];
    for (const [flag, reason] of liveFlags) {
      if (compactLiveFlagEnabled(status[flag])) reasons.push(reason);
    }
  }
  const hardBoundary = workspaceStatus?.hard_boundary_contract;
  if (!hardBoundary) {
    reasons.push("hard_boundary_contract is not loaded");
  } else {
    if (hardBoundary.blocked === true) {
      reasons.push(hardBoundary.blocked_reasons?.[0] ?? "hard_boundary_contract is blocked");
    }
    for (const reason of hardBoundary.live_flag_violations ?? []) {
      reasons.push(reason);
    }
    const hardBoundaryFlags: Array<[keyof NonNullable<WorkspaceStatus["hard_boundary_contract"]>, string]> = [
      ["would_execute", "hard_boundary_contract would_execute must remain false"],
      ["would_dispatch", "hard_boundary_contract would_dispatch must remain false"],
      ["would_session_send", "hard_boundary_contract would_session_send must remain false"],
      ["execution_enabled", "hard_boundary_contract execution_enabled must remain false"],
      ["dispatch_enabled", "hard_boundary_contract dispatch_enabled must remain false"],
      ["session_send_enabled", "hard_boundary_contract session_send_enabled must remain false"],
      ["send_to_jenny_enabled", "hard_boundary_contract send_to_jenny_enabled must remain false"],
      ["worker_dispatch_enabled", "hard_boundary_contract worker_dispatch_enabled must remain false"],
      ["execution_ready", "hard_boundary_contract execution_ready must remain false"],
      ["live_operations_enabled", "hard_boundary_contract live_operations_enabled must remain false"],
    ];
    for (const [flag, reason] of hardBoundaryFlags) {
      if (compactLiveFlagEnabled(hardBoundary[flag])) reasons.push(reason);
    }
  }
  const operatorPacket = workspaceStatus?.operator_decision_packet;
  reasons.push(...(operatorPacket?.execution_lock_blocked_reasons ?? []));
  reasons.push(...compactExecutionLockReasons("operator_decision_packet", operatorPacket));
  reasons.push(...compactExecutionLockReasons("orchestration_readiness", workspaceStatus?.orchestration_readiness));

  const uniqueReasons = [...new Set(reasons)];
  return { reasons: uniqueReasons, safe: uniqueReasons.length === 0 };
}

function compactBridgeBlockedMessage(safety: CompactBridgeSafety): string {
  return `Manual Jenny bridge blocked: ${safety.reasons[0] ?? "bridge safety is not confirmed"}`;
}

function noReplyStatusMessage(error: unknown): string {
  const rawError = error ?? "no matching pending request";
  if (isNoPendingBridgeError(rawError)) {
    return "Jenny is caught up. Send a new message to start the next reply.";
  }
  return `Jenny did not reply: ${String(rawError)}`;
}

function jennyDeliveryStatus(
  pendingCount: number,
  responseCount: number,
  bridgeStatus: JennyBridgePollerStatus,
  githubBridgeStatus: GitHubBridgeStatus,
): string {
  if (normalizedBridgeError(bridgeStatus, githubBridgeStatus)) {
    return "Jenny bridge needs attention";
  }
  if (githubBridgeStatus.foreground_watch_running) {
    return pendingCount ? `${pendingCount} waiting while bridge is watching` : "Bridge watching for replies";
  }
  if (pendingCount) {
    return `${pendingCount} sent; waiting for Jenny`;
  }
  if (responseCount) {
    return "Replies up to date";
  }
  return "Ready for your first message";
}

function jennyConnectionState(
  pendingCount: number,
  responseCount: number,
  bridgeStatus: JennyBridgePollerStatus,
  githubBridgeStatus: GitHubBridgeStatus,
): { detail: string; label: string; tone: "bad" | "good" | "idle" | "warn" } {
  if (normalizedBridgeError(bridgeStatus, githubBridgeStatus)) {
    return {
      detail: "Jenny hit a guarded bridge issue. Open Safety details only if you need diagnostics.",
      label: "Jenny needs attention",
      tone: "bad",
    };
  }
  if (githubBridgeStatus.foreground_watch_running) {
    return {
      detail: pendingCount ? `${pendingCount} message${pendingCount === 1 ? "" : "s"} waiting while the bridge watches.` : "Bridge is watching for replies.",
      label: "Jenny is watching",
      tone: "good",
    };
  }
  if (pendingCount) {
    return {
      detail: `${pendingCount} message${pendingCount === 1 ? "" : "s"} sent; waiting for Jenny.`,
      label: "Waiting for Jenny",
      tone: "warn",
    };
  }
  if (responseCount) {
    return {
      detail: "Review the latest reply, then send the next bounded message.",
      label: "Jenny replied",
      tone: "good",
    };
  }
  return {
    detail: "Type one bounded project message to start.",
    label: "Ready to message",
    tone: "idle",
  };
}

function jennyStatusToneClass(tone: "bad" | "good" | "idle" | "warn"): string {
  if (tone === "bad") {
    return "border-destructive/40 bg-destructive/10 text-destructive";
  }
  if (tone === "good") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  }
  if (tone === "warn") {
    return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
  }
  return "border-border/70 bg-muted/40 text-muted-foreground";
}

function jennyRunStatusToneClass(progress: JennyRunProgress | null, connectionTone: "bad" | "good" | "idle" | "warn"): string {
  if (progress?.phase === "error" || connectionTone === "bad") {
    return "border-red-500/35 bg-red-500/10 text-red-100";
  }
  if (progress?.phase === "starting" || progress?.phase === "waiting") {
    return "border-sky-500/35 bg-sky-500/10 text-sky-100";
  }
  if (progress?.phase === "queued" || connectionTone === "warn") {
    return "border-amber-500/35 bg-amber-500/10 text-amber-100";
  }
  if (progress?.phase === "complete" || connectionTone === "good") {
    return "border-emerald-500/35 bg-emerald-500/10 text-emerald-100";
  }
  return "border-[#f3ebda]/10 bg-[#15101a]/70 text-[#f3ebda]";
}

function jennyNextStep(
  pendingCount: number,
  responseCount: number,
  hasRunnablePendingMessage: boolean,
  bridgeStatus: JennyBridgePollerStatus,
  githubBridgeStatus: GitHubBridgeStatus,
): string {
  if (normalizedBridgeError(bridgeStatus, githubBridgeStatus)) {
    return "Jenny hit a guarded bridge issue. Open Safety details only if you need diagnostics.";
  }
  if (hasRunnablePendingMessage) {
    return "A message is waiting for Jenny; send your next message only after this reply finishes.";
  }
  if (pendingCount) {
    return "A message is waiting for Jenny.";
  }
  if (responseCount) {
    return "Review Jenny's latest reply, then send the next bounded message.";
  }
  return "Type one bounded project message, then tap Send.";
}

function jennyOperatorGuidance({
  bridgeError,
  hasRunnablePendingMessage,
  pendingCount,
  progress,
  replyReviewTone,
  responseCount,
}: {
  bridgeError: string;
  hasRunnablePendingMessage: boolean;
  pendingCount: number;
  progress: JennyRunProgress | null;
  replyReviewTone: "accepted" | "blocked" | "none" | "warn";
  responseCount: number;
}): { detail: string; label: string; tone: "bad" | "good" | "idle" | "warn" } {
  if (bridgeError || progress?.phase === "error") {
    return {
      detail: hasRunnablePendingMessage
        ? "Jenny hit a guarded error. Send a short follow-up only after the error is reviewed."
        : "Jenny hit a guarded error. Open Safety details if you need the bridge diagnostics before sending more work.",
      label: "Jenny needs attention",
      tone: "bad",
    };
  }
  if (isJennyRunActive(progress)) {
    return {
      detail: "Jenny has one bounded reply in progress. Do not send another request until this finishes.",
      label: "Wait for Jenny",
      tone: "warn",
    };
  }
  if (replyReviewTone === "blocked" || replyReviewTone === "warn") {
    return {
      detail: "Review the latest Jenny answer. Ask for evidence or challenge the plan before treating it as done.",
      label: "Review Jenny reply",
      tone: "warn",
    };
  }
  if (hasRunnablePendingMessage || pendingCount) {
    return {
      detail: "A message is waiting for Jenny. Mission Control will keep the chat status visible.",
      label: "Waiting for Jenny",
      tone: "warn",
    };
  }
  if (responseCount) {
    return {
      detail: "The latest reply is available. Send the next bounded request when you are ready.",
      label: "Ready for next message",
      tone: "good",
    };
  }
  return {
    detail: "Type one clear request. Jenny should challenge vague, unsafe, or wrong-approach work before planning.",
    label: "Start with one request",
    tone: "idle",
  };
}

function lineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map(item => item.trim())
    .filter(Boolean);
}

function artifactText(state: ProjectStateRecord | undefined, report: ReportRecord | undefined): string {
  return listText(state?.artifact_links ?? report?.metadata?.artifact_links ?? report?.changed_files, "No artifact/report links recorded");
}

function reportContractMissing(report: ReportRecord | undefined): string[] {
  if (!report) {
    return ["report"];
  }

  const hasRisks = Boolean(report.risks?.length || report.blockers?.length);
  const hasEvidence = Boolean(report.changed_files?.length || report.metadata?.artifact_links?.length);
  return [
    report.summary ? "" : "summary",
    report.result ? "" : "result",
    hasRisks ? "" : "risks/blockers",
    hasEvidence ? "" : "evidence",
    report.tests?.length ? "" : "tests",
    report.next_recommended_lane ? "" : "next lane",
  ].filter(Boolean);
}

function reportContractSummary(report: ReportRecord | undefined): string {
  const missing = reportContractMissing(report);
  if (missing.includes("report")) {
    return "No report yet";
  }
  return missing.length ? `Missing: ${missing.join(", ")}` : "Complete";
}

function reportContractSummaryForState(state: ProjectStateRecord | undefined, report: ReportRecord | undefined): string {
  const contract = state?.report_contract;
  const missing = contract?.missing_fields?.filter(Boolean) ?? [];
  if (contract?.state === "missing_report" || missing.includes("report")) {
    return "No report yet";
  }
  if (missing.length) {
    return `Missing: ${missing.join(", ")}`;
  }
  if (contract?.complete === true || contract?.state === "complete") {
    return "Complete";
  }
  return reportContractSummary(report);
}

function projectRank(project: ProjectRecord): number {
  const idIndex = REAL_PROJECT_IDS.findIndex(id => id === project.project_id);
  if (idIndex >= 0) return idIndex;
  const nameIndex = REAL_PROJECT_NAMES.findIndex(name => name === project.name);
  return nameIndex >= 0 ? nameIndex : Number.MAX_SAFE_INTEGER;
}

function isRealProject(project: ProjectRecord): boolean {
  return projectRank(project) !== Number.MAX_SAFE_INTEGER;
}

function isSmokeProject(project: ProjectRecord): boolean {
  return /smoke|support/i.test(`${project.project_id} ${project.name} ${project.status ?? ""}`);
}

function compactSessionRoute(sessionId: string): string {
  return `/chat?resume=${encodeURIComponent(sessionId)}`;
}

function canonicalRealProjects(projects: ProjectRecord[]): ProjectRecord[] {
  return CANONICAL_REAL_PROJECTS.map(canonical => {
    const existing = projects.find(project => project.project_id === canonical.project_id)
      ?? projects.find(project => project.name === canonical.name);

    return existing ? { ...canonical, ...existing } : canonical;
  });
}

function formatBytes(value: unknown): string {
  const bytes = typeof value === "number" && Number.isFinite(value) ? value : 0;
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = bytes / 1024;
  for (const unit of units) {
    if (amount < 1024 || unit === units[units.length - 1]) {
      return `${amount.toFixed(amount >= 10 ? 0 : 1)} ${unit}`;
    }
    amount /= 1024;
  }
  return `${bytes} B`;
}

function formatPercent(value: unknown): string {
  const percent = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return `${Math.max(0, Math.round(percent))}%`;
}

function compactModelLabel(info: CompactModelInfo | null): string {
  const provider = info?.provider?.trim();
  const model = info?.model?.trim();
  if (provider && model) return `${provider} / ${model}`;
  return model || provider || "model unknown";
}

function compactModelChoiceKey(provider: string, model: string): string {
  return `${provider}\u0000${model}`;
}

function compactModelChoiceFromKey(value: string): CompactRunSettings | null {
  const [provider, model] = value.split("\u0000");
  if (!provider?.trim() || !model?.trim()) {
    return null;
  }
  return { effort: "", model: model.trim(), provider: provider.trim() };
}

function compactRunSettingsLabel(settings: CompactRunSettings): string {
  const provider = settings.provider.trim();
  const model = settings.model.trim();
  const effort = COMPACT_RUN_EFFORTS.find(option => option.value === settings.effort)?.label ?? settings.effort;
  return [
    provider && model ? `${provider} / ${model}` : model || provider || "model unknown",
    effort ? `effort ${effort}` : "",
  ].filter(Boolean).join(" / ");
}

function compactRunSettingsLines(settings: CompactRunSettings): string[] {
  const effortLabel = COMPACT_RUN_EFFORTS.find(option => option.value === settings.effort)?.label ?? settings.effort;
  return [
    "Run preference:",
    `Requested model: ${settings.provider && settings.model ? `${settings.provider} / ${settings.model}` : settings.model || settings.provider || "current Hermes model"}`,
    `Requested effort: ${effortLabel || "current default"}`,
    "These are foreground handoff preferences only; this compact page does not mutate global model routing.",
    "",
  ];
}

function latestForProject<T extends { project_id?: string }>(projectId: string, values: T[]): T | undefined {
  return [...values].reverse().find(value => value.project_id === projectId);
}

function projectReadinessLabel(brief: ProjectBriefRecord | undefined, review: ChallengeReviewRecord | undefined): { detail: string; label: string } {
  if (!brief) {
    return { detail: "Create or update the project brief before Jenny drafts work.", label: "Needs brief" };
  }
  if (!review) {
    return { detail: "Run the Jenny challenge gate before creating a lane draft.", label: "Needs challenge" };
  }
  if (review.decision_state === "clear_and_safe") {
    return { detail: "Latest challenge review cleared a bounded lane draft.", label: "Lane draft ok" };
  }
  if (review.decision_state === "needs_approval") {
    return { detail: "Travis needs to approve the path before Jenny proceeds.", label: "Needs approval" };
  }
  if (review.decision_state === "unsafe" || review.decision_state === "wrong_approach_likely") {
    return { detail: "Jenny should push back and recommend a safer path.", label: "Challenge blocked" };
  }
  return { detail: "Clarify the request or split it before a lane draft.", label: "Spec first" };
}

function laneDraftBlockMessage(review: ChallengeReviewRecord | undefined): string | null {
  if (!review) {
    return "Create a Jenny challenge review before saving a lane request draft.";
  }
  if (review.decision_state !== "clear_and_safe") {
    return `Latest challenge review is ${review.decision_state || "missing"}. Resolve that before saving a lane request draft.`;
  }
  return null;
}

function hasBlockingSignal(projectView: ProjectViewModel): boolean {
  const decision = projectView.challengeReview?.decision_state ?? "";
  if (decision === "unsafe" || decision === "wrong_approach_likely") {
    return true;
  }
  const combined = `${projectView.risks} ${projectView.blockers}`.toLowerCase();
  return /\b(blocked|blocker|rollback|unsafe|wrong approach)\b/.test(combined) && !/\b(no blockers?|none)\b/.test(combined);
}

function projectKanbanColumnFor(projectView: ProjectViewModel): ProjectKanbanColumnId {
  if (hasBlockingSignal(projectView)) {
    return "blocked-rollback";
  }
  if (!projectView.projectBrief) {
    return "intake";
  }
  if (!projectView.challengeReview) {
    return "challenge-review";
  }
  if (projectView.challengeReview.decision_state === "needs_spec_first") {
    return "needs-clarification";
  }
  if (projectView.challengeReview.decision_state === "needs_approval") {
    return "awaiting-approval";
  }
  if (projectView.challengeReview.decision_state !== "clear_and_safe") {
    return "needs-clarification";
  }
  if (!projectView.latestLaneRequest) {
    return "lane-draft";
  }

  const laneStatus = (projectView.latestLaneRequest.status ?? "").toLowerCase();
  if (laneStatus === "accepted" || laneStatus === "completed" || laneStatus === "complete") {
    return "accepted";
  }
  if (laneStatus === "active" || laneStatus === "approved" || laneStatus === "running") {
    return "active";
  }
  if (projectView.projectState?.has_real_report || projectView.latestReport !== "No report yet") {
    return "evidence-review";
  }
  if (laneStatus === "draft" || laneStatus === "pending" || laneStatus === "proposed" || laneStatus === "") {
    return "awaiting-approval";
  }

  return "lane-draft";
}

function viewModelForProject(snapshot: CompactSnapshot, project: ProjectRecord): ProjectViewModel {
  const state = latestForProject(project.project_id, snapshot.projectStates);
  const report = latestForProject(project.project_id, snapshot.reports);
  const lane = latestForProject(project.project_id, snapshot.laneRequests);
  const projectBrief = latestForProject(project.project_id, snapshot.projectBriefs);
  const challengeReview = latestForProject(project.project_id, snapshot.challengeReviews);
  const readiness = projectReadinessLabel(projectBrief, challengeReview);
  const riskValues = state?.risks ?? state?.risks_blockers ?? report?.risks;
  const blockerValues = state?.blockers ?? report?.blockers;

  return {
    artifactLinks: artifactText(state, report),
    blockers: listText(blockerValues, "No blockers recorded"),
    currentGoal: text(state?.current_goal ?? project.current_goal, "No current goal recorded"),
    freshness: state?.has_real_report ? "Live report available" : "Seed only — needs first report",
    latestActivity: text(state?.latest_activity_at, "No activity time recorded"),
    latestLane: text(state?.latest_lane_title ?? lane?.title, "No lane recorded"),
    latestLaneRequest: lane,
    latestReport: text(state?.latest_report_summary || report?.summary || project.latest_report_summary, "No report yet"),
    latestResult: text(state?.latest_result || report?.result || project.latest_result, "No result yet"),
    missingFields: listText(state?.missing_state_fields, "None - report state is current"),
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane ?? lane?.title, "No recommended lane yet"),
    projectBrief,
    projectState: state,
    project,
    reportContract: reportContractSummaryForState(state, report),
    report,
    readinessDetail: readiness.detail,
    readinessLabel: readiness.label,
    challengeReview,
    risks: listText(riskValues, "No risks recorded"),
    status: text(state?.status ?? project.status, "Status not recorded"),
  };
}

function safetySummary(status: WorkspaceStatus): string {
  const guard = status.runtime_worktree_guard?.decision_state ?? "unknown";
  const dispatch = status.safety?.dispatch_in_gateway === false ? "false" : "unknown";
  const activeLaneCount = status.lane?.active_lane_count ?? 0;
  const staleWarnings = status.stale_context?.warnings ?? [];
  return `guard=${guard}; dispatch=${dispatch}; active_lane_count=${activeLaneCount}; stale_warnings=${staleWarnings.length ? staleWarnings.join(", ") : "none"}`;
}

function firstReason(values: string[] | undefined, fallback: string): string {
  return values?.find(value => value.trim()) ?? fallback;
}

function compactRecordText(record: Record<string, unknown> | undefined, field: string): string {
  const value = record?.[field];
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function compactStateLabel(value: string | undefined, fallback = "unknown"): string {
  return (value?.trim() || fallback).replaceAll("_", " ");
}

function compactOperatorSummary(status: WorkspaceStatus): string {
  const packet = status.operator_decision_packet;
  return compactText(
    packet?.execution_lock_blocked_reasons?.length
      ? `Operator execution locks: ${firstReason(packet.execution_lock_blocked_reasons, "review nested execution lock blockers")}`
      : (
        packet?.recommended_operator_instruction
        || packet?.next_safe_action_label
        || packet?.plain_language_summary
        || "Keep Mission Control preview-only and review the next safe action."
      ),
    260,
  );
}

function compactReadinessSummary(status: WorkspaceStatus): string {
  const states = status.orchestration_readiness?.states;
  return [
    `read-only ${compactStateLabel(states?.supervised_read_only_autonomy)}`,
    `scoped PR ${compactStateLabel(states?.scoped_pr_creation)}`,
    `laptop Codex ${compactStateLabel(states?.laptop_codex_worker_node)}`,
  ].join("; ");
}

function structuredJennyHandoff(projectName: string): string {
  return [
    "Structured handoff:",
    `Goal: answer the request for ${projectName} as a bounded engineering lane.`,
    "Scope: use this project room context and approved repo/runtime evidence only.",
    "Challenge: question unclear, unsafe, or wrong-approach requests before implementation.",
    "Definition of done: state exact change, evidence, remaining risk, and next safe lane.",
    "Validation: list checks run or why a check is blocked.",
    "Report format: preflight, recommendation, work done, validation, risks, safety confirmation.",
    "Evidence contract:",
    "1. Recommendation: one-sentence next lane.",
    "2. Evidence: exact files/commands/checks/PR/CI/runtime/links used.",
    "3. Tests: pass/fail/not-run with reason.",
    "4. Risks: blockers, unsafe assumptions, missing info.",
    "5. Approval/rollback: approval needed before live action plus rollback path.",
    "6. Next safe lane: smallest bounded step.",
    "Rule: if evidence is missing, say \"not proven\"; do not present it as done.",
  ].join("\n");
}

interface RequestIntakeAssessment {
  detail: string;
  jennyInstruction: string;
  label: string;
  state: "approval_required" | "challenge_first" | "ready" | "spec_first";
}

function assessProjectRequest(requestText: string, review: ChallengeReviewRecord | undefined): RequestIntakeAssessment {
  const normalized = requestText.replace(/\s+/g, " ").trim();
  const lower = normalized.toLowerCase();
  const riskyAction = /\b(deploy|restart|runtime switch|gateway|payment|checkout|outreach|post|publish|delete|remove|cleanup|update|upgrade|install|configure|migrate|worker|timer|daemon|cron|secret|token|waha|whatsapp)\b/.test(lower);
  const vagueRequest = normalized.length < 24 || /\b(fix it|make it better|do whatever|handle this|everything|autonomous|fully functional|robust)\b/.test(lower);

  if (!normalized) {
    return {
      detail: "Write one bounded request before Jenny receives work.",
      jennyInstruction: "Ask Travis for the missing request before proposing implementation.",
      label: "Needs request",
      state: "spec_first",
    };
  }
  if (riskyAction) {
    return {
      detail: "Contains protected actions; Jenny should challenge scope and identify approvals before work.",
      jennyInstruction: "Do not execute. First return a preflight, risks, required approvals, and a safer bounded lane.",
      label: "Approval check",
      state: "approval_required",
    };
  }
  if (!review || review.decision_state !== "clear_and_safe") {
    return {
      detail: "No clear challenge review is recorded for this project lane.",
      jennyInstruction: "Treat this as challenge/spec-first. Ask clarifying questions or create a narrow plan before implementation.",
      label: "Challenge first",
      state: "challenge_first",
    };
  }
  if (vagueRequest) {
    return {
      detail: "Request may be too broad or underspecified; Jenny should narrow it before implementation.",
      jennyInstruction: "Question assumptions, split the request into a bounded lane, and ask Travis if critical details are missing.",
      label: "Spec first",
      state: "spec_first",
    };
  }
  return {
    detail: "Request is bounded enough for a guarded Jenny reply.",
    jennyInstruction: "Proceed with a bounded recommendation or implementation plan, still challenging unsafe assumptions first.",
    label: "Ready",
    state: "ready",
  };
}

function buildSpecFirstComposerText(projectName: string, requestText: string, intake: RequestIntakeAssessment, settings?: CompactRunSettings): string {
  const request = compactText(requestText, 520) || "<write the request Travis is considering>";
  return [
    "Spec-first request for Jenny:",
    `Project: ${projectName}`,
    ...(settings ? compactRunSettingsLines(settings) : []),
    "Request Travis is considering:",
    request,
    "",
    `Current intake: ${intake.label} / ${intake.detail}`,
    "",
    "Jenny, do not implement yet. First challenge the request like a senior engineer:",
    "1. Restate the goal in plain English.",
    "2. List missing facts or questions Travis must answer.",
    "3. Call out wrong-approach risks, hidden assumptions, and protected actions.",
    "4. Propose the smallest safe lane.",
    "5. Define evidence, tests, rollback/stop conditions, and approval needs.",
    "",
    "Return only the spec/challenge review and the recommended next safe lane.",
  ].join("\n");
}

function shouldAutoChallengeRequest(intake: RequestIntakeAssessment): boolean {
  return intake.state !== "ready";
}

function jennySendButtonLabel(): string {
  return "Send";
}

function buildCompactNextLanePrompt(projectView: ProjectViewModel, workspaceStatus: WorkspaceStatus): string {
  const guidance = PROJECT_LANE_GUIDANCE[projectView.project.project_id] ?? "Read-only Mission Control status lane. Report current state and the next safe manual step.";
  return [
    "MISSION CONTROL COMPACT - REVIEW PACKET",
    "",
    `Project: ${projectView.project.name}`,
    `Status: ${projectView.status}`,
    `Current goal: ${projectView.currentGoal}`,
    `Latest report/result: ${projectView.latestReport} / ${projectView.latestResult}`,
    `Risks/blockers: ${projectView.risks} / ${projectView.blockers}`,
    `Next recommended lane: ${projectView.nextLane}`,
    "",
    `Project-specific prompt: ${guidance}`,
    "Allowed actions: read existing GET-only Mission Control state, inspect approved source-of-truth, and report a bounded next lane.",
    "Forbidden actions: no POST, session-send, dispatch, queue/Kanban/Waha/model routing, workers, timers, browser storage, records/config mutation, deploy, restart, or secrets.",
    `Safety status: ${safetySummary(workspaceStatus)}`,
    "Use guarded project chat for the Jenny mailbox, or copy this packet manually after review. Direct session send remains disabled.",
  ].join("\n");
}

function buildPhoneSafeProjectPacket(projectView: ProjectViewModel, requestText: string, workspaceStatus: WorkspaceStatus, settings?: CompactRunSettings): string {
  const request = compactText(requestText, 420) || "<write the request>";
  const brief = projectView.projectBrief;
  const review = projectView.challengeReview;
  const intake = assessProjectRequest(requestText, review);
  const categories = review?.challenge_categories?.length ? review.challenge_categories.join(", ") : "none recorded";
  const verdicts = review?.blocking_verdicts?.length ? review.blocking_verdicts.join(", ") : "none recorded";
  const guard = compactText(projectView.project.mistakes_guards, 220) || "guarded mailbox only; no live action";
  const packet = [
    "Project room request:",
    projectView.project.name,
    "",
    ...(settings ? compactRunSettingsLines(settings) : []),
    "Request:",
    request,
    "",
    "Request intake:",
    `${intake.label} / ${intake.detail}`,
    `Jenny instruction: ${intake.jennyInstruction}`,
    "",
    "Current brief:",
    compactText(brief?.outcome, 220) || "missing project brief",
    "",
    "Challenge state:",
    `${compactText(review?.decision_state, 60) || "missing"} / ${compactText(review?.recommended_path, 240) || "challenge review required before lane draft"}`,
    `Categories: ${compactText(categories, 240)}`,
    `Blocking verdicts: ${compactText(verdicts, 240)}`,
    "",
    "Readiness:",
    projectView.readinessLabel,
    "",
    "Guards:",
    guard,
    "",
    "Allowed: read approved context, report status, recommend next safe lane.",
    "Forbidden: no direct session send, live mutation, Waha, queue, model, social, payment, worker, timer, deploy, restart, runtime switch, config/state, or secrets unless separately approved.",
    "",
    `Safety status: ${safetySummary(workspaceStatus)}`,
    "",
    structuredJennyHandoff(projectView.project.name),
  ].join("\n").trim();
  return boundCompactJennyMessage(packet);
}

function boundCompactJennyMessage(message: string): string {
  const trimmed = message.trim();
  return trimmed.length <= COMPACT_JENNY_MESSAGE_LIMIT
    ? trimmed
    : `${trimmed.slice(0, COMPACT_JENNY_MESSAGE_LIMIT - 3).trim()}...`;
}

function buildJennyMailboxMessage(projectView: ProjectViewModel, requestText: string, workspaceStatus: WorkspaceStatus, settings?: CompactRunSettings): string {
  const request = chatRequestText(requestText);
  const intake = assessProjectRequest(request, projectView.challengeReview);
  if (shouldAutoChallengeRequest(intake)) {
    return boundCompactJennyMessage(buildSpecFirstComposerText(projectView.project.name, request, intake, settings));
  }
  return boundCompactJennyMessage(buildPhoneSafeProjectPacket(projectView, request, workspaceStatus, settings));
}

function buildHermesUpdateLanePacket(workspaceStatus: WorkspaceStatus): string {
  return [
    "Hermes update lane request:",
    "",
    HERMES_UPDATE_LANE_REQUEST,
    "",
    "Required safe sequence:",
    "1. Read-only inventory of VPS dashboard/gateway runtime paths/heads and current package versions.",
    "2. Read-only inventory of the existing VPS-triggered laptop worker-node update path and laptop installed version.",
    "3. Prepare a non-live VPS dashboard runtime at accepted-live only after source and worker-node target are clear.",
    "4. Validate markers, record compatibility, dashboard assets, and rollback path before any dashboard-only switch.",
    "5. Keep gateway update and laptop worker-node update as separate explicit approval steps.",
    "",
    "Allowed: read-only inventory, non-live runtime preparation, tests/checks, report exact next approval.",
    "Forbidden: laptop worker-node auto-update, gateway restart/switch, dispatch, session sending, Waha/social/payment/customer action, new background worker/timer/daemon/cron, secrets, in-place runtime mutation.",
    "",
    `Current Mission Control safety status: ${safetySummary(workspaceStatus)}`,
  ].join("\n");
}

function buildHermesStorageCleanupLanePacket(workspaceStatus: WorkspaceStatus): string {
  return [
    "Hermes storage cleanup lane request:",
    "",
    HERMES_STORAGE_CLEANUP_LANE_REQUEST,
    "",
    "Required safe sequence:",
    "1. Read-only inventory of VPS disk usage, largest Hermes runtimes/worktrees/caches/build outputs/logs/backups, and current rollback runtimes.",
    "2. Build a timestamped dry-run manifest with exact candidate paths, protected paths, expected GiB recovered, and rollback risk.",
    "3. Protect current dashboard runtime, gateway runtime, shared runtime venv, latest rollback runtime, live records/secrets/service files, dirty project worktrees, report-builder/customer/payment/outreach data, and anything uncertain.",
    "4. With explicit cleanup approval, remove only clean stale Hermes runtime worktrees, clean stale review worktrees, old caches/build outputs/logs, and other manifest-approved low-risk artifacts.",
    "5. Measure df -h and top du consumers before and after each pass; target about 50% disk usage, then stop and report residual risk.",
    "",
    "Allowed: storage inventory, dry-run manifest, approved stale runtime/worktree/cache/log cleanup, archive recommendation, and before/after effectiveness report.",
    "Forbidden: dirty worktrees, Tool & Tally report-builder data, records/config/state.db, secrets, current/rollback runtimes, gateway restart/switch, laptop worker-node cleanup, dispatch, session sending, Waha/social/payment/customer action, workers/timers/daemons/cron.",
    "",
    `Current Mission Control safety status: ${safetySummary(workspaceStatus)}`,
  ].join("\n");
}

function missionControlErrorMessage(err: unknown): string {
  return String(err instanceof Error ? err.message : err);
}

function jennyChatErrorMessage(err: unknown): string {
  const raw = missionControlErrorMessage(err);
  const lower = raw.toLowerCase();
  if (lower.includes("econnrefused") || lower.includes("failed to fetch") || lower.includes("gateway offline")) {
    return "Jenny bridge is offline. Start or reconnect the Hermes gateway, then send the message again.";
  }
  if (lower.includes("bridge field is too large") || lower.includes("field is too large")) {
    return "That message was too large for the Jenny bridge. Shorten it and send one focused request.";
  }
  if (lower.includes("no matching pending") || lower.includes("no pending message") || lower.includes("no pending request")) {
    return "No message is waiting for Jenny. Send a message first.";
  }
  if (lower.includes("timed out") || lower.includes("timeout")) {
    return "Jenny did not answer before the time limit. The request is still guarded; try again with one smaller task.";
  }
  return raw.replace(/^Error invoking remote method 'hermes:api':\s*/i, "").trim();
}

async function loadMissionControlEndpoint<T>(
  label: string,
  load: () => Promise<T>,
  fallback: T | ((error: string) => T),
): Promise<T> {
  try {
    return await load();
  } catch {
    try {
      return await load();
    } catch (err) {
      const message = missionControlErrorMessage(err);
      console.warn(`[mission-control] ${label} unavailable`, err);
      return typeof fallback === "function" ? (fallback as (error: string) => T)(message) : fallback;
    }
  }
}

async function loadCompactSnapshot(): Promise<CompactSnapshot> {
  const [workspaceStatus, projects, projectBriefs, challengeReviews, laneRequests, reports, projectState, jennyBridgeOutbox, jennyBridgeInbox, jennyBridgePollerStatus, githubBridgeStatus, jennyReplyReviews, memoryStorage] = await Promise.all([
    loadMissionControlEndpoint("workspace status", () => fetchJSON<WorkspaceStatus>(WORKSPACE_STATUS_URL), {}),
    loadMissionControlEndpoint("projects", () => fetchJSON<{ projects?: Array<WrappedRecord<ProjectRecord> | ProjectRecord> }>(WORKSPACE_PROJECTS_URL), { projects: [] }),
    loadMissionControlEndpoint("project briefs", () => fetchJSON<{ project_briefs?: Array<WrappedRecord<ProjectBriefRecord> | ProjectBriefRecord> }>(WORKSPACE_PROJECT_BRIEFS_URL), { project_briefs: [] }),
    loadMissionControlEndpoint("challenge reviews", () => fetchJSON<{ challenge_reviews?: Array<WrappedRecord<ChallengeReviewRecord> | ChallengeReviewRecord> }>(WORKSPACE_CHALLENGE_REVIEWS_URL), { challenge_reviews: [] }),
    loadMissionControlEndpoint("lane requests", () => fetchJSON<{ lane_requests?: Array<WrappedRecord<LaneRequestRecord> | LaneRequestRecord> }>(WORKSPACE_LANE_REQUESTS_URL), { lane_requests: [] }),
    loadMissionControlEndpoint("reports", () => fetchJSON<{ reports?: Array<WrappedRecord<ReportRecord> | ReportRecord> }>(WORKSPACE_REPORTS_URL), { reports: [] }),
    loadMissionControlEndpoint("project state", () => fetchJSON<{ project_states?: ProjectStateRecord[] }>(WORKSPACE_PROJECT_STATE_URL), { project_states: [] }),
    loadMissionControlEndpoint("Jenny bridge outbox", () => fetchJSON<{ requests?: Array<WrappedRecord<JennyBridgeRequestRecord> | JennyBridgeRequestRecord> }>(WORKSPACE_JENNY_BRIDGE_OUTBOX_URL), { requests: [] }),
    loadMissionControlEndpoint("Jenny bridge inbox", () => fetchJSON<{ responses?: Array<WrappedRecord<JennyBridgeResponseRecord> | JennyBridgeResponseRecord> }>(WORKSPACE_JENNY_BRIDGE_INBOX_URL), { responses: [] }),
    loadMissionControlEndpoint("Jenny bridge poller status", () => fetchJSON<JennyBridgePollerStatus>(WORKSPACE_JENNY_BRIDGE_POLLER_STATUS_URL), error => ({
      last_error: `Jenny bridge poller unavailable: ${error}`,
    })),
    loadMissionControlEndpoint("GitHub bridge status", () => fetchJSON<GitHubBridgeStatus>(WORKSPACE_GITHUB_BRIDGE_STATUS_URL), error => ({
      last_error: `Jenny activity unavailable: ${error}`,
      pending_messages: [],
      recent_messages: [],
      response_messages: [],
    })),
    loadMissionControlEndpoint("Jenny reply reviews", () => fetchJSON<{ reply_reviews?: Array<WrappedRecord<JennyReplyReviewRecord> | JennyReplyReviewRecord> }>(WORKSPACE_JENNY_REPLY_REVIEWS_URL), { reply_reviews: [] }),
    loadMissionControlEndpoint("profile storage", () => fetchJSON<ProfileMemoryStorage>(WORKSPACE_PROFILE_MEMORY_STORAGE_URL), error => ({
      errors: [{ error }],
      profiles: [],
    })),
  ]);

  return {
    challengeReviews: unwrapRecords(challengeReviews.challenge_reviews),
    jennyBridgeRequests: unwrapRecords(jennyBridgeOutbox.requests),
    jennyBridgeResponses: unwrapRecords(jennyBridgeInbox.responses),
    jennyReplyReviews: unwrapRecords(jennyReplyReviews.reply_reviews),
    jennyBridgePollerStatus,
    githubBridgeStatus,
    laneRequests: unwrapRecords(laneRequests.lane_requests),
    memoryStorage,
    projectBriefs: unwrapRecords(projectBriefs.project_briefs),
    projectStates: projectState.project_states ?? [],
    projects: unwrapRecords(projects.projects),
    reports: unwrapRecords(reports.reports),
    workspaceStatus,
  };
}

export default function MissionControlCompactPage() {
  const { setTitle } = usePageHeader();
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<CompactSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copiedProjectId, setCopiedProjectId] = useState("");
  const [reportForm, setReportForm] = useState<ReportFormState>(EMPTY_REPORT_FORM);
  const [reportMessage, setReportMessage] = useState("");
  const [savingReport, setSavingReport] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [projectRequest, setProjectRequest] = useState("");
  const [roomMessage, setRoomMessage] = useState("");
  const [roomBusy, setRoomBusy] = useState(false);
  const [jennyRunElapsedSeconds, setJennyRunElapsedSeconds] = useState(0);
  const [jennyRunProgress, setJennyRunProgress] = useState<JennyRunProgress | null>(null);
  const [modelInfo, setModelInfo] = useState<CompactModelInfo | null>(null);
  const [modelOptions, setModelOptions] = useState<CompactModelOptions | null>(null);
  const [selectedModelChoice, setSelectedModelChoice] = useState("");
  const [selectedEffort, setSelectedEffort] = useState("xhigh");

  useEffect(() => {
    setTitle("Jenny");
    return () => setTitle(null);
  }, [setTitle]);

  useEffect(() => {
    let cancelled = false;
    loadCompactSnapshot()
      .then(nextSnapshot => {
        if (!cancelled) setSnapshot(nextSnapshot);
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadMissionControlEndpoint<CompactModelInfo | null>("model info", () => fetchJSON<CompactModelInfo>(MODEL_INFO_URL), null)
      .then(info => {
        if (!cancelled) setModelInfo(info);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadMissionControlEndpoint<CompactModelOptions | null>("model options", () => fetchJSON<CompactModelOptions>(MODEL_OPTIONS_URL), null)
      .then(options => {
        if (!cancelled) setModelOptions(options);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedProjectId && !snapshot?.projects.length) {
      return;
    }

    const timer = window.setInterval(() => {
      loadCompactSnapshot()
        .then(nextSnapshot => {
          setSnapshot(nextSnapshot);
          setError("");
        })
        .catch(err => setError(err instanceof Error ? err.message : String(err)));
    }, roomBusy ? 2500 : 15000);

    return () => window.clearInterval(timer);
  }, [roomBusy, selectedProjectId, snapshot?.projects.length]);

  useEffect(() => {
    if (!isJennyRunActive(jennyRunProgress)) {
      return;
    }

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setJennyRunElapsedSeconds(Math.max(1, Math.floor((Date.now() - startedAt) / 1000)));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [jennyRunProgress]);

  const realProjects = useMemo(() => {
    if (!snapshot) return [];
    return canonicalRealProjects(snapshot.projects.filter(isRealProject).sort((a, b) => projectRank(a) - projectRank(b)));
  }, [snapshot]);
  const activeProjects = useMemo(() => {
    const projects = realProjects.filter(project => ACTIVE_OS_PROJECT_IDS.includes(project.project_id));
    return projects.length ? projects : realProjects;
  }, [realProjects]);
  const pausedProjects = useMemo(
    () => realProjects.filter(project => PAUSED_PROJECT_IDS.includes(project.project_id) || !ACTIVE_OS_PROJECT_IDS.includes(project.project_id)),
    [realProjects],
  );
  const projectRoomProjects = realProjects.length ? realProjects : activeProjects;

  const supportProjects = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.projects.filter(project => !isRealProject(project) || isSmokeProject(project));
  }, [snapshot]);

  const selectedProjectView = useMemo(() => {
    if (!snapshot || !projectRoomProjects.length) return null;
    const selected = projectRoomProjects.find(project => project.project_id === selectedProjectId) ?? projectRoomProjects[0];
    return viewModelForProject(snapshot, selected);
  }, [projectRoomProjects, selectedProjectId, snapshot]);
  const modelChoices = useMemo(() => {
    const choices: Array<{ key: string; label: string }> = [];
    for (const provider of modelOptions?.providers ?? []) {
      for (const model of provider.models ?? []) {
        const key = compactModelChoiceKey(provider.slug, model);
        choices.push({
          key,
          label: `${provider.name || provider.slug} / ${model}`,
        });
      }
    }
    const currentProvider = modelOptions?.provider || modelInfo?.provider || "";
    const currentModel = modelOptions?.model || modelInfo?.model || "";
    if (currentProvider && currentModel) {
      const key = compactModelChoiceKey(currentProvider, currentModel);
      if (!choices.some(choice => choice.key === key)) {
        choices.unshift({ key, label: `${currentProvider} / ${currentModel}` });
      }
    }
    return choices;
  }, [modelInfo, modelOptions]);
  const currentModelChoice = selectedModelChoice || modelChoices[0]?.key || "";
  const currentModelSelection = compactModelChoiceFromKey(currentModelChoice);
  const compactRunSettings: CompactRunSettings = {
    effort: selectedEffort,
    model: currentModelSelection?.model || modelInfo?.model || "",
    provider: currentModelSelection?.provider || modelInfo?.provider || "",
  };
  const updateNotice = useMemo(() => snapshot ? dashboardUpdateNotice(snapshot.workspaceStatus) : "", [snapshot]);

  async function copyPrompt(projectView: ProjectViewModel) {
    const prompt = buildCompactNextLanePrompt(projectView, snapshot?.workspaceStatus ?? {});
    await navigator.clipboard?.writeText(prompt);
    setCopiedProjectId(projectView.project.project_id);
  }

  async function copyPhoneSafePacket(projectView: ProjectViewModel) {
    const packet = buildPhoneSafeProjectPacket(projectView, chatRequestText(projectRequest), snapshot?.workspaceStatus ?? {}, compactRunSettings);
    if (!navigator.clipboard?.writeText) {
      setRoomMessage("Clipboard unavailable. Select and copy the phone-safe packet manually.");
      return;
    }
    await navigator.clipboard.writeText(packet);
    setRoomMessage("Copied phone-safe project packet.");
  }

  async function queueJennyBridgeMessage(projectView: ProjectViewModel) {
    const chatRequest = chatRequestText(projectRequest);
    if (!chatRequest) {
      setRoomMessage("Write one bounded request before queuing a Jenny bridge message.");
      return;
    }
    const bridgeSafety = compactGitHubBridgeSafety(snapshot?.githubBridgeStatus, snapshot?.workspaceStatus);
    if (!bridgeSafety.safe) {
      setRoomMessage(compactBridgeBlockedMessage(bridgeSafety));
      return;
    }
    const requestId = bridgeRequestId();
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await fetchJSON<{ message?: { request_id?: string } }>(WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          from_agent: "travis",
          message: buildJennyMailboxMessage(projectView, chatRequest, snapshot?.workspaceStatus ?? {}, compactRunSettings),
          metadata: {
            requested_effort: compactRunSettings.effort,
            requested_model: compactRunSettings.model,
            requested_provider: compactRunSettings.provider,
          },
          project_id: projectView.project.project_id,
          request_id: requestId,
          to_agent: "jenny",
          user_message: boundCompactJennyMessage(chatRequest),
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      setJennyRunProgress({
        detail: "Message sent. Use Get reply when you want the foreground Jenny run; no hidden worker was started.",
        phase: "queued",
      });
      setProjectRequest("");
      setRoomMessage("Message sent. Use Get reply to run one foreground Jenny answer, or Refresh to check for an existing reply.");
      setRoomBusy(false);
      void refreshSnapshot().catch(err => {
        console.warn("[mission-control] compact chat snapshot refresh failed after queue", err);
      });
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function runJennyOnce(projectView: ProjectViewModel, requestId?: string) {
    const bridgeSafety = compactGitHubBridgeSafety(snapshot?.githubBridgeStatus, snapshot?.workspaceStatus);
    if (!bridgeSafety.safe) {
      setRoomMessage(compactBridgeBlockedMessage(bridgeSafety));
      return;
    }
    const pendingRequestId = requestId || latestVisiblePendingGitHubBridgeMessageForProject(
      unwrapRecords(snapshot?.githubBridgeStatus.visible_pending_messages),
      projectView.project.project_id,
    )?.request_id || latestVisiblePendingGitHubBridgeMessageForProject(
        [
          ...unwrapRecords(snapshot?.githubBridgeStatus.pending_messages),
          ...unwrapRecords(snapshot?.githubBridgeStatus.recent_messages),
          ...unwrapRecords(snapshot?.githubBridgeStatus.response_messages),
        ],
        projectView.project.project_id,
      )?.request_id;
    if (!pendingRequestId) {
      setRoomMessage("Send Jenny a project message first; there is no pending request to answer.");
      return;
    }

    setRoomBusy(true);
    setJennyRunElapsedSeconds(0);
    setJennyRunProgress({
      detail: "Starting the guarded one-reply Jenny run.",
      phase: "starting",
    });
    setRoomMessage("Jenny is answering one pending message...");
    try {
      setJennyRunProgress({
        detail: "Mission Control sent the latest project message to Jenny and is waiting for one bounded reply.",
        phase: "waiting",
      });
      const result = await fetchJSON<{ answered?: boolean; status?: { last_error?: string } }>(WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL, {
        body: JSON.stringify({
          confirm_manual_hermes_answer: true,
          project_id: projectView.project.project_id,
          request_id: pendingRequestId,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      let recordedReply: GitHubBridgeMessageRecord | null = null;
      try {
        const nextSnapshot = await loadCompactSnapshot();
        setSnapshot(nextSnapshot);
        recordedReply = latestGitHubBridgeReplyForRequest(nextSnapshot.githubBridgeStatus, pendingRequestId);
      } catch (refreshErr) {
        console.warn("[mission-control] compact chat snapshot refresh failed after Jenny run", refreshErr);
      }
      const answered = Boolean(result.answered || recordedReply);
      setJennyRunProgress({
        detail: answered ? "Jenny replied to the latest project message." : noReplyStatusMessage(result.status?.last_error),
        phase: answered ? "complete" : "error",
      });
      setRoomMessage(answered ? "Jenny replied to the latest pending project message." : noReplyStatusMessage(result.status?.last_error));
    } catch (err) {
      try {
        const nextSnapshot = await loadCompactSnapshot();
        setSnapshot(nextSnapshot);
        if (latestGitHubBridgeReplyForRequest(nextSnapshot.githubBridgeStatus, pendingRequestId)) {
          setJennyRunProgress({
            detail: "Jenny replied to the latest project message.",
            phase: "complete",
          });
          setRoomMessage("Jenny replied to the latest pending project message.");
          return;
        }
      } catch (refreshErr) {
        console.warn("[mission-control] compact chat reply reconciliation failed", refreshErr);
      }
      const message = jennyChatErrorMessage(err);
      setJennyRunProgress({
        detail: message,
        phase: "error",
      });
      setRoomMessage(message);
    } finally {
      setRoomBusy(false);
    }
  }

  async function reviewJennyReply(
    projectView: ProjectViewModel,
    decision: JennyReplyReviewDecision,
    responseId: string,
    reply: string,
  ) {
    const promptAction = decision === "accepted" ? "accept" : decision === "needs_evidence" ? "evidence" : "safer-plan";
    setProjectRequest(buildJennyReplyReviewPrompt(promptAction, projectView.project.name, reply));
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await fetchJSON(WORKSPACE_JENNY_REPLY_REVIEWS_CREATE_URL, {
        body: JSON.stringify({
          decision,
          note: jennyReplyReviewDecisionLabel(decision),
          project_id: projectView.project.project_id,
          response_id: responseId,
          reviewer: "travis",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage(`${jennyReplyReviewDecisionLabel(decision)}. Follow-up prompt is ready to send if needed.`);
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function queueHermesUpdateLane(projectView: ProjectViewModel) {
    const bridgeSafety = compactGitHubBridgeSafety(snapshot?.githubBridgeStatus, snapshot?.workspaceStatus);
    if (!bridgeSafety.safe) {
      setRoomMessage(compactBridgeBlockedMessage(bridgeSafety));
      return;
    }
    setRoomBusy(true);
    setRoomMessage("");
    setProjectRequest(HERMES_UPDATE_LANE_REQUEST);
    try {
      await fetchJSON(WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          from_agent: "travis",
          message: buildHermesUpdateLanePacket(snapshot?.workspaceStatus ?? {}),
          project_id: projectView.project.project_id,
          request_id: bridgeRequestId(),
          to_agent: "jenny",
          user_message: HERMES_UPDATE_LANE_REQUEST,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Sent safe Hermes update lane to Jenny mailbox. It is append-only and does not update the laptop worker node, switch runtimes, or restart gateway.");
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function queueHermesStorageCleanupLane(projectView: ProjectViewModel) {
    const bridgeSafety = compactGitHubBridgeSafety(snapshot?.githubBridgeStatus, snapshot?.workspaceStatus);
    if (!bridgeSafety.safe) {
      setRoomMessage(compactBridgeBlockedMessage(bridgeSafety));
      return;
    }
    setRoomBusy(true);
    setRoomMessage("");
    setProjectRequest(HERMES_STORAGE_CLEANUP_LANE_REQUEST);
    try {
      await fetchJSON(WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          from_agent: "travis",
          message: buildHermesStorageCleanupLanePacket(snapshot?.workspaceStatus ?? {}),
          project_id: projectView.project.project_id,
          request_id: bridgeRequestId(),
          to_agent: "jenny",
          user_message: HERMES_STORAGE_CLEANUP_LANE_REQUEST,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Sent safe Hermes storage cleanup lane to Jenny mailbox. It is append-only and does not delete, move, upload, restart, or switch anything.");
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function refreshSnapshot() {
    const nextSnapshot = await loadCompactSnapshot();
    setSnapshot(nextSnapshot);
  }

  async function refreshBridge() {
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await refreshSnapshot();
      setRoomMessage("Refreshed bridge inbox/outbox.");
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function saveChallengeDraft(projectView: ProjectViewModel) {
    if (!projectRequest.trim()) {
      setRoomMessage("Write one bounded request before saving a challenge draft.");
      return;
    }
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await fetchJSON(WORKSPACE_CHALLENGE_REVIEWS_CREATE_URL, {
        body: JSON.stringify({
          blocking_verdicts: ["requires_spec_update", "blocks_lane_draft"],
          challenge_categories: ["questions_required", "missing_context"],
          concerns: ["request entered from compact project room requires Jenny challenge review"],
          decision_state: "needs_spec_first",
          project_id: projectView.project.project_id,
          questions: ["What outcome should this project request produce?"],
          recommended_path: "Clarify the request, update the project brief if needed, then draft a bounded read-only lane.",
          request_summary: projectRequest.trim(),
          required_approvals: ["explicit approval before any send path or live action"],
          suggested_lane_title: compactText(projectRequest, 90) || "Read-only project room request",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Saved challenge draft. Jenny should question or narrow this before work starts.");
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function saveReadOnlyLaneDraft(projectView: ProjectViewModel) {
    if (!projectRequest.trim()) {
      setRoomMessage("Write one bounded request before saving a lane draft.");
      return;
    }
    const blockMessage = laneDraftBlockMessage(projectView.challengeReview);
    if (blockMessage) {
      setRoomMessage(blockMessage);
      return;
    }
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await fetchJSON(WORKSPACE_LANE_REQUESTS_CREATE_URL, {
        body: JSON.stringify({
          allowed_actions: ["read approved project context", "report status", "recommend next safe lane"],
          draft_prompt: buildPhoneSafeProjectPacket(projectView, projectRequest, snapshot?.workspaceStatus ?? {}, compactRunSettings),
          expected_report_format: ["preflight", "recommendation", "risks", "next lane", "safety confirmation"],
          forbidden_actions: ["dispatch", "run tools", "queue mutation", "Waha mutation", "model routing", "automatic send"],
          objective: projectRequest.trim(),
          project_id: projectView.project.project_id,
          stop_conditions: ["workspace-status preflight fails", "request requires approval"],
          title: compactText(projectView.challengeReview?.suggested_lane_title || projectRequest, 120) || "Read-only project room request",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Saved read-only lane draft. It remains inert until separately approved.");
    } catch (err) {
      setRoomMessage(jennyChatErrorMessage(err));
    } finally {
      setRoomBusy(false);
    }
  }

  function updateReportField(field: keyof ReportFormState, value: string) {
    setReportForm(current => ({ ...current, [field]: value }));
  }

  async function saveManualReport() {
    if (!reportForm.projectId || !reportForm.summary.trim()) {
      setReportMessage("Choose a project and enter a report summary before saving.");
      return;
    }
    setSavingReport(true);
    setReportMessage("");
    try {
      await fetchJSON(WORKSPACE_REPORTS_CREATE_URL, {
        body: JSON.stringify({
          artifact_links: lineList(reportForm.artifactLinks),
          changed_files: lineList(reportForm.changedFiles),
          next_recommended_lane: reportForm.nextRecommendedLane.trim() || undefined,
          project_id: reportForm.projectId,
          result: reportForm.result.trim() || undefined,
          risks: lineList(reportForm.risks),
          summary: reportForm.summary.trim(),
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      const nextSnapshot = await loadCompactSnapshot();
      setSnapshot(nextSnapshot);
      setReportForm({ ...EMPTY_REPORT_FORM, projectId: reportForm.projectId });
      setReportMessage("Jenny report saved manually. Direct session send remains disabled.");
    } catch (err) {
      setReportMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingReport(false);
    }
  }

  return (
    <main className="box-border flex min-h-full w-full min-w-0 max-w-full touch-pan-y flex-col overflow-visible overflow-x-clip overscroll-x-none bg-[#0e0b12] px-0 py-0 pb-[max(env(safe-area-inset-bottom),0.75rem)] text-[#f7efe4] [overflow-wrap:anywhere] [word-break:break-word] sm:h-full sm:max-h-full sm:min-h-0 sm:flex-1 sm:overflow-hidden sm:px-3 sm:py-1 [&_*]:box-border" data-testid="mission-control-compact-route">
      <header className="sr-only">
        <p className="sr-only max-w-full text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#a89782] [overflow-wrap:anywhere]">
          <span className="font-serif text-lg italic text-[#d4a574]">IV.</span>
          <span className="ml-2">Agent · Jenny</span>
        </p>
        <div className="mt-2 grid min-w-0 gap-2 sm:flex sm:items-start sm:justify-between">
          <div className="min-w-0 max-w-full">
            <h1 className="max-w-full text-xl font-semibold leading-tight text-[#fff8ed] [overflow-wrap:anywhere]">Jenny</h1>
            <p className="sr-only max-w-full text-xs text-[#a89782] [overflow-wrap:anywhere]">Pick a project and chat. Guardrails stay in the background.</p>
            <p className="sr-only">Chat with Jenny first; safety and project records stay collapsed below.</p>
          </div>
          <span className="sr-only max-w-full rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-emerald-300 [overflow-wrap:anywhere]">
            guarded
          </span>
        </div>
        <div className="sr-only mt-3 hidden min-w-0 max-w-full gap-2 pb-1 sm:flex sm:flex-wrap">
          {["Chat", "Talk", "Studio", "Sessions", "Workspace", "MCPs", "Control"].map((tab, index) => (
            <span
              className={cn(
                "min-w-0 truncate rounded-full border px-3 py-1.5 text-center text-xs",
                index === 0 ? "border-blue-400/60 bg-blue-500/10 text-blue-200" : "border-[#f7efe4]/10 bg-[#15101a]/60 text-[#c9b8a2]",
              )}
              key={tab}
            >
              {tab}
            </span>
          ))}
        </div>
      </header>

      {loading ? <p className="mt-4 rounded-xl border border-border/70 p-3 text-sm text-muted-foreground">Loading compact Mission Control...</p> : null}
      {error ? <p className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p> : null}

      {updateNotice ? (
        <p className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200">
          {updateNotice}
        </p>
      ) : null}

      {selectedProjectView ? (
        <div className="block w-full min-w-0 max-w-full overflow-visible overflow-x-clip sm:flex sm:flex-1 sm:min-h-0 sm:overflow-hidden">
          <div className="min-w-0 max-w-full overflow-visible sm:flex-1 sm:min-h-0 sm:overflow-hidden">
            <CompactProjectRoom
              busy={roomBusy}
              message={roomMessage}
              bridgeRequests={snapshot?.jennyBridgeRequests.filter(request => request.project_id === selectedProjectView.project.project_id) ?? []}
              bridgeResponses={snapshot?.jennyBridgeResponses.filter(response => response.project_id === selectedProjectView.project.project_id) ?? []}
              bridgeStatus={snapshot?.jennyBridgePollerStatus ?? {}}
              githubBridgeMessages={uniqueGitHubBridgeMessages([
                ...unwrapRecords(snapshot?.githubBridgeStatus.visible_pending_messages),
                ...unwrapRecords(snapshot?.githubBridgeStatus.pending_messages),
                ...unwrapRecords(snapshot?.githubBridgeStatus.recent_messages),
                ...unwrapRecords(snapshot?.githubBridgeStatus.response_messages),
              ]).filter(message => message.project_id === selectedProjectView.project.project_id)}
              githubBridgeStatus={snapshot?.githubBridgeStatus ?? {}}
              jennyRunElapsedSeconds={jennyRunElapsedSeconds}
              jennyRunProgress={jennyRunProgress}
              memoryStorage={snapshot?.memoryStorage ?? {}}
              modelChoices={modelChoices}
              modelChoice={currentModelChoice}
              modelLabel={compactModelLabel(modelInfo)}
              onEffortChange={setSelectedEffort}
              replyReviews={snapshot?.jennyReplyReviews.filter(review => review.project_id === selectedProjectView.project.project_id) ?? []}
              onCopyPacket={() => void copyPhoneSafePacket(selectedProjectView)}
              onModelChoiceChange={setSelectedModelChoice}
              onQueueBridge={() => void queueJennyBridgeMessage(selectedProjectView)}
              onQueueHermesUpdate={selectedProjectView.project.project_id === HERMES_PROJECT_ID ? () => void queueHermesUpdateLane(selectedProjectView) : undefined}
              onQueueStorageCleanup={selectedProjectView.project.project_id === HERMES_PROJECT_ID ? () => void queueHermesStorageCleanupLane(selectedProjectView) : undefined}
              onRefreshBridge={() => void refreshBridge()}
              onRequestChange={setProjectRequest}
              onReviewReply={(decision, responseId, reply) => void reviewJennyReply(selectedProjectView, decision, responseId, reply)}
              onRunJennyOnce={() => void runJennyOnce(selectedProjectView)}
              onSaveChallenge={() => void saveChallengeDraft(selectedProjectView)}
              onSaveLane={() => void saveReadOnlyLaneDraft(selectedProjectView)}
              onOpenSession={session => {
                if (session.session_id) {
                  navigate(compactSessionRoute(session.session_id));
                }
              }}
              onSelectProject={projectId => {
                setSelectedProjectId(projectId);
                setRoomMessage("");
              }}
              packet={buildPhoneSafeProjectPacket(selectedProjectView, projectRequest, snapshot?.workspaceStatus ?? {}, compactRunSettings)}
              paused={!ACTIVE_OS_PROJECT_IDS.includes(selectedProjectView.project.project_id)}
              projectRequest={projectRequest}
              projects={projectRoomProjects}
              runEffort={selectedEffort}
              runSettingsLabel={compactRunSettingsLabel(compactRunSettings)}
              selectedProjectView={selectedProjectView}
              workspaceStatus={snapshot?.workspaceStatus ?? {}}
            />
          </div>
          <div className="sr-only order-2 min-w-0 max-w-full overflow-hidden">
            <CompactLiveActivityRail
              bridgeStatus={snapshot?.jennyBridgePollerStatus ?? {}}
              githubBridgeStatus={snapshot?.githubBridgeStatus ?? {}}
              jennyRunElapsedSeconds={jennyRunElapsedSeconds}
              jennyRunProgress={jennyRunProgress}
            />
          </div>
        </div>
      ) : null}

      <details className="hidden mt-3 max-w-full overflow-hidden rounded-xl border border-border/60 bg-card/70 p-3 sm:block">
        <summary className="cursor-pointer text-sm font-semibold text-muted-foreground">Safety details</summary>
        <div className="mt-3 grid gap-4">
          {snapshot ? (
            <CompactHermesHealthDashboard
              activeProjectViews={activeProjects.map(project => viewModelForProject(snapshot, project))}
              pausedProjects={pausedProjects}
              snapshot={snapshot}
            />
          ) : null}

          <CompactKanbanParkedCard />

          {snapshot ? (
            <details className="rounded-2xl border border-border/70 bg-background p-3">
              <summary className="cursor-pointer text-sm font-semibold">Advanced diagnostic records</summary>
              <div className="mt-3 grid gap-3">
                <SafetyStrip status={snapshot.workspaceStatus} />

                <CompactActiveLanes
                  projectViews={activeProjects.map(project => viewModelForProject(snapshot, project))}
                  status={snapshot.workspaceStatus}
                />

                <details className="rounded-2xl border border-border/70 bg-card p-3">
                  <summary className="cursor-pointer text-sm font-semibold">Manual record repair</summary>
                  <CompactReportIngestion
                    form={reportForm}
                    message={reportMessage}
                    onChange={updateReportField}
                    onSave={() => void saveManualReport()}
                    projects={realProjects}
                    saving={savingReport}
                  />
                </details>
              </div>
            </details>
          ) : null}

      <section className="mt-4 grid max-w-full gap-3 overflow-hidden" aria-label="Project report archive">
        {snapshot && realProjects.length !== 5 ? (
          <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
            {realProjects.length} of 5 real projects loaded. Check backend project records before using this as the daily workspace.
          </p>
        ) : null}
        {snapshot
          ? realProjects.map(project => {
              const projectView = viewModelForProject(snapshot, project);
              return <CompactProjectCard copied={copiedProjectId === project.project_id} key={project.project_id} onCopy={() => void copyPrompt(projectView)} projectView={projectView} />;
            })
          : null}
      </section>

      {supportProjects.length ? (
        <section className="rounded-xl border border-dashed border-border/70 bg-muted/20 p-3 opacity-70" aria-label="Smoke support projects de-emphasized">
          <h2 className="text-sm font-semibold">Smoke/support records de-emphasized</h2>
          <div className="mt-2 grid gap-2">
            {supportProjects.map(project => (
              <p className="rounded-lg border border-border/60 bg-background/50 p-2 text-xs text-muted-foreground" key={project.project_id || project.name}>
                {project.name} - support only
              </p>
            ))}
          </div>
        </section>
      ) : null}
      {pausedProjects.length ? (
        <section className="rounded-xl border border-dashed border-border/70 bg-muted/20 p-3" aria-label="Paused projects">
          <h2 className="text-sm font-semibold">Projects on hold</h2>
          <p className="mt-1 text-xs text-muted-foreground">Visible for audit context only while Jenny/Mission Control is the active OS lane.</p>
          <div className="mt-2 grid gap-2">
            {pausedProjects.map(project => (
              <div className="rounded-lg border border-border/60 bg-background/50 p-2 text-xs text-muted-foreground" key={project.project_id || project.name}>
                <div className="font-medium text-foreground/80">{project.name}</div>
                <p className="mt-1">On hold. No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}
        </div>
      </details>
    </main>
  );
}

function compactActiveLaneStage(projectView: ProjectViewModel): string {
  if (!projectView.projectBrief) {
    return "needs brief";
  }
  if (!projectView.challengeReview) {
    return "needs challenge";
  }
  if (projectView.challengeReview.decision_state !== "clear_and_safe") {
    return `challenge: ${projectView.challengeReview.decision_state ?? "unknown"}`;
  }
  if (!projectView.latestLaneRequest) {
    return "ready for lane draft";
  }
  return projectView.latestLaneRequest.status ? `${projectView.latestLaneRequest.status} lane` : "lane drafted";
}

function CompactActiveLanes({ projectViews, status }: { projectViews: ProjectViewModel[]; status: WorkspaceStatus }) {
  return (
    <section className="mt-4 max-w-full overflow-hidden rounded-2xl border border-border/70 bg-card p-3" aria-label="Active Jenny OS lane compact">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">Active Jenny OS Lane</h2>
          <p className="mt-1 max-w-full text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Mission Control/Jenny stability lane only. Display-only; no dispatch, queue mutation, worker, or timer.</p>
        </div>
        <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-[0.65rem] font-semibold text-sky-700 dark:text-sky-300">
          display-only
        </span>
      </div>
      <div className="mt-3 grid gap-2">
        {projectViews.map(projectView => (
          <article className="max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2 text-xs" key={projectView.project.project_id}>
            <div className="flex min-w-0 items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="font-semibold leading-tight">{projectView.project.name}</h3>
                <p className="mt-1 max-w-full text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">{projectView.status}</p>
              </div>
              <span className="max-w-[45%] shrink-0 rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground [overflow-wrap:anywhere]">{compactActiveLaneStage(projectView)}</span>
            </div>
            <CompactField label="next safe lane" value={projectView.nextLane} />
            <CompactField label="latest evidence" value={projectView.latestReport} />
            <CompactField label="report contract" value={projectView.reportContract} />
            <CompactField label="readiness" value={projectView.readinessDetail} />
          </article>
        ))}
      </div>
      <p className="mt-3 max-w-full text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Safety status: {safetySummary(status)}</p>
    </section>
  );
}

function CompactPausedProjectResumeChecklist() {
  const requirements = [
    "Project brief is current",
    "Jenny challenge review clears the approach",
    "Allowed and forbidden actions are explicit",
    "Travis approval is recorded before work resumes",
  ];

  return (
    <section className="mt-3 max-w-full overflow-hidden rounded-2xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
      <h3 className="font-semibold text-amber-800 dark:text-amber-200">Resume requirements</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        This project is on hold. Jenny cannot receive work here until these checks are true.
      </p>
      <ul className="mt-3 grid gap-2 text-xs text-muted-foreground">
        {requirements.map(requirement => (
          <li className="rounded-xl border border-amber-500/20 bg-background px-3 py-2 [overflow-wrap:anywhere]" key={requirement}>
            {requirement}
          </li>
        ))}
      </ul>
    </section>
  );
}

function CompactLiveActivityRail({
  bridgeStatus,
  githubBridgeStatus,
  jennyRunElapsedSeconds,
  jennyRunProgress,
}: {
  bridgeStatus: JennyBridgePollerStatus;
  githubBridgeStatus: GitHubBridgeStatus;
  jennyRunElapsedSeconds: number;
  jennyRunProgress: JennyRunProgress | null;
}) {
  const activityItems = jennyActivityItems(githubBridgeStatus);
  const hasError = Boolean(normalizedBridgeError(bridgeStatus, githubBridgeStatus));
  const runActive = isJennyRunActive(jennyRunProgress);
  const runCopy = jennyRunProgressCopy(jennyRunProgress, jennyRunElapsedSeconds);
  const visiblePendingCount = githubBridgeStatus.visible_pending_count ?? githubBridgeStatus.pending_count ?? 0;
  const liveLabel = runActive ? "Jenny is working" : jennyRunProgress?.phase === "complete" ? "Last reply complete" : hasError ? "Needs attention" : githubBridgeStatus.last_status === "hermes_answer_completed" ? "Last reply complete" : "Standing by";

  return (
    <details className="w-full max-w-full overflow-hidden rounded-2xl border border-[#f7efe4]/10 bg-[#1b1422]/80 p-3 shadow-[0_20px_70px_rgba(0,0,0,0.32)]">
      <summary className="cursor-pointer list-none">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#a89782]">Latest Jenny activity</div>
            <h2 className="mt-1 text-base font-semibold text-[#fff8ed] [overflow-wrap:anywhere] sm:text-lg">{liveLabel}</h2>
          </div>
          <span
            className={cn(
              "mt-1 h-3 w-3 shrink-0 rounded-full",
              runActive ? "bg-blue-400 shadow-[0_0_24px_rgba(96,165,250,0.85)]" : hasError || jennyRunProgress?.phase === "error" ? "bg-red-400" : "bg-emerald-400",
            )}
          />
        </div>
      </summary>

      <div className="mt-3">
      <div className="grid min-w-0 max-w-full gap-2 overflow-hidden text-xs">
        <CompactField label="bridge" value={bridgeStatus.last_status || "idle"} />
        <CompactField label="mailbox" value={githubBridgeStatus.mode || "manual"} />
        <CompactField label="pending" value={String(visiblePendingCount)} />
        <CompactField label="last response" value={githubBridgeStatus.last_response_request_id || githubBridgeStatus.last_response_at || "none"} />
      </div>

      <div className="mt-4 border-t border-[#f7efe4]/10 pt-3">
        <div className="mb-2 text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#a89782]">Jenny stream</div>
        <div className="grid gap-2">
          {jennyRunProgress ? (
            <p className="rounded-xl border border-blue-400/30 bg-blue-500/10 p-2 text-xs text-blue-100 [overflow-wrap:anywhere]">
              <span className="block font-semibold">{runCopy.label}</span>
              <span className="mt-1 block leading-relaxed">{runCopy.detail}</span>
            </p>
          ) : null}
          {activityItems.length ? (
            activityItems.map(item => (
              <article className="min-w-0 max-w-full overflow-hidden rounded-xl border border-[#f7efe4]/10 bg-[#100b15]/80 p-2 text-xs" key={item.status_id ?? `${item.status}:${item.created_at}`}>
                <div className="grid min-w-0 max-w-full gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
                  <span className="min-w-0 font-semibold text-[#fff8ed] [overflow-wrap:anywhere]">{jennyActivityLabel(item.status)}</span>
                  <span className="min-w-0 max-w-full text-[#a89782] [overflow-wrap:anywhere] [word-break:break-all] sm:text-right">{item.created_at || "time unknown"}</span>
                </div>
                <p className="mt-1 max-w-full leading-relaxed text-[#c9b8a2] [overflow-wrap:anywhere] [word-break:break-word]">{jennyActivityDetail(item)}</p>
              </article>
            ))
          ) : (
            <p className="rounded-xl border border-dashed border-[#f7efe4]/10 p-2 text-xs text-[#a89782]">No live activity records yet.</p>
          )}
        </div>
      </div>
      </div>
    </details>
  );
}

function CompactProjectRoom({
  busy,
  bridgeRequests,
  bridgeResponses,
  bridgeStatus,
  githubBridgeStatus,
  githubBridgeMessages,
  jennyRunElapsedSeconds,
  jennyRunProgress,
  memoryStorage,
  message,
  modelChoices,
  modelChoice,
  modelLabel,
  onCopyPacket,
  onEffortChange,
  onModelChoiceChange,
  onQueueBridge,
  onQueueHermesUpdate,
  onQueueStorageCleanup,
  onOpenSession,
  onRefreshBridge,
  onReviewReply,
  onRequestChange,
  onRunJennyOnce,
  onSaveChallenge,
  onSaveLane,
  onSelectProject,
  packet,
  paused,
  projectRequest,
  projects,
  replyReviews,
  runEffort,
  runSettingsLabel,
  selectedProjectView,
  workspaceStatus,
}: {
  busy: boolean;
  bridgeRequests: JennyBridgeRequestRecord[];
  bridgeResponses: JennyBridgeResponseRecord[];
  bridgeStatus: JennyBridgePollerStatus;
  githubBridgeStatus: GitHubBridgeStatus;
  githubBridgeMessages: GitHubBridgeMessageRecord[];
  jennyRunElapsedSeconds: number;
  jennyRunProgress: JennyRunProgress | null;
  memoryStorage: ProfileMemoryStorage;
  message: string;
  modelChoices: Array<{ key: string; label: string }>;
  modelChoice: string;
  modelLabel: string;
  onCopyPacket: () => void;
  onEffortChange: (value: string) => void;
  onModelChoiceChange: (value: string) => void;
  onQueueBridge: () => void;
  onQueueHermesUpdate?: () => void;
  onQueueStorageCleanup?: () => void;
  onOpenSession: (session: ProjectSessionRecord) => void;
  onRefreshBridge: () => void;
  onReviewReply: (decision: JennyReplyReviewDecision, responseId: string, reply: string) => void;
  onRequestChange: (value: string) => void;
  onRunJennyOnce: () => void;
  onSaveChallenge: () => void;
  onSaveLane: () => void;
  onSelectProject: (projectId: string) => void;
  packet: string;
  paused: boolean;
  projectRequest: string;
  projects: ProjectRecord[];
  replyReviews: JennyReplyReviewRecord[];
  runEffort: string;
  runSettingsLabel: string;
  selectedProjectView: ProjectViewModel;
  workspaceStatus: WorkspaceStatus;
}) {
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const sessions = selectedProjectView.projectState?.recent_sessions ?? [];
  const review = selectedProjectView.challengeReview;
  const brief = selectedProjectView.projectBrief;
  const visibleBridgeRequests = bridgeRequests.filter(request => !isDiagnosticChatMessage(request.message));
  const visibleBridgeResponses = bridgeResponses.filter(response => !isDiagnosticChatMessage(response.message));
  const visibleGitHubBridgeMessages = githubBridgeMessages.filter(message => !isDiagnosticChatMessage(message.message) && !isOperatorBridgeMessage(message));
  const latestReplyAt = latestJennyReplyTimestamp(visibleBridgeResponses, visibleGitHubBridgeMessages);
  const currentPendingBridgeRequests = visibleBridgeRequests.filter(request => isCurrentAfterReply(request.created_at, latestReplyAt));
  const currentPendingGitHubBridgeMessages = visibleGitHubBridgeMessages.filter(message => isCurrentAfterReply(message.created_at, latestReplyAt));
  const repliedRequestIds = new Set(visibleBridgeResponses.map(response => response.request_id).filter(Boolean));
  const githubResponseIds = new Set(
    visibleGitHubBridgeMessages
      .filter(message => message.from_agent === "jenny")
      .map(message => message.request_id)
      .filter(Boolean),
  );
  const githubPendingCount = currentPendingGitHubBridgeMessages.filter(message =>
    message.to_agent === "jenny" &&
    ["queued", "retry_requested"].includes(message.status ?? "") &&
    !githubResponseIds.has(message.request_id),
  ).length;
  const latestPending = latestPendingGitHubBridgeMessage(currentPendingGitHubBridgeMessages);
  const projectedVisiblePending = latestVisiblePendingGitHubBridgeMessageForProject(
    unwrapRecords(githubBridgeStatus.visible_pending_messages),
    selectedProjectView.project.project_id,
  );
  const githubResponseCount = visibleGitHubBridgeMessages.filter(message => message.from_agent === "jenny").length;
  const pendingCount = pendingJennyMessageCount(currentPendingBridgeRequests, visibleBridgeResponses) + githubPendingCount;
  const responseCount = visibleBridgeResponses.length + githubResponseCount;
  const deliveryStatus = jennyDeliveryStatus(pendingCount, responseCount, bridgeStatus, githubBridgeStatus);
  const connectionState = jennyConnectionState(pendingCount, responseCount, bridgeStatus, githubBridgeStatus);
  const bridgeNextStep = jennyNextStep(pendingCount, responseCount, Boolean(projectedVisiblePending ?? latestPending), bridgeStatus, githubBridgeStatus);
  const activityItems = jennyActivityItems(githubBridgeStatus);
  const requestIntake = assessProjectRequest(projectRequest, review);
  const specFirstComposerText = buildSpecFirstComposerText(selectedProjectView.project.name, projectRequest, requestIntake);
  const sendButtonLabel = jennySendButtonLabel();
  const latestReviewByResponseId = latestReplyReviewByResponseId(replyReviews);
  const bridgeError = normalizedBridgeError(bridgeStatus, githubBridgeStatus);
  const githubBridgeSafety = compactGitHubBridgeSafety(githubBridgeStatus, workspaceStatus);
  const bridgeActionDisabled = busy || paused || !githubBridgeSafety.safe;
  const hasRunnablePendingMessage = Boolean(projectedVisiblePending ?? latestPending);
  const canRunForegroundReply = !paused && githubBridgeSafety.safe && (hasRunnablePendingMessage || pendingCount > 0);
  const statusRecords = unwrapRecords(githubBridgeStatus.status_records);
  const statusSourceBridgeMessages = [
    ...visibleGitHubBridgeMessages,
    ...unwrapRecords(githubBridgeStatus.visible_pending_messages),
    ...unwrapRecords(githubBridgeStatus.pending_messages),
    ...unwrapRecords(githubBridgeStatus.recent_messages),
    ...unwrapRecords(githubBridgeStatus.response_messages),
  ];
  const chatMessages: ProjectChatMessage[] = [
    ...visibleBridgeRequests.map(request => ({
      body: request.message,
      displayBody: cleanChatDisplayMessage(request.metadata, request.message, 750),
      id: request.request_id || request.ack_key || request.created_at || "bridge-request",
      meta: chatStatusLabel(request.bridge_state ?? (request.request_id && repliedRequestIds.has(request.request_id) ? "replied" : request.status ?? "queued")),
      speaker: "You" as const,
      time: request.created_at,
    })),
    ...visibleBridgeResponses.map(response => ({
      body: response.message,
      id: response.response_id || response.request_id || response.created_at || "bridge-response",
      meta: chatStatusLabel(response.status ?? "reply"),
      speaker: "Jenny" as const,
      time: response.created_at,
    })),
    ...visibleGitHubBridgeMessages.map(message => ({
      body: message.message,
      displayBody: message.from_agent === "jenny" ? undefined : cleanChatDisplayMessage(message.metadata, message.message, 750),
      id: message.github_comment_id || message.request_id || message.created_at || "github-message",
      meta: chatStatusLabel(message.status),
      speaker: message.from_agent === "jenny" ? "Jenny" as const : "You" as const,
      time: message.created_at,
    })),
  ].sort((left, right) => String(left.time ?? "").localeCompare(String(right.time ?? ""))).slice(-8);
  const effectiveJennyRunProgress = jennyRunProgress ?? recordBackedJennyRunProgress(statusRecords, statusSourceBridgeMessages, selectedProjectView.project.project_id);
  const runActive = isJennyRunActive(effectiveJennyRunProgress);
  const runCopy = jennyRunProgressCopy(effectiveJennyRunProgress, jennyRunElapsedSeconds);
  const latestReplyReview = latestReviewedJennyReply(chatMessages, latestReviewByResponseId);
  const replyReviewStatus = jennyReplyReviewStatus(latestReplyReview);
  const latestActualJennyReply = latestJennyReply(chatMessages);
  const latestActualReplyReview = latestActualJennyReply ? latestReviewByResponseId.get(latestActualJennyReply.id) ?? null : null;
  const showJennyStatusInChat = Boolean(effectiveJennyRunProgress && (
    runActive ||
    effectiveJennyRunProgress.phase === "queued" ||
    effectiveJennyRunProgress.phase === "error" ||
    (effectiveJennyRunProgress.phase === "complete" && !latestActualJennyReply)
  ));
  const latestJennyOutcome = latestJennyOutcomeStatus(latestActualJennyReply, latestActualReplyReview);
  const reviewRequired = Boolean(latestActualJennyReply && !latestActualReplyReview);
  const nextStep = replyReviewStatus.nextStep ?? bridgeNextStep;
  const statusCopy = effectiveJennyRunProgress
    ? runCopy
    : { detail: paused ? "This project is paused until Jenny is stable." : nextStep, label: connectionState.label };
  const latestUserMessage = [...chatMessages].reverse().find(chat => chat.speaker === "You");
  const liveStatusItems = jennyLiveStatusItems({
    elapsedSeconds: jennyRunElapsedSeconds,
    latestUserMessage: latestUserMessage ? projectRequestPreview(latestUserMessage.displayBody ?? latestUserMessage.body, 72) : "",
    pendingCount,
    progress: effectiveJennyRunProgress,
    responseCount,
    statusLabel: statusCopy.label,
  });
  const workSessionSteps = jennyWorkSessionSteps({
    hasError: Boolean(bridgeError),
    hasRunnablePendingMessage,
    pendingCount,
    progress: effectiveJennyRunProgress,
    replyReviewTone: replyReviewStatus.tone,
    responseCount,
  });
  useEffect(() => {
    if (typeof window !== "undefined" && !window.matchMedia("(min-width: 640px)").matches) {
      return;
    }
    chatEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [
    chatMessages.length,
    effectiveJennyRunProgress?.phase,
    selectedProjectView.project.project_id,
  ]);
  const operatorGuidance = jennyOperatorGuidance({
    bridgeError,
    hasRunnablePendingMessage,
    pendingCount,
    progress: effectiveJennyRunProgress,
    replyReviewTone: replyReviewStatus.tone,
    responseCount,
  });
  return (
    <section
      className="flex min-h-0 w-full min-w-0 max-w-full flex-col overflow-visible overflow-x-clip rounded-none border-0 border-[#d4a574]/10 bg-[#15101a] sm:h-full sm:overflow-hidden sm:rounded-md sm:border"
      aria-label="Project chat workspace"
    >
      <div className="w-full min-w-0 max-w-full shrink-0 overflow-hidden overflow-x-clip border-b border-[#f3ebda]/10 bg-[#15101a] px-2 py-2">
        <label className="grid w-full min-w-0 max-w-xl gap-1">
          <span className="sr-only">Active project</span>
          <select
            className="w-full min-w-0 max-w-full truncate rounded-md border border-[#f3ebda]/10 bg-[#100b15] px-3 py-2 text-sm font-semibold text-[#f3ebda] outline-none [overflow-wrap:anywhere] [word-break:break-word]"
            onChange={event => onSelectProject(event.target.value)}
            value={selectedProjectView.project.project_id}
          >
            {projects.map(project => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <div className="sr-only w-full min-w-0 max-w-full gap-1.5">
          <span className="sr-only">Local studio</span>
          <span className="hidden self-center text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-[#a59783] sm:block sm:pr-1">Projects</span>
          <span className="sr-only">{projects.length} projects</span>
          {projects.map(project => (
            <button
              className={cn(
                "min-w-0 max-w-full overflow-hidden rounded-full border px-3 py-1.5 text-left text-xs transition hover:border-[#d4a574]/30 hover:bg-[#251d2c]/70",
                project.project_id === selectedProjectView.project.project_id ? "border-[#d4a574]/50 bg-[#2e2436]/80" : "border-[#f3ebda]/10 bg-transparent",
              )}
              key={project.project_id}
              onClick={() => onSelectProject(project.project_id)}
              type="button"
            >
              <span className="block max-w-full truncate font-semibold text-[#f3ebda]">{project.name}</span>
              <span className="sr-only">
                {project.project_id === HERMES_PROJECT_ID ? "Active recovery lane" : "Paused until Jenny is stable"}
              </span>
            </button>
          ))}
        </div>
      </div>

      <article className="flex min-h-0 min-w-0 max-w-full flex-col overflow-visible overflow-x-clip px-2 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] pt-2 sm:min-h-0 sm:flex-1 sm:overflow-hidden" data-testid="compact-project-room">
        <div className="sr-only grid min-w-0 gap-2 border-b border-[#f3ebda]/10 pb-2 sm:flex sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2">
            <span className="sr-only">IV. — Jenny workspace</span>
            <h2 className="max-w-full text-lg font-semibold leading-tight text-[#f3ebda] [overflow-wrap:anywhere]">{selectedProjectView.project.name}</h2>
            <span className="sr-only hidden max-w-[30rem] truncate text-xs text-[#a59783] md:inline">{compactText(selectedProjectView.currentGoal, 120)}</span>
          </div>
          <div className="grid min-w-0 grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:flex sm:flex-wrap sm:justify-end">
            <span className={cn("max-w-full rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold [overflow-wrap:anywhere]", jennyStatusToneClass(connectionState.tone))}>
              {connectionState.label}
            </span>
            <span className={cn(
              "sr-only max-w-full rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold [overflow-wrap:anywhere]",
              paused
                ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
                : "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
            )}>
              {paused ? "Paused" : selectedProjectView.readinessLabel}
            </span>
            <span className={cn("sr-only max-w-full rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold [overflow-wrap:anywhere]", jennyReplyReviewStatusClass(replyReviewStatus.tone))}>
              {replyReviewStatus.label}
            </span>
          </div>
        </div>
        <section
          className="sr-only"
          aria-label="Jenny chat status"
        >
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <div className="min-w-0">
              <div className="font-semibold text-[#f3ebda] [overflow-wrap:anywhere]">{paused ? "Project paused" : statusCopy.label}</div>
              <p className="sr-only mt-0.5 max-w-full text-xs leading-snug opacity-85 [overflow-wrap:anywhere]">
                {paused ? "This project is on hold while Jenny is stabilized." : statusCopy.detail}
              </p>
            </div>
            <span>Pending {pendingCount}</span>
            <span>Replies {responseCount}</span>
            {runActive ? <span>Elapsed {jennyRunElapsedSeconds}s</span> : null}
          </div>
          <p className="sr-only mt-2 max-w-full text-xs leading-snug opacity-80 [overflow-wrap:anywhere]">Next: {paused ? "Resume this project after Jenny is stable." : nextStep}</p>
        </section>

        <details className="sr-only mt-1 max-w-full overflow-hidden rounded-md border border-[#f3ebda]/10 bg-[#1c1622]/50 px-3 py-1.5 text-xs">
          <summary className="cursor-pointer font-semibold text-muted-foreground">
            Room status
            <span className="sr-only">Next step</span>
          </summary>
            <div className="mt-2 grid min-w-0 gap-1 sm:flex sm:flex-wrap sm:items-center sm:gap-x-3 sm:gap-y-1">
              <span className="font-semibold text-[#f3ebda]">Goal</span>
              <span className="min-w-0 text-[#a59783] [overflow-wrap:anywhere] sm:flex-1 sm:truncate">{compactText(selectedProjectView.currentGoal, 180)}</span>
              <span className="font-semibold text-[#f3ebda]">Jenny:</span>
              <span className="text-[#a59783] [overflow-wrap:anywhere]">{deliveryStatus}. {connectionState.detail}</span>
              <span className="rounded-full border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-0.5 text-[#a59783]">Pending {pendingCount}</span>
              <span className="rounded-full border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-0.5 text-[#a59783]">Replies {responseCount}</span>
            </div>
            <p className="mt-2 max-w-full text-sm text-[#f3ebda] [overflow-wrap:anywhere]">
              {paused ? "Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project." : nextStep}
            </p>
            <div className="mt-2 grid gap-2 text-xs">
              <CompactField label="readiness" value={selectedProjectView.readinessDetail} />
              <CompactField label="reply review" value={replyReviewStatus.detail} />
              <CompactField label="last update" value={compactText(selectedProjectView.latestReport, 220)} />
              <CompactField label="report contract" value={selectedProjectView.reportContract} />
            </div>
        </details>

        <details className="sr-only mt-2 max-w-full overflow-hidden rounded-md border border-[#f3ebda]/10 bg-[#1c1622]/50 px-3 py-2 text-sm">
          <summary className="cursor-pointer text-[#f3ebda]">
            <span className="font-semibold">Next:</span> {latestJennyOutcome.label}. {latestJennyOutcome.nextStep}
          </summary>
        <section
          className={cn("mt-2 max-w-full rounded-md border px-3 py-2 text-sm", jennyRunStatusToneClass(effectiveJennyRunProgress, connectionState.tone))}
          aria-label="Jenny current status"
        >
          <div className="grid min-w-0 gap-2 sm:flex sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] opacity-75">Jenny status</div>
              <div className="mt-0.5 font-semibold">{statusCopy.label}</div>
            </div>
            <div className="flex min-w-0 flex-wrap gap-1.5 text-xs">
              <span className="rounded-full border border-current/20 px-2 py-0.5">Pending {pendingCount}</span>
              <span className="rounded-full border border-current/20 px-2 py-0.5">Replies {responseCount}</span>
              {runActive ? <span className="rounded-full border border-current/20 px-2 py-0.5">Elapsed {jennyRunElapsedSeconds}s</span> : null}
            </div>
          </div>
          <p className="mt-2 max-w-full text-sm leading-snug [overflow-wrap:anywhere]">{statusCopy.detail}</p>
          <div aria-label="Jenny operator guidance" className={cn("mt-2 max-w-full rounded-md border px-3 py-2 text-xs", jennyStatusToneClass(operatorGuidance.tone))}>
            <div className="font-semibold">{operatorGuidance.label}</div>
            <p className="mt-1 leading-snug [overflow-wrap:anywhere]">{operatorGuidance.detail}</p>
            <div className="mt-2 flex min-w-0 flex-wrap gap-1.5">
              <span className="rounded-full border border-current/20 px-2 py-0.5">one reply at a time</span>
              <span className="rounded-full border border-current/20 px-2 py-0.5">evidence required</span>
              <span className="rounded-full border border-current/20 px-2 py-0.5">no hidden execution</span>
            </div>
          </div>
          <div aria-label="Jenny live status" className="mt-2 grid min-w-0 gap-2 text-xs min-[420px]:grid-cols-2 sm:grid-cols-4">
            {liveStatusItems.map(item => (
              <div className="min-w-0 max-w-full overflow-hidden rounded-md border border-current/15 bg-black/10 px-2 py-1" key={item.label}>
                <div className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] opacity-70">{item.label}</div>
                <div className="mt-0.5 font-semibold [overflow-wrap:anywhere] [word-break:break-word]">{item.value}</div>
              </div>
            ))}
          </div>
          {bridgeError ? <p className="mt-2 max-w-full text-xs [overflow-wrap:anywhere]">Bridge error: {bridgeError}</p> : null}
        </section>

        <section
          className={cn("mt-2 max-w-full rounded-md border px-3 py-2 text-sm", jennyReplyReviewStatusClass(latestJennyOutcome.tone))}
          aria-label="Latest Jenny outcome"
        >
          <div className="grid min-w-0 gap-2 sm:flex sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] opacity-75">Latest Jenny outcome</div>
              <div className="mt-0.5 font-semibold [overflow-wrap:anywhere]">{latestJennyOutcome.label}</div>
            </div>
            <span className="max-w-full rounded-full border border-current/20 px-2 py-0.5 text-[0.68rem] [overflow-wrap:anywhere]">{latestJennyOutcome.reviewLabel}</span>
          </div>
          <p className="mt-2 max-w-full leading-snug [overflow-wrap:anywhere]">{latestJennyOutcome.detail}</p>
          <p className="mt-1 max-w-full text-xs leading-snug opacity-85 [overflow-wrap:anywhere]">Next: {latestJennyOutcome.nextStep}</p>
        </section>

        <JennyWorkSessionTimeline steps={workSessionSteps} />
        </details>

        <details className="sr-only mt-2 min-w-0 max-w-full overflow-hidden rounded-md border border-[#60a5fa]/25 bg-[#60a5fa]/10 px-3 py-2" aria-label="Jenny activity">
          <summary className="cursor-pointer text-sm font-semibold text-[#f3ebda]">Jenny activity</summary>
          <div className="sr-only grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
            <h3 className="sr-only">Jenny activity</h3>
            <span className="text-[0.68rem] text-[#a59783] [overflow-wrap:anywhere] sm:text-right">
              {runActive ? "refreshing every 2.5s" : "recent bridge status"}
            </span>
          </div>
          <div className="mt-2 grid min-w-0 gap-2">
            {runActive ? (
              <p className="rounded-xl border border-[#60a5fa]/20 bg-[#15101a]/70 p-2 text-xs text-[#93c5fd] [overflow-wrap:anywhere]">
                {runCopy.label}: {runCopy.detail}
              </p>
            ) : null}
            {activityItems.length ? (
              activityItems.map(item => (
                <article className="rounded-xl border border-[#60a5fa]/20 bg-[#15101a]/70 p-2 text-xs" key={item.status_id ?? `${item.status}:${item.created_at}`}>
                  <div className="grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
                    <span className="font-semibold text-[#f3ebda] [overflow-wrap:anywhere]">{jennyActivityLabel(item.status)}</span>
                    <span className="min-w-0 text-[#a59783] [overflow-wrap:anywhere] [word-break:break-all] sm:text-right">{item.created_at || "time unknown"}</span>
                  </div>
                  <p className="mt-1 text-[#a59783] [overflow-wrap:anywhere]">{jennyActivityDetail(item)}</p>
                </article>
              ))
            ) : (
              <p className="rounded-xl border border-dashed border-[#60a5fa]/20 p-2 text-xs text-[#a59783] [overflow-wrap:anywhere]">
                No Jenny activity records yet.
              </p>
            )}
          </div>
        </details>

        <section className="order-3 mt-2 flex min-w-0 max-w-full touch-pan-y flex-none flex-col overflow-visible overflow-x-clip p-0 sm:order-none sm:min-h-0 sm:flex-1 sm:overflow-hidden" aria-label="Project chat transcript">
          <div className="sr-only">
            <h3 className="text-sm font-semibold text-[#f3ebda]">Conversation</h3>
            <span className="text-[0.68rem] text-[#a59783] [overflow-wrap:anywhere] sm:text-right">{chatMessages.length ? `${chatMessages.length} recent messages` : "No messages yet"}</span>
          </div>
          <div className="mt-2 grid min-w-0 max-w-full auto-rows-max content-start gap-2 overflow-visible overflow-x-hidden overscroll-contain pb-4 pr-1 sm:min-h-0 sm:flex-1 sm:content-end sm:overflow-y-auto sm:pb-3 sm:scroll-pb-6 [-webkit-overflow-scrolling:touch]" data-testid="compact-chat-scroll">
            {chatMessages.length ? (
              chatMessages.map(chat => {
                const replyReview = latestReviewByResponseId.get(chat.id)
                const isLatestJennyReply = chat.speaker === "Jenny" && latestActualJennyReply?.id === chat.id
                const showLatestReplyActions = isLatestJennyReply && !replyReview

                return (
                <article
                  className={cn(
                    "min-w-0 w-full max-w-full rounded-lg border px-3 py-2 text-sm [overflow-wrap:anywhere] [word-break:break-word] sm:w-fit sm:max-w-[88%]",
                    chat.speaker === "You" ? "justify-self-end border-[#5ab896]/30 bg-[#5ab896]/10 text-[#f3ebda]" : "justify-self-start border-[#f3ebda]/10 bg-[#1c1622]/90 text-[#f3ebda]",
                  )}
                  key={`${chat.speaker}:${chat.id}`}
                >
                  <div className="mb-1 grid min-w-0 gap-1 text-[0.68rem] sm:flex sm:items-center sm:justify-between sm:gap-3">
                    <span className="font-semibold">{chat.speaker}</span>
                    <span className="min-w-0 text-[#a59783] [overflow-wrap:anywhere] sm:text-right">{chat.meta}</span>
                  </div>
                  <p
                    className={cn(
                      "max-w-full whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]",
                      chat.speaker === "Jenny"
                        ? "overflow-visible pr-0 sm:max-h-[min(52dvh,32rem)] sm:touch-pan-y sm:overflow-y-auto sm:overscroll-contain sm:pr-1 sm:[-webkit-overflow-scrolling:touch]"
                        : "overflow-visible",
                    )}
                    data-testid={chat.speaker === "Jenny" ? "compact-jenny-reply-body" : undefined}
                  >
                    {chat.speaker === "You" ? chat.displayBody ?? projectRequestPreview(chat.body, 750) : ownerVisibleJennyReply(chat.body)}
                  </p>
                  {chat.speaker === "Jenny" ? (
                    <details className="mt-2 min-w-0 overflow-visible border-t border-[#f3ebda]/10 pt-2 text-[0.68rem]">
                      <summary className="cursor-pointer list-none font-semibold text-[#a59783] [overflow-wrap:anywhere] marker:hidden">
                        Review reply
                      </summary>
                      <div className="mt-2 grid min-w-0 gap-2">
                        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                          <span className={cn(
                            "rounded-full border px-2 py-1 font-semibold [overflow-wrap:anywhere]",
                            jennyReplyContract(chat.body).tone === "complete"
                              ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200"
                              : "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-100",
                          )}>
                            {jennyReplyContract(chat.body).label}
                          </span>
                          {replyReview ? (
                            <span className="rounded-full border border-[#f3ebda]/10 bg-[#15101a]/60 px-2 py-1 text-[#a59783] [overflow-wrap:anywhere]">
                              {jennyReplyReviewDecisionLabel(replyReview.decision)}
                            </span>
                          ) : null}
                        </div>
                        <pre className="max-h-48 min-w-0 max-w-full overflow-auto whitespace-pre-wrap rounded-md border border-[#f3ebda]/10 bg-[#0e0b12]/80 p-2 font-mono text-[0.68rem] leading-snug text-[#a59783] [overflow-wrap:anywhere] [word-break:break-word]" data-testid="compact-jenny-raw-reply">
                          {chat.body}
                        </pre>
                        {showLatestReplyActions ? (
                          <div className="flex min-w-0 flex-wrap gap-1.5" aria-label="Review latest Jenny reply">
                            <button
                              className="rounded-full border border-emerald-500/30 px-2.5 py-1 font-semibold text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-300"
                              onClick={() => onReviewReply("accepted", chat.id, chat.body)}
                              type="button"
                            >
                              Looks good
                            </button>
                            <button
                              className="rounded-full border border-sky-500/30 px-2.5 py-1 font-semibold text-sky-700 hover:bg-sky-500/10 dark:text-sky-300"
                              onClick={() => onReviewReply("needs_evidence", chat.id, chat.body)}
                              type="button"
                            >
                              Ask for evidence
                            </button>
                            <button
                              className="rounded-full border border-amber-500/30 px-2.5 py-1 font-semibold text-amber-700 hover:bg-amber-500/10 dark:text-amber-300"
                              onClick={() => onReviewReply("needs_safer_plan", chat.id, chat.body)}
                              type="button"
                            >
                              Challenge
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </details>
                  ) : null}
                </article>
                )
              })
            ) : (
              <p className="rounded-xl border border-dashed border-[#f3ebda]/10 p-3 text-sm text-[#a59783] [overflow-wrap:anywhere]">
                Ask Jenny a bounded question or give her one safe next task below.
              </p>
            )}
            {showJennyStatusInChat ? (
              <article className={cn(
                "min-w-0 w-full max-w-full justify-self-start rounded-lg border px-3 py-2 text-sm text-[#f3ebda] [overflow-wrap:anywhere] [word-break:break-word] sm:w-fit sm:max-w-[88%]",
                effectiveJennyRunProgress?.phase === "error"
                  ? "border-red-500/30 bg-red-500/10"
                  : "border-sky-500/30 bg-sky-500/10",
              )}>
                <div className="mb-1 grid min-w-0 gap-1 text-[0.68rem] sm:flex sm:items-center sm:justify-between sm:gap-3">
                  <span className="font-semibold">Jenny</span>
                  <span className={cn(
                    "min-w-0 [overflow-wrap:anywhere] sm:text-right",
                    effectiveJennyRunProgress?.phase === "error" ? "text-red-200" : "text-sky-300",
                  )}>
                    {runCopy.label}
                  </span>
                </div>
                <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
                  {runCopy.detail}
                </p>
              </article>
            ) : null}
            <div ref={chatEndRef} />
          </div>
        </section>

        <div className="order-1 z-10 mt-2 mb-[max(env(safe-area-inset-bottom),1rem)] min-w-0 max-w-full shrink-0 overflow-hidden overflow-x-clip rounded-[1.5rem] border border-[#f3ebda]/10 bg-[#15101a]/95 p-2 pb-[max(env(safe-area-inset-bottom),0.5rem)] shadow-[0_-18px_40px_rgba(14,11,18,0.88)] backdrop-blur sm:order-none" aria-label="Project chat composer" data-testid="compact-chat-composer">
          {reviewRequired ? (
            <p className="mb-2 max-w-full text-xs font-semibold text-amber-700 [overflow-wrap:anywhere] dark:text-amber-100" role="status">
              Review the latest Jenny reply in the chat before acting on it.
            </p>
          ) : null}
          {!githubBridgeSafety.safe ? (
            <p className="mb-2 max-w-full rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-700 [overflow-wrap:anywhere] dark:text-red-200" role="status">
              {compactBridgeBlockedMessage(githubBridgeSafety)}
            </p>
          ) : null}
          <div className="mb-2 grid min-w-0 max-w-full grid-cols-2 gap-1.5 text-[0.68rem]" aria-label="Compact chat tools">
            <label className="min-w-0">
              <span className="mb-1 block font-semibold uppercase tracking-[0.14em] text-[#a59783]">Model</span>
              <select
                aria-label="Requested model"
                className="min-h-10 w-full min-w-0 max-w-full truncate rounded-full border border-[#f3ebda]/15 bg-[#0e0b12]/80 px-2 py-1 font-semibold text-[#c9b8a2] outline-none focus:border-[#d4a574]/50"
                disabled={!modelChoices.length}
                onChange={event => onModelChoiceChange(event.target.value)}
                value={modelChoice}
              >
                {modelChoices.length ? (
                  modelChoices.map(choice => (
                    <option key={choice.key} value={choice.key}>
                      {choice.label}
                    </option>
                  ))
                ) : (
                  <option value="">{modelLabel}</option>
                )}
              </select>
            </label>
            <label className="min-w-0">
              <span className="mb-1 block font-semibold uppercase tracking-[0.14em] text-[#a59783]">Effort</span>
              <select
                aria-label="Requested effort"
                className="min-h-10 w-full min-w-0 max-w-full rounded-full border border-[#f3ebda]/15 bg-[#0e0b12]/80 px-2 py-1 font-semibold text-[#c9b8a2] outline-none focus:border-[#d4a574]/50"
                onChange={event => onEffortChange(event.target.value)}
                value={runEffort}
              >
                {COMPACT_RUN_EFFORTS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex min-w-0 items-end gap-2">
            <label className="min-w-0 flex-1 text-sm font-medium">
              <span className="sr-only">Message Jenny</span>
              <textarea
                className="max-h-28 min-h-11 w-full min-w-0 max-w-full resize-none rounded-2xl border border-[#f3ebda]/10 bg-[#0e0b12] px-3 py-2.5 text-base text-[#f3ebda] outline-none transition placeholder:text-[#6e6353] focus:border-[#d4a574]/50 [overflow-wrap:anywhere] [word-break:break-word]"
                disabled={paused}
                onChange={event => onRequestChange(event.target.value)}
                placeholder={paused ? "This project is on hold until Jenny is stable." : "Tell Jenny what you want to discuss or ask her to do next..."}
                value={projectRequest}
              />
            </label>

            <div className="flex min-w-0 shrink-0 justify-end">
              <button className="min-h-11 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-500/15 disabled:opacity-60 dark:text-emerald-300" disabled={bridgeActionDisabled} onClick={onQueueBridge} type="button">
                {sendButtonLabel}
              </button>
            </div>
          </div>
          <div className="mt-2 flex min-w-0 max-w-full flex-wrap items-center gap-1.5 text-[0.68rem]">
            <span className="min-w-0 max-w-full rounded-full border border-[#f3ebda]/10 bg-[#0e0b12]/70 px-2 py-1 text-[#a59783] [overflow-wrap:anywhere]">
              {runSettingsLabel}
            </span>
            <button
              className="min-h-9 rounded-full border border-sky-500/35 bg-sky-500/10 px-3 py-1.5 font-semibold text-sky-700 hover:bg-sky-500/15 disabled:opacity-60 dark:text-sky-300"
              disabled={busy || !canRunForegroundReply}
              onClick={onRunJennyOnce}
              type="button"
            >
              Get reply
            </button>
            <button
              className="min-h-9 rounded-full border border-[#f3ebda]/15 bg-[#0e0b12]/70 px-3 py-1.5 font-semibold text-[#c9b8a2] hover:bg-[#251d2c]/70 disabled:opacity-60"
              disabled={busy}
              onClick={onRefreshBridge}
              type="button"
            >
              Refresh
            </button>
          </div>
          <details className="hidden" hidden>
            <summary className="cursor-pointer text-sm font-semibold">Request options</summary>
            <button className="mt-2 w-full rounded-lg border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60 sm:w-auto" disabled={busy} onClick={onRefreshBridge} type="button">
              Refresh replies
            </button>
            <p className={cn(
              "mt-2 max-w-full rounded-lg border px-3 py-2 [overflow-wrap:anywhere]",
              requestIntake.state === "ready"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200"
                : requestIntake.state === "approval_required"
                  ? "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-200"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-100",
            )}>
              <span className="font-semibold">Request intake: {requestIntake.label}.</span> {requestIntake.detail}
              {shouldAutoChallengeRequest(requestIntake) ? (
                <span className="mt-1 block">Jenny will challenge this request before planning any implementation.</span>
              ) : null}
            </p>
            {shouldAutoChallengeRequest(requestIntake) ? (
              <div aria-label="Jenny challenge checklist" className="mt-2 max-w-full rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 [overflow-wrap:anywhere] dark:text-amber-100">
                <div className="font-semibold">Jenny must challenge first</div>
                <ul className="mt-1 grid gap-1">
                  <li>Question missing facts and unsafe assumptions.</li>
                  <li>Push back on protected actions or broad scope.</li>
                  <li>Return the smallest safe lane with evidence and approval needs.</li>
                </ul>
              </div>
            ) : null}
            <p className="mt-2 text-muted-foreground [overflow-wrap:anywhere]">
              Use these when Jenny should challenge, narrow, or formalize the request before normal work.
            </p>
            {requestIntake.state !== "ready" ? (
              <button
                className="mt-2 w-full rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-500/15 disabled:opacity-60 dark:text-amber-300 sm:w-auto"
                disabled={busy || paused}
                onClick={() => onRequestChange(specFirstComposerText)}
                type="button"
              >
                Use spec-first prompt
              </button>
            ) : (
              <p className="mt-2 text-muted-foreground [overflow-wrap:anywhere]">This request is bounded enough for a guarded Jenny reply.</p>
            )}
          </details>
          <p className="sr-only mt-2 max-w-full text-xs text-muted-foreground [overflow-wrap:anywhere]">
            {paused
              ? "This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable."
              : "Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates."}
          </p>
          {paused ? <CompactPausedProjectResumeChecklist /> : null}
        </div>

        {message ? <p className="mt-2 max-w-full text-xs text-muted-foreground [overflow-wrap:anywhere]">{message}</p> : null}

        <details className="hidden mt-2 max-w-full overflow-hidden rounded-lg border border-border/70 bg-background p-3 sm:block">
          <summary className="cursor-pointer text-sm font-semibold">Previous sessions</summary>
          <div className="grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
            <h3 className="sr-only">Previous sessions</h3>
            <span className="w-fit rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{sessions.length} linked</span>
          </div>
          <div className="mt-2 grid min-w-0 gap-2">
            {sessions.length ? (
              sessions.map((session, index) => (
                session.session_id ? (
                  <button
                    className="min-w-0 rounded-lg border border-border/60 bg-card/60 p-2 text-left text-xs transition hover:border-emerald-500/40 hover:bg-emerald-500/10"
                    key={session.session_id}
                    onClick={() => onOpenSession(session)}
                    type="button"
                  >
                    <span className="block max-w-full font-semibold [overflow-wrap:anywhere]">{session.title || session.session_id || "Linked session"}</span>
                    <span className="mt-0.5 block max-w-full text-muted-foreground [overflow-wrap:anywhere]">
                      {[session.profile, session.source, session.cwd_snapshot].filter(Boolean).join(" / ") || "session context"}
                    </span>
                    <span className="mt-1 block text-[0.65rem] font-semibold text-emerald-700 dark:text-emerald-300">Open session</span>
                  </button>
                ) : (
                  <div className="max-w-full overflow-hidden rounded-lg border border-border/60 bg-card/60 p-2 text-xs" key={index}>
                    <div className="font-semibold [overflow-wrap:anywhere]">{session.title || "Linked session"}</div>
                    <div className="mt-0.5 text-muted-foreground [overflow-wrap:anywhere]">
                      {[session.profile, session.source, session.cwd_snapshot].filter(Boolean).join(" / ") || "session context"}
                    </div>
                  </div>
                )
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No linked sessions for this project yet.</p>
            )}
          </div>
        </details>

        <details className="hidden mt-2 max-w-full overflow-hidden rounded-lg border border-border/70 bg-background/60 p-3 sm:block">
          <summary className="cursor-pointer text-sm font-semibold">Advanced</summary>
          <section className="mt-3 max-w-full overflow-hidden rounded-xl border border-violet-500/30 bg-violet-500/5 p-3">
            <div className="grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
              <h3 className="text-sm font-semibold">Jenny memory storage</h3>
              <span className="min-w-0 text-[0.68rem] text-violet-700 [overflow-wrap:anywhere] dark:text-violet-300 sm:text-right">
                {memoryStorage.profile_count ?? memoryStorage.profiles?.length ?? 0} profiles / {formatBytes(memoryStorage.total_bytes)}
              </span>
            </div>
            <div className="mt-2 grid min-w-0 gap-2">
              {(memoryStorage.profiles ?? []).length ? (
                (memoryStorage.profiles ?? []).map(profile => (
                  <article className="max-w-full overflow-hidden rounded-lg border border-violet-500/20 bg-background/70 p-2 text-xs" key={profile.profile ?? profile.home}>
                    <div className="font-semibold [overflow-wrap:anywhere]">{profile.profile ?? "profile"}</div>
                    <div className="mt-1 text-muted-foreground [overflow-wrap:anywhere]">Memory: {formatBytes(profile.memory?.bytes)} / {profile.memory?.chars ?? 0} chars / {profile.memory?.percent_used ?? 0}%</div>
                    <div className="text-muted-foreground [overflow-wrap:anywhere]">User: {formatBytes(profile.user?.bytes)} / {profile.user?.chars ?? 0} chars / {profile.user?.percent_used ?? 0}%</div>
                    <div className="text-muted-foreground [overflow-wrap:anywhere]">Mount: {profile.mount?.path ?? "unknown"} / {formatBytes(profile.mount?.used_bytes)} used of {formatBytes(profile.mount?.total_bytes)} / {formatPercent(profile.mount?.percent_used)}</div>
                    {profile.memory?.error || profile.user?.error || profile.mount?.error ? <div className="mt-1 text-destructive [overflow-wrap:anywhere]">Read issue: {profile.memory?.error || profile.user?.error || profile.mount?.error}</div> : null}
                  </article>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">No profile memory files reported.</p>
              )}
            </div>
          </section>
          <div className="mt-3 grid min-w-0 gap-2 sm:grid-cols-2">
            <CompactField label="project brief" value={compactText(brief?.outcome, 320) || "No project brief recorded"} />
            <CompactField label="challenge review" value={review ? `${review.decision_state ?? "unknown"} / ${review.recommended_path ?? "No recommended path recorded"}` : "No challenge review recorded"} />
            <CompactField label="latest report contract" value={selectedProjectView.reportContract} />
            <CompactField label="latest result" value={selectedProjectView.latestResult} />
          </div>
          {onQueueHermesUpdate || onQueueStorageCleanup ? (
            <section className="mt-3 rounded-xl border border-border/70 bg-card/60 p-3">
              <h3 className="text-sm font-semibold">Maintenance lanes</h3>
              <p className="mt-1 text-xs text-muted-foreground [overflow-wrap:anywhere]">
                These only queue guarded Jenny requests. They do not restart, update, delete files, or switch runtimes.
              </p>
              <div className="mt-2 grid min-w-0 gap-2 sm:flex sm:flex-wrap">
                {onQueueHermesUpdate ? (
                  <button className="w-full rounded-xl border border-amber-500/40 px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-500/10 disabled:opacity-60 dark:text-amber-300 sm:w-auto" disabled={busy || !githubBridgeSafety.safe} onClick={onQueueHermesUpdate} type="button">
                    Start Hermes update lane
                  </button>
                ) : null}
                {onQueueStorageCleanup ? (
                  <button className="w-full rounded-xl border border-sky-500/40 px-3 py-2 text-sm font-semibold text-sky-700 hover:bg-sky-500/10 disabled:opacity-60 dark:text-sky-300 sm:w-auto" disabled={busy || !githubBridgeSafety.safe} onClick={onQueueStorageCleanup} type="button">
                    Start storage cleanup lane
                  </button>
                ) : null}
              </div>
            </section>
          ) : null}
          <div className="mt-3 grid min-w-0 gap-2 sm:grid-cols-3">
            <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy} onClick={onCopyPacket} type="button">
              Copy phone-safe packet
            </button>
            <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy || paused} onClick={onSaveChallenge} type="button">
              Save challenge draft
            </button>
            <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy || paused} onClick={onSaveLane} type="button">
              Save read-only lane draft
            </button>
          </div>
          <div className="sr-only">Queue for Jenny bridge</div>
          <div className="mt-4 max-w-full overflow-hidden rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3">
            <div className="grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
              <h3 className="text-sm font-semibold">Jenny bridge</h3>
              <span className="w-fit rounded-full border border-emerald-500/30 px-2 py-0.5 text-[0.65rem] text-emerald-700 dark:text-emerald-300">no dispatch</span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground [overflow-wrap:anywhere]">Record-backed outbox/inbox for Jenny relay. Use refresh to check replies. Direct send remains disabled.</p>
            <div className="mt-3 grid min-w-0 gap-2 rounded-lg border border-emerald-500/20 bg-background/70 p-2 text-xs sm:grid-cols-2">
              <CompactField label="manual relay" value={bridgeStatus.manual_start_only === false ? "disabled" : "manual-start only"} />
              <CompactField label="pending" value={String(pendingCount)} />
              <CompactField label="last status" value={bridgeStatus.last_status ?? "idle"} />
              <CompactField label="last response" value={bridgeStatus.last_response_request_id || bridgeStatus.last_response_at || "none"} />
              <CompactField label="last error" value={bridgeStatus.last_error || "none"} />
              <CompactField label="worker/timer" value={`worker ${bridgeStatus.worker_enabled ? "enabled" : "disabled"} / timer ${bridgeStatus.timer_enabled ? "enabled" : "disabled"}`} />
            </div>
            <div className="mt-3 grid min-w-0 gap-2 rounded-lg border border-sky-500/20 bg-sky-500/5 p-2 text-xs sm:grid-cols-2">
              <CompactField label="GitHub mailbox" value={githubBridgeStatus.manual_start_only === false ? "disabled" : "manual-start only"} />
              <CompactField label="GitHub safety" value={githubBridgeSafety.safe ? "manual-only confirmed" : compactBridgeBlockedMessage(githubBridgeSafety)} />
              <CompactField label="GitHub mode" value={githubBridgeStatus.mode || "manual"} />
              <CompactField
                label="GitHub pending"
                value={`visible ${githubBridgeStatus.visible_pending_count ?? githubBridgeStatus.pending_count ?? 0} / background ${githubBridgeStatus.background_pending_count ?? 0}`}
              />
              <CompactField label="GitHub last poll" value={githubBridgeStatus.last_poll_at || githubBridgeStatus.last_status || "not polled"} />
              <CompactField label="GitHub last response" value={githubBridgeStatus.last_response_request_id || githubBridgeStatus.last_response_at || "none"} />
              <CompactField label="GitHub last error" value={githubBridgeStatus.last_error || "none"} />
              <CompactField label="daemon/worker/timer" value={`daemon ${githubBridgeStatus.daemon_enabled ? "enabled" : "disabled"} / worker ${githubBridgeStatus.worker_enabled ? "enabled" : "disabled"} / timer ${githubBridgeStatus.timer_enabled ? "enabled" : "disabled"}`} />
            </div>
            <div className="mt-3 grid min-w-0 gap-2 sm:grid-cols-2">
              <CompactBridgeList
                title="Outbound"
                empty="No queued messages."
                items={visibleBridgeRequests}
                renderItem={item => `${item.bridge_state ?? (item.request_id && repliedRequestIds.has(item.request_id) ? "replied" : item.status ?? "queued")} / ${item.message}`}
              />
              <CompactBridgeList title="Replies" empty="No replies yet." items={visibleBridgeResponses} renderItem={item => `${item.responder ?? "jenny"} / ${item.message}`} />
            </div>
          </div>
          <div className="mt-4 max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-3">
            <div className="grid min-w-0 gap-1 sm:flex sm:items-center sm:justify-between sm:gap-2">
              <h3 className="text-sm font-semibold">Phone-safe packet</h3>
              <span className="w-fit rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{packet.length} / 1900</span>
            </div>
            <pre className="mt-2 max-h-64 max-w-full overflow-y-auto overflow-x-hidden whitespace-pre-wrap break-words text-xs leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">{packet}</pre>
          </div>
        </details>
      </article>
    </section>
  );
}

function CompactBridgeList<T>({
  empty,
  items,
  renderItem,
  title,
}: {
  empty: string;
  items: T[];
  renderItem: (item: T) => string;
  title: string;
}) {
  return (
    <section className="min-w-0 max-w-full overflow-hidden rounded-lg border border-border/70 bg-background/70 p-2 text-xs">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <h4 className="font-semibold">{title}</h4>
        <span className="text-muted-foreground">{items.length}</span>
      </div>
      <div className="mt-2 grid min-w-0 gap-2">
        {items.length ? (
          items.slice(-2).reverse().map((item, index) => (
            <p className="line-clamp-3 rounded-md border border-border/60 bg-background p-2 text-muted-foreground [overflow-wrap:anywhere]" key={index}>
              {renderItem(item)}
            </p>
          ))
        ) : (
          <p className="text-muted-foreground [overflow-wrap:anywhere]">{empty}</p>
        )}
      </div>
    </section>
  );
}

export function CompactProjectKanban({ projectViews }: { projectViews: ProjectViewModel[] }) {
  return (
    <section className="mt-4 max-w-full overflow-hidden rounded-2xl border border-border/70 bg-card p-3" aria-label="Project Kanban">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">Project Kanban</h2>
          <p className="mt-1 max-w-full text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">
            Record-backed lifecycle. Dragging disabled; cards move only when briefs, challenge reviews, lane drafts, approvals, or reports change.
          </p>
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[0.65rem] font-semibold text-amber-700 dark:text-amber-300">
          read-only board
        </span>
      </div>

      <div className="mt-3 grid min-w-0 gap-2">
        {PROJECT_KANBAN_COLUMNS.map(column => {
          const cards = projectViews.filter(projectView => projectKanbanColumnFor(projectView) === column.id);
          return (
            <section className="max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2" key={column.id}>
              <div className="flex min-w-0 items-center justify-between gap-2">
                <h3 className="text-xs font-semibold">{column.title}</h3>
                <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{cards.length}</span>
              </div>
              <p className="mt-1 text-[0.65rem] leading-snug text-muted-foreground [overflow-wrap:anywhere]">{column.description}</p>
              <div className="mt-2 grid min-w-0 gap-2">
                {cards.length ? (
                  cards.map(projectView => (
                    <article className="max-w-full overflow-hidden rounded-lg border border-border/60 bg-card/70 p-2 text-xs" key={projectView.project.project_id}>
                      <div className="font-semibold leading-tight [overflow-wrap:anywhere]">{projectView.project.name}</div>
                      <div className="mt-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">{projectView.readinessLabel}</div>
                      <div className="mt-2 text-[0.68rem] leading-snug text-muted-foreground [overflow-wrap:anywhere]">Lane: {projectView.latestLane}</div>
                      <div className="mt-1 text-[0.68rem] leading-snug text-muted-foreground [overflow-wrap:anywhere]">Next: {projectView.nextLane}</div>
                      <div className="mt-1 text-[0.68rem] leading-snug text-muted-foreground [overflow-wrap:anywhere]">Contract: {projectView.reportContract}</div>
                    </article>
                  ))
                ) : (
                  <p className="rounded-lg border border-dashed border-border/70 p-2 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">No project cards.</p>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

function CompactReportIngestion({
  form,
  message,
  onChange,
  onSave,
  projects,
  saving,
}: {
  form: ReportFormState;
  message: string;
  onChange: (field: keyof ReportFormState, value: string) => void;
  onSave: () => void;
  projects: ProjectRecord[];
  saving: boolean;
}) {
  return (
    <section className="mt-3 max-w-full overflow-hidden rounded-2xl border border-border/70 bg-card p-3" aria-label="Manual record repair compact">
      <h2 className="text-sm font-semibold">Save a missing Jenny report</h2>
      <p className="mt-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Repair tool for when Jenny gave a useful report but Mission Control did not capture it automatically. Not needed for normal chat.</p>
      <label className="mt-3 grid gap-1 text-xs font-medium">
        Project
        <select className="rounded-xl border border-border/80 bg-background px-3 py-2 text-sm" onChange={event => onChange("projectId", event.target.value)} value={form.projectId}>
          <option value="">Choose a real project</option>
          {projects.map(project => (
            <option key={project.project_id} value={project.project_id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
      <CompactReportInput label="Report summary" onChange={value => onChange("summary", value)} value={form.summary} />
      <CompactReportInput label="Latest result" onChange={value => onChange("result", value)} value={form.result} />
      <CompactReportInput label="Risks/blockers - one per line" onChange={value => onChange("risks", value)} value={form.risks} />
      <CompactReportInput label="Artifact/report links - one per line" onChange={value => onChange("artifactLinks", value)} value={form.artifactLinks} />
      <CompactReportInput label="Changed files/evidence - one per line" onChange={value => onChange("changedFiles", value)} value={form.changedFiles} />
      <CompactReportInput label="Next recommended lane" onChange={value => onChange("nextRecommendedLane", value)} value={form.nextRecommendedLane} />
      <button className="mt-3 w-full rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving} onClick={onSave} type="button">
        {saving ? "Saving report..." : "Save missing report"}
      </button>
      {message ? <p className="mt-2 text-xs text-muted-foreground [overflow-wrap:anywhere]">{message}</p> : null}
    </section>
  );
}

function CompactReportInput({ label, onChange, value }: { label: string; onChange: (value: string) => void; value: string }) {
  return (
    <label className="mt-3 grid gap-1 text-xs font-medium">
      {label}
      <textarea className="min-h-16 max-w-full rounded-xl border border-border/80 bg-background px-3 py-2 text-sm" onChange={event => onChange(event.target.value)} value={value} />
    </label>
  );
}

function SafetyStrip({ status }: { status: WorkspaceStatus }) {
  const guard = status.runtime_worktree_guard?.decision_state ?? "unknown";
  const dispatch = status.safety?.dispatch_in_gateway;
  const activeLaneCount = status.lane?.active_lane_count ?? 0;
  const warnings = status.stale_context?.warnings ?? [];
  const deployState = status.deployment_gap?.state ?? "unknown";
  const acceptedLiveHead = status.deployment_gap?.accepted_live_head ?? status.accepted_baseline?.head ?? "";
  const deployedHead = status.deployment_gap?.deployed_head ?? status.accepted_baseline?.head ?? "";
  return (
    <section className="mt-4 grid min-w-0 grid-cols-1 gap-2 text-xs sm:grid-cols-2" aria-label="Safety status">
      <SafetyPill label="Guard" good={guard === "pass"} value={guard} />
      <SafetyPill label="Dispatch" good={dispatch === false} value={dispatch === false ? "false" : "unknown"} />
      <SafetyPill label="Active lanes" good={activeLaneCount === 0} value={String(activeLaneCount)} />
      <SafetyPill label="Warnings" good={warnings.length === 0} value={warnings.length ? String(warnings.length) : "none"} />
      <SafetyPill label="Deploy state" good={deployState === "deployed_and_accepted"} value={deployState.replaceAll("_", " ")} />
      <SafetyPill label="Accepted / deployed" good={!status.deployment_gap?.dashboard_deploy_needed} value={`${acceptedLiveHead.slice(0, 8) || "unknown"} / ${deployedHead.slice(0, 8) || "unknown"}`} />
      <SafetyPill label="Desktop app" good={false} value="separate worker-node update" />
    </section>
  );
}

type CompactHealthTone = "bad" | "good" | "idle" | "warn";

type CompactExecutionLockSource = {
  dispatch_enabled?: boolean;
  execution_enabled?: boolean;
  execution_ready?: boolean;
  send_to_jenny_enabled?: boolean;
  session_send_enabled?: boolean;
  would_dispatch?: boolean;
  would_execute?: boolean;
  would_session_send?: boolean;
  worker_dispatch_enabled?: boolean;
  worker_enabled?: boolean;
};

const COMPACT_EXECUTION_LOCK_FLAGS: Array<[keyof CompactExecutionLockSource, string]> = [
  ["would_execute", "would_execute must remain false"],
  ["would_dispatch", "would_dispatch must remain false"],
  ["would_session_send", "would_session_send must remain false"],
  ["dispatch_enabled", "dispatch_enabled must remain false"],
  ["execution_enabled", "execution_enabled must remain false"],
  ["execution_ready", "execution_ready must remain false"],
  ["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"],
  ["session_send_enabled", "session_send_enabled must remain false"],
  ["worker_dispatch_enabled", "worker_dispatch_enabled must remain false"],
  ["worker_enabled", "worker_enabled must remain false"],
];

function compactExecutionLockReasons(label: string, source?: CompactExecutionLockSource | null): string[] {
  if (!source) return [];
  return COMPACT_EXECUTION_LOCK_FLAGS
    .filter(([flag]) => compactLiveFlagEnabled(source[flag]))
    .map(([, reason]) => `${label}: ${reason}`);
}

function compactLiveFlagEnabled(value: unknown): boolean {
  if (value === true) return true;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    return ["1", "true", "yes", "y", "on", "enabled"].includes(value.trim().toLowerCase());
  }
  return false;
}

function CompactHermesHealthDashboard({
  activeProjectViews,
  pausedProjects,
  snapshot,
}: {
  activeProjectViews: ProjectViewModel[];
  pausedProjects: ProjectRecord[];
  snapshot: CompactSnapshot;
}) {
  const status = snapshot.workspaceStatus;
  const guard = status.runtime_worktree_guard?.decision_state ?? "unknown";
  const dispatch = status.safety?.dispatch_in_gateway;
  const activeLaneCount = status.lane?.active_lane_count ?? 0;
  const staleWarnings = status.stale_context?.warnings ?? [];
  const bridgeError = normalizedBridgeError(snapshot.jennyBridgePollerStatus, snapshot.githubBridgeStatus);
  const bridgePending = snapshot.githubBridgeStatus.visible_pending_count ?? snapshot.githubBridgeStatus.pending_count ?? snapshot.jennyBridgePollerStatus.pending_count ?? 0;
  const bridgeWatching = snapshot.githubBridgeStatus.foreground_watch_running === true;
  const memoryErrors = snapshot.memoryStorage.errors ?? [];
  const reportCount = activeProjectViews.filter(projectView => projectView.projectState?.has_real_report || projectView.report).length;
  const deployedHead = status.deployment_gap?.deployed_head ?? status.accepted_baseline?.head ?? "unknown";
  const executionMode = status.execution_mode_classification;
  const executionPacket = status.execution_packet_preview;
  const hardBoundary = status.hard_boundary_contract;
  const operatorPacket = status.operator_decision_packet;
  const readiness = status.orchestration_readiness;
  const approvalLifecycle = status.approval_lifecycle;
  const runLifecycle = status.run_lifecycle;
  const childProjection = status.child_agent_orchestration;
  const childInstruction = status.child_agent_instruction_preview;
  const runGraph = status.orchestration_run_graph;
  const workerInstruction = status.worker_node_instruction_preview;
  const workerPresence = status.worker_node_presence;
  const resultIngestion = status.result_ingestion_contract;
  const reportCompletion = status.report_completion_path;
  const reportLifecycle = status.report_lifecycle;
  const nextSafeActions = status.next_safe_actions;
  const resultIngestionBlocked = resultIngestion?.blocked_report_count ?? 0;
  const reportCompletionBlocked = reportCompletion?.blocked_completion_count ?? 0;
  const approvalMissingRecordCount = Object.keys(approvalLifecycle?.runs_with_missing_approval_record ?? {}).length;
  const approvalUnavailableRunCount = Object.keys(approvalLifecycle?.runs_with_unavailable_approval ?? {}).length;
  const approvalGapCount =
    (approvalLifecycle?.duplicate_approval_ids?.length ?? 0)
    + (approvalLifecycle?.consumed_approval_ids?.length ?? 0)
    + (approvalLifecycle?.rejected_or_cancelled_approval_ids?.length ?? 0)
    + (approvalLifecycle?.runs_missing_approval_id?.length ?? 0)
    + approvalMissingRecordCount
    + approvalUnavailableRunCount;
  const runTerminalMissingLinkedCount = Object.values(runLifecycle?.terminal_runs_with_missing_linked_report_ids ?? {}).reduce(
    (count, reportIds) => count + reportIds.length,
    0,
  );
  const runGapCount =
    (runLifecycle?.duplicate_run_ids?.length ?? 0)
    + (runLifecycle?.terminal_runs_missing_report?.length ?? 0)
    + runTerminalMissingLinkedCount
    + (runLifecycle?.one_active_mutation_lane_rule_passed === false ? 1 : 0);
  const reportDuplicateCount = reportLifecycle?.duplicate_report_ids?.length ?? 0;
  const reportMissingRunCount = reportLifecycle?.runs_missing_report?.length ?? 0;
  const reportMissingLinkedCount = Object.values(reportLifecycle?.runs_with_missing_linked_report_ids ?? {}).reduce(
    (count, reportIds) => count + reportIds.length,
    0,
  );
  const reportOverwriteConflictCount = reportLifecycle?.report_overwrite_conflict_count ?? reportLifecycle?.report_overwrite_conflict_ids?.length ?? 0;
  const reportGapCount = reportDuplicateCount + reportOverwriteConflictCount + reportMissingRunCount + reportMissingLinkedCount;
  const hardBoundaryViolationCount = hardBoundary?.live_flag_violation_count ?? hardBoundary?.live_flag_violations?.length ?? 0;
  const hardBoundaryForbiddenCount = hardBoundary?.forbidden_action_count ?? hardBoundary?.forbidden_actions?.length ?? 0;
  const hardBoundarySeparateApprovalCount = hardBoundary?.separate_approval_action_count ?? hardBoundary?.separate_approval_actions?.length ?? 0;
  const workerPresenceState = workerPresence?.presence_state ?? "unknown";
  const readinessStates = readiness?.states;
  const nextSafeActionLockReasons = compactExecutionLockReasons("Safe next actions", nextSafeActions);
  const approvalLifecycleLockReasons = compactExecutionLockReasons("Approval lifecycle", approvalLifecycle);
  const runLifecycleLockReasons = compactExecutionLockReasons("Run lifecycle", runLifecycle);
  const runGraphLockReasons = compactExecutionLockReasons("Orchestration run graph", runGraph);
  const childProjectionLockReasons = compactExecutionLockReasons("Child agent", childProjection);
  const childInstructionLockReasons = compactExecutionLockReasons("Child handoff", childInstruction);
  const executionModeLockReasons = compactExecutionLockReasons("Execution mode", executionMode);
  const executionPacketLockReasons = compactExecutionLockReasons("Execution packet", executionPacket);
  const executionPacketBodyLockReasons = compactExecutionLockReasons("Execution packet body", executionPacket?.packet);
  const workerContractLockReasons = compactExecutionLockReasons("Worker contract", executionPacket?.packet?.worker_node_contract);
  const hardBoundaryLockReasons = compactExecutionLockReasons("Hard boundary", hardBoundary);
  const operatorLockReasons = compactExecutionLockReasons("Operator decision", operatorPacket);
  const operatorExecutionLockBlockedReasons = operatorPacket?.execution_lock_blocked_reasons ?? [];
  const readinessLockReasons = compactExecutionLockReasons("Preview readiness", readiness);
  const workerInstructionLockReasons = compactExecutionLockReasons("Worker handoff", workerInstruction);
  const workerLockReasons = compactExecutionLockReasons("Worker node", workerPresence);
  const ingestionLockReasons = compactExecutionLockReasons("Result ingestion", resultIngestion);
  const completionLockReasons = compactExecutionLockReasons("Report completion", reportCompletion);
  const reportLifecycleLockReasons = compactExecutionLockReasons("Report lifecycle", reportLifecycle);
  const issues = [
    bridgeError ? `Jenny bridge error: ${bridgeError}` : "",
    guard !== "pass" ? `Runtime guard is ${guard}` : "",
    dispatch !== false ? "Dispatch safety is not confirmed off" : "",
    compactLiveFlagEnabled(status.safety?.model_routing_enabled) ? "Model routing safety is not confirmed off" : "",
    activeLaneCount > 1 ? `${activeLaneCount} active lanes recorded` : "",
    status.deployment_gap?.dashboard_deploy_needed ? "Phone/web dashboard needs a dashboard-only update" : "",
    staleWarnings.length ? `Stale context: ${staleWarnings.join(", ")}` : "",
    memoryErrors.length ? `${memoryErrors.length} memory storage warning${memoryErrors.length === 1 ? "" : "s"}` : "",
    ...nextSafeActionLockReasons,
    ...approvalLifecycleLockReasons,
    ...runLifecycleLockReasons,
    ...runGraphLockReasons,
    ...childProjectionLockReasons,
    ...childInstructionLockReasons,
    ...executionModeLockReasons,
    ...executionPacketLockReasons,
    ...executionPacketBodyLockReasons,
    ...workerContractLockReasons,
    ...hardBoundaryLockReasons,
    ...operatorLockReasons,
    operatorExecutionLockBlockedReasons.length ? firstReason(operatorExecutionLockBlockedReasons, "Operator execution locks need review") : "",
    ...readinessLockReasons,
    ...workerInstructionLockReasons,
    ...workerLockReasons,
    ...ingestionLockReasons,
    ...completionLockReasons,
    ...reportLifecycleLockReasons,
    hardBoundary?.blocked ? firstReason(hardBoundary.blocked_reasons, "Hard boundary contract needs review") : "",
    operatorPacket?.blocked ? firstReason(operatorPacket.blocked_reasons, "Operator decision packet is blocked") : "",
    approvalLifecycle?.blocked ? firstReason(approvalLifecycle.blocked_reasons, "Approval lifecycle needs review") : "",
    runLifecycle?.blocked ? firstReason(runLifecycle.blocked_reasons, "Run lifecycle needs review") : "",
    runGraph?.blocked ? firstReason(runGraph.blocked_reasons, "Orchestration run graph needs review") : "",
    childProjection?.blocked_reasons?.length ? firstReason(childProjection.blocked_reasons, "Child-agent projection needs review") : "",
    childInstruction?.blocked ? firstReason(childInstruction.blocked_reasons, "Child handoff preview needs review") : "",
    executionMode?.blocked ? firstReason(executionMode.blocked_reasons, "Execution mode preview is blocked") : "",
    executionPacket?.blocked_reasons?.length ? firstReason(executionPacket.blocked_reasons, "Execution packet preview is blocked") : "",
    readiness?.blocked_reasons?.length ? firstReason(readiness.blocked_reasons, "Orchestration readiness is blocked") : "",
    workerInstruction?.blocked_reasons?.length ? firstReason(workerInstruction.blocked_reasons, "Worker handoff preview is blocked") : "",
    workerPresence?.blocked ? firstReason(workerPresence.blocked_reasons, "Laptop Codex worker-node presence is blocked") : "",
    resultIngestionBlocked ? firstReason(resultIngestion?.blocked_reasons, "Result ingestion needs review") : "",
    reportCompletionBlocked ? firstReason(reportCompletion?.blocked_reasons, "Report completion path needs review") : "",
    reportLifecycle?.blocked ? firstReason(reportLifecycle.blocked_reasons, "Report lifecycle needs review") : "",
  ].filter(Boolean);
  const overallTone: CompactHealthTone = issues.length ? "warn" : "good";
  const bridgeTone: CompactHealthTone = bridgeError ? "bad" : bridgePending ? "warn" : "good";
  const safetyOk = guard === "pass" && dispatch === false && !compactLiveFlagEnabled(status.safety?.model_routing_enabled) && activeLaneCount <= 1 && staleWarnings.length === 0;
  const approvalLifecycleTone: CompactHealthTone = approvalLifecycleLockReasons.length
    ? "bad"
    : approvalLifecycle?.blocked || approvalGapCount
      ? "warn"
      : "good";
  const runLifecycleTone: CompactHealthTone = runLifecycleLockReasons.length
    ? "bad"
    : runLifecycle?.blocked || runGapCount
      ? "warn"
      : "good";
  const runGraphTone: CompactHealthTone = runGraphLockReasons.length
    ? "bad"
    : !runGraph || runGraph.blocked || runGraph.blocked_reasons?.length
      ? "warn"
      : "good";
  const childProjectionTone: CompactHealthTone = childProjectionLockReasons.length
    ? "bad"
    : childProjection?.blocked_reasons?.length
      ? "warn"
      : "good";
  const childInstructionTone: CompactHealthTone = childInstructionLockReasons.length
    ? "bad"
    : childInstruction?.blocked_reasons?.length || childInstruction?.ready_for_handoff !== true
      ? "warn"
      : "good";
  const executionPreviewTone: CompactHealthTone = [
    ...executionModeLockReasons,
    ...executionPacketLockReasons,
    ...executionPacketBodyLockReasons,
    ...workerContractLockReasons,
  ].length
    ? "bad"
    : executionMode?.blocked || executionPacket?.eligible === false || executionPacket?.blocked_reasons?.length
      ? "warn"
      : "good";
  const operatorTone: CompactHealthTone = operatorLockReasons.length
    ? "bad"
    : operatorExecutionLockBlockedReasons.length
      ? "bad"
      : operatorPacket?.blocked || operatorPacket?.jenny_review_required
      ? "warn"
      : "good";
  const hardBoundaryTone: CompactHealthTone = hardBoundaryLockReasons.length || hardBoundaryViolationCount
    ? "bad"
    : !hardBoundary || hardBoundary.live_operations_enabled !== false || hardBoundary.live_operations_goal !== false || hardBoundary.execution_ready !== false
      ? "warn"
      : "good";
  const readinessTone: CompactHealthTone = readinessLockReasons.length
    ? "bad"
    : readiness?.blocked_reasons?.length
      ? "warn"
      : "good";
  const workerInstructionTone: CompactHealthTone = workerInstructionLockReasons.length
    ? "bad"
    : workerInstruction?.blocked_reasons?.length || workerInstruction?.ready_for_handoff !== true
      ? "warn"
      : "good";
  const workerTone: CompactHealthTone = workerLockReasons.length
    ? "bad"
    : workerPresence?.online
      ? "good"
      : "warn";
  const ingestionTone: CompactHealthTone = ingestionLockReasons.length
    ? "bad"
    : resultIngestionBlocked
      ? "warn"
      : "good";
  const completionTone: CompactHealthTone = completionLockReasons.length
    ? "bad"
    : reportCompletionBlocked
      ? "warn"
      : "good";
  const reportLifecycleTone: CompactHealthTone = reportLifecycleLockReasons.length
    ? "bad"
    : reportLifecycle?.blocked || reportGapCount
      ? "warn"
      : "good";
  const maxMountPercent = Math.max(0, ...(snapshot.memoryStorage.profiles ?? []).map(profile => profile.mount?.percent_used ?? 0));
  const executionPreviewDetail = compactText([
    ...executionModeLockReasons,
    ...executionPacketLockReasons,
    ...executionPacketBodyLockReasons,
    ...workerContractLockReasons,
    firstReason(executionMode?.blocked_reasons, ""),
    firstReason(executionPacket?.blocked_reasons, ""),
    ...(executionPacket?.warnings ?? []),
    ...(executionMode?.warnings ?? []),
    "Execution preview remains display-only; dispatch, session send, and worker activation stay disabled.",
  ].find(Boolean) ?? "Execution preview remains display-only.", 260);
  const hardBoundaryDetail = compactText([
    ...hardBoundaryLockReasons,
    firstReason(hardBoundary?.blocked_reasons, ""),
    hardBoundary?.plain_language_summary,
    "Live operations require separate approval.",
  ].find(Boolean) ?? "Live operations require separate approval.", 260);
  const workerInstructionDetail = compactText([
    ...workerInstructionLockReasons,
    firstReason(workerInstruction?.blocked_reasons, ""),
    workerInstruction?.manual_handoff_prompt,
    "No worker-node instruction preview recorded.",
  ].find(Boolean) ?? "No worker-node instruction preview recorded.", 260);
  const approvalLifecycleDetail = compactText([
    ...approvalLifecycleLockReasons,
    firstReason(approvalLifecycle?.blocked_reasons, ""),
    `Approval gaps: duplicates ${approvalLifecycle?.duplicate_approval_ids?.length ?? 0}, consumed ${approvalLifecycle?.consumed_approval_ids?.length ?? 0}, unavailable runs ${approvalUnavailableRunCount}.`,
  ].find(Boolean), 260);
  const runLifecycleDetail = compactText([
    ...runLifecycleLockReasons,
    firstReason(runLifecycle?.blocked_reasons, ""),
    `Run gaps: duplicates ${runLifecycle?.duplicate_run_ids?.length ?? 0}, missing reports ${runLifecycle?.terminal_runs_missing_report?.length ?? 0}, stale links ${runTerminalMissingLinkedCount}.`,
  ].find(Boolean), 260);
  const childRecord = childProjection?.active_runs?.[0] ?? Object.values(childProjection?.latest_by_id ?? {})[0];
  const childLatestStatus = compactRecordText(childRecord, "status") || "none";
  const childLatestObjective = compactRecordText(childRecord, "objective") || compactRecordText(childRecord, "agent_identity") || "no child agent recorded";
  const childLatestReport = compactRecordText(childRecord, "report_id") || "none";
  const childLatestReportReview = compactRecordText(childRecord, "linked_report_review_status") || compactRecordText(childRecord, "report_review_status") || "not reviewed";
  const runGraphDetail = compactText([
    ...runGraphLockReasons,
    firstReason(runGraph?.blocked_reasons, ""),
    `Run graph: runs ${runGraph?.run_node_count ?? 0}, child ${runGraph?.child_run_node_count ?? 0}, worker ${runGraph?.worker_node_run_count ?? 0}, reports ${runGraph?.report_node_count ?? 0}.`,
  ].find(Boolean), 260);
  const childProjectionDetail = compactText([
    ...childProjectionLockReasons,
    firstReason(childProjection?.blocked_reasons, ""),
    childLatestObjective,
  ].find(Boolean), 260);
  const childInstructionDetail = compactText([
    ...childInstructionLockReasons,
    firstReason(childInstruction?.blocked_reasons, ""),
    childInstruction?.manual_handoff_prompt,
    "No child-agent instruction preview recorded.",
  ].find(Boolean), 260);
  const reportLifecycleDetail = compactText([
    ...reportLifecycleLockReasons,
    firstReason(reportLifecycle?.blocked_reasons, ""),
    `Report gaps: duplicates ${reportDuplicateCount}, overwrite conflicts ${reportOverwriteConflictCount}, missing ${reportMissingRunCount}, stale links ${reportMissingLinkedCount}.`,
  ].find(Boolean), 260);

  return (
    <section className="max-w-full overflow-hidden rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-3" aria-label="Hermes health dashboard">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">Hermes health dashboard</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Jenny, phone/web, safety locks, project coverage, and parked tools.</p>
        </div>
        <CompactHealthBadge tone={overallTone}>{issues.length ? "Needs attention" : "Healthy"}</CompactHealthBadge>
      </div>

      <div className="mt-3 grid min-w-0 gap-2">
        <CompactHealthTile
          detail={issues.length ? issues[0] : "No blocking Mission Control health issue is currently recorded."}
          label="Overall"
          tone={overallTone}
          value={issues.length ? `${issues.length} item${issues.length === 1 ? "" : "s"}` : "Ready"}
        />
        <CompactHealthTile
          detail={bridgeError || (bridgeWatching ? "Live reply refresh is watching for Jenny." : bridgePending ? "A message is waiting for Jenny." : "No bridge error is recorded.")}
          label="Jenny bridge"
          tone={bridgeTone}
          value={bridgeError ? "Error" : bridgePending ? `${bridgePending} pending` : "Ready"}
        />
        <CompactHealthTile
          detail={status.deployment_gap?.dashboard_deploy_needed ? "Desktop may be current while phone/web waits for the dashboard bundle." : `Served head ${deployedHead.slice(0, 8)}.`}
          label="Phone and web"
          tone={status.deployment_gap?.dashboard_deploy_needed ? "warn" : "good"}
          value={status.deployment_gap?.dashboard_deploy_needed ? "Update waiting" : "Current"}
        />
        <CompactHealthTile
          detail={`Guard=${guard}; dispatch=${dispatch === false ? "false" : "unknown"}; model routing=${compactLiveFlagEnabled(status.safety?.model_routing_enabled) ? "enabled" : "disabled"}; active lanes=${activeLaneCount}.`}
          label="Safety locks"
          tone={safetyOk ? "good" : "warn"}
          value={safetyOk ? "Holding" : "Check"}
        />
        <CompactHealthTile
          detail={approvalLifecycleDetail}
          label="Approval lifecycle"
          tone={approvalLifecycleTone}
          value={`available ${approvalLifecycle?.available_approval_ids?.length ?? 0} / pending ${approvalLifecycle?.pending_approval_ids?.length ?? 0} / expired ${approvalLifecycle?.expired_approval_ids?.length ?? 0}`}
        />
        <CompactHealthTile
          detail={approvalGapCount ? "Approval gaps block autonomy until approval records and active run links are exact and available." : "No approval lifecycle gaps are currently recorded."}
          label="Approval gaps"
          tone={approvalGapCount ? "warn" : "good"}
          value={`duplicates ${approvalLifecycle?.duplicate_approval_ids?.length ?? 0} / consumed ${approvalLifecycle?.consumed_approval_ids?.length ?? 0} / unavailable runs ${approvalUnavailableRunCount}`}
        />
        <CompactHealthTile
          detail={runLifecycleDetail}
          label="Run lifecycle"
          tone={runLifecycleTone}
          value={`active ${runLifecycle?.active_run_ids?.length ?? 0} / terminal ${runLifecycle?.terminal_run_ids?.length ?? 0} / stop-cancel ${runLifecycle?.stop_cancel_run_ids?.length ?? 0}`}
        />
        <CompactHealthTile
          detail={runLifecycle?.one_active_mutation_lane_rule_passed === false ? "More than one active mutation lane is recorded; autonomy and PR lanes stay blocked." : "Run gaps cover duplicate runs, missing reports, stale report links, and the one-active-mutation-lane rule."}
          label="Run gaps"
          tone={runGapCount ? "warn" : "good"}
          value={`duplicates ${runLifecycle?.duplicate_run_ids?.length ?? 0} / missing reports ${runLifecycle?.terminal_runs_missing_report?.length ?? 0} / stale links ${runTerminalMissingLinkedCount}`}
        />
        <CompactHealthTile
          detail={runGraphDetail}
          label="Run graph"
          tone={runGraphTone}
          value={`nodes ${runGraph?.node_count ?? 0} / edges ${runGraph?.edge_count ?? 0}`}
        />
        <CompactHealthTile
          detail={childProjectionDetail}
          label="Child agent"
          tone={childProjectionTone}
          value={`${childProjection?.active_count ?? 0} active / latest ${compactStateLabel(childLatestStatus, "none")}`}
        />
        <CompactHealthTile
          detail={`report ${childLatestReport} / review ${compactStateLabel(childLatestReportReview, "not reviewed")}`}
          label="Child report"
          tone={childProjection?.blocked_reasons?.length ? "warn" : "good"}
          value={childLatestReport}
        />
        <CompactHealthTile
          detail={childInstructionDetail}
          label="Child handoff"
          tone={childInstructionTone}
          value={`available ${childInstruction?.available ? "yes" : "no"} / handoff ${childInstruction?.ready_for_handoff ? "yes" : "no"} / manual ${childInstruction?.manual_handoff_only === false ? "no" : "yes"}`}
        />
        <CompactHealthTile
          detail={compactOperatorSummary(status)}
          label="Operator decision"
          tone={operatorTone}
          value={`${compactStateLabel(operatorPacket?.state)} / display-only ${operatorPacket?.display_only === false ? "no" : "yes"}`}
        />
        <CompactHealthTile
          detail={hardBoundaryDetail}
          label="Hard boundary"
          tone={hardBoundaryTone}
          value={`${compactStateLabel(hardBoundary?.state)} / forbidden ${hardBoundaryForbiddenCount} / separate approval ${hardBoundarySeparateApprovalCount}`}
        />
        <CompactHealthTile
          detail={`${compactReadinessSummary(status)}. Next safe action: ${nextSafeActions?.primary_action_label || operatorPacket?.next_safe_action_label || "review Mission Control status"}.`}
          label="Preview readiness"
          tone={readinessTone}
          value={`read-only ${compactStateLabel(readinessStates?.supervised_read_only_autonomy)} / worker ${compactStateLabel(readinessStates?.laptop_codex_worker_node)}`}
        />
        <CompactHealthTile
          detail={executionPreviewDetail}
          label="Execution preview"
          tone={executionPreviewTone}
          value={`${compactStateLabel(executionMode?.mode_family)} / packet ${compactStateLabel(executionPacket?.packet?.mode)} / execute ${executionPacket?.execution_enabled ? "yes" : "no"}`}
        />
        <CompactHealthTile
          detail={workerInstructionDetail}
          label="Worker handoff"
          tone={workerInstructionTone}
          value={`available ${workerInstruction?.available ? "yes" : "no"} / handoff ${workerInstruction?.ready_for_handoff ? "yes" : "no"} / manual ${workerInstruction?.manual_handoff_only === false ? "no" : "yes"}`}
        />
        <CompactHealthTile
          detail={workerPresence?.blocked_reasons?.length ? firstReason(workerPresence.blocked_reasons, "Worker-node presence needs review.") : `${workerPresence?.worker_host_label ?? "laptop Codex"} ${workerPresence?.online ? "is online" : "is not confirmed online"}.`}
          label="Worker node"
          tone={workerTone}
          value={`${compactStateLabel(workerPresenceState)} / online ${workerPresence?.online ? "yes" : "no"}`}
        />
        <CompactHealthTile
          detail={resultIngestionBlocked ? firstReason(resultIngestion?.blocked_reasons, "Reports need ingestion review.") : "Reports that Jenny can rely on are linked, redacted, metadata-safe, and safety-confirmed."}
          label="Result ingestion"
          tone={ingestionTone}
          value={`${resultIngestion?.ingestion_ready_count ?? 0} ready / ${resultIngestionBlocked} blocked`}
        />
        <CompactHealthTile
          detail={reportCompletionBlocked ? firstReason(reportCompletion?.blocked_reasons, "Terminal work needs report completion review.") : "Terminal runs, child runs, and worker-node runs have reviewed completion evidence."}
          label="Report completion"
          tone={completionTone}
          value={`${reportCompletion?.completion_ready_count ?? 0} ready / ${reportCompletionBlocked} blocked`}
        />
        <CompactHealthTile
          detail={reportLifecycleDetail}
          label="Report lifecycle"
          tone={reportLifecycleTone}
          value={`open ${reportLifecycle?.open_report_ids?.length ?? 0} / reviewed ${reportLifecycle?.reviewed_report_ids?.length ?? 0} / terminal ${reportLifecycle?.terminal_report_ids?.length ?? 0}`}
        />
        <CompactHealthTile
          detail={reportOverwriteConflictCount ? "Overwrite conflicts quarantine duplicate report IDs until Travis reviews the append-only report history." : "No duplicate report overwrite conflict is currently recorded."}
          label="Report gaps"
          tone={reportGapCount ? "warn" : "good"}
          value={`duplicates ${reportDuplicateCount} / overwrite conflicts ${reportOverwriteConflictCount} / missing ${reportMissingRunCount} / stale links ${reportMissingLinkedCount}`}
        />
        <CompactHealthTile
          detail={`${reportCount} active project${reportCount === 1 ? "" : "s"} have live report evidence. ${pausedProjects.length} projects remain intentionally on hold.`}
          label="Project rooms"
          tone={activeProjectViews.length === 1 && pausedProjects.length === 4 ? "good" : "warn"}
          value={`${activeProjectViews.length} active / ${pausedProjects.length} paused`}
        />
        <CompactHealthTile
          detail={`${snapshot.memoryStorage.profile_count ?? snapshot.memoryStorage.profiles?.length ?? 0} profiles. Highest mount usage ${formatPercent(maxMountPercent)}. ${memoryErrors.length ? memoryErrors[0]?.error ?? "Storage warning recorded." : "No memory storage errors recorded."}`}
          label="Memory"
          tone={memoryErrors.length ? "warn" : "good"}
          value={formatBytes(snapshot.memoryStorage.total_bytes)}
        />
      </div>

      <CompactProfileStorageList memoryStorage={snapshot.memoryStorage} />

      <section className="mt-3 max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2">
        <h3 className="text-xs font-semibold">Needs attention</h3>
        {issues.length ? (
          <ul className="mt-2 grid gap-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">
            {issues.map(issue => <li key={issue}>{issue}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Nothing urgent is recorded. Keep Hermes / Mission Control as the only active lane.</p>
        )}
      </section>
      <section className="mt-3 max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2">
        <h3 className="text-xs font-semibold">Safe next actions</h3>
        <ul className="mt-2 grid gap-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">
          <li>Review Jenny's latest reply before sending the next bounded message.</li>
          <li>Keep paused projects on hold until you explicitly resume them.</li>
          <li>Use Kanban later after the real task board is reliable.</li>
        </ul>
      </section>
    </section>
  );
}

function CompactProfileStorageList({ memoryStorage }: { memoryStorage: ProfileMemoryStorage }) {
  const profiles = memoryStorage.profiles ?? [];
  return (
    <section className="mt-3 max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2" aria-label="Profile storage usage">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xs font-semibold">Profile storage usage</h3>
        <span className="text-[0.65rem] text-muted-foreground">{profiles.length} profiles / {formatBytes(memoryStorage.total_profile_data_bytes ?? memoryStorage.total_bytes)}</span>
      </div>
      {profiles.length ? (
        <div className="mt-2 grid gap-2">
          {profiles.map(profile => (
            <article key={`${profile.profile ?? "profile"}-${profile.home ?? ""}`} className="rounded-lg border border-border/60 bg-muted/20 p-2">
              <div className="flex min-w-0 items-center justify-between gap-2">
                <div className="min-w-0 truncate text-[0.72rem] font-semibold">{profile.profile ?? "default"}</div>
                <div className="shrink-0 text-[0.68rem] text-muted-foreground">mount {formatPercent(profile.mount?.percent_used)}</div>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-1 text-[0.65rem] text-muted-foreground">
                <div>Profile data: {formatBytes(profile.data?.bytes ?? profile.total_bytes)}</div>
                <div>State DB: {formatBytes(profile.data?.components?.state?.bytes)}</div>
                <div>Sessions: {formatBytes(profile.data?.components?.sessions?.bytes)}</div>
                <div>Recall files: {formatBytes(profile.recall_file_bytes ?? ((profile.memory?.bytes ?? 0) + (profile.user?.bytes ?? 0)))}</div>
                <div>Mount used: {formatBytes(profile.mount?.used_bytes)}</div>
                <div>Mount max: {formatBytes(profile.mount?.total_bytes)}</div>
              </div>
              <div className="mt-1 truncate text-[0.62rem] text-muted-foreground" title={profile.mount?.path ?? profile.home ?? ""}>
                {profile.mount?.path ?? "unknown mount"}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-[0.68rem] text-muted-foreground">No profile storage records are available yet.</p>
      )}
    </section>
  );
}

function CompactKanbanParkedCard() {
  return (
    <section className="max-w-full overflow-hidden rounded-2xl border border-amber-500/25 bg-amber-500/10 p-3" aria-label="Kanban parked">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">Kanban parked for later</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">The task board is hidden until it can show real tasks and reliable controls.</p>
        </div>
        <CompactHealthBadge tone="idle">Later</CompactHealthBadge>
      </div>
    </section>
  );
}

function CompactHealthBadge({ children, tone }: { children: string; tone: CompactHealthTone }) {
  return (
    <span className={cn("rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold", compactHealthToneClass(tone))}>
      {children}
    </span>
  );
}

function CompactHealthTile({
  detail,
  label,
  tone,
  value,
}: {
  detail: string;
  label: string;
  tone: CompactHealthTone;
  value: string;
}) {
  return (
    <article className="max-w-full overflow-hidden rounded-xl border border-border/70 bg-background p-2">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[0.65rem] font-medium uppercase text-muted-foreground [overflow-wrap:anywhere]">{label}</div>
          <div className="mt-1 text-xs font-semibold [overflow-wrap:anywhere]">{value}</div>
        </div>
        <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", compactHealthDotClass(tone))} aria-hidden="true" />
      </div>
      <p className="mt-2 text-[0.68rem] leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">{detail}</p>
    </article>
  );
}

function compactHealthToneClass(tone: CompactHealthTone): string {
  if (tone === "bad") {
    return "border-destructive/40 bg-destructive/10 text-destructive";
  }
  if (tone === "good") {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  }
  if (tone === "warn") {
    return "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300";
  }
  return "border-border/70 bg-muted/40 text-muted-foreground";
}

function compactHealthDotClass(tone: CompactHealthTone): string {
  if (tone === "bad") {
    return "bg-destructive";
  }
  if (tone === "good") {
    return "bg-emerald-500";
  }
  if (tone === "warn") {
    return "bg-amber-500";
  }
  return "bg-muted-foreground";
}

function dashboardUpdateNotice(status: WorkspaceStatus): string {
  if (!status.deployment_gap?.dashboard_deploy_needed) {
    return "";
  }

  const latest = status.deployment_gap?.latest_merged_pr ? ` PR #${status.deployment_gap.latest_merged_pr}` : " the latest accepted-live changes";
  return `Desktop can be current while phone/web waits for a safe dashboard-only update.${latest} is merged but not served by the dashboard yet.`;
}

function SafetyPill({ good, label, value }: { good: boolean; label: string; value: string }) {
  return (
    <div className={cn("min-w-0 rounded-xl border p-2", good ? "border-emerald-500/30 bg-emerald-500/10" : "border-amber-500/30 bg-amber-500/10")}>
      <div className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-semibold [overflow-wrap:anywhere]">{value}</div>
    </div>
  );
}

function CompactProjectCard({ copied, onCopy, projectView }: { copied: boolean; onCopy: () => void; projectView: ProjectViewModel }) {
  return (
    <article className="max-w-full overflow-hidden rounded-2xl border border-border/70 bg-card p-3 shadow-sm" data-testid={`compact-project-${projectView.project.project_id}`}>
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-base font-semibold leading-tight [overflow-wrap:anywhere]">{projectView.project.name}</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">{projectView.project.project_id}</p>
        </div>
        <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">compact</span>
      </div>
      <CompactField label="status" value={projectView.status} />
      <CompactField label="freshness" value={projectView.freshness} />
      <CompactField label="latest lane" value={projectView.latestLane} />
      <CompactField label="next recommended lane" value={projectView.nextLane} />
      <CompactField label="latest report/result" value={`${projectView.latestReport} / ${projectView.latestResult}`} />
      <CompactField label="risks/blockers" value={`${projectView.risks} / ${projectView.blockers}`} />
      <CompactField label="last action time" value={projectView.latestActivity} />
      <CompactField label="artifact/report links" value={projectView.artifactLinks} />
      <CompactField label="missing state" value={projectView.missingFields} />
      <button className="mt-3 w-full rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted" onClick={onCopy} type="button">
        {copied ? "Prompt copied" : "Copy next lane prompt"}
      </button>
      <p className="mt-2 text-[0.68rem] text-muted-foreground [overflow-wrap:anywhere]">Use project chat for the guarded Jenny mailbox, or copy this archive prompt manually.</p>
    </article>
  );
}

function CompactField({ label, value }: { label: string; value: string }) {
  return (
    <div className="mt-3 min-w-0 max-w-full overflow-hidden">
      <div className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm leading-snug [overflow-wrap:anywhere]">{value}</div>
    </div>
  );
}

function jennyWorkSessionStepClass(state: JennyWorkSessionStepState): string {
  if (state === "done") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200";
  }
  if (state === "active") {
    return "border-sky-500/35 bg-sky-500/10 text-sky-700 dark:text-sky-200";
  }
  if (state === "blocked") {
    return "border-red-500/35 bg-red-500/10 text-red-700 dark:text-red-200";
  }
  return "border-border/70 bg-background/70 text-muted-foreground";
}

function JennyWorkSessionTimeline({ steps }: { steps: JennyWorkSessionStep[] }) {
  return (
    <section aria-label="Jenny work session" className="mt-2 max-w-full overflow-hidden rounded-md border border-border/70 bg-background/70 p-2">
      <div className="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Work session</div>
      <div className="mt-2 grid min-w-0 gap-2 min-[420px]:grid-cols-2">
        {steps.map((step, index) => (
          <article className={cn("min-w-0 max-w-full rounded-md border px-2.5 py-2 text-xs", jennyWorkSessionStepClass(step.state))} key={step.label}>
            <div className="flex min-w-0 items-center gap-2 font-semibold">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full border border-current/25 text-[0.65rem]">{index + 1}</span>
              <span className="min-w-0 [overflow-wrap:anywhere]">{step.label}</span>
            </div>
            <p className="mt-1 max-w-full leading-snug opacity-80 [overflow-wrap:anywhere]">{step.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
