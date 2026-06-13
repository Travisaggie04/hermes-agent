import { useEffect, useMemo, useState } from "react";

import { fetchJSON } from "@/lib/api";
import { cn } from "@/lib/utils";

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
const WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox/create";
const WORKSPACE_JENNY_BRIDGE_INBOX_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/inbox";
const WORKSPACE_JENNY_BRIDGE_POLLER_STATUS_URL = "/api/plugins/mission-control-governance/workspace/jenny-bridge/poller-status";
const WORKSPACE_GITHUB_BRIDGE_STATUS_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/status";
const WORKSPACE_PROJECT_STATE_URL = "/api/plugins/mission-control-governance/workspace/project-state";

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
  "Prepare a non-live VPS dashboard runtime at accepted-live and validate it before any dashboard-only switch.",
  "Keep gateway update as a separate explicit lane.",
  "Do not trigger the laptop worker-node update automatically, restart/switch gateway, dispatch, send sessions, use Waha/social/payment/customer actions, enable new background workers/timers/daemons/cron, or inspect/print secrets.",
].join(" ");

const REAL_PROJECT_NAMES = [
  "Hermes / Mission Control",
  "Long-form Video",
  "Shorts Video",
  "Tool & Tally",
  "Waha Work",
] as const;

const TONIGHT_PROJECT_IDS = [
  "project-hermes-mission-control",
  "project-shorts-video",
  "project-long-form-video",
  "project-tool-tally",
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
  has_response?: boolean;
  message: string;
  project_id?: string;
  request_id?: string;
  status?: string;
  target_agent?: string;
}

interface JennyBridgeResponseRecord {
  message: string;
  project_id?: string;
  request_id?: string;
  responder?: string;
  response_id?: string;
  status?: string;
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
  session_send_enabled?: boolean;
  timer_enabled?: boolean;
  worker_enabled?: boolean;
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
  lane?: { active_lane_count?: number };
  runtime_worktree_guard?: { decision_state?: string };
  safety?: { dispatch_in_gateway?: boolean };
  stale_context?: { warnings?: string[] };
}

interface CompactSnapshot {
  challengeReviews: ChallengeReviewRecord[];
  jennyBridgeRequests: JennyBridgeRequestRecord[];
  jennyBridgeResponses: JennyBridgeResponseRecord[];
  jennyBridgePollerStatus: JennyBridgePollerStatus;
  githubBridgeStatus: GitHubBridgeStatus;
  laneRequests: LaneRequestRecord[];
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
    missingFields: listText(state?.missing_state_fields, "None — report state is current"),
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane ?? lane?.title, "No recommended lane yet"),
    projectBrief,
    projectState: state,
    project,
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

function buildCompactNextLanePrompt(projectView: ProjectViewModel, workspaceStatus: WorkspaceStatus): string {
  const guidance = PROJECT_LANE_GUIDANCE[projectView.project.project_id] ?? "Read-only Mission Control status lane. Report current state and the next safe manual step.";
  return [
    "MISSION CONTROL COMPACT — MANUAL COPY ONLY",
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
    "Send to Jenny disabled. Copy this prompt manually only after review.",
  ].join("\n");
}

function buildPhoneSafeProjectPacket(projectView: ProjectViewModel, requestText: string, workspaceStatus: WorkspaceStatus): string {
  const request = compactText(requestText, 420) || "<write the request>";
  const brief = projectView.projectBrief;
  const review = projectView.challengeReview;
  const categories = review?.challenge_categories?.length ? review.challenge_categories.join(", ") : "none recorded";
  const verdicts = review?.blocking_verdicts?.length ? review.blocking_verdicts.join(", ") : "none recorded";
  const guard = compactText(projectView.project.mistakes_guards, 220) || "manual-copy only; no live action";
  const packet = [
    "Project room request:",
    projectView.project.name,
    "",
    "Request:",
    request,
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
    "Forbidden: no send path, live mutation, Waha, queue, model, social, payment, worker, timer, deploy, restart, runtime switch, config/state, or secrets unless separately approved.",
    "",
    `Safety status: ${safetySummary(workspaceStatus)}`,
    "",
    "Return: preflight, recommendation, risks, next lane, safety confirmation.",
  ].join("\n").trim();
  return packet.length <= 1900 ? packet : `${packet.slice(0, 1897).trim()}...`;
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

async function loadCompactSnapshot(): Promise<CompactSnapshot> {
  const [workspaceStatus, projects, projectBriefs, challengeReviews, laneRequests, reports, projectState, jennyBridgeOutbox, jennyBridgeInbox, jennyBridgePollerStatus, githubBridgeStatus] = await Promise.all([
    fetchJSON<WorkspaceStatus>(WORKSPACE_STATUS_URL),
    fetchJSON<{ projects?: Array<WrappedRecord<ProjectRecord> | ProjectRecord> }>(WORKSPACE_PROJECTS_URL),
    fetchJSON<{ project_briefs?: Array<WrappedRecord<ProjectBriefRecord> | ProjectBriefRecord> }>(WORKSPACE_PROJECT_BRIEFS_URL),
    fetchJSON<{ challenge_reviews?: Array<WrappedRecord<ChallengeReviewRecord> | ChallengeReviewRecord> }>(WORKSPACE_CHALLENGE_REVIEWS_URL),
    fetchJSON<{ lane_requests?: Array<WrappedRecord<LaneRequestRecord> | LaneRequestRecord> }>(WORKSPACE_LANE_REQUESTS_URL),
    fetchJSON<{ reports?: Array<WrappedRecord<ReportRecord> | ReportRecord> }>(WORKSPACE_REPORTS_URL),
    fetchJSON<{ project_states?: ProjectStateRecord[] }>(WORKSPACE_PROJECT_STATE_URL),
    fetchJSON<{ requests?: Array<WrappedRecord<JennyBridgeRequestRecord> | JennyBridgeRequestRecord> }>(WORKSPACE_JENNY_BRIDGE_OUTBOX_URL),
    fetchJSON<{ responses?: Array<WrappedRecord<JennyBridgeResponseRecord> | JennyBridgeResponseRecord> }>(WORKSPACE_JENNY_BRIDGE_INBOX_URL),
    fetchJSON<JennyBridgePollerStatus>(WORKSPACE_JENNY_BRIDGE_POLLER_STATUS_URL),
    fetchJSON<GitHubBridgeStatus>(WORKSPACE_GITHUB_BRIDGE_STATUS_URL),
  ]);

  return {
    challengeReviews: unwrapRecords(challengeReviews.challenge_reviews),
    jennyBridgeRequests: unwrapRecords(jennyBridgeOutbox.requests),
    jennyBridgeResponses: unwrapRecords(jennyBridgeInbox.responses),
    jennyBridgePollerStatus,
    githubBridgeStatus,
    laneRequests: unwrapRecords(laneRequests.lane_requests),
    projectBriefs: unwrapRecords(projectBriefs.project_briefs),
    projectStates: projectState.project_states ?? [],
    projects: unwrapRecords(projects.projects),
    reports: unwrapRecords(reports.reports),
    workspaceStatus,
  };
}

export default function MissionControlCompactPage() {
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

  const realProjects = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.projects.filter(isRealProject).sort((a, b) => projectRank(a) - projectRank(b));
  }, [snapshot]);

  const supportProjects = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.projects.filter(project => !isRealProject(project) || isSmokeProject(project));
  }, [snapshot]);

  const selectedProjectView = useMemo(() => {
    if (!snapshot || !realProjects.length) return null;
    const selected = realProjects.find(project => project.project_id === selectedProjectId) ?? realProjects[0];
    return viewModelForProject(snapshot, selected);
  }, [realProjects, selectedProjectId, snapshot]);

  async function copyPrompt(projectView: ProjectViewModel) {
    const prompt = buildCompactNextLanePrompt(projectView, snapshot?.workspaceStatus ?? {});
    await navigator.clipboard?.writeText(prompt);
    setCopiedProjectId(projectView.project.project_id);
  }

  async function copyPhoneSafePacket(projectView: ProjectViewModel) {
    const packet = buildPhoneSafeProjectPacket(projectView, projectRequest, snapshot?.workspaceStatus ?? {});
    if (!navigator.clipboard?.writeText) {
      setRoomMessage("Clipboard unavailable. Select and copy the phone-safe packet manually.");
      return;
    }
    await navigator.clipboard.writeText(packet);
    setRoomMessage("Copied phone-safe project packet.");
  }

  async function queueJennyBridgeMessage(projectView: ProjectViewModel) {
    if (!projectRequest.trim()) {
      setRoomMessage("Write one bounded request before queuing a Jenny bridge message.");
      return;
    }
    setRoomBusy(true);
    setRoomMessage("");
    try {
      await fetchJSON(WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          ack_key: `${projectView.project.project_id}:${Date.now()}`,
          message: buildPhoneSafeProjectPacket(projectView, projectRequest, snapshot?.workspaceStatus ?? {}),
          project_id: projectView.project.project_id,
          sender: "codex",
          target_agent: "jenny",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Queued outbound Jenny bridge message. It is append-only and still requires Jenny polling/relay.");
    } catch (err) {
      setRoomMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setRoomBusy(false);
    }
  }

  async function queueHermesUpdateLane(projectView: ProjectViewModel) {
    setRoomBusy(true);
    setRoomMessage("");
    setProjectRequest(HERMES_UPDATE_LANE_REQUEST);
    try {
      await fetchJSON(WORKSPACE_JENNY_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          ack_key: `${projectView.project.project_id}:hermes-update:${Date.now()}`,
          message: buildHermesUpdateLanePacket(snapshot?.workspaceStatus ?? {}),
          project_id: projectView.project.project_id,
          sender: "codex",
          target_agent: "jenny",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      await refreshSnapshot();
      setRoomMessage("Queued safe Hermes update lane. It is append-only and does not update the laptop worker node, switch runtimes, or restart gateway.");
    } catch (err) {
      setRoomMessage(err instanceof Error ? err.message : String(err));
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
      setRoomMessage(err instanceof Error ? err.message : String(err));
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
      setRoomMessage(err instanceof Error ? err.message : String(err));
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
          draft_prompt: buildPhoneSafeProjectPacket(projectView, projectRequest, snapshot?.workspaceStatus ?? {}),
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
      setRoomMessage(err instanceof Error ? err.message : String(err));
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
      setReportMessage("Jenny report saved manually. Send to Jenny remains disabled.");
    } catch (err) {
      setReportMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingReport(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-3 py-4 text-foreground sm:px-5" data-testid="mission-control-compact-route">
      <header className="sticky top-0 z-10 -mx-3 border-b border-border/70 bg-background/95 px-3 pb-3 pt-1 backdrop-blur sm:-mx-5 sm:px-5">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Mission Control compact</p>
        <div className="mt-1 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold leading-tight">Phone project workspace</h1>
            <p className="mt-1 text-xs text-muted-foreground">Use direct backend http://100.115.125.111:9119. Proxy 9121 API routes are not required.</p>
          </div>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-emerald-700 dark:text-emerald-300">
            Send disabled
          </span>
        </div>
      </header>

      {loading ? <p className="mt-4 rounded-xl border border-border/70 p-3 text-sm text-muted-foreground">Loading compact Mission Control…</p> : null}
      {error ? <p className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</p> : null}

      {snapshot ? <SafetyStrip status={snapshot.workspaceStatus} /> : null}

      {snapshot ? (
        <CompactActiveLanes
          projectViews={realProjects.filter(project => TONIGHT_PROJECT_IDS.includes(project.project_id)).map(project => viewModelForProject(snapshot, project))}
          status={snapshot.workspaceStatus}
        />
      ) : null}

      {selectedProjectView ? (
        <CompactProjectRoom
          busy={roomBusy}
          message={roomMessage}
          bridgeRequests={snapshot?.jennyBridgeRequests.filter(request => request.project_id === selectedProjectView.project.project_id) ?? []}
          bridgeResponses={snapshot?.jennyBridgeResponses.filter(response => response.project_id === selectedProjectView.project.project_id) ?? []}
          bridgeStatus={snapshot?.jennyBridgePollerStatus ?? {}}
          githubBridgeStatus={snapshot?.githubBridgeStatus ?? {}}
          onCopyPacket={() => void copyPhoneSafePacket(selectedProjectView)}
          onQueueBridge={() => void queueJennyBridgeMessage(selectedProjectView)}
          onQueueHermesUpdate={selectedProjectView.project.project_id === HERMES_PROJECT_ID ? () => void queueHermesUpdateLane(selectedProjectView) : undefined}
          onRefreshBridge={() => void refreshBridge()}
          onRequestChange={setProjectRequest}
          onSaveChallenge={() => void saveChallengeDraft(selectedProjectView)}
          onSaveLane={() => void saveReadOnlyLaneDraft(selectedProjectView)}
          onSelectProject={projectId => {
            setSelectedProjectId(projectId);
            setRoomMessage("");
          }}
          packet={buildPhoneSafeProjectPacket(selectedProjectView, projectRequest, snapshot?.workspaceStatus ?? {})}
          projectRequest={projectRequest}
          projects={realProjects}
          selectedProjectView={selectedProjectView}
        />
      ) : null}

      {snapshot ? (
        <CompactProjectKanban projectViews={realProjects.map(project => viewModelForProject(snapshot, project))} />
      ) : null}

      {snapshot ? (
        <CompactReportIngestion
          form={reportForm}
          message={reportMessage}
          onChange={updateReportField}
          onSave={() => void saveManualReport()}
          projects={realProjects}
          saving={savingReport}
        />
      ) : null}

      <section className="mt-4 grid gap-3" aria-label="Five real Mission Control projects">
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
        <section className="mt-5 rounded-xl border border-dashed border-border/70 bg-muted/20 p-3 opacity-70" aria-label="Smoke support projects de-emphasized">
          <h2 className="text-sm font-semibold">Smoke/support records de-emphasized</h2>
          <div className="mt-2 grid gap-2">
            {supportProjects.map(project => (
              <p className="rounded-lg border border-border/60 bg-background/50 p-2 text-xs text-muted-foreground" key={project.project_id || project.name}>
                {project.name} — support only
              </p>
            ))}
          </div>
        </section>
      ) : null}
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
    <section className="mt-4 rounded-2xl border border-border/70 bg-card p-3" aria-label="Tonight active lanes compact">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Tonight / Active Lanes</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground">Four-project overnight board. Display-only; no dispatch, queue mutation, worker, or timer.</p>
        </div>
        <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-[0.65rem] font-semibold text-sky-700 dark:text-sky-300">
          display-only
        </span>
      </div>
      <div className="mt-3 grid gap-2">
        {projectViews.map(projectView => (
          <article className="rounded-xl border border-border/70 bg-background p-2 text-xs" key={projectView.project.project_id}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold leading-tight">{projectView.project.name}</h3>
                <p className="mt-1 text-[0.68rem] text-muted-foreground">{projectView.status}</p>
              </div>
              <span className="shrink-0 rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{compactActiveLaneStage(projectView)}</span>
            </div>
            <CompactField label="next safe lane" value={projectView.nextLane} />
            <CompactField label="latest evidence" value={projectView.latestReport} />
            <CompactField label="report contract" value={reportContractSummary(projectView.report)} />
            <CompactField label="readiness" value={projectView.readinessDetail} />
          </article>
        ))}
      </div>
      <p className="mt-3 text-[0.68rem] text-muted-foreground">Safety status: {safetySummary(status)}</p>
    </section>
  );
}

function CompactProjectRoom({
  busy,
  bridgeRequests,
  bridgeResponses,
  bridgeStatus,
  githubBridgeStatus,
  message,
  onCopyPacket,
  onQueueBridge,
  onQueueHermesUpdate,
  onRefreshBridge,
  onRequestChange,
  onSaveChallenge,
  onSaveLane,
  onSelectProject,
  packet,
  projectRequest,
  projects,
  selectedProjectView,
}: {
  busy: boolean;
  bridgeRequests: JennyBridgeRequestRecord[];
  bridgeResponses: JennyBridgeResponseRecord[];
  bridgeStatus: JennyBridgePollerStatus;
  githubBridgeStatus: GitHubBridgeStatus;
  message: string;
  onCopyPacket: () => void;
  onQueueBridge: () => void;
  onQueueHermesUpdate?: () => void;
  onRefreshBridge: () => void;
  onRequestChange: (value: string) => void;
  onSaveChallenge: () => void;
  onSaveLane: () => void;
  onSelectProject: (projectId: string) => void;
  packet: string;
  projectRequest: string;
  projects: ProjectRecord[];
  selectedProjectView: ProjectViewModel;
}) {
  const sessions = selectedProjectView.projectState?.recent_sessions ?? [];
  const review = selectedProjectView.challengeReview;
  const brief = selectedProjectView.projectBrief;
  const repliedRequestIds = new Set(bridgeResponses.map(response => response.request_id).filter(Boolean));
  return (
    <section className="mt-4 grid gap-3 lg:grid-cols-[minmax(12rem,18rem)_1fr]" aria-label="Project Rooms">
      <div className="rounded-2xl border border-border/70 bg-card p-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Project Rooms</h2>
          <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{projects.length}</span>
        </div>
        <div className="mt-3 grid gap-2">
          {projects.map(project => (
            <button
              className={cn(
                "rounded-xl border px-3 py-2 text-left text-sm transition hover:bg-muted",
                project.project_id === selectedProjectView.project.project_id ? "border-emerald-500/40 bg-emerald-500/10" : "border-border/70 bg-background",
              )}
              key={project.project_id}
              onClick={() => onSelectProject(project.project_id)}
              type="button"
            >
              <span className="block font-semibold">{project.name}</span>
              <span className="mt-0.5 block text-[0.68rem] text-muted-foreground">{project.project_id}</span>
            </button>
          ))}
        </div>
      </div>

      <article className="rounded-2xl border border-border/70 bg-card p-3" data-testid="compact-project-room">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Project Room</p>
            <h2 className="mt-1 text-lg font-semibold leading-tight">Project Room: {selectedProjectView.project.name}</h2>
          </div>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-emerald-700 dark:text-emerald-300">
            {selectedProjectView.readinessLabel}
          </span>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <CompactField label="current goal" value={selectedProjectView.currentGoal} />
          <CompactField label="readiness" value={selectedProjectView.readinessDetail} />
          <CompactField label="latest report contract" value={reportContractSummary(selectedProjectView.report)} />
          <CompactField label="latest report/result" value={`${selectedProjectView.latestReport} / ${selectedProjectView.latestResult}`} />
          <CompactField label="next recommended lane" value={selectedProjectView.nextLane} />
          <CompactField label="project brief" value={compactText(brief?.outcome, 320) || "No project brief recorded"} />
          <CompactField
            label="challenge review"
            value={review ? `${review.decision_state ?? "unknown"} / ${review.recommended_path ?? "No recommended path recorded"}` : "No challenge review recorded"}
          />
        </div>

        <label className="mt-4 grid gap-1 text-xs font-medium">
          Ask Jenny / Propose Work
          <textarea
            className="min-h-24 rounded-xl border border-border/80 bg-background px-3 py-2 text-sm"
            onChange={event => onRequestChange(event.target.value)}
            placeholder="One bounded project request..."
            value={projectRequest}
          />
        </label>

        <div className="mt-3 grid gap-2 sm:grid-cols-5">
          <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy} onClick={onCopyPacket} type="button">
            Copy phone-safe packet
          </button>
          <button className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-500/15 disabled:opacity-60 dark:text-emerald-300" disabled={busy} onClick={onQueueBridge} type="button">
            Queue for Jenny bridge
          </button>
          <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy} onClick={onRefreshBridge} type="button">
            Refresh bridge
          </button>
          <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy} onClick={onSaveChallenge} type="button">
            Save challenge draft
          </button>
          <button className="rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={busy} onClick={onSaveLane} type="button">
            Save read-only lane draft
          </button>
        </div>
        {onQueueHermesUpdate ? (
          <div className="mt-2 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold">Hermes update lane</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Queues a guarded VPS/laptop worker-node update checklist only. No runtime switch, restart, or laptop update happens here.
                </p>
              </div>
              <button className="rounded-xl border border-amber-500/40 px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-500/10 disabled:opacity-60 dark:text-amber-300" disabled={busy} onClick={onQueueHermesUpdate} type="button">
                Start Hermes update lane
              </button>
            </div>
          </div>
        ) : null}
        {message ? <p className="mt-2 text-xs text-muted-foreground">{message}</p> : null}

        <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Jenny bridge</h3>
            <span className="rounded-full border border-emerald-500/30 px-2 py-0.5 text-[0.65rem] text-emerald-700 dark:text-emerald-300">no dispatch</span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Record-backed outbox/inbox for Jenny relay. Use refresh to check replies. Direct send remains disabled.</p>
          <div className="mt-3 grid gap-2 rounded-lg border border-emerald-500/20 bg-background/70 p-2 text-xs sm:grid-cols-2">
            <CompactField label="manual relay" value={bridgeStatus.manual_start_only === false ? "disabled" : "manual-start only"} />
            <CompactField label="pending" value={String(bridgeStatus.pending_count ?? bridgeRequests.filter(request => (request.bridge_state ?? request.status ?? "queued") !== "replied").length)} />
            <CompactField label="last status" value={bridgeStatus.last_status ?? "idle"} />
            <CompactField label="last response" value={bridgeStatus.last_response_request_id || bridgeStatus.last_response_at || "none"} />
            <CompactField label="last error" value={bridgeStatus.last_error || "none"} />
            <CompactField label="worker/timer" value={`worker ${bridgeStatus.worker_enabled ? "enabled" : "disabled"} / timer ${bridgeStatus.timer_enabled ? "enabled" : "disabled"}`} />
          </div>
          <div className="mt-3 grid gap-2 rounded-lg border border-sky-500/20 bg-sky-500/5 p-2 text-xs sm:grid-cols-2">
            <CompactField label="GitHub mailbox" value={githubBridgeStatus.manual_start_only === false ? "disabled" : "manual-start only"} />
            <CompactField label="GitHub mode" value={githubBridgeStatus.mode || "manual"} />
            <CompactField label="GitHub pending" value={String(githubBridgeStatus.pending_count ?? 0)} />
            <CompactField label="GitHub last poll" value={githubBridgeStatus.last_poll_at || githubBridgeStatus.last_status || "not polled"} />
            <CompactField label="GitHub last response" value={githubBridgeStatus.last_response_request_id || githubBridgeStatus.last_response_at || "none"} />
            <CompactField label="GitHub last error" value={githubBridgeStatus.last_error || "none"} />
            <CompactField label="daemon/worker/timer" value={`daemon ${githubBridgeStatus.daemon_enabled ? "enabled" : "disabled"} / worker ${githubBridgeStatus.worker_enabled ? "enabled" : "disabled"} / timer ${githubBridgeStatus.timer_enabled ? "enabled" : "disabled"}`} />
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <CompactBridgeList
              title="Outbound"
              empty="No queued messages."
              items={bridgeRequests}
              renderItem={item => `${item.bridge_state ?? (item.request_id && repliedRequestIds.has(item.request_id) ? "replied" : item.status ?? "queued")} / ${item.message}`}
            />
            <CompactBridgeList title="Replies" empty="No replies yet." items={bridgeResponses} renderItem={item => `${item.responder ?? "jenny"} / ${item.message}`} />
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-border/70 bg-background p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Phone-safe packet</h3>
            <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{packet.length} / 1900</span>
          </div>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-muted-foreground">{packet}</pre>
        </div>

        <div className="mt-4 rounded-xl border border-border/70 bg-background p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Project Sessions</h3>
            <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{sessions.length} linked</span>
          </div>
          <div className="mt-2 grid gap-2">
            {sessions.length ? (
              sessions.map((session, index) => (
                <div className="rounded-lg border border-border/60 bg-card/60 p-2 text-xs" key={session.session_id || index}>
                  <div className="font-semibold">{session.title || session.session_id || "Linked session"}</div>
                  <div className="mt-0.5 text-muted-foreground">
                    {[session.profile, session.source, session.cwd_snapshot].filter(Boolean).join(" / ") || "session context"}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">No linked sessions for this project yet.</p>
            )}
          </div>
        </div>
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
    <section className="rounded-lg border border-border/70 bg-background/70 p-2 text-xs">
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-semibold">{title}</h4>
        <span className="text-muted-foreground">{items.length}</span>
      </div>
      <div className="mt-2 grid gap-2">
        {items.length ? (
          items.slice(-2).reverse().map((item, index) => (
            <p className="line-clamp-3 rounded-md border border-border/60 bg-background p-2 text-muted-foreground" key={index}>
              {renderItem(item)}
            </p>
          ))
        ) : (
          <p className="text-muted-foreground">{empty}</p>
        )}
      </div>
    </section>
  );
}

function CompactProjectKanban({ projectViews }: { projectViews: ProjectViewModel[] }) {
  return (
    <section className="mt-4 rounded-2xl border border-border/70 bg-card p-3" aria-label="Project Kanban">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Project Kanban</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground">
            Record-backed lifecycle. Dragging disabled; cards move only when briefs, challenge reviews, lane drafts, approvals, or reports change.
          </p>
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[0.65rem] font-semibold text-amber-700 dark:text-amber-300">
          read-only board
        </span>
      </div>

      <div className="mt-3 grid gap-2">
        {PROJECT_KANBAN_COLUMNS.map(column => {
          const cards = projectViews.filter(projectView => projectKanbanColumnFor(projectView) === column.id);
          return (
            <section className="rounded-xl border border-border/70 bg-background p-2" key={column.id}>
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-xs font-semibold">{column.title}</h3>
                <span className="rounded-full border border-border/70 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{cards.length}</span>
              </div>
              <p className="mt-1 text-[0.65rem] leading-snug text-muted-foreground">{column.description}</p>
              <div className="mt-2 grid gap-2">
                {cards.length ? (
                  cards.map(projectView => (
                    <article className="rounded-lg border border-border/60 bg-card/70 p-2 text-xs" key={projectView.project.project_id}>
                      <div className="font-semibold leading-tight">{projectView.project.name}</div>
                      <div className="mt-1 text-[0.68rem] text-muted-foreground">{projectView.readinessLabel}</div>
                      <div className="mt-2 text-[0.68rem] leading-snug text-muted-foreground">Lane: {projectView.latestLane}</div>
                      <div className="mt-1 text-[0.68rem] leading-snug text-muted-foreground">Next: {projectView.nextLane}</div>
                      <div className="mt-1 text-[0.68rem] leading-snug text-muted-foreground">Contract: {reportContractSummary(projectView.report)}</div>
                    </article>
                  ))
                ) : (
                  <p className="rounded-lg border border-dashed border-border/70 p-2 text-[0.68rem] text-muted-foreground">No project cards.</p>
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
    <section className="mt-4 rounded-2xl border border-border/70 bg-card p-3" aria-label="Manual Jenny report ingestion compact">
      <h2 className="text-sm font-semibold">Save Jenny report manually</h2>
      <p className="mt-1 text-[0.68rem] text-muted-foreground">Append-only reports/create only. Send to Jenny disabled; no dispatch or queue routing.</p>
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
      <CompactReportInput label="Risks/blockers — one per line" onChange={value => onChange("risks", value)} value={form.risks} />
      <CompactReportInput label="Artifact/report links — one per line" onChange={value => onChange("artifactLinks", value)} value={form.artifactLinks} />
      <CompactReportInput label="Changed files/evidence — one per line" onChange={value => onChange("changedFiles", value)} value={form.changedFiles} />
      <CompactReportInput label="Next recommended lane" onChange={value => onChange("nextRecommendedLane", value)} value={form.nextRecommendedLane} />
      <button className="mt-3 w-full rounded-xl border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60" disabled={saving} onClick={onSave} type="button">
        {saving ? "Saving report…" : "Save Jenny report manually"}
      </button>
      {message ? <p className="mt-2 text-xs text-muted-foreground">{message}</p> : null}
    </section>
  );
}

function CompactReportInput({ label, onChange, value }: { label: string; onChange: (value: string) => void; value: string }) {
  return (
    <label className="mt-3 grid gap-1 text-xs font-medium">
      {label}
      <textarea className="min-h-16 rounded-xl border border-border/80 bg-background px-3 py-2 text-sm" onChange={event => onChange(event.target.value)} value={value} />
    </label>
  );
}

function SafetyStrip({ status }: { status: WorkspaceStatus }) {
  const guard = status.runtime_worktree_guard?.decision_state ?? "unknown";
  const dispatch = status.safety?.dispatch_in_gateway;
  const activeLaneCount = status.lane?.active_lane_count ?? 0;
  const warnings = status.stale_context?.warnings ?? [];
  return (
    <section className="mt-4 grid grid-cols-2 gap-2 text-xs" aria-label="Safety status">
      <SafetyPill label="Guard" good={guard === "pass"} value={guard} />
      <SafetyPill label="Dispatch" good={dispatch === false} value={dispatch === false ? "false" : "unknown"} />
      <SafetyPill label="Active lanes" good={activeLaneCount === 0} value={String(activeLaneCount)} />
      <SafetyPill label="Warnings" good={warnings.length === 0} value={warnings.length ? String(warnings.length) : "none"} />
    </section>
  );
}

function SafetyPill({ good, label, value }: { good: boolean; label: string; value: string }) {
  return (
    <div className={cn("rounded-xl border p-2", good ? "border-emerald-500/30 bg-emerald-500/10" : "border-amber-500/30 bg-amber-500/10")}>
      <div className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-semibold">{value}</div>
    </div>
  );
}

function CompactProjectCard({ copied, onCopy, projectView }: { copied: boolean; onCopy: () => void; projectView: ProjectViewModel }) {
  return (
    <article className="rounded-2xl border border-border/70 bg-card p-3 shadow-sm" data-testid={`compact-project-${projectView.project.project_id}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold leading-tight">{projectView.project.name}</h2>
          <p className="mt-1 text-[0.68rem] text-muted-foreground">{projectView.project.project_id}</p>
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
      <p className="mt-2 text-[0.68rem] text-muted-foreground">Send to Jenny disabled — manual copy only.</p>
    </article>
  );
}

function CompactField({ label, value }: { label: string; value: string }) {
  return (
    <div className="mt-3">
      <div className="text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm leading-snug">{value}</div>
    </div>
  );
}
