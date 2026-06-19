import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Folder,
  Loader2,
  Menu,
  Plus,
  RefreshCw,
  Send,
  X,
} from "lucide-react";

import { fetchJSON, type ModelInfoResponse, type ModelOptionsResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const WORKSPACE_PROJECTS_URL = "/api/plugins/mission-control-governance/workspace/projects";
const WORKSPACE_STATUS_URL = "/api/plugins/mission-control-governance/workspace-status";
const WORKSPACE_GITHUB_BRIDGE_STATUS_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/status";
const WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/outbox/create";
const WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL = "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once";
const MODEL_INFO_URL = "/api/model/info";
const MODEL_OPTIONS_URL = "/api/model/options";

const SELECTED_PROJECT_STORAGE_KEY = "jenny-mobile-selected-project";
const SELECTED_MODEL_STORAGE_KEY = "jenny-mobile-selected-model";
const SELECTED_EFFORT_STORAGE_KEY = "jenny-mobile-selected-effort";
const MOBILE_MESSAGE_LIMIT = 1800;
const MAX_MODEL_CHOICES = 60;
const ANSWER_ONCE_TIMEOUT_MS = 45_000;

const MOBILE_PROJECTS: MobileProject[] = [
  {
    name: "Hermes / Mission Control",
    project_id: "project-hermes-mission-control",
    status: "Active",
  },
  {
    name: "Long-form Video",
    project_id: "project-long-form-video",
    status: "Paused",
  },
  {
    name: "Shorts Video",
    project_id: "project-shorts-video",
    status: "Paused",
  },
  {
    name: "Tool & Tally",
    project_id: "project-tool-tally",
    status: "Paused",
  },
  {
    name: "Waha Work",
    project_id: "project-waha-work",
    status: "Paused",
  },
  {
    name: "Other chats",
    project_id: "other-chats",
    status: "Unfiled",
  },
];

const MOBILE_PROJECT_ORDER = new Map(
  MOBILE_PROJECTS.map((project, index) => [project.project_id, index]),
);

const MOBILE_EFFORTS = [
  { label: "Minimal", value: "minimal" },
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Extra high", value: "xhigh" },
] as const;

type MobileMessageStatus = "queued" | "working" | "replied" | "failed" | "sent";
type MobileMessageRole = "assistant" | "user" | "system";

interface WrappedRecord<T> {
  record?: T;
}

interface MobileProject {
  name: string;
  project_id: string;
  status?: string;
}

interface GitHubBridgeMessageRecord {
  created_at?: string;
  from_agent?: string;
  github_comment_id?: string;
  message?: string;
  metadata?: Record<string, unknown>;
  project_id?: string;
  request_id?: string;
  status?: string;
  to_agent?: string;
}

interface GitHubBridgeStatusRecord {
  created_at?: string;
  handled_request_id?: string;
  last_error?: string;
  mode?: string;
  pending_count?: number;
  status?: string;
}

interface GitHubBridgeStatus {
  background_pending_count?: number;
  daemon_enabled?: boolean;
  discord_automation_enabled?: boolean;
  dispatch_enabled?: boolean;
  execution_enabled?: boolean;
  foreground_watch_running?: boolean;
  foreground_watch_supported?: boolean;
  last_error?: string;
  last_poll_at?: string;
  last_response_at?: string;
  last_response_request_id?: string;
  last_status?: string;
  manual_start_only?: boolean;
  model_routing_enabled?: boolean;
  pending_count?: number;
  pending_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  recent_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  response_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  send_to_jenny_enabled?: boolean;
  session_send_enabled?: boolean;
  status_records?: Array<WrappedRecord<GitHubBridgeStatusRecord> | GitHubBridgeStatusRecord>;
  timer_enabled?: boolean;
  visible_pending_count?: number;
  visible_pending_messages?: Array<WrappedRecord<GitHubBridgeMessageRecord> | GitHubBridgeMessageRecord>;
  worker_dispatch_enabled?: boolean;
  would_execute?: boolean;
  worker_enabled?: boolean;
}

interface MobileExecutionLockSource {
  dispatch_enabled?: unknown;
  execution_enabled?: unknown;
  execution_ready?: unknown;
  live_operations_enabled?: unknown;
  send_to_jenny_enabled?: unknown;
  session_send_enabled?: unknown;
  worker_dispatch_enabled?: unknown;
  worker_enabled?: unknown;
  would_dispatch?: unknown;
  would_execute?: unknown;
  would_session_send?: unknown;
}

interface MobileReportLifecycle extends MobileExecutionLockSource {
  blocked?: boolean;
  blocked_reasons?: string[];
  duplicate_report_ids?: string[];
  open_report_ids?: string[];
  report_overwrite_conflict_count?: number;
  report_overwrite_conflict_ids?: string[];
  reviewed_report_ids?: string[];
  runs_missing_report?: string[];
  runs_with_missing_linked_report_ids?: Record<string, string[]>;
  terminal_report_ids?: string[];
}

interface MobileWorkerNodePresence extends MobileExecutionLockSource {
  blocked_reasons?: string[];
  capability_summary?: string;
  last_seen_at?: string;
  online?: boolean;
  presence_state?: string;
  worker_host_label?: string;
  worker_run_id?: string;
}

interface MobileWorkerNodeInstructionPreview extends MobileExecutionLockSource {
  available?: boolean;
  blocked_reasons?: string[];
  manual_handoff_only?: boolean;
  manual_handoff_prompt?: string;
  ready_for_handoff?: boolean;
  worker_host_label?: string;
}

interface MobileWorkerNodeOrchestration extends MobileExecutionLockSource {
  active_count?: number;
  active_runs?: Array<Record<string, unknown>>;
  blocked_reasons?: string[];
  latest_by_id?: Record<string, Record<string, unknown>>;
}

interface MobileWorkspaceStatus {
  hard_boundary_contract?: MobileExecutionLockSource & {
    blocked?: boolean;
    blocked_reasons?: string[];
    live_flag_violations?: string[];
  };
  operator_decision_packet?: MobileExecutionLockSource & {
    execution_lock_blocked_reasons?: string[];
  };
  orchestration_readiness?: MobileExecutionLockSource & {
    states?: {
      laptop_codex_worker_node?: string;
      scoped_pr_creation?: string;
      supervised_read_only_autonomy?: string;
    };
  };
  report_lifecycle?: MobileReportLifecycle;
  worker_node_instruction_preview?: MobileWorkerNodeInstructionPreview;
  worker_node_orchestration?: MobileWorkerNodeOrchestration;
  worker_node_presence?: MobileWorkerNodePresence;
}

interface OutboxResponse {
  message?: GitHubBridgeMessageRecord | null;
  status?: GitHubBridgeStatusRecord;
}

interface AnswerOnceResponse {
  answered?: boolean;
  response?: GitHubBridgeMessageRecord;
  status?: GitHubBridgeStatusRecord;
}

interface ChatMessage {
  createdAt: string;
  id: string;
  optimistic?: boolean;
  requestId?: string;
  role: MobileMessageRole;
  status: MobileMessageStatus;
  text: string;
}

interface RunState {
  detail: string;
  requestId?: string;
  status: "idle" | "queued" | "working" | "replied" | "failed";
}

interface MobileBridgeSafety {
  reasons: string[];
  safe: boolean;
}

interface ModelChoice {
  key: string;
  label: string;
  model: string;
  provider: string;
}

function unwrapRecords<T>(items: Array<WrappedRecord<T> | T> | undefined): T[] {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => ("record" in Object(item) ? (item as WrappedRecord<T>).record : item))
    .filter(Boolean) as T[];
}

function compactText(value: string | undefined, maxChars: number): string {
  const normalized = (value ?? "").replace(/\s+/g, " ").trim();
  if (normalized.length <= maxChars) return normalized;
  return `${normalized.slice(0, Math.max(0, maxChars - 3)).trim()}...`;
}

function boundedMobileMessage(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length <= MOBILE_MESSAGE_LIMIT) return trimmed;
  return `${trimmed.slice(0, MOBILE_MESSAGE_LIMIT - 3).trim()}...`;
}

async function fetchJSONWithTimeout<T>(url: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchJSON<T>(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Jenny reply timed out. The message is still queued; retry when the bridge is ready.");
    }
    throw err;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function stripHiddenJennyContext(value: string): string {
  const trimmed = value.trimStart();
  if (!/^Hidden Jenny OS project context:/i.test(trimmed)) return value;

  const rest = trimmed.replace(/^Hidden Jenny OS project context:[ \t]*\r?\n/i, "");
  const blank = rest.match(/\r?\n[ \t]*\r?\n/);
  if (blank?.index !== undefined) {
    return rest.slice(blank.index + blank[0].length).trimStart();
  }

  const lines = rest.split(/\r?\n/);
  const visibleRule = lines.findIndex((line) => /^Visible chat rule:/i.test(line.trim()));
  return visibleRule >= 0 ? lines.slice(visibleRule + 1).join("\n").trimStart() : "";
}

function projectRequestPreview(value: string, maxChars: number): string {
  const visible = stripHiddenJennyContext(value);
  const normalized = visible.replace(/\s+/g, " ").trim();
  const patterns = [
    /(?:^|\s)Visible request from Travis:\s*([\s\S]*?)(?=\s+Reply as Jenny|$)/i,
    /^Spec-first request for Jenny:\s*Project:\s*.+?\s+Request Travis is considering:\s*([\s\S]*?)(?=\s+Current intake:|$)/i,
    /^Project room request:\s*(?:.+?\s+)?Request:\s*([\s\S]*?)(?=\s+(?:Request intake:|Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i,
    /(?:^|[\s/])Request:\s*([\s\S]*?)(?=\s+(?:Request intake:|Current brief:|Challenge state:|Categories:|Blocking verdicts:|Readiness:|Current goal:|Allowed:|Forbidden:|Safety(?: status)?:|Structured handoff:|Evidence contract:)|$)/i,
  ];
  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (match?.[1]) return compactText(match[1], maxChars);
  }
  return compactText(visible, maxChars) || "Project message";
}

function cleanVisibleUserMessage(
  metadata: Record<string, unknown> | undefined,
  fallback: string | undefined,
): string {
  const userMessage = typeof metadata?.user_message === "string" ? metadata.user_message : "";
  return compactText(userMessage || projectRequestPreview(fallback ?? "", 900), 900);
}

function cleanJennyReply(value: string | undefined): string {
  const normalized = (value ?? "").replace(/\r\n/g, "\n").trim();
  if (!normalized) return "Jenny replied.";
  const lower = normalized.toLowerCase();
  const technicalMarkers = [
    "session_id:",
    "preflight",
    "safety confirmation",
    "no live github/ci/runtime check",
    "stale-runtime confusion",
    "do not deploy",
    "do not resume tool",
  ];
  if (!technicalMarkers.some((marker) => lower.includes(marker))) {
    return normalized;
  }
  const recommendation = normalized.match(
    /(?:^|\n)\s*recommendation\s*\n([\s\S]*?)(?=\n\s*(?:risks?|safety confirmation|validation|evidence|blockers?|approval|$))/i,
  )?.[1];
  const cleaned = compactText(recommendation?.replace(/^\s*[-*]\s*/gm, "").replace(/\n+/g, " "), 220);
  return cleaned
    ? `Jenny replied with a guarded status update. Recommendation: ${cleaned}`
    : "Jenny replied with a guarded status update. Open Activity for details before relying on it.";
}

function chatStatusLabel(value: string | undefined): MobileMessageStatus {
  switch (value) {
    case "queued":
    case "retry_requested":
      return "queued";
    case "hermes_answer_started":
    case "manual_hermes_answer_started":
      return "working";
    case "replied":
    case "closed":
    case "response_appended":
    case "hermes_answer_completed":
      return "replied";
    case "failed":
    case "error":
    case "hermes_answer_error":
      return "failed";
    default:
      return "sent";
  }
}

function timestampValue(value?: string): number {
  const time = Date.parse(value ?? "");
  return Number.isFinite(time) ? time : 0;
}

function isDiagnosticMessage(message?: string): boolean {
  const text = (message ?? "").toLowerCase();
  return [
    "codex app-server startup failed",
    "desktop phone bridge",
    "failure guarded",
    "mission control two process",
    "success smoke reached",
    "bridge works",
  ].some((marker) => text.includes(marker));
}

function isOperatorMessage(message: GitHubBridgeMessageRecord): boolean {
  const fromAgent = message.from_agent?.toLowerCase() ?? "";
  const requestId = message.request_id?.toLowerCase() ?? "";
  const text = message.message?.toLowerCase() ?? "";
  return (
    fromAgent === "codex" ||
    requestId.startsWith("codex-") ||
    text.includes("bounded dashboard-only deploy check") ||
    text.includes("review pr #")
  );
}

function messageKey(message: ChatMessage): string {
  return message.requestId ? `${message.requestId}:${message.role}` : message.id;
}

function mergeMessages(existing: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  const byKey = new Map<string, ChatMessage>();
  for (const message of existing) {
    byKey.set(messageKey(message), message);
  }
  for (const message of incoming) {
    const key = messageKey(message);
    const current = byKey.get(key);
    byKey.set(key, current?.optimistic && !message.optimistic ? message : { ...current, ...message });
  }
  return [...byKey.values()]
    .sort((left, right) => timestampValue(left.createdAt) - timestampValue(right.createdAt))
    .slice(-24);
}

function messagesFromStatus(status: GitHubBridgeStatus): ChatMessage[] {
  const rawMessages = [
    ...unwrapRecords(status.recent_messages),
    ...unwrapRecords(status.visible_pending_messages),
    ...unwrapRecords(status.response_messages),
  ];
  const seen = new Set<string>();
  const responses = new Set(
    rawMessages
      .filter((message) => message.from_agent === "jenny" || ["replied", "closed"].includes(message.status ?? ""))
      .map((message) => message.request_id)
      .filter(Boolean) as string[],
  );

  return rawMessages
    .filter((message) => !isDiagnosticMessage(message.message) && !isOperatorMessage(message))
    .filter((message) => {
      const key = [
        message.request_id ?? "",
        message.from_agent ?? "",
        message.to_agent ?? "",
        message.status ?? "",
        message.github_comment_id ?? "",
        message.created_at ?? "",
      ].join(":");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((message) => {
      const role: MobileMessageRole = message.from_agent === "jenny" ? "assistant" : "user";
      const requestId = message.request_id;
      const statusValue = role === "assistant"
        ? "replied"
        : requestId && responses.has(requestId)
          ? "replied"
          : chatStatusLabel(message.status);
      return {
        createdAt: message.created_at || new Date().toISOString(),
        id: message.github_comment_id || message.request_id || message.created_at || `${role}-${Math.random()}`,
        requestId,
        role,
        status: statusValue,
        text: role === "assistant"
          ? cleanJennyReply(message.message)
          : cleanVisibleUserMessage(message.metadata, message.message),
      };
    })
    .sort((left, right) => timestampValue(left.createdAt) - timestampValue(right.createdAt))
    .slice(-20);
}

function latestPendingRequestId(messages: ChatMessage[]): string {
  const pending = [...messages].reverse().find(
    (message) => message.role === "user" && ["queued", "working", "failed"].includes(message.status) && message.requestId,
  );
  return pending?.requestId ?? "";
}

function statusFromBridge(status: GitHubBridgeStatus | undefined): RunState {
  if (!status) {
    return { detail: "Ready for a bounded Jenny request.", status: "idle" };
  }
  const lastStatus = status.last_status ?? "";
  const lastError = status.last_error ?? "";
  if (lastError) {
    return { detail: lastError, requestId: status.last_response_request_id, status: "failed" };
  }
  if (/started|working/i.test(lastStatus)) {
    return { detail: "Jenny is working on the latest request.", requestId: status.last_response_request_id, status: "working" };
  }
  if (/completed|response_appended|replied/i.test(lastStatus)) {
    return { detail: "Jenny replied to the latest request.", requestId: status.last_response_request_id, status: "replied" };
  }
  if ((status.visible_pending_count ?? status.pending_count ?? 0) > 0) {
    return { detail: "A message is queued for Jenny.", status: "queued" };
  }
  return { detail: "Ready for a bounded Jenny request.", status: "idle" };
}

function mobileBridgeSafety(status: GitHubBridgeStatus | undefined): MobileBridgeSafety {
  const reasons: string[] = [];
  if (!status) {
    reasons.push("bridge status not loaded");
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
      if (mobileLiveFlagEnabled(status[flag])) reasons.push(reason);
    }
  }
  return { reasons, safe: reasons.length === 0 };
}

function mobileLiveFlagEnabled(value: unknown): boolean {
  if (value === true) return true;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    return ["1", "true", "yes", "y", "on", "enabled"].includes(value.trim().toLowerCase());
  }
  return false;
}

function mobileExecutionLockReasons(label: string, source?: MobileExecutionLockSource | null): string[] {
  if (!source) return [];
  const flags: Array<[keyof MobileExecutionLockSource, string]> = [
    ["would_execute", "would_execute must remain false"],
    ["would_dispatch", "would_dispatch must remain false"],
    ["would_session_send", "would_session_send must remain false"],
    ["dispatch_enabled", "dispatch_enabled must remain false"],
    ["execution_enabled", "execution_enabled must remain false"],
    ["execution_ready", "execution_ready must remain false"],
    ["live_operations_enabled", "live_operations_enabled must remain false"],
    ["send_to_jenny_enabled", "send_to_jenny_enabled must remain false"],
    ["session_send_enabled", "session_send_enabled must remain false"],
    ["worker_dispatch_enabled", "worker_dispatch_enabled must remain false"],
    ["worker_enabled", "worker_enabled must remain false"],
  ];
  return flags
    .filter(([flag]) => mobileLiveFlagEnabled(source[flag]))
    .map(([, reason]) => `${label}: ${reason}`);
}

function mobileRecordText(record: Record<string, unknown> | undefined, field: string): string {
  const value = record?.[field];
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function mobileWorkspaceSafety(status: MobileWorkspaceStatus | null): MobileBridgeSafety {
  const reasons: string[] = [];
  if (!status) {
    reasons.push("workspace status not loaded");
  }

  const hardBoundary = status?.hard_boundary_contract;
  if (!hardBoundary) {
    reasons.push("hard_boundary_contract is not loaded");
  } else {
    if (hardBoundary.blocked === true) {
      reasons.push(hardBoundary.blocked_reasons?.[0] ?? "hard_boundary_contract is blocked");
    }
    for (const reason of hardBoundary.live_flag_violations ?? []) {
      reasons.push(reason);
    }
    reasons.push(...mobileExecutionLockReasons("hard_boundary_contract", hardBoundary));
  }

  const operatorPacket = status?.operator_decision_packet;
  reasons.push(...(operatorPacket?.execution_lock_blocked_reasons ?? []));
  reasons.push(...mobileExecutionLockReasons("operator_decision_packet", operatorPacket));
  reasons.push(...mobileExecutionLockReasons("orchestration_readiness", status?.orchestration_readiness));
  reasons.push(...mobileExecutionLockReasons("report_lifecycle", status?.report_lifecycle));
  reasons.push(...mobileExecutionLockReasons("worker_node_presence", status?.worker_node_presence));
  reasons.push(...mobileExecutionLockReasons("worker_node_orchestration", status?.worker_node_orchestration));
  reasons.push(...mobileExecutionLockReasons("worker_node_instruction_preview", status?.worker_node_instruction_preview));

  const uniqueReasons = [...new Set(reasons)];
  return { reasons: uniqueReasons, safe: uniqueReasons.length === 0 };
}

function combineMobileSafety(...checks: MobileBridgeSafety[]): MobileBridgeSafety {
  const reasons = [...new Set(checks.flatMap((check) => check.reasons))];
  return { reasons, safe: reasons.length === 0 };
}

function mobileRequestId(): string {
  const fallback = Math.random().toString(16).slice(2, 14);
  return `jenny-mobile-${globalThis.crypto?.randomUUID?.() ?? fallback}`;
}

function modelChoiceKey(provider: string, model: string): string {
  return `${provider}\u0000${model}`;
}

function modelChoiceFromKey(value: string): { model: string; provider: string } {
  const [provider, model] = value.split("\u0000");
  return { model: model?.trim() ?? "", provider: provider?.trim() ?? "" };
}

function modelLabel(model: string, provider: string): string {
  if (provider && model) return `${provider} / ${model}`;
  return model || provider || "Current model";
}

function buildModelChoices(info: ModelInfoResponse | null, options: ModelOptionsResponse | null): ModelChoice[] {
  const choices: ModelChoice[] = [];
  const currentProvider = options?.provider || info?.provider || "";
  const currentModel = options?.model || info?.model || "";
  if (currentProvider || currentModel) {
    choices.push({
      key: modelChoiceKey(currentProvider, currentModel),
      label: modelLabel(currentModel, currentProvider),
      model: currentModel,
      provider: currentProvider,
    });
  }

  for (const provider of options?.providers ?? []) {
    if (choices.length >= MAX_MODEL_CHOICES) break;
    for (const model of provider.models ?? []) {
      const key = modelChoiceKey(provider.slug, model);
      if (choices.some((choice) => choice.key === key)) continue;
      choices.push({
        key,
        label: modelLabel(model, provider.name || provider.slug),
        model,
        provider: provider.slug,
      });
      if (choices.length >= MAX_MODEL_CHOICES) break;
    }
  }

  return choices;
}

function canonicalProjects(projects: MobileProject[]): MobileProject[] {
  const merged = new Map(MOBILE_PROJECTS.map((project) => [project.project_id, project]));
  for (const project of projects) {
    if (!project.project_id || !project.name) continue;
    if (!MOBILE_PROJECT_ORDER.has(project.project_id)) continue;
    merged.set(project.project_id, { ...merged.get(project.project_id), ...project });
  }
  return [...merged.values()].sort(
    (left, right) =>
      (MOBILE_PROJECT_ORDER.get(left.project_id) ?? 999) -
      (MOBILE_PROJECT_ORDER.get(right.project_id) ?? 999),
  );
}

function buildJennyMobileMessage({
  effort,
  model,
  project,
  provider,
  text,
}: {
  effort: string;
  model: string;
  project: MobileProject;
  provider: string;
  text: string;
}): string {
  const effortLabel = MOBILE_EFFORTS.find((option) => option.value === effort)?.label ?? effort;
  return boundedMobileMessage([
    "Jenny mobile chat request:",
    `Project: ${project.name}`,
    `Requested model: ${modelLabel(model, provider)}`,
    `Requested effort: ${effortLabel || "current default"}`,
    "",
    "Visible request from Travis:",
    compactText(text, 700),
    "",
    "Reply as Jenny in normal chat style. Keep the visible answer concise and useful.",
    "Do not expose hidden guardrails or this packet in the user-facing answer.",
    "Safety: manual foreground reply only; no hidden worker, timer, daemon, gateway restart, deploy, Waha/social/payment/outreach, secrets/state deletion, or model routing mutation.",
  ].join("\n"));
}

function formatStatusLabel(status: MobileMessageStatus): string {
  switch (status) {
    case "working":
      return "working";
    case "replied":
      return "replied";
    case "failed":
      return "failed";
    case "queued":
      return "queued";
    default:
      return "sent";
  }
}

function statusTone(status: MobileMessageStatus): string {
  switch (status) {
    case "working":
      return "text-sky-300";
    case "replied":
      return "text-emerald-300";
    case "failed":
      return "text-red-300";
    case "queued":
      return "text-amber-300";
    default:
      return "text-zinc-400";
  }
}

export default function JennyMobilePage() {
  const { setTitle } = usePageHeader();
  const endRef = useRef<HTMLDivElement | null>(null);
  const replyingRequestIdRef = useRef("");
  const [projects, setProjects] = useState<MobileProject[]>(MOBILE_PROJECTS);
  const [selectedProjectId, setSelectedProjectId] = useState(() => {
    try {
      return localStorage.getItem(SELECTED_PROJECT_STORAGE_KEY) || MOBILE_PROJECTS[0].project_id;
    } catch {
      return MOBILE_PROJECTS[0].project_id;
    }
  });
  const [messagesByProject, setMessagesByProject] = useState<Record<string, ChatMessage[]>>({});
  const [statusByProject, setStatusByProject] = useState<Record<string, GitHubBridgeStatus>>({});
  const [workspaceStatus, setWorkspaceStatus] = useState<MobileWorkspaceStatus | null>(null);
  const [runByProject, setRunByProject] = useState<Record<string, RunState>>({});
  const [composer, setComposer] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [replyingRequestId, setReplyingRequestId] = useState("");
  const [error, setError] = useState("");
  const [activityOpen, setActivityOpen] = useState(false);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [modelOptions, setModelOptions] = useState<ModelOptionsResponse | null>(null);
  const [selectedModelChoice, setSelectedModelChoice] = useState(() => {
    try {
      return localStorage.getItem(SELECTED_MODEL_STORAGE_KEY) || "";
    } catch {
      return "";
    }
  });
  const [selectedEffort, setSelectedEffort] = useState(() => {
    try {
      return localStorage.getItem(SELECTED_EFFORT_STORAGE_KEY) || "xhigh";
    } catch {
      return "xhigh";
    }
  });

  useEffect(() => {
    setTitle("Jenny Mobile");
  }, [setTitle]);

  useEffect(() => {
    try {
      localStorage.setItem(SELECTED_PROJECT_STORAGE_KEY, selectedProjectId);
    } catch {
      /* localStorage may be unavailable. */
    }
  }, [selectedProjectId]);

  useEffect(() => {
    try {
      if (selectedModelChoice) localStorage.setItem(SELECTED_MODEL_STORAGE_KEY, selectedModelChoice);
      localStorage.setItem(SELECTED_EFFORT_STORAGE_KEY, selectedEffort);
    } catch {
      /* localStorage may be unavailable. */
    }
  }, [selectedEffort, selectedModelChoice]);

  useEffect(() => {
    let cancelled = false;
    async function loadChrome() {
      try {
        const [projectsPayload, info, options, workspace] = await Promise.all([
          fetchJSON<{ projects?: Array<WrappedRecord<MobileProject> | MobileProject> }>(`${WORKSPACE_PROJECTS_URL}?limit=25`),
          fetchJSON<ModelInfoResponse>(MODEL_INFO_URL),
          fetchJSON<ModelOptionsResponse>(MODEL_OPTIONS_URL),
          fetchJSON<MobileWorkspaceStatus>(WORKSPACE_STATUS_URL),
        ]);
        if (cancelled) return;
        setProjects(canonicalProjects(unwrapRecords(projectsPayload.projects)));
        setModelInfo(info);
        setModelOptions(options);
        setWorkspaceStatus(workspace);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    }
    void loadChrome();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? MOBILE_PROJECTS[0],
    [projects, selectedProjectId],
  );

  const messages = messagesByProject[selectedProject.project_id] ?? [];
  const bridgeStatus = statusByProject[selectedProject.project_id];
  const runState = runByProject[selectedProject.project_id] ?? statusFromBridge(bridgeStatus);
  const bridgeSafety = useMemo(() => mobileBridgeSafety(bridgeStatus), [bridgeStatus]);
  const workspaceSafety = useMemo(() => mobileWorkspaceSafety(workspaceStatus), [workspaceStatus]);
  const mobileSafety = useMemo(() => combineMobileSafety(bridgeSafety, workspaceSafety), [bridgeSafety, workspaceSafety]);
  const visibleRunState: RunState = mobileSafety.safe
    ? runState
    : {
        detail: `Manual chat blocked: ${mobileSafety.reasons[0] ?? "backend safety is not confirmed"}`,
        status: "failed",
      };
  const modelChoices = useMemo(() => buildModelChoices(modelInfo, modelOptions), [modelInfo, modelOptions]);
  const currentModelChoice = selectedModelChoice || modelChoices[0]?.key || "";
  const selectedModel = modelChoiceFromKey(currentModelChoice);
  const statusRecords = unwrapRecords(bridgeStatus?.status_records).slice(-5).reverse();
  const latestPendingId = latestPendingRequestId(messages);
  const sendDisabled = sending || loading || !composer.trim() || !mobileSafety.safe;
  const reportLifecycle = workspaceStatus?.report_lifecycle;
  const reportMissingLinkedCount = Object.values(reportLifecycle?.runs_with_missing_linked_report_ids ?? {}).reduce(
    (count, reportIds) => count + reportIds.length,
    0,
  );
  const reportOverwriteConflictCount = reportLifecycle?.report_overwrite_conflict_count ?? reportLifecycle?.report_overwrite_conflict_ids?.length ?? 0;
  const reportGapCount =
    (reportLifecycle?.duplicate_report_ids?.length ?? 0)
    + reportOverwriteConflictCount
    + (reportLifecycle?.runs_missing_report?.length ?? 0)
    + reportMissingLinkedCount;
  const readinessStates = workspaceStatus?.orchestration_readiness?.states;
  const workerPresence = workspaceStatus?.worker_node_presence;
  const workerInstruction = workspaceStatus?.worker_node_instruction_preview;
  const workerProjection = workspaceStatus?.worker_node_orchestration;
  const workerRecord = workerProjection?.active_runs?.[0] ?? Object.values(workerProjection?.latest_by_id ?? {})[0];
  const workerLatestStatus = mobileRecordText(workerRecord, "status") || "none";
  const workerLatestObjective = mobileRecordText(workerRecord, "objective") || "no assigned objective";
  const workerBlockedReasons = [
    ...(workerPresence?.blocked_reasons ?? []),
    ...(workerProjection?.blocked_reasons ?? []),
    ...(workerInstruction?.blocked_reasons ?? []),
  ].filter(Boolean);

  const refreshMessages = useCallback(async (projectId: string) => {
    const [status, workspace] = await Promise.all([
      fetchJSON<GitHubBridgeStatus>(
        `${WORKSPACE_GITHUB_BRIDGE_STATUS_URL}?project_id=${encodeURIComponent(projectId)}&limit=80`,
      ),
      fetchJSON<MobileWorkspaceStatus>(WORKSPACE_STATUS_URL),
    ]);
    const incoming = messagesFromStatus(status);
    setStatusByProject((prev) => ({ ...prev, [projectId]: status }));
    setWorkspaceStatus(workspace);
    setMessagesByProject((prev) => ({
      ...prev,
      [projectId]: mergeMessages(prev[projectId] ?? [], incoming),
    }));
    setRunByProject((prev) => ({ ...prev, [projectId]: statusFromBridge(status) }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    refreshMessages(selectedProject.project_id)
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshMessages, selectedProject.project_id]);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages.length, visibleRunState.status, selectedProject.project_id]);

  const updateMessageStatus = useCallback((projectId: string, requestId: string, status: MobileMessageStatus) => {
    setMessagesByProject((prev) => ({
      ...prev,
      [projectId]: (prev[projectId] ?? []).map((message) =>
        message.requestId === requestId && message.role === "user"
          ? { ...message, status }
          : message,
      ),
    }));
  }, []);

  const appendMessage = useCallback((projectId: string, message: ChatMessage) => {
    setMessagesByProject((prev) => ({
      ...prev,
      [projectId]: mergeMessages(prev[projectId] ?? [], [message]),
    }));
  }, []);

  const runJennyOnce = useCallback(async (projectId: string, requestId: string) => {
    if (!requestId || replyingRequestIdRef.current) return;
    if (!mobileSafety.safe) {
      setRunByProject((prev) => ({
        ...prev,
        [projectId]: {
          detail: `Manual chat blocked: ${mobileSafety.reasons[0] ?? "backend safety is not confirmed"}`,
          requestId,
          status: "failed",
        },
      }));
      return;
    }
    replyingRequestIdRef.current = requestId;
    setReplyingRequestId(requestId);
    setRunByProject((prev) => ({
      ...prev,
      [projectId]: { detail: "Jenny is working on one foreground reply.", requestId, status: "working" },
    }));
    updateMessageStatus(projectId, requestId, "working");
    try {
      const result = await fetchJSONWithTimeout<AnswerOnceResponse>(WORKSPACE_GITHUB_BRIDGE_ANSWER_ONCE_URL, {
        body: JSON.stringify({
          confirm_manual_hermes_answer: true,
          project_id: projectId,
          request_id: requestId,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      }, ANSWER_ONCE_TIMEOUT_MS);

      if (result.response?.message) {
        appendMessage(projectId, {
          createdAt: result.response.created_at || new Date().toISOString(),
          id: result.response.github_comment_id || result.response.request_id || `reply-${requestId}`,
          requestId,
          role: "assistant",
          status: "replied",
          text: cleanJennyReply(result.response.message),
        });
      }

      const answered = Boolean(result.answered || result.response?.message);
      const nextStatus = answered ? "replied" : "failed";
      setRunByProject((prev) => ({
        ...prev,
        [projectId]: {
          detail: answered ? "Jenny replied." : result.status?.last_error || "Jenny did not return a reply.",
          requestId,
          status: nextStatus,
        },
      }));
      await refreshMessages(projectId);
      updateMessageStatus(projectId, requestId, nextStatus);
    } catch (err) {
      await refreshMessages(projectId).catch(() => undefined);
      updateMessageStatus(projectId, requestId, "failed");
      setRunByProject((prev) => ({
        ...prev,
        [projectId]: {
          detail: err instanceof Error ? err.message : String(err),
          requestId,
          status: "failed",
        },
      }));
    } finally {
      replyingRequestIdRef.current = "";
      setReplyingRequestId("");
    }
  }, [appendMessage, mobileSafety.reasons, mobileSafety.safe, refreshMessages, updateMessageStatus]);

  async function sendMessage() {
    const text = composer.trim();
    if (!text || sendDisabled) return;
    const project = selectedProject;
    const requestId = mobileRequestId();
    const createdAt = new Date().toISOString();
    setComposer("");
    setSending(true);
    setError("");
    appendMessage(project.project_id, {
      createdAt,
      id: requestId,
      optimistic: true,
      requestId,
      role: "user",
      status: "queued",
      text,
    });
    setRunByProject((prev) => ({
      ...prev,
      [project.project_id]: { detail: "Message queued for Jenny.", requestId, status: "queued" },
    }));

    try {
      await fetchJSON<OutboxResponse>(WORKSPACE_GITHUB_BRIDGE_OUTBOX_CREATE_URL, {
        body: JSON.stringify({
          from_agent: "travis",
          message: buildJennyMobileMessage({
            effort: selectedEffort,
            model: selectedModel.model,
            project,
            provider: selectedModel.provider,
            text,
          }),
          project_id: project.project_id,
          request_id: requestId,
          to_agent: "jenny",
          user_message: text,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      setSending(false);
      void refreshMessages(project.project_id).catch((refreshErr) => {
        setError(refreshErr instanceof Error ? refreshErr.message : String(refreshErr));
      });
      void runJennyOnce(project.project_id, requestId);
    } catch (err) {
      updateMessageStatus(project.project_id, requestId, "failed");
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      setRunByProject((prev) => ({
        ...prev,
        [project.project_id]: { detail: message, requestId, status: "failed" },
      }));
    } finally {
      setSending(false);
    }
  }

  return (
    <main
      className="relative min-h-[100dvh] w-full min-w-0 overflow-x-hidden bg-[#070808] text-zinc-100 [overflow-wrap:anywhere]"
      data-testid="jenny-mobile-route"
    >
      <div className="fixed inset-x-0 top-0 z-30 border-b border-white/10 bg-[#070808] px-3 pb-2 pt-[calc(0.65rem+env(safe-area-inset-top,0px))]">
        <div className="mx-auto flex max-w-2xl items-center gap-2">
          <button
            type="button"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.06] text-zinc-100"
            onClick={() => setActivityOpen(true)}
            aria-label="Open activity"
          >
            <Plus className="h-5 w-5" />
          </button>

          <label className="relative min-w-0 flex-1" aria-label="Active Jenny project">
            <span className="sr-only">Active Jenny project</span>
            <Folder className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-300" />
            <select
              className="h-11 w-full appearance-none truncate rounded-full border border-white/10 bg-white/[0.08] py-0 pl-9 pr-9 text-sm font-semibold text-zinc-50 outline-none focus:border-emerald-300"
              data-testid="jenny-mobile-project-select"
              onChange={(event) => setSelectedProjectId(event.target.value)}
              value={selectedProject.project_id}
            >
              {projects.map((project) => (
                <option className="bg-zinc-950 text-zinc-50" key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-300" />
          </label>

          <button
            type="button"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.06] text-zinc-100 disabled:opacity-50"
            onClick={() => void refreshMessages(selectedProject.project_id)}
            disabled={loading}
            aria-label="Refresh Jenny mobile chat"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      <section className="mx-auto flex min-h-[calc(100dvh-9rem)] max-w-2xl flex-col gap-4 px-3 pb-[calc(9.75rem+env(safe-area-inset-bottom,0px))] pt-[calc(4.75rem+env(safe-area-inset-top,0px))]">
        <div className="flex items-center justify-between gap-3 px-1 text-xs text-zinc-400">
          <span className={cn(
            "inline-flex items-center gap-1 font-medium",
            visibleRunState.status === "failed" ? "text-red-300" : visibleRunState.status === "working" ? "text-sky-300" : "text-emerald-300",
          )}>
            {visibleRunState.status === "working" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : visibleRunState.status === "failed" ? <AlertCircle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            {visibleRunState.status}
          </span>
          <span className="min-w-0 truncate text-right">{visibleRunState.detail}</span>
        </div>

        {error ? (
          <p className="rounded-lg bg-red-950/60 px-3 py-2 text-sm text-red-100" role="alert">
            {error}
          </p>
        ) : null}

        {loading && !messages.length ? (
          <div className="flex flex-1 items-center justify-center py-16 text-sm text-zinc-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading recent chat
          </div>
        ) : messages.length ? (
          <div className="flex flex-col gap-4" data-testid="jenny-mobile-chat-timeline">
            {messages.map((message) => (
              <article
                className={cn(
                  "flex w-full min-w-0",
                  message.role === "user" ? "justify-end" : "justify-start",
                )}
                key={`${message.id}-${message.role}`}
              >
                <div className={cn(
                  "max-w-[88%] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-[0.95rem] leading-6 shadow-sm",
                  message.role === "user"
                    ? "rounded-br-md bg-emerald-500 text-zinc-950"
                    : "rounded-bl-md bg-zinc-900 text-zinc-100",
                )}>
                  <p>{message.text}</p>
                  <div className="mt-1.5 flex items-center justify-end gap-2 text-[0.7rem] font-medium">
                    <span className={message.role === "user" ? "text-zinc-900/70" : statusTone(message.status)}>
                      {formatStatusLabel(message.status)}
                    </span>
                    {message.role === "user" && ["queued", "failed"].includes(message.status) && message.requestId ? (
                      <button
                        className="rounded-full bg-black/15 px-2 py-0.5 text-[0.7rem] font-semibold text-zinc-950 disabled:opacity-50"
                        type="button"
                        disabled={replyingRequestId !== "" || sending || !mobileSafety.safe}
                        onClick={() => void runJennyOnce(selectedProject.project_id, message.requestId ?? "")}
                      >
                        {message.status === "failed" ? "Retry" : "Get reply"}
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            ))}
            <div ref={endRef} />
          </div>
        ) : (
          <div className="flex flex-1 flex-col justify-center py-16 text-center text-zinc-300">
            <Menu className="mx-auto mb-3 h-8 w-8 text-emerald-300" />
            <h2 className="text-lg font-semibold">Jenny mobile chat</h2>
            <p className="mx-auto mt-2 max-w-xs text-sm text-zinc-400">
              Pick a project, send one bounded message, and Jenny will answer in this thread.
            </p>
          </div>
        )}
      </section>

      <form
        className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-[#070808] px-3 pb-[calc(0.6rem+env(safe-area-inset-bottom,0px))] pt-2"
        data-testid="jenny-mobile-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void sendMessage();
        }}
      >
        <div className="mx-auto max-w-2xl">
          <div className="mb-2 flex min-w-0 gap-2">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Model</span>
              <select
                className="h-9 w-full appearance-none truncate rounded-full border border-white/10 bg-white/[0.08] px-3 text-xs font-semibold text-zinc-100 outline-none focus:border-emerald-300"
                data-testid="jenny-mobile-model-select"
                onChange={(event) => setSelectedModelChoice(event.target.value)}
                value={currentModelChoice}
              >
                {modelChoices.length ? modelChoices.map((choice) => (
                  <option className="bg-zinc-950 text-zinc-50" key={choice.key} value={choice.key}>
                    {choice.label}
                  </option>
                )) : (
                  <option className="bg-zinc-950 text-zinc-50" value="">
                    Current model
                  </option>
                )}
              </select>
            </label>

            <label className="w-32 shrink-0">
              <span className="sr-only">Effort</span>
              <select
                className="h-9 w-full appearance-none truncate rounded-full border border-white/10 bg-white/[0.08] px-3 text-xs font-semibold text-zinc-100 outline-none focus:border-emerald-300"
                data-testid="jenny-mobile-effort-select"
                onChange={(event) => setSelectedEffort(event.target.value)}
                value={selectedEffort}
              >
                {MOBILE_EFFORTS.map((option) => (
                  <option className="bg-zinc-950 text-zinc-50" key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex min-w-0 items-end gap-2">
            <button
              type="button"
              className="mb-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.06] text-zinc-100"
              onClick={() => setActivityOpen(true)}
              aria-label="Open activity details"
            >
              <Plus className="h-5 w-5" />
            </button>

            <textarea
              className="max-h-28 min-h-11 flex-1 resize-none rounded-3xl border border-white/10 bg-white/[0.08] px-4 py-3 text-[1rem] leading-5 text-zinc-50 outline-none placeholder:text-zinc-500 focus:border-emerald-300"
              data-testid="jenny-mobile-input"
              onChange={(event) => setComposer(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              placeholder="Ask Jenny"
              rows={1}
              value={composer}
            />

            <button
              type="submit"
              className="mb-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-full bg-emerald-400 text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-500"
              disabled={sendDisabled}
              aria-label="Send Jenny message"
            >
              {sending || replyingRequestId ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </form>

      {activityOpen ? (
        <div className="fixed inset-0 z-40 bg-black/70" data-testid="jenny-mobile-activity-drawer">
          <button
            aria-label="Close activity"
            className="absolute inset-0 h-full w-full cursor-default"
            onClick={() => setActivityOpen(false)}
            type="button"
          />
          <section className="absolute inset-x-0 bottom-0 max-h-[72dvh] overflow-y-auto rounded-t-2xl border-t border-white/10 bg-zinc-950 px-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] pt-3 text-zinc-100">
            <div className="mx-auto max-w-2xl">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Activity</h2>
                <button
                  type="button"
                  className="grid h-9 w-9 place-items-center rounded-full bg-white/[0.08]"
                  onClick={() => setActivityOpen(false)}
                  aria-label="Close activity"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <dl className="grid gap-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Project</dt>
                  <dd className="min-w-0 truncate text-right">{selectedProject.name}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Model</dt>
                  <dd className="min-w-0 truncate text-right">{modelLabel(selectedModel.model, selectedModel.provider)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Effort</dt>
                  <dd className="text-right">{MOBILE_EFFORTS.find((option) => option.value === selectedEffort)?.label ?? selectedEffort}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Latest pending</dt>
                  <dd className="min-w-0 truncate text-right">{latestPendingId || "none"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Safety</dt>
                  <dd className={cn("text-right", mobileSafety.safe ? "text-emerald-300" : "text-red-300")}>
                    {mobileSafety.safe ? "manual foreground only" : "blocked"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Readiness</dt>
                  <dd className="min-w-0 truncate text-right">
                    read-only {readinessStates?.supervised_read_only_autonomy?.replaceAll("_", " ") ?? "unknown"} / worker{" "}
                    {readinessStates?.laptop_codex_worker_node?.replaceAll("_", " ") ?? "unknown"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Laptop Codex</dt>
                  <dd className={cn("min-w-0 truncate text-right", workerPresence?.online ? "text-emerald-300" : "text-amber-300")}>
                    {workerPresence?.worker_host_label ?? "laptop Codex"} / {workerPresence?.presence_state?.replaceAll("_", " ") ?? "unknown"} / online{" "}
                    {workerPresence?.online ? "yes" : "no"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Worker objective</dt>
                  <dd className="min-w-0 truncate text-right">{workerLatestObjective}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Worker handoff</dt>
                  <dd className={cn("min-w-0 truncate text-right", workerInstruction?.ready_for_handoff ? "text-emerald-300" : "text-amber-300")}>
                    latest {workerLatestStatus} / available {workerInstruction?.available ? "yes" : "no"} / handoff{" "}
                    {workerInstruction?.ready_for_handoff ? "yes" : "no"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Report lifecycle</dt>
                  <dd className={cn("min-w-0 truncate text-right", reportLifecycle?.blocked ? "text-amber-300" : "text-emerald-300")}>
                    open {reportLifecycle?.open_report_ids?.length ?? 0} / reviewed{" "}
                    {reportLifecycle?.reviewed_report_ids?.length ?? 0} / terminal{" "}
                    {reportLifecycle?.terminal_report_ids?.length ?? 0}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-zinc-400">Report gaps</dt>
                  <dd className={cn("min-w-0 truncate text-right", reportGapCount ? "text-amber-300" : "text-emerald-300")}>
                    dup {reportLifecycle?.duplicate_report_ids?.length ?? 0} / overwrite {reportOverwriteConflictCount} / missing{" "}
                    {reportLifecycle?.runs_missing_report?.length ?? 0} / stale {reportMissingLinkedCount}
                  </dd>
                </div>
              </dl>

              {!mobileSafety.safe ? (
                <div className="mt-3 rounded-lg border border-red-400/30 bg-red-950/40 px-3 py-2 text-sm text-red-100">
                  <p className="font-medium">Manual chat blocked</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {mobileSafety.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {reportLifecycle?.blocked_reasons?.length ? (
                <div className="mt-3 rounded-lg border border-amber-400/30 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
                  <p className="font-medium">Report lifecycle needs Jenny review</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {reportLifecycle.blocked_reasons.slice(0, 4).map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {workerBlockedReasons.length ? (
                <div className="mt-3 rounded-lg border border-amber-400/30 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
                  <p className="font-medium">Laptop Codex needs review</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    {[...new Set(workerBlockedReasons)].slice(0, 4).map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="mt-4 border-t border-white/10 pt-3">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">Recent status</h3>
                {statusRecords.length ? (
                  <ul className="space-y-2 text-sm">
                    {statusRecords.map((record, index) => (
                      <li className="rounded-lg bg-white/[0.05] px-3 py-2" key={`${record.created_at ?? ""}-${index}`}>
                        <p className="font-medium">{record.status?.replaceAll("_", " ") || "status"}</p>
                        <p className="mt-0.5 text-xs text-zinc-400">
                          {[record.mode, record.handled_request_id, record.last_error].filter(Boolean).join(" / ") || record.created_at || "bridge status"}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-zinc-400">No bridge activity for this project yet.</p>
                )}
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
