import { useEffect, useMemo, useState } from 'react'

import {
  getMissionControlLaneRequests,
  getMissionControlProjects,
  getMissionControlProjectState,
  getMissionControlReports,
  getMissionControlWorkspaceStatus,
  type MissionControlLaneRequestRecord,
  type MissionControlProjectRecord,
  type MissionControlProjectState,
  type MissionControlReportRecord,
  type MissionControlWorkspaceStatus
} from '@/hermes'
import { cn } from '@/lib/utils'

interface MissionControlSnapshot {
  laneRequests: MissionControlLaneRequestRecord[]
  projects: MissionControlProjectRecord[]
  projectStates: MissionControlProjectState[]
  reports: MissionControlReportRecord[]
  workspaceStatus: MissionControlWorkspaceStatus
}

const emptySnapshot: MissionControlSnapshot = {
  laneRequests: [],
  projects: [],
  projectStates: [],
  reports: [],
  workspaceStatus: {}
}

const REAL_PROJECT_IDS = [
  'project-hermes-mission-control',
  'project-long-form-video',
  'project-shorts-video',
  'project-tool-tally',
  'project-waha-work'
]

const REAL_PROJECT_NAMES = [
  'Hermes / Mission Control',
  'Long-form Video',
  'Shorts Video',
  'Tool & Tally',
  'Waha Work'
]

const MAX_COPY_PROMPT_CHARS = 2000

function text(value: unknown, fallback = 'Not recorded'): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function yesNo(value: unknown): string {
  return value === true ? 'yes' : value === false ? 'no' : 'unknown'
}

function listText(values: unknown, fallback = 'None recorded'): string {
  if (!Array.isArray(values) || values.length === 0) {
    return fallback
  }

  return values.map(item => String(item)).filter(Boolean).join(', ') || fallback
}

function truncate(value: string, maxChars: number): string {
  if (value.length <= maxChars) {
    return value
  }

  return `${value.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`
}

function unwrapRecords<T>(items: Array<{ record?: T } | T> | undefined): T[] {
  if (!Array.isArray(items)) {
    return []
  }

  return items.map(item => ('record' in Object(item) ? (item as { record?: T }).record : item)).filter(Boolean) as T[]
}

function isRealProject(project: MissionControlProjectRecord): boolean {
  return REAL_PROJECT_IDS.includes(project.project_id) || REAL_PROJECT_NAMES.includes(project.name)
}

function isSmokeProject(project: MissionControlProjectRecord): boolean {
  return /smoke/i.test(`${project.project_id} ${project.name} ${project.status ?? ''}`)
}

function sortRealProjects(projects: MissionControlProjectRecord[]): MissionControlProjectRecord[] {
  return [...projects].sort((a, b) => {
    const aIndex = REAL_PROJECT_IDS.includes(a.project_id) ? REAL_PROJECT_IDS.indexOf(a.project_id) : REAL_PROJECT_NAMES.indexOf(a.name)
    const bIndex = REAL_PROJECT_IDS.includes(b.project_id) ? REAL_PROJECT_IDS.indexOf(b.project_id) : REAL_PROJECT_NAMES.indexOf(b.name)

    return (aIndex < 0 ? Number.MAX_SAFE_INTEGER : aIndex) - (bIndex < 0 ? Number.MAX_SAFE_INTEGER : bIndex)
  })
}

function stateForProject(project: MissionControlProjectRecord, states: MissionControlProjectState[]) {
  return states.find(state => state.project_id === project.project_id) ?? null
}

function latestLaneForProject(projectId: string, lanes: MissionControlLaneRequestRecord[]) {
  return [...lanes].reverse().find(lane => lane.project_id === projectId) ?? null
}

function latestReportForProject(projectId: string, reports: MissionControlReportRecord[]) {
  return [...reports].reverse().find(report => report.project_id === projectId) ?? null
}

export function summarizeWorkspaceStatus(status: MissionControlWorkspaceStatus) {
  return {
    activeLaneCount: status.lane?.active_lane_count ?? 0,
    dispatch: status.safety?.dispatch_in_gateway,
    guard: status.runtime_worktree_guard?.decision_state ?? 'unknown',
    head: status.accepted_baseline?.head ?? 'unknown',
    runtime: status.accepted_baseline?.runtime_path ?? 'unknown',
    staleWarnings: status.stale_context?.warnings ?? []
  }
}

interface ProjectRenderModel {
  blockers: unknown
  latestReportSummary: string
  latestResult: string
  nextLane: string
  risks: unknown
}

function projectRenderModel(
  project: MissionControlProjectRecord,
  report: MissionControlReportRecord | null,
  state: MissionControlProjectState | null
): ProjectRenderModel {
  return {
    blockers: state?.blockers ?? report?.blockers,
    latestReportSummary: text(state?.latest_report_summary ?? report?.summary, 'No report yet'),
    latestResult: text(state?.latest_result ?? report?.result, 'No result yet'),
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane, 'No recommended lane yet'),
    risks: state?.risks ?? report?.risks
  }
}

export function buildMissionControlCopyPrompt({
  project,
  status,
  state,
  report
}: {
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
}): string {
  const model = projectRenderModel(project, report, state)

  const prompt = `MISSION CONTROL PROJECT LANE — MANUAL COPY ONLY

Project: ${project.name}
Status: ${text(state?.status ?? project.status)}
Current goal: ${text(state?.current_goal ?? project.current_goal)}
Latest report summary: ${model.latestReportSummary}
Latest result: ${model.latestResult}
Risks/blockers: ${[listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'}
Next recommended lane: ${model.nextLane}

Safety status:
- Runtime Worktree Guard: ${status.guard}
- dispatch_in_gateway: ${yesNo(status.dispatch)}
- active_lane_count: ${status.activeLaneCount}
- stale_warnings: ${status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'}

Mode: read-only/manual-copy planning packet unless Travis explicitly approves a narrower implementation lane.
Forbidden: dispatch, queue/Kanban/Waha/model routing, enforcement, hidden workers, deploy, restart, runtime switch, records/config mutation, public/customer actions, payments, or secrets.
Expected report: preflight, actions taken, verification, blockers, and no-forbidden-mutation confirmation.`

  return truncate(prompt, MAX_COPY_PROMPT_CHARS)
}

export function MissionControlView() {
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(emptySnapshot)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copiedProjectId, setCopiedProjectId] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError('')

        const [workspaceStatus, projects, laneRequests, reports, projectState] = await Promise.all([
          getMissionControlWorkspaceStatus(),
          getMissionControlProjects(),
          getMissionControlLaneRequests(),
          getMissionControlReports(),
          getMissionControlProjectState()
        ])

        if (cancelled) {
          return
        }

        setSnapshot({
          laneRequests: unwrapRecords(laneRequests.lane_requests),
          projects: unwrapRecords(projects.projects),
          projectStates: projectState.project_states ?? [],
          reports: unwrapRecords(reports.reports),
          workspaceStatus
        })
      } catch (err) {
        if (!cancelled) {
          setError(String(err instanceof Error ? err.message : err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  const status = useMemo(() => summarizeWorkspaceStatus(snapshot.workspaceStatus), [snapshot.workspaceStatus])
  const realProjects = useMemo(() => sortRealProjects(snapshot.projects.filter(isRealProject)), [snapshot.projects])

  const supportingProjects = useMemo(
    () => snapshot.projects.filter(project => !isRealProject(project) || isSmokeProject(project)),
    [snapshot.projects]
  )

  async function copyPrompt(project: MissionControlProjectRecord) {
    const state = stateForProject(project, snapshot.projectStates)
    const report = state?.latest_report ?? latestReportForProject(project.project_id, snapshot.reports)
    const prompt = buildMissionControlCopyPrompt({ project, report, state, status })
    await navigator.clipboard?.writeText(prompt)
    setCopiedProjectId(project.project_id)
  }

  return (
    <section className="flex h-full min-h-0 flex-col overflow-auto bg-(--ui-chat-surface-background) px-5 py-5 text-foreground">
      <header className="mb-5 flex flex-col gap-2 border-b border-border/60 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Mission Control</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Native desktop project workspace. The five real projects are primary; smoke records are de-emphasized.
            </p>
          </div>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
            Send to Jenny disabled
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Manual-copy only. No dispatch, queue mutation, protected-domain mutation, routing change, guard enforcement, browser storage, timer, or hidden worker.
        </p>
      </header>

      {error ? <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div> : null}
      {loading ? <div className="rounded-lg border border-border/70 p-4 text-sm text-muted-foreground">Loading Mission Control workspace…</div> : null}

      <WorkspaceStatusPanel status={status} />

      <section className="mt-5">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold">Real project workspace</h2>
            <p className="text-xs text-muted-foreground">Primary cards for Travis’s active operating domains.</p>
          </div>
          <span className="text-xs text-muted-foreground">{realProjects.length} of 5 real projects loaded</span>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {realProjects.length === 0 ? (
            <div className="rounded-xl border border-border/70 p-4 text-sm text-muted-foreground">
              No real Mission Control ProjectRecord entries found yet.
            </div>
          ) : (
            realProjects.map(project => {
              const state = stateForProject(project, snapshot.projectStates)

              return (
                <ProjectCard
                  copied={copiedProjectId === project.project_id}
                  key={project.project_id}
                  lane={state?.latest_lane_request ?? latestLaneForProject(project.project_id, snapshot.laneRequests)}
                  onCopy={() => void copyPrompt(project)}
                  project={project}
                  report={state?.latest_report ?? latestReportForProject(project.project_id, snapshot.reports)}
                  state={state}
                  status={status}
                />
              )
            })
          )}
        </div>
      </section>

      {supportingProjects.length ? (
        <section className="mt-6 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 opacity-70">
          <h2 className="text-sm font-semibold">Supporting / smoke records</h2>
          <p className="mt-1 text-xs text-muted-foreground">These records stay available for audit context but are not part of the daily workspace.</p>
          <div className="mt-3 grid gap-2">
            {supportingProjects.map(project => (
              <div className="rounded-lg border border-border/60 bg-background/40 p-3 text-xs text-muted-foreground" key={project.project_id}>
                <span className="font-medium text-foreground/80">{project.name}</span> — de-emphasized smoke/support record
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  )
}

function WorkspaceStatusPanel({ status }: { status: ReturnType<typeof summarizeWorkspaceStatus> }) {
  return (
    <div className="grid gap-3 rounded-xl border border-border/70 bg-background/40 p-4 md:grid-cols-3">
      <StatusItem label="Runtime Worktree Guard" tone={status.guard === 'pass' ? 'good' : 'warn'} value={status.guard} />
      <StatusItem label="dispatch_in_gateway" tone={status.dispatch === false ? 'good' : 'warn'} value={yesNo(status.dispatch)} />
      <StatusItem label="active_lane_count" tone={status.activeLaneCount === 0 ? 'good' : 'warn'} value={String(status.activeLaneCount)} />
      <StatusItem className="md:col-span-2" label="accepted runtime" value={status.runtime} />
      <StatusItem label="accepted head" value={status.head.slice(0, 12)} />
      <StatusItem className="md:col-span-3" label="stale warnings" tone={status.staleWarnings.length ? 'warn' : 'good'} value={status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'} />
    </div>
  )
}

function ProjectCard({
  copied,
  lane,
  onCopy,
  project,
  report,
  state,
  status
}: {
  copied: boolean
  lane: MissionControlLaneRequestRecord | null
  onCopy: () => void
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
}) {
  const model = projectRenderModel(project, report, state)
  const risksBlockers = [listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'
  const prompt = buildMissionControlCopyPrompt({ project, report, state, status })

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border/70 bg-background/50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{project.name}</h3>
          <p className="text-xs text-muted-foreground">{project.project_id}</p>
        </div>
        <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-700 dark:text-emerald-300">Primary project</span>
      </div>
      <Field label="status" value={state?.status ?? project.status} />
      <Field label="current goal" value={state?.current_goal ?? project.current_goal} />
      <Field label="latest Jenny report summary" value={model.latestReportSummary} />
      <Field label="latest result" value={model.latestResult} />
      <Field label="risks/blockers" value={risksBlockers} />
      <Field label="next recommended lane" value={model.nextLane} />
      <Field label="lane request draft" value={lane ? `${lane.title}${lane.status ? ` (${lane.status})` : ''}` : 'No draft lane request recorded'} />
      <Field label="source of truth" value={project.source_of_truth} />
      <div className="grid gap-2 rounded-lg border border-border/70 bg-background/60 p-3 text-xs text-muted-foreground sm:grid-cols-3">
        <span>send_to_jenny: disabled</span>
        <span>dispatch: disabled</span>
        <span>execution: disabled</span>
      </div>
      <div className="rounded-lg border border-dashed border-border/80 p-3 text-xs text-muted-foreground">
        <div className="mb-2 font-medium text-foreground/80">Copy prompt preview ({prompt.length}/{MAX_COPY_PROMPT_CHARS})</div>
        <p className="line-clamp-4 whitespace-pre-wrap">{prompt}</p>
        <button
          className="mt-3 rounded-md border border-border/80 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
          onClick={onCopy}
          type="button"
        >
          {copied ? 'Prompt copied' : 'Copy prompt'}
        </button>
      </div>
    </article>
  )
}

function Field({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="grid gap-1">
      <span className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">{label}</span>
      <span className="text-sm leading-relaxed text-foreground/90">{text(value)}</span>
    </div>
  )
}

function StatusItem({
  className,
  label,
  tone,
  value
}: {
  className?: string
  label: string
  tone?: 'good' | 'warn'
  value: string
}) {
  return (
    <div className={cn('min-w-0 rounded-lg border border-border/60 bg-background/70 p-3', className)}>
      <div className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">{label}</div>
      <div
        className={cn(
          'mt-1 break-words text-sm font-medium',
          tone === 'good' && 'text-emerald-700 dark:text-emerald-300',
          tone === 'warn' && 'text-amber-700 dark:text-amber-300'
        )}
      >
        {value}
      </div>
    </div>
  )
}
