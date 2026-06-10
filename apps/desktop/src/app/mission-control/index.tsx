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

function unwrapRecords<T>(items: Array<{ record?: T } | T> | undefined): T[] {
  if (!Array.isArray(items)) {
    return []
  }

  return items.map(item => ('record' in Object(item) ? (item as { record?: T }).record : item)).filter(Boolean) as T[]
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

export function MissionControlView() {
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(emptySnapshot)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  return (
    <section className="flex h-full min-h-0 flex-col overflow-auto bg-(--ui-chat-surface-background) px-5 py-5 text-foreground">
      <header className="mb-5 flex flex-col gap-2 border-b border-border/60 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Mission Control</h1>
            <p className="max-w-3xl text-sm text-muted-foreground">
              Native desktop project workspace. Read-only view over Mission Control records and guards.
            </p>
          </div>
          <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
            Send to Jenny disabled
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Manual-copy only. No dispatch, queue mutation, protected-domain mutation, routing change, guard enforcement, or hidden worker.
        </p>
      </header>

      {error ? <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div> : null}
      {loading ? <div className="rounded-lg border border-border/70 p-4 text-sm text-muted-foreground">Loading Mission Control workspace…</div> : null}

      <WorkspaceStatusPanel status={status} />

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {snapshot.projects.length === 0 ? (
          <div className="rounded-xl border border-border/70 p-4 text-sm text-muted-foreground">
            No durable ProjectRecord entries found yet.
          </div>
        ) : (
          snapshot.projects.map(project => (
            <ProjectCard
              key={project.project_id}
              lane={stateForProject(project, snapshot.projectStates)?.latest_lane_request ?? latestLaneForProject(project.project_id, snapshot.laneRequests)}
              project={project}
              report={stateForProject(project, snapshot.projectStates)?.latest_report ?? latestReportForProject(project.project_id, snapshot.reports)}
              state={stateForProject(project, snapshot.projectStates)}
            />
          ))
        )}
      </div>
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
  lane,
  project,
  report,
  state
}: {
  lane: MissionControlLaneRequestRecord | null
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  state: MissionControlProjectState | null
}) {
  const latestReportSummary = state?.latest_report_summary ?? report?.summary
  const latestResult = state?.latest_result ?? report?.result
  const nextLane = state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane
  const risks = state?.risks ?? report?.risks
  const blockers = state?.blockers ?? report?.blockers

  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border/70 bg-background/50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{project.name}</h2>
          <p className="text-xs text-muted-foreground">{project.project_id}</p>
        </div>
        <span className="rounded-full border border-border/70 px-2.5 py-1 text-xs text-muted-foreground">Durable ProjectRecord</span>
      </div>
      <Field label="status" value={state?.status ?? project.status} />
      <Field label="current goal" value={state?.current_goal ?? project.current_goal} />
      <Field label="latest Jenny report summary" value={latestReportSummary} />
      <Field label="latest result" value={latestResult} />
      <Field label="risks/blockers" value={[listText(risks), listText(blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'} />
      <Field label="next recommended lane" value={nextLane} />
      <Field label="lane request draft" value={lane ? `${lane.title}${lane.status ? ` (${lane.status})` : ''}` : 'No draft lane request recorded'} />
      <Field label="source of truth" value={project.source_of_truth} />
      <div className="rounded-lg border border-dashed border-border/80 p-3 text-xs text-muted-foreground">
        Send to Jenny is disabled. Use this page to decide what next; transport remains manual-copy only.
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
