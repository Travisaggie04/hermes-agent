import { useEffect, useState } from "react";
import { Database, ShieldCheck } from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { H2 } from "@/components/NouiTypography";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { MissionControlArtifact } from "@/lib/api";
import { cn } from "@/lib/utils";

const panel = "rounded-xl border border-[#284848] bg-black/30 p-4";
const mutedLabel = "text-xs font-semibold uppercase tracking-[0.08em] text-text-secondary";

function formatTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function compactObject(value: Record<string, unknown> | Record<string, number> | Record<string, string[]>): string {
  const entries = Object.entries(value).filter(([, item]) => {
    if (Array.isArray(item)) return item.length > 0;
    return item !== null && item !== undefined && item !== "";
  });
  if (!entries.length) return "-";
  return entries
    .map(([key, item]) => `${key}: ${Array.isArray(item) ? item.join(", ") : String(item)}`)
    .join(" | ");
}

function artifactKey(item: MissionControlArtifact): string {
  return `${item.source_type}:${item.record_id}`;
}

export function ArtifactWorkspaceBrowser() {
  const [items, setItems] = useState<MissionControlArtifact[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadArtifacts() {
      try {
        const response = await api.listMissionControlArtifacts();
        if (cancelled) return;
        setItems(response.items);
        setWarnings(response.warnings);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Could not load artifact metadata");
        }
      } finally {
        if (!cancelled) setLoaded(true);
      }
    }

    void loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card className="font-readable-ui border-[#264545] bg-[#071717]/90 shadow-[0_0_0_1px_rgba(47,214,161,0.04),0_18px_60px_rgba(0,0,0,0.28)]">
      <CardContent className="space-y-5 p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-midground">
              <Database className="h-5 w-5" />
              <H2 className="text-xl">Artifact / Workspace Browser</H2>
            </div>
            <div className="mt-1 text-sm leading-6 text-text-secondary">
              Metadata inventory for Mission Control records and workspace references.
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="outline" className="border-amber-400/35 bg-amber-500/10 text-amber-100">
              Untrusted metadata
            </Badge>
            <Badge tone="outline" className="border-emerald-400/35 bg-emerald-500/10 text-emerald-100">
              Inert context only
            </Badge>
            <Badge tone="outline" className="border-red-400/35 bg-red-500/10 text-red-100">
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
              Not trusted for execution
            </Badge>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
            Could not load artifact metadata: {error}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="space-y-2 rounded-xl border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">
            {warnings.map((warning) => (
              <div key={warning}>{warning}</div>
            ))}
          </div>
        )}

        {!error && loaded && items.length === 0 && (
          <div className={cn(panel, "text-sm text-text-secondary")}>No artifact metadata recorded.</div>
        )}

        {!error && items.length > 0 && (
          <div className="grid gap-3">
            {items.map((item) => (
              <article key={artifactKey(item)} className={panel}>
                <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="break-words text-base font-semibold text-text-primary">{item.title || item.record_id}</div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-secondary">
                      <span>{item.source_type}</span>
                      <span>{item.kind}</span>
                      <span>{item.status || "unknown"}</span>
                      {item.project && <span>{item.project}</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone="outline" className="border-amber-400/30 text-amber-100">
                      untrusted={String(item.untrusted)}
                    </Badge>
                    <Badge tone="outline" className="border-emerald-400/30 text-emerald-100">
                      inert_context_only={String(item.inert_context_only)}
                    </Badge>
                    <Badge tone="outline" className="border-red-400/30 text-red-100">
                      trusted_for_execution={String(item.trusted_for_execution)}
                    </Badge>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <div className={mutedLabel}>Record ID</div>
                    <pre className="mt-1 whitespace-pre-wrap break-words rounded-lg border border-[#284848] bg-black/35 p-2 font-mono text-xs text-text-secondary">
                      {String(item.record_id || "-")}
                    </pre>
                  </div>
                  <div>
                    <div className={mutedLabel}>Updated</div>
                    <div className="mt-1 text-sm text-text-secondary">{formatTime(item.updated_at || item.created_at)}</div>
                  </div>
                  <div>
                    <div className={mutedLabel}>source_ref_count</div>
                    <div className="mt-1 text-sm text-text-secondary">{item.source_ref_count}</div>
                  </div>
                  <div>
                    <div className={mutedLabel}>Counts</div>
                    <div className="mt-1 break-words text-sm text-text-secondary">{compactObject(item.counts)}</div>
                  </div>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <div className={mutedLabel}>Linked IDs</div>
                    <div className="mt-1 break-words text-sm text-text-secondary">{compactObject(item.linked_ids)}</div>
                  </div>
                  <div>
                    <div className={mutedLabel}>Flags</div>
                    <div className="mt-1 break-words text-sm text-text-secondary">{compactObject(item.flags)}</div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
