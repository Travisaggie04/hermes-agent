import { useEffect, useMemo, useState } from "react";

import { fetchJSON } from "@/lib/api";
import { cn } from "@/lib/utils";

const WORKSPACE_STATUS_URL = "/api/plugins/mission-control-governance/workspace-status";
const WORKSPACE_PROJECTS_URL = "/api/plugins/mission-control-governance/workspace/projects";
const WORKSPACE_LANE_REQUESTS_URL = "/api/plugins/mission-control-governance/workspace/lane-requests";
const WORKSPACE_REPORTS_URL = "/api/plugins/mission-control-governance/workspace/reports";
const WORKSPACE_REPORTS_CREATE_URL = "/api/plugins/mission-control-governance/workspace/reports/create";
const WORKSPACE_PROJECT_STATE_URL = "/api/plugins/mission-control-governance/workspace/project-state";

const REAL_PROJECT_IDS = [
  "project-hermes-mission-control",
  "project-long-form-video",
  "project-shorts-video",
  "project-tool-tally",
  "project-waha-work",
] as const;

const REAL_PROJECT_NAMES = [
  "Hermes / Mission Control",
  "Long-form Video",
  "Shorts Video",
  "Tool & Tally",
  "Waha Work",
] as const;

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

interface ReportRecord {
  blockers?: string[];
  changed_files?: string[];
  metadata?: { artifact_links?: string[]; [key: string]: unknown };
  project_id?: string;
  result?: string;
  risks?: string[];
  summary?: string;
  next_recommended_lane?: string;
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
  risks?: string[];
  risks_blockers?: string[];
  status?: string;
}

interface WorkspaceStatus {
  accepted_baseline?: { head?: string; runtime_path?: string };
  lane?: { active_lane_count?: number };
  runtime_worktree_guard?: { decision_state?: string };
  safety?: { dispatch_in_gateway?: boolean };
  stale_context?: { warnings?: string[] };
}

interface CompactSnapshot {
  laneRequests: LaneRequestRecord[];
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
  latestReport: string;
  latestResult: string;
  missingFields: string;
  nextLane: string;
  project: ProjectRecord;
  risks: string;
  status: string;
}

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

function lineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map(item => item.trim())
    .filter(Boolean);
}

function artifactText(state: ProjectStateRecord | undefined, report: ReportRecord | undefined): string {
  return listText(state?.artifact_links ?? report?.metadata?.artifact_links ?? report?.changed_files, "No artifact/report links recorded");
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

function viewModelForProject(snapshot: CompactSnapshot, project: ProjectRecord): ProjectViewModel {
  const state = latestForProject(project.project_id, snapshot.projectStates);
  const report = latestForProject(project.project_id, snapshot.reports);
  const lane = latestForProject(project.project_id, snapshot.laneRequests);
  const riskValues = state?.risks ?? state?.risks_blockers ?? report?.risks;
  const blockerValues = state?.blockers ?? report?.blockers;

  return {
    artifactLinks: artifactText(state, report),
    blockers: listText(blockerValues, "No blockers recorded"),
    currentGoal: text(state?.current_goal ?? project.current_goal, "No current goal recorded"),
    freshness: state?.has_real_report ? "Live report available" : "Seed only — needs first report",
    latestActivity: text(state?.latest_activity_at, "No activity time recorded"),
    latestLane: text(state?.latest_lane_title ?? lane?.title, "No lane recorded"),
    latestReport: text(state?.latest_report_summary || report?.summary || project.latest_report_summary, "No report yet"),
    latestResult: text(state?.latest_result || report?.result || project.latest_result, "No result yet"),
    missingFields: listText(state?.missing_state_fields, "None — report state is current"),
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane ?? lane?.title, "No recommended lane yet"),
    project,
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

async function loadCompactSnapshot(): Promise<CompactSnapshot> {
  const [workspaceStatus, projects, laneRequests, reports, projectState] = await Promise.all([
    fetchJSON<WorkspaceStatus>(WORKSPACE_STATUS_URL),
    fetchJSON<{ projects?: Array<WrappedRecord<ProjectRecord> | ProjectRecord> }>(WORKSPACE_PROJECTS_URL),
    fetchJSON<{ lane_requests?: Array<WrappedRecord<LaneRequestRecord> | LaneRequestRecord> }>(WORKSPACE_LANE_REQUESTS_URL),
    fetchJSON<{ reports?: Array<WrappedRecord<ReportRecord> | ReportRecord> }>(WORKSPACE_REPORTS_URL),
    fetchJSON<{ project_states?: ProjectStateRecord[] }>(WORKSPACE_PROJECT_STATE_URL),
  ]);

  return {
    laneRequests: unwrapRecords(laneRequests.lane_requests),
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

  async function copyPrompt(projectView: ProjectViewModel) {
    const prompt = buildCompactNextLanePrompt(projectView, snapshot?.workspaceStatus ?? {});
    await navigator.clipboard?.writeText(prompt);
    setCopiedProjectId(projectView.project.project_id);
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
