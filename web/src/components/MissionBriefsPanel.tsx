import { useCallback, useEffect, useState } from "react";
import { Archive, FileText, ShieldCheck } from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { H2 } from "@/components/NouiTypography";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { MissionBrief, MissionBriefSummary } from "@/lib/api";

const field =
  "w-full rounded-lg border border-[#284848] bg-black/45 p-3 text-sm text-text-primary outline-none focus:border-emerald-400/60";

function splitReferences(value: string): string[] {
  return value.split("\n").filter((item) => item.length > 0);
}

export function MissionBriefsPanel() {
  const [items, setItems] = useState<MissionBriefSummary[]>([]);
  const [selected, setSelected] = useState<MissionBrief | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [references, setReferences] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadBriefs = useCallback(async (preferredId?: string) => {
    const response = await api.listMissionBriefs();
    setItems(response.items);
    const nextId = preferredId || response.items[0]?.id;
    if (!nextId) {
      setSelected(null);
      return;
    }
    const detail = await api.getMissionBrief(nextId);
    setSelected(detail.brief);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialBriefs() {
      try {
        const response = await api.listMissionBriefs();
        if (cancelled) return;
        setItems(response.items);
        const nextId = response.items[0]?.id;
        if (!nextId) {
          setSelected(null);
          return;
        }
        const detail = await api.getMissionBrief(nextId);
        if (!cancelled) setSelected(detail.brief);
      } catch (error) {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : "Could not load Mission Briefs");
        }
      }
    }

    void loadInitialBriefs();
    return () => {
      cancelled = true;
    };
  }, []);

  const saveBrief = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.createMissionBrief({
        title,
        summary,
        references: splitReferences(references),
        author: "dashboard",
      });
      setTitle("");
      setSummary("");
      setReferences("");
      setMessage("Saved local inert Mission Brief.");
      await loadBriefs(response.brief.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save Mission Brief");
    } finally {
      setBusy(false);
    }
  };

  const archiveBrief = async () => {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await api.archiveMissionBrief(selected.id);
      setMessage("Archived Mission Brief locally.");
      await loadBriefs(response.brief.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not archive Mission Brief");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="font-readable-ui border-[#264545] bg-[#071717]/90 shadow-[0_0_0_1px_rgba(47,214,161,0.04),0_18px_60px_rgba(0,0,0,0.28)]">
      <CardContent className="space-y-5 p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-midground">
              <FileText className="h-5 w-5" />
              <H2 className="text-xl">Mission Briefs</H2>
            </div>
            <div className="mt-1 text-sm leading-6 text-text-secondary">
              Local brief notes with opaque user-entered references.
            </div>
          </div>
          <Badge tone="outline" className="border-emerald-400/35 bg-emerald-500/10 text-emerald-100">
            <ShieldCheck className="mr-1 h-3.5 w-3.5" />
            Inert local store
          </Badge>
        </div>

        {message && (
          <div className="rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
            {message}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="space-y-3 rounded-xl border border-[#284848] bg-black/25 p-4">
            <div>
              <Label htmlFor="mission-brief-title">Title</Label>
              <Input
                id="mission-brief-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Phase 1A review brief"
              />
            </div>
            <div>
              <Label htmlFor="mission-brief-summary">Summary</Label>
              <textarea
                id="mission-brief-summary"
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                className={field}
                rows={4}
              />
            </div>
            <div>
              <Label htmlFor="mission-brief-references">References</Label>
              <textarea
                id="mission-brief-references"
                value={references}
                onChange={(event) => setReferences(event.target.value)}
                className={field}
                rows={5}
                placeholder={"/path/kept-as-text\nhttps://kept-as-text.example"}
              />
            </div>
            <Button type="button" onClick={saveBrief} disabled={busy || !title.trim()} className="w-full">
              Save Brief
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-[minmax(180px,0.55fr)_minmax(0,1fr)]">
            <div className="space-y-2 rounded-xl border border-[#284848] bg-black/25 p-3">
              {items.length ? (
                items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() =>
                      api
                        .getMissionBrief(item.id)
                        .then((response) => setSelected(response.brief))
                        .catch((error) => setMessage(error instanceof Error ? error.message : "Could not load brief"))
                    }
                    className="block w-full rounded-lg border border-[#284848] bg-black/35 px-3 py-2 text-left text-sm text-text-primary hover:border-emerald-400/45"
                  >
                    <div className="font-semibold">{item.title}</div>
                    <div className="mt-1 text-xs text-text-secondary">{item.status} · {item.reference_count} refs</div>
                  </button>
                ))
              ) : (
                <div className="text-sm text-text-secondary">No Mission Briefs saved.</div>
              )}
            </div>

            <div className="rounded-xl border border-[#284848] bg-black/25 p-4">
              {selected ? (
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold text-text-primary">{selected.title}</div>
                      <div className="mt-1 text-xs uppercase tracking-wide text-text-secondary">{selected.status}</div>
                    </div>
                    <Button type="button" onClick={archiveBrief} disabled={busy || selected.status === "archived"} outlined>
                      <Archive className="mr-2 h-4 w-4" />
                      Archive
                    </Button>
                  </div>
                  <div className="whitespace-pre-wrap text-sm leading-6 text-text-secondary">{selected.summary || "No summary."}</div>
                  <div className="space-y-2">
                    <div className="text-xs font-semibold uppercase tracking-wide text-text-secondary">Opaque References</div>
                    {selected.references.length ? (
                      selected.references.map((ref, idx) => (
                        <pre key={idx} className="whitespace-pre-wrap break-words rounded-lg border border-[#284848] bg-black/35 p-2 font-mono text-xs text-text-secondary">
                          {ref}
                        </pre>
                      ))
                    ) : (
                      <div className="text-sm text-text-secondary">None recorded.</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-text-secondary">Select or create a Mission Brief.</div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
