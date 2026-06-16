import { type CSSProperties, useState } from 'react'

import introCopyJsonl from './intro-copy.jsonl?raw'

type IntroCopy = {
  headline: string
  body: string
}

type IntroCopyRecord = IntroCopy & {
  personality: string
}

export type IntroProps = {
  personality?: string
  projectName?: string
  projectOptions?: { id: string; name: string }[]
  projectsLoading?: boolean
  onCreateProject?: () => void
  onSelectProject?: (projectId: string, projectName: string) => void
  seed?: number
}

const NEUTRAL_PERSONALITIES = new Set(['', 'default', 'none', 'neutral'])

const FALLBACK_COPY: IntroCopy[] = [
  {
    headline: 'What are we moving today?',
    body: "Send a bug, branch, plan, or rough idea. I'll inspect the repo and turn it into the next concrete step."
  },
  {
    headline: "What's on your mind?",
    body: "Bring the code, question, or stuck part. I'll read the room before making changes."
  },
  {
    headline: 'What should Hermes look at?',
    body: "Send the task, failing path, or half-formed plan. I'll help turn it into action."
  },
  {
    headline: 'Where should we start?',
    body: "Bring the problem, goal, or file. I'll inspect first and keep the next step concrete."
  },
  {
    headline: 'What needs attention?',
    body: "Send the context you have. I'll help sort it into a plan or a fix."
  }
]

function normalizeKey(value?: string): string {
  return (value || '').trim().toLowerCase()
}

function titleize(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function isIntroCopyRecord(value: unknown): value is IntroCopyRecord {
  if (!value || typeof value !== 'object') {
    return false
  }

  const record = value as Record<string, unknown>

  return (
    typeof record.personality === 'string' &&
    typeof record.headline === 'string' &&
    typeof record.body === 'string' &&
    Boolean(record.personality.trim()) &&
    Boolean(record.headline.trim()) &&
    Boolean(record.body.trim())
  )
}

function parseIntroCopy(raw: string): Record<string, IntroCopy[]> {
  const byPersonality: Record<string, IntroCopy[]> = {}

  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim()

    if (!trimmed) {
      continue
    }

    try {
      const parsed: unknown = JSON.parse(trimmed)

      if (!isIntroCopyRecord(parsed)) {
        continue
      }

      const key = normalizeKey(parsed.personality)
      byPersonality[key] ??= []
      byPersonality[key].push({
        headline: parsed.headline.trim(),
        body: parsed.body.trim()
      })
    } catch {
      // Bad generated copy should not break the whole desktop app.
    }
  }

  return byPersonality
}

const INTRO_COPY_BY_PERSONALITY = parseIntroCopy(introCopyJsonl)

function neutralCopy(): IntroCopy[] {
  return INTRO_COPY_BY_PERSONALITY.none || INTRO_COPY_BY_PERSONALITY.default || FALLBACK_COPY
}

function fallbackCopyForPersonality(personalityKey: string): IntroCopy[] {
  if (NEUTRAL_PERSONALITIES.has(personalityKey)) {
    return neutralCopy()
  }

  const label = titleize(personalityKey)

  return [
    {
      headline: `${label} mode is on. What should we work on?`,
      body: "Send the task, file, or rough idea. I'll use your configured voice and keep the work grounded in this repo."
    },
    {
      headline: `What does ${label} Hermes need to see?`,
      body: "Bring the context or the stuck part. I'll adapt to your configured personality."
    },
    {
      headline: `${label} mode is ready.`,
      body: "Send the problem, file, or idea. I'll follow the personality you've configured."
    },
    {
      headline: `What should ${label} Hermes tackle?`,
      body: "Drop the task here. I'll keep the work grounded in the repo."
    },
    {
      headline: 'Where should we begin?',
      body: `Give me the context and I'll answer in ${label} mode.`
    }
  ]
}

function pickCopy(copies: IntroCopy[], seed = 0): IntroCopy {
  return copies[Math.abs(seed) % copies.length] || FALLBACK_COPY[0]
}

const WORDMARK = 'HERMES AGENT'

function resolveCopy(personality?: string, seed?: number): IntroCopy {
  const personalityKey = normalizeKey(personality)

  const copies = NEUTRAL_PERSONALITIES.has(personalityKey)
    ? INTRO_COPY_BY_PERSONALITY[personalityKey] || neutralCopy()
    : INTRO_COPY_BY_PERSONALITY[personalityKey] || fallbackCopyForPersonality(personalityKey)

  return pickCopy(copies, seed)
}

export function Intro({
  personality,
  projectName,
  projectOptions = [],
  projectsLoading = false,
  onCreateProject,
  onSelectProject,
  seed
}: IntroProps) {
  const [mountSeed] = useState(() => Math.floor(Math.random() * 100000))
  const copy = resolveCopy(personality, mountSeed + (seed ?? 0))
  const projectLabel = projectName?.trim() || ''
  const showProjectHome = !projectLabel && (projectsLoading || projectOptions.length > 0)

  return (
    <div
      className="flex w-full min-w-0 flex-col items-center justify-center px-3 py-6 text-center text-muted-foreground sm:px-6 lg:px-8"
      data-slot="aui_intro"
    >
      <div className={showProjectHome ? 'pointer-events-auto w-full min-w-0' : 'pointer-events-none w-full min-w-0'}>
        <p
          aria-label={showProjectHome ? 'Projects' : WORDMARK}
          className={
            showProjectHome
              ? "mx-auto mb-5 text-xs font-semibold uppercase tracking-[0.26em] text-(--ui-text-tertiary)"
              : "fit-text mx-auto mb-3 w-[88%] font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          }
          style={{ '--fit-text-line-height': '0.9', '--fit-text-min': '2.75rem' } as CSSProperties}
        >
          <span>
            <span>{showProjectHome ? 'Projects' : WORDMARK}</span>
          </span>
          {!showProjectHome && <span aria-hidden="true">{WORDMARK}</span>}
        </p>

        {projectLabel ? (
          <div className="mx-auto mb-3 flex max-w-2xl flex-col items-center gap-1 text-center">
            <p className="m-0 text-xs font-medium uppercase text-(--ui-text-tertiary)">Project chat</p>
            <p className="m-0 max-w-full truncate text-lg font-semibold text-foreground">{projectLabel}</p>
            <p className="m-0 text-sm leading-normal tracking-tight">
              Send normally. Jenny replies here, with project context and safety checks in the background.
            </p>
          </div>
        ) : showProjectHome ? (
          <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-3">
            <div className="grid gap-1 text-center">
              <h1 className="m-0 text-2xl font-semibold text-foreground">Pick a project</h1>
              <p className="m-0 max-w-xl text-sm leading-normal tracking-tight">
                Pick a project, then chat normally. Jenny gets the project brief and guardrails without extra copy/paste.
              </p>
            </div>
            <div className="grid w-full max-w-xl gap-2 sm:grid-cols-2">
              {projectsLoading && !projectOptions.length ? (
                <div className="col-span-full rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-sm text-(--ui-text-tertiary)">
                  Loading projects...
                </div>
              ) : (
                projectOptions.map(project => (
                  <button
                    className="min-w-0 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-control-active-background) px-3 py-2 text-left text-sm text-(--ui-text-secondary) transition-colors hover:border-(--ui-accent)/60 hover:bg-(--ui-control-hover-background) hover:text-foreground focus-visible:border-(--ui-accent)/70 focus-visible:outline-none"
                    key={project.id}
                    onClick={() => onSelectProject?.(project.id, project.name)}
                    type="button"
                  >
                    <span className="block truncate font-medium">{project.name}</span>
                    <span className="mt-0.5 block truncate text-xs text-(--ui-text-tertiary)">Open project chat</span>
                  </button>
                ))
              )}
            </div>
            {onCreateProject ? (
              <button
                className="rounded-full border border-(--ui-stroke-tertiary) bg-transparent px-3 py-1.5 text-xs font-medium text-(--ui-text-secondary) transition-colors hover:border-(--ui-accent)/60 hover:bg-(--ui-control-hover-background) hover:text-foreground focus-visible:border-(--ui-accent)/70 focus-visible:outline-none"
                onClick={onCreateProject}
                type="button"
              >
                Create project
              </button>
            ) : null}
          </div>
        ) : (
          <p className="m-0 text-center leading-normal tracking-tight">{copy.body}</p>
        )}
      </div>
    </div>
  )
}
