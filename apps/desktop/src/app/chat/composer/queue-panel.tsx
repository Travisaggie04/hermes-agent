import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { DisclosureCaret } from '@/components/ui/disclosure-caret'
import { Tip } from '@/components/ui/tooltip'
import { type Translations, useI18n } from '@/i18n'
import { AlertTriangle, ArrowUp, Pencil, Trash2, X } from '@/lib/icons'
import { cn } from '@/lib/utils'
import type { QueuedPromptEntry } from '@/store/composer-queue'

interface QueuePanelProps {
  busy: boolean
  editingId: null | string
  entries: QueuedPromptEntry[]
  onDelete: (id: string) => void
  onEdit: (entry: QueuedPromptEntry) => void
  onRemoveAttachment: (entryId: string, attachmentId: string) => void
  onSendNow: (id: string) => void
}

const entryPreview = (entry: QueuedPromptEntry, c: Translations['composer']) =>
  entry.text.trim() || (entry.attachments.length > 0 ? c.attachmentOnly : c.emptyTurn)

export function QueuePanel({
  busy,
  editingId,
  entries,
  onDelete,
  onEdit,
  onRemoveAttachment,
  onSendNow
}: QueuePanelProps) {
  const { t } = useI18n()
  const c = t.composer
  const [collapsed, setCollapsed] = useState(false)

  if (entries.length === 0) {
    return null
  }

  return (
    <div className="rounded-2xl border border-border/65 bg-[color-mix(in_srgb,var(--dt-card)_70%,transparent)] py-0.5 shadow-[0_0_0_1px_color-mix(in_srgb,var(--dt-card)_30%,transparent)_inset]">
      <button
        className="flex w-full items-center gap-1.5 px-2.5 py-1 text-left text-[0.72rem] font-medium text-muted-foreground/92 transition-colors hover:text-foreground/90"
        onClick={() => setCollapsed(open => !open)}
        type="button"
      >
        <DisclosureCaret className="shrink-0" open={!collapsed} size="0.875rem" />
        <span className="truncate">{c.queued(entries.length)}</span>
      </button>

      {!collapsed && (
        <div className="space-y-0.5 px-1.5 pb-0.5">
          {entries.map(entry => {
            const isEditing = editingId === entry.id
            const isFailed = entry.status === 'failed'
            const attachmentsCount = entry.attachments.length

            return (
              <div
                className={cn(
                  'group/queue-row flex items-start gap-1.5 rounded-lg border border-transparent px-1.5 py-1',
                  'transition-colors duration-300 ease-out hover:bg-(--chrome-action-hover) hover:transition-none',
                  isEditing && 'border-[color-mix(in_srgb,var(--dt-composer-ring)_40%,transparent)] bg-accent/25',
                  isFailed && 'border-destructive/35 bg-destructive/10'
                )}
                key={entry.id}
              >
                {isFailed ? (
                  <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive/80" />
                ) : (
                  <span
                    aria-hidden
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full border border-foreground/35 bg-transparent"
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[0.73rem] leading-4 text-foreground/92">{entryPreview(entry, c)}</p>
                  {(attachmentsCount > 0 || isEditing || isFailed) && (
                    <div className="mt-0.5 flex items-center gap-1.5 text-[0.64rem] text-muted-foreground/75">
                      {attachmentsCount > 0 && (
                        <span>
                          {c.attachments(attachmentsCount)}
                        </span>
                      )}
                      {isEditing && (
                        <span className="text-[color-mix(in_srgb,var(--dt-composer-ring)_78%,var(--muted-foreground))]">
                          {c.editingInComposer}
                        </span>
                      )}
                    </div>
                  )}
                  {isFailed && (
                    <p className="mt-0.5 line-clamp-2 text-[0.64rem] leading-3 text-destructive/85">
                      {entry.failureReason || c.queuedSendFailed}
                    </p>
                  )}
                  {isFailed && entry.attachments.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {entry.attachments.map(attachment => (
                        <button
                          className="inline-flex max-w-40 items-center gap-1 rounded-md border border-border/55 bg-background/50 px-1.5 py-0.5 text-[0.62rem] text-muted-foreground transition hover:border-destructive/45 hover:text-foreground"
                          key={attachment.id}
                          onClick={() => onRemoveAttachment(entry.id, attachment.id)}
                          type="button"
                        >
                          <span className="truncate">{attachment.label}</span>
                          <X aria-hidden className="h-2.5 w-2.5 shrink-0" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div
                  className={cn(
                    'flex shrink-0 items-center gap-0 transition-opacity',
                    isEditing
                      ? 'opacity-100'
                      : 'opacity-0 group-hover/queue-row:opacity-100 group-focus-within/queue-row:opacity-100'
                  )}
                >
                  <Tip label={c.editQueued}>
                    <Button
                      aria-label={c.editQueued}
                      className="h-5 w-5 rounded-md"
                      disabled={Boolean(editingId) && !isEditing}
                      onClick={() => onEdit(entry)}
                      size="icon-xs"
                      type="button"
                      variant="ghost"
                    >
                      <Pencil size={11} />
                    </Button>
                  </Tip>
                  <Tip label={c.sendQueuedNow}>
                    <Button
                      aria-label={c.sendQueuedNow}
                      className="h-5 w-5 rounded-md"
                      disabled={busy || isEditing}
                      onClick={() => onSendNow(entry.id)}
                      size="icon-xs"
                      type="button"
                      variant="ghost"
                    >
                      <ArrowUp size={11} />
                    </Button>
                  </Tip>
                  <Tip label={c.deleteQueued}>
                    <Button
                      aria-label={c.deleteQueued}
                      className="h-5 w-5 rounded-md"
                      onClick={() => onDelete(entry.id)}
                      size="icon-xs"
                      type="button"
                      variant="ghost"
                    >
                      <Trash2 size={11} />
                    </Button>
                  </Tip>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
