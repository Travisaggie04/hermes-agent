import { useEffect, useMemo, useState } from 'react'

import {
  createMissionControlReport,
  createMissionControlSessionProjectLink,
  getMissionControlLaneRequests,
  getMissionControlProjects,
  getMissionControlProjectSessions,
  getMissionControlProjectState,
  getMissionControlReports,
  getMissionControlWorkspaceStatus,
  type MissionControlLaneRequestRecord,
  type MissionControlProjectRecord,
  type MissionControlProjectSession,
  type MissionControlProjectSessionGroup,
  type MissionControlProjectState,
  type MissionControlReportRecord,
  type MissionControlWorkspaceStatus
} from '@/hermes'
import { cn } from '@/lib/utils'

interface MissionControlSnapshot {
  laneRequests: MissionControlLaneRequestRecord[]
  projectSessionGroups: MissionControlProjectSessionGroup[]
  projects: MissionControlProjectRecord[]
  projectStates: MissionControlProjectState[]
  reports: MissionControlReportRecord[]
  workspaceStatus: MissionControlWorkspaceStatus
}

const emptySnapshot: MissionControlSnapshot = {
  laneRequests: [],
  projectSessionGroups: [],
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

function lineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map(item => item.trim())
    .filter(Boolean)
}

function reportArtifactLinks(report: MissionControlReportRecord | null, state: MissionControlProjectState | null): string[] {
  return state?.artifact_links ?? report?.metadata?.artifact_links ?? report?.changed_files ?? []
}

function freshnessLabel(state: MissionControlProjectState | null): string {
  if (state?.has_real_report) {
    return 'Live report available'
  }

  return 'Seed only — needs first report'
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

function sessionGroupForProject(project: MissionControlProjectRecord, groups: MissionControlProjectSessionGroup[]) {
  return groups.find(group => group.project_id === project.project_id) ?? null
}

function unassignedSessionGroup(groups: MissionControlProjectSessionGroup[]) {
  return groups.find(group => group.project_id === 'unassigned-general') ?? null
}

function suggestedSessionsForProject(projectId: string, groups: MissionControlProjectSessionGroup[]): MissionControlProjectSession[] {
  return (unassignedSessionGroup(groups)?.sessions ?? []).filter(session => session.suggested_project_id === projectId).slice(0, 3)
}

function projectNameForId(projectId: string, projects: MissionControlProjectRecord[]): string {
  return projects.find(project => project.project_id === projectId)?.name ?? projectId
}

function sessionTitle(session: MissionControlProjectSession): string {
  return text(session.title || session.preview || session.session_id, 'Untitled session')
}

function basename(path: string | null | undefined): string {
  if (!path) {
    return ''
  }

  return path
    .replace(/[\\/]+$/, '')
    .split(/[\\/]/)
    .filter(Boolean)
    .pop() ?? path
}

function sessionMeta(session: MissionControlProjectSession): string {
  const meta = [session.profile, session.source, basename(session.cwd)].filter(Boolean)

  return meta.length ? meta.join(' · ') : 'No profile/source recorded'
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
  artifactLinks: string[]
  blockers: unknown
  latestActivityAt: string
  latestActivitySource: string
  latestReportSummary: string
  latestResult: string
  missingStateFields: string[]
  nextLane: string
  risks: unknown
}

interface ReportFormState {
  projectId: string
  laneRequestId: string
  summary: string
  result: string
  risks: string
  changedFiles: string
  tests: string
  artifactLinks: string
  nextRecommendedLane: string
}

const emptyReportForm: ReportFormState = {
  artifactLinks: '',
  changedFiles: '',
  laneRequestId: '',
  nextRecommendedLane: '',
  projectId: '',
  result: '',
  risks: '',
  summary: '',
  tests: ''
}

type SessionLinkAction = 'link' | 'move' | 'suggested'

interface SessionLinkDialogState {
  action: SessionLinkAction
  confirmed: boolean
  currentProjectId: string
  projectId: string
  session: MissionControlProjectSession
}

function durableSessionId(session: MissionControlProjectSession): string {
  return session.lineage_root_id || session.durable_session_id || session.session_id
}

function sessionLinkPayload(dialog: SessionLinkDialogState) {
  const durable = durableSessionId(dialog.session)

  return {
    confidence: 'manual',
    cwd_snapshot: dialog.session.cwd || undefined,
    lineage_root_id: durable || undefined,
    link_method: 'manual',
    profile: dialog.session.profile || undefined,
    project_id: dialog.projectId,
    session_id: dialog.session.session_id,
    source: dialog.session.source || undefined,
    status: 'active',
    title_snapshot: sessionTitle(dialog.session)
  }
}

function projectOptionsForDialog(projects: MissionControlProjectRecord[], dialog: SessionLinkDialogState | null): MissionControlProjectRecord[] {
  if (!dialog || dialog.action !== 'move') {
    return projects
  }

  return projects.filter(project => project.project_id !== dialog.currentProjectId)
}

function projectForDialog(projects: MissionControlProjectRecord[], projectId: string): MissionControlProjectRecord | null {
  return projects.find(project => project.project_id === projectId) ?? null
}

function projectRenderModel(
  project: MissionControlProjectRecord,
  report: MissionControlReportRecord | null,
  state: MissionControlProjectState | null
): ProjectRenderModel {
  return {
    artifactLinks: reportArtifactLinks(report, state),
    blockers: state?.blockers ?? report?.blockers,
    latestActivityAt: text(state?.latest_activity_at, 'No activity time recorded'),
    latestActivitySource: text(state?.latest_activity_source, 'project'),
    latestReportSummary: text(state?.latest_report_summary || report?.summary, 'No report yet'),
    latestResult: text(state?.latest_result || report?.result, 'No result yet'),
    missingStateFields: state?.missing_state_fields ?? [],
    nextLane: text(state?.next_recommended_lane ?? report?.next_recommended_lane ?? project.next_recommended_lane, 'No recommended lane yet'),
    risks: state?.risks ?? state?.risks_blockers ?? report?.risks
  }
}

interface ProjectLaneTemplate {
  allowed: string
  forbidden: string
  objective: string
  preflight: string
  report: string
  stop: string
}

const PROJECT_LANE_TEMPLATES: Record<string, ProjectLaneTemplate> = {
  'project-hermes-mission-control': {
    allowed: 'Read APIs, inspect Desktop/backend state, edit scoped Desktop source/tests only when implementation is explicitly approved.',
    forbidden: 'No deploy, restart, runtime switch, records/config mutation, dispatch, queue/model routing, enforcement, hidden workers, or secrets.',
    objective: 'Improve Mission Control as the primary Desktop workspace while keeping backend source-of-truth and manual-copy controls.',
    preflight: 'Confirm accepted runtime/head, Runtime Worktree Guard=pass, dispatch=false, active_lane_count=0, stale_warnings=[].',
    report: 'preflight, changed files, UI/source proof, tests, PR/status, no-forbidden-mutation confirmation.',
    stop: 'Stop if live runtime drifts, guard fails, dispatch enables, stale warnings appear, or a deploy/restart would be needed.'
  },
  'project-long-form-video': {
    allowed: 'Plan/review adult animated/vector explainer pipeline, toolchain proofs, scripts, QA criteria, and manual next-lane packets.',
    forbidden: 'No posting, paid API render, avatar-first pivot, generic static-card fallback, long unattended render, or public/customer action.',
    objective: 'Advance the long-form adult animated explainer lane with reusable character/prop workflow and evidence-backed watchability.',
    preflight: 'Check current concept/toolchain status, cost/risk gates, review artifacts, and whether a small proof is safer than long production.',
    report: 'objective, source/toolchain checks, recommended proof, risks/costs, review package path if any, next decision needed.',
    stop: 'Stop if paid spend, public publishing, account linking, or a long render is required without fresh approval.'
  },
  'project-shorts-video': {
    allowed: 'Plan short-form topics/hooks, review proof packages, improve prompts/QA, and prepare manual production packets.',
    forbidden: 'No posting, paid API spend, account changes, fake evidence framing, avatar fallback, or unreviewed batch publishing.',
    objective: 'Improve Shorts/Signal Room style output with strong hooks, readable typography, motion quality, and platform-safe packaging.',
    preflight: 'Check channel/status lock, latest proof quality, topic fit, cost/credit exposure, and no public-action gate is crossed.',
    report: 'hook/topic, proof status, QA notes, risks, exact next production lane, approval needed before posting/spend.',
    stop: 'Stop if posting, paid rendering, credential/account mutation, or unbounded batch work is needed.'
  },
  'project-tool-tally': {
    allowed: 'Inspect staging/public pages, draft careful PRs, validate read-only customer-facing copy, and prepare gated launch/hardening packets.',
    forbidden: 'No payments, paid-order mutation, launch, customer delivery, outreach, public intake changes, or production deploy without approval.',
    objective: 'Move Tool & Tally forward safely while preserving launch gates, payment safety, and evidence-first customer-facing quality.',
    preflight: 'Confirm environment, changed-file scope, no live/payment/outreach path, order watchdog unaffected, and customer-facing copy is sanitized.',
    report: 'preflight, files/URLs checked, risk/payment/outreach gates, tests or browser QA, PR/status, next approval gate.',
    stop: 'Stop if payment/order data, public launch, customer contact, deploy, or credential change becomes necessary.'
  },
  'project-waha-work': {
    allowed: 'Prepare owner-side Waha inspection packets, review technical docs, and keep work isolated to Waha profile/context.',
    forbidden: 'No cross-profile memory bleed, no business/social/Family Hub contamination, no unapproved numbers as final, no public/customer action.',
    objective: 'Support Waha owner-side inspection engineering with isolated, evidence-based technical review and clear management-safe outputs.',
    preflight: 'Confirm Waha profile/thread/context, document scope, source standards, assumptions, and review-only status before analysis.',
    report: 'scope, documents/standards used, findings, R/Y/G or technical notes, assumptions, exact Travis review questions.',
    stop: 'Stop if context belongs outside Waha, source docs are missing, numbers need approval, or cross-contamination risk appears.'
  }
}

function templateForProject(project: MissionControlProjectRecord): ProjectLaneTemplate {
  return PROJECT_LANE_TEMPLATES[project.project_id] ?? {
    allowed: 'Read current project state and prepare a manual next-lane packet only.',
    forbidden: 'No dispatch, deploy, restart, records/config mutation, public/customer action, payments, or secrets.',
    objective: `Prepare the next safe lane for ${project.name}.`,
    preflight: 'Confirm source-of-truth state, guard status, dispatch=false, active_lane_count=0, and stale_warnings=[].',
    report: 'preflight, recommended lane, blockers, verification, no-forbidden-mutation confirmation.',
    stop: 'Stop if the task requires mutation or approval outside the current manual-copy lane.'
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
  const template = templateForProject(project)
  const risksBlockers = [listText(model.risks), listText(model.blockers)].filter(value => value !== 'None recorded').join(' · ') || 'None recorded'
  const noHistory = model.latestReportSummary === 'No report yet' && model.latestResult === 'No result yet'
  const historyFallback = noHistory ? 'No prior report/result exists; start by verifying current state before acting.' : ''

  const prompt = `PROJECT NEXT LANE — MANUAL COPY ONLY

Project: ${project.name}
Objective: ${template.objective}
Current goal: ${text(state?.current_goal ?? project.current_goal)}
Status: ${text(state?.status ?? project.status)}
Latest report: ${model.latestReportSummary}
Latest result: ${model.latestResult}
${historyFallback ? `Fallback: ${historyFallback}
` : ''}Risks/blockers: ${risksBlockers}
Next lane: ${model.nextLane}

Allowed actions: ${template.allowed}
Forbidden actions: ${template.forbidden}
Preflight checks: ${template.preflight}
Stop conditions: ${template.stop}
Expected report format: ${template.report}

Safety: guard=${status.guard}; dispatch=${yesNo(status.dispatch)}; active_lane_count=${status.activeLaneCount}; stale_warnings=${status.staleWarnings.length ? status.staleWarnings.join(', ') : 'none'}.
Send to Jenny remains disabled; paste manually only after review.`

  return truncate(prompt, MAX_COPY_PROMPT_CHARS)
}

async function loadMissionControlSnapshot(): Promise<MissionControlSnapshot> {
  const [workspaceStatus, projects, laneRequests, reports, projectState, projectSessions] = await Promise.all([
    getMissionControlWorkspaceStatus(),
    getMissionControlProjects(),
    getMissionControlLaneRequests(),
    getMissionControlReports(),
    getMissionControlProjectState(),
    getMissionControlProjectSessions()
  ])

  return {
    laneRequests: unwrapRecords(laneRequests.lane_requests),
    projectSessionGroups: projectSessions.groups ?? [],
    projects: unwrapRecords(projects.projects),
    projectStates: projectState.project_states ?? [],
    reports: unwrapRecords(reports.reports),
    workspaceStatus
  }
}

export function MissionControlView() {
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(emptySnapshot)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copiedProjectId, setCopiedProjectId] = useState('')
  const [reportForm, setReportForm] = useState<ReportFormState>(emptyReportForm)
  const [reportSaving, setReportSaving] = useState(false)
  const [reportMessage, setReportMessage] = useState('')
  const [sessionLinkDialog, setSessionLinkDialog] = useState<SessionLinkDialogState | null>(null)
  const [sessionLinkSaving, setSessionLinkSaving] = useState(false)
  const [sessionLinkMessage, setSessionLinkMessage] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError('')
        const nextSnapshot = await loadMissionControlSnapshot()

        if (cancelled) {
          return
        }

        setSnapshot(nextSnapshot)
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
  const unassignedGroup = useMemo(() => unassignedSessionGroup(snapshot.projectSessionGroups), [snapshot.projectSessionGroups])

  const supportingProjects = useMemo(
    () => snapshot.projects.filter(project => !isRealProject(project) || isSmokeProject(project)),
    [snapshot.projects]
  )

  async function copyPrompt(project: MissionControlProjectRecord) {
    const state = stateForProject(project, snapshot.projectStates)
    const report = state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)
    const prompt = buildMissionControlCopyPrompt({ project, report, state, status })
    await navigator.clipboard?.writeText(prompt)
    setCopiedProjectId(project.project_id)
  }

  function updateReportField(field: keyof ReportFormState, value: string) {
    setReportForm(current => ({ ...current, [field]: value }))
  }

  async function saveManualReport() {
    if (!reportForm.projectId || !reportForm.summary.trim()) {
      setReportMessage('Choose a project and enter a report summary before saving.')

      return
    }

    setReportSaving(true)
    setReportMessage('')

    try {
      await createMissionControlReport({
        artifact_links: lineList(reportForm.artifactLinks),
        changed_files: lineList(reportForm.changedFiles),
        lane_request_id: reportForm.laneRequestId.trim() || undefined,
        next_recommended_lane: reportForm.nextRecommendedLane.trim() || undefined,
        project_id: reportForm.projectId,
        result: reportForm.result.trim() || undefined,
        risks: lineList(reportForm.risks),
        summary: reportForm.summary.trim(),
        tests: lineList(reportForm.tests)
      })
      setReportForm({ ...emptyReportForm, projectId: reportForm.projectId })
      setReportMessage('Jenny report saved manually. Send to Jenny is still disabled.')
      setSnapshot(await loadMissionControlSnapshot())
    } catch (err) {
      setReportMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setReportSaving(false)
    }
  }

  function openSessionLinkDialog(
    action: SessionLinkAction,
    session: MissionControlProjectSession,
    projectId = '',
    currentProjectId = ''
  ) {
    setSessionLinkMessage('')
    setSessionLinkDialog({ action, confirmed: false, currentProjectId, projectId, session })
  }

  function updateSessionLinkDialog(next: Partial<Pick<SessionLinkDialogState, 'confirmed' | 'projectId'>>) {
    setSessionLinkDialog(current => (current ? { ...current, ...next } : current))
  }

  async function saveSessionProjectLink() {
    if (!sessionLinkDialog || !sessionLinkDialog.confirmed || !sessionLinkDialog.projectId) {
      setSessionLinkMessage('Choose a project and confirm that one append-only record will be written.')

      return
    }

    setSessionLinkSaving(true)
    setSessionLinkMessage('')

    try {
      await createMissionControlSessionProjectLink(sessionLinkPayload(sessionLinkDialog))
      setSessionLinkMessage('Session link record appended. Send to Jenny remains disabled.')
      setSessionLinkDialog(null)
      setSnapshot(await loadMissionControlSnapshot())
    } catch (err) {
      setSessionLinkMessage(String(err instanceof Error ? err.message : err))
    } finally {
      setSessionLinkSaving(false)
    }
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

      <ManualReportIngestion
        form={reportForm}
        message={reportMessage}
        onChange={updateReportField}
        onSave={() => void saveManualReport()}
        projects={realProjects}
        saving={reportSaving}
      />

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
                  onConfirmSuggestedLink={session => openSessionLinkDialog('suggested', session, project.project_id)}
                  onCopy={() => void copyPrompt(project)}
                  onMoveLink={session => openSessionLinkDialog('move', session, '', project.project_id)}
                  project={project}
                  report={state?.latest_report ?? state?.latest_jenny_report ?? latestReportForProject(project.project_id, snapshot.reports)}
                  sessionGroup={sessionGroupForProject(project, snapshot.projectSessionGroups)}
                  state={state}
                  status={status}
                  suggestedSessions={suggestedSessionsForProject(project.project_id, snapshot.projectSessionGroups)}
                />
              )
            })
          )}
        </div>
      </section>

      <UnassignedSessionsPanel
        group={unassignedGroup}
        onLinkManual={session => openSessionLinkDialog('link', session, session.suggested_project_id || '')}
        projects={realProjects}
      />

      <SessionLinkConfirmationDialog
        dialog={sessionLinkDialog}
        message={sessionLinkMessage}
        onCancel={() => setSessionLinkDialog(null)}
        onChange={updateSessionLinkDialog}
        onSave={() => void saveSessionProjectLink()}
        projects={realProjects}
        saving={sessionLinkSaving}
      />

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

function ManualReportIngestion({
  form,
  message,
  onChange,
  onSave,
  projects,
  saving
}: {
  form: ReportFormState
  message: string
  onChange: (field: keyof ReportFormState, value: string) => void
  onSave: () => void
  projects: MissionControlProjectRecord[]
  saving: boolean
}) {
  return (
    <section aria-label="Manual Jenny report ingestion" className="mt-5 rounded-xl border border-border/70 bg-background/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Manual Jenny report ingestion</h2>
          <p className="text-xs text-muted-foreground">
            Append-only report save for real project state. Send to Jenny remains disabled; this does not dispatch work.
          </p>
        </div>
        <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-700 dark:text-blue-300">
          POST allowed only: reports/create
        </span>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <label className="grid gap-1 text-xs font-medium">
          Project
          <select
            className="rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
            onChange={event => onChange('projectId', event.target.value)}
            value={form.projectId}
          >
            <option value="">Choose one of five real projects</option>
            {projects.map(project => (
              <option key={project.project_id} value={project.project_id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <ReportInput label="Optional lane request ID" onChange={value => onChange('laneRequestId', value)} value={form.laneRequestId} />
        <ReportInput label="Jenny report summary" onChange={value => onChange('summary', value)} required value={form.summary} />
        <ReportInput label="Latest result" onChange={value => onChange('result', value)} value={form.result} />
        <ReportInput label="Risks/blockers — one per line" onChange={value => onChange('risks', value)} value={form.risks} />
        <ReportInput label="Artifact/report links — one per line" onChange={value => onChange('artifactLinks', value)} value={form.artifactLinks} />
        <ReportInput label="Changed files or evidence paths — one per line" onChange={value => onChange('changedFiles', value)} value={form.changedFiles} />
        <ReportInput label="Tests/checks — one per line" onChange={value => onChange('tests', value)} value={form.tests} />
        <ReportInput className="lg:col-span-2" label="Next recommended lane" onChange={value => onChange('nextRecommendedLane', value)} value={form.nextRecommendedLane} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60"
          disabled={saving}
          onClick={onSave}
          type="button"
        >
          {saving ? 'Saving report…' : 'Save Jenny report manually'}
        </button>
        <span className="text-xs text-muted-foreground">Manual-copy only · no session send · no queue mutation · no model routing</span>
      </div>
      {message ? <p className="mt-2 text-sm text-muted-foreground">{message}</p> : null}
    </section>
  )
}

function ReportInput({
  className,
  label,
  onChange,
  required,
  value
}: {
  className?: string
  label: string
  onChange: (value: string) => void
  required?: boolean
  value: string
}) {
  return (
    <label className={cn('grid gap-1 text-xs font-medium', className)}>
      {label}
      <textarea
        className="min-h-20 rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
        onChange={event => onChange(event.target.value)}
        required={required}
        value={value}
      />
    </label>
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

function ProjectSessionSummary({
  linkedCount,
  onConfirmSuggestedLink,
  onMoveLink,
  recentSessions,
  suggestedSessions
}: {
  linkedCount: number
  onConfirmSuggestedLink: (session: MissionControlProjectSession) => void
  onMoveLink: (session: MissionControlProjectSession) => void
  recentSessions: MissionControlProjectSession[]
  suggestedSessions: MissionControlProjectSession[]
}) {
  return (
    <section aria-label="Project sessions" className="rounded-lg border border-border/70 bg-background/60 p-3 text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-foreground/80">Project sessions</span>
        <span>{linkedCount} linked</span>
      </div>
      {recentSessions.length ? (
        <div className="mt-2 grid gap-2">
          {recentSessions.slice(0, 3).map(session => (
            <SessionSummaryRow
              actionLabel="Move link"
              badge="Linked · source of truth"
              key={session.durable_session_id || session.session_id}
              onAction={() => onMoveLink(session)}
              session={session}
            />
          ))}
        </div>
      ) : (
        <p className="mt-2">No linked sessions yet.</p>
      )}
      {suggestedSessions.length ? (
        <div className="mt-3 rounded-md border border-dashed border-amber-500/40 bg-amber-500/5 p-2">
          <div className="font-medium text-amber-800 dark:text-amber-200">Suggested sessions — display-only</div>
          <p className="mt-1">Suggestions do not create links or become source-of-truth records.</p>
          <div className="mt-2 grid gap-2">
            {suggestedSessions.map(session => (
              <SessionSummaryRow
                actionLabel="Review link"
                badge="Display-only suggestion"
                key={session.durable_session_id || session.session_id}
                onAction={() => onConfirmSuggestedLink(session)}
                session={session}
              />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function SessionSummaryRow({
  actionLabel,
  badge,
  onAction,
  session
}: {
  actionLabel?: string
  badge?: string
  onAction?: () => void
  session: MissionControlProjectSession
}) {
  return (
    <div className="rounded-md border border-border/60 bg-background/70 p-2">
      <div className="font-medium text-foreground/90">{sessionTitle(session)}</div>
      <div className="mt-0.5 text-[0.7rem] text-muted-foreground">{sessionMeta(session)}</div>
      {badge ? <div className="mt-1 text-[0.7rem] font-medium text-amber-700 dark:text-amber-200">{badge}</div> : null}
      {onAction && actionLabel ? (
        <button className="mt-2 rounded-md border border-border/70 px-2 py-1 text-[0.7rem] font-medium text-foreground hover:bg-muted" onClick={onAction} type="button">
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}

function UnassignedSessionsPanel({
  group,
  onLinkManual,
  projects
}: {
  group: MissionControlProjectSessionGroup | null
  onLinkManual: (session: MissionControlProjectSession) => void
  projects: MissionControlProjectRecord[]
}) {
  const sessions = group?.sessions ?? []
  const suggestionCount = group?.unassigned_suggestion_count ?? sessions.filter(session => session.suggested_project_id).length

  return (
    <section className="mt-6 rounded-xl border border-border/70 bg-background/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Unassigned / General sessions</h2>
          <p className="text-xs text-muted-foreground">Recent sessions not linked to a Mission Control project yet.</p>
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-800 dark:text-amber-200">
          {sessions.length} recent · {suggestionCount} suggestions
        </span>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Suggested project badges are display-only. They do not create SessionProjectLinkRecord truth.</p>
      {sessions.length ? (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {sessions.slice(0, 6).map(session => (
            <div className="rounded-lg border border-border/60 bg-background/60 p-3 text-xs" key={session.durable_session_id || session.session_id}>
              <div className="font-medium text-foreground/90">{sessionTitle(session)}</div>
              <div className="mt-1 text-muted-foreground">{sessionMeta(session)}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {session.suggested_project_id ? (
                  <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[0.68rem] font-medium text-blue-700 dark:text-blue-300">
                    Suggested: {projectNameForId(session.suggested_project_id, projects)} · display-only
                  </span>
                ) : (
                  <span className="text-[0.68rem] text-muted-foreground">No suggested project</span>
                )}
                <button className="rounded-md border border-border/70 px-2 py-1 text-[0.7rem] font-medium text-foreground hover:bg-muted" onClick={() => onLinkManual(session)} type="button">
                  Link manually
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-border/60 bg-background/60 p-3 text-sm text-muted-foreground">No unassigned sessions returned.</div>
      )}
    </section>
  )
}

function ProjectCard({
  copied,
  lane,
  onConfirmSuggestedLink,
  onCopy,
  onMoveLink,
  project,
  report,
  sessionGroup,
  state,
  status,
  suggestedSessions
}: {
  copied: boolean
  lane: MissionControlLaneRequestRecord | null
  onConfirmSuggestedLink: (session: MissionControlProjectSession) => void
  onCopy: () => void
  onMoveLink: (session: MissionControlProjectSession) => void
  project: MissionControlProjectRecord
  report: MissionControlReportRecord | null
  sessionGroup: MissionControlProjectSessionGroup | null
  state: MissionControlProjectState | null
  status: ReturnType<typeof summarizeWorkspaceStatus>
  suggestedSessions: MissionControlProjectSession[]
}) {
  const model = projectRenderModel(project, report, state)
  const linkedSessionCount = state?.linked_session_count ?? sessionGroup?.linked_session_count ?? sessionGroup?.sessions.length ?? 0
  const recentSessions = state?.recent_sessions?.length ? state.recent_sessions : (sessionGroup?.sessions ?? [])
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
      <Field label="freshness" value={freshnessLabel(state)} />
      <Field label="latest lane" value={lane ? `${lane.title}${lane.status ? ` (${lane.status})` : ''}${lane.objective ? ` — ${lane.objective}` : ''}` : 'No draft lane request recorded'} />
      <Field label="latest Jenny report summary" value={model.latestReportSummary} />
      <Field label="latest result" value={model.latestResult} />
      <Field label="risks/blockers" value={risksBlockers} />
      <Field label="last action time" value={`${model.latestActivityAt} (${model.latestActivitySource})`} />
      <Field label="artifact/report links" value={listText(model.artifactLinks, 'No artifact/report links recorded')} />
      <Field label="missing state fields" value={listText(model.missingStateFields, 'None — report state is current')} />
      <Field label="next recommended lane" value={model.nextLane} />
      <Field label="source of truth" value={project.source_of_truth} />
      <ProjectSessionSummary
        linkedCount={linkedSessionCount}
        onConfirmSuggestedLink={onConfirmSuggestedLink}
        onMoveLink={onMoveLink}
        recentSessions={recentSessions}
        suggestedSessions={suggestedSessions}
      />
      <div className="grid gap-2 rounded-lg border border-border/70 bg-background/60 p-3 text-xs text-muted-foreground sm:grid-cols-3">
        <span>send_to_jenny: disabled</span>
        <span>dispatch: disabled</span>
        <span>execution: disabled</span>
      </div>
      <div className="rounded-lg border border-dashed border-border/80 p-3 text-xs text-muted-foreground">
        <div className="mb-2 font-medium text-foreground/80">Next lane prompt preview ({prompt.length}/{MAX_COPY_PROMPT_CHARS})</div>
        <p className="line-clamp-4 whitespace-pre-wrap">{prompt}</p>
        <button
          className="mt-3 rounded-md border border-border/80 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted"
          onClick={onCopy}
          type="button"
        >
          {copied ? 'Prompt copied' : 'Copy next lane prompt'}
        </button>
      </div>
    </article>
  )
}

function SessionLinkConfirmationDialog({
  dialog,
  message,
  onCancel,
  onChange,
  onSave,
  projects,
  saving
}: {
  dialog: SessionLinkDialogState | null
  message: string
  onCancel: () => void
  onChange: (next: Partial<Pick<SessionLinkDialogState, 'confirmed' | 'projectId'>>) => void
  onSave: () => void
  projects: MissionControlProjectRecord[]
  saving: boolean
}) {
  if (!dialog) {
    return message ? <p className="mt-3 text-sm text-muted-foreground">{message}</p> : null
  }

  const availableProjects = projectOptionsForDialog(projects, dialog)
  const selectedProject = projectForDialog(projects, dialog.projectId)
  const title = dialog.action === 'move' ? 'Move linked session' : dialog.action === 'suggested' ? 'Confirm suggested link' : 'Link session manually'
  const buttonLabel = dialog.action === 'move' ? 'Append superseding link record' : dialog.action === 'suggested' ? 'Confirm suggested link' : 'Append manual link record'
  const disabled = saving || !dialog.confirmed || !dialog.projectId || (dialog.action === 'move' && dialog.projectId === dialog.currentProjectId)

  return (
    <div aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog">
      <section className="max-w-2xl rounded-xl border border-border bg-background p-5 shadow-xl">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Append a manual SessionProjectLinkRecord for <span className="font-medium text-foreground">{sessionTitle(dialog.session)}</span>
          {selectedProject ? ` to ${selectedProject.name}` : ''}.
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          <li>One append-only SessionProjectLinkRecord will be written.</li>
          <li>This does not edit the session database.</li>
          <li>This does not send work to Jenny.</li>
          <li>This does not dispatch anything.</li>
          <li>This does not enable routing.</li>
          <li>Suggestions are display-only until confirmed.</li>
          <li>Moving a link appends a newer record instead of changing old records.</li>
        </ul>
        <div className="mt-4 grid gap-3">
          <label className="grid gap-1 text-xs font-medium">
            Project
            <select
              className="rounded-md border border-border/80 bg-background px-3 py-2 text-sm"
              onChange={event => onChange({ projectId: event.target.value })}
              value={dialog.projectId}
            >
              <option value="">Choose one project</option>
              {availableProjects.map(project => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          {dialog.session.suggested_project_id ? (
            <p className="text-xs text-amber-700 dark:text-amber-200">
              Suggested project: {projectNameForId(dialog.session.suggested_project_id, projects)} · display-only until confirmed.
            </p>
          ) : null}
          <label className="flex items-start gap-2 text-xs text-muted-foreground">
            <input checked={dialog.confirmed} onChange={event => onChange({ confirmed: event.target.checked })} type="checkbox" />
            <span>I understand this appends one Mission Control record only.</span>
          </label>
        </div>
        {message ? <p className="mt-3 text-sm text-muted-foreground">{message}</p> : null}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button className="rounded-md border border-border/80 px-3 py-2 text-sm font-medium hover:bg-muted" onClick={onCancel} type="button">
            Cancel
          </button>
          <button
            className="rounded-md border border-border/80 px-3 py-2 text-sm font-semibold hover:bg-muted disabled:opacity-60"
            disabled={disabled}
            onClick={onSave}
            type="button"
          >
            {saving ? 'Appending record…' : buttonLabel}
          </button>
        </div>
      </section>
    </div>
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
