"use client";

import { api, type TrackerItem, type TrackerStatus } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";

const COLUMNS: TrackerStatus[] = ["saved", "applied", "interview", "offer", "rejected"];

export default function TrackerPage() {
  const [items, setItems] = useState<TrackerItem[]>([]);
  const [view, setView] = useState<"kanban" | "table">("kanban");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      setItems(await api.listTracker());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tracker");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const byStatus = useMemo(() => {
    const map: Record<TrackerStatus, TrackerItem[]> = {
      saved: [],
      applied: [],
      interview: [],
      offer: [],
      rejected: [],
    };
    for (const item of items) {
      map[item.status]?.push(item);
    }
    return map;
  }, [items]);

  async function move(id: string, status: TrackerStatus) {
    const updated = await api.updateTracker(id, { status });
    setItems((prev) => prev.map((i) => (i.id === id ? updated : i)));
  }

  async function remove(id: string) {
    await api.deleteTracker(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1
            className="text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Tracker
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Kanban / table of roles saved by you or the agent.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setView("kanban")}
            className={`rounded-md px-3 py-1.5 text-sm ${view === "kanban" ? "bg-[var(--bg-2)]" : "text-[var(--muted)]"}`}
          >
            Kanban
          </button>
          <button
            type="button"
            onClick={() => setView("table")}
            className={`rounded-md px-3 py-1.5 text-sm ${view === "table" ? "bg-[var(--bg-2)]" : "text-[var(--muted)]"}`}
          >
            Table
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-md border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)]"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
      {loading && <p className="text-sm text-[var(--muted)]">Loading…</p>}

      {!loading && view === "kanban" && (
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
          {COLUMNS.map((col) => (
            <div
              key={col}
              className="glass min-h-40 rounded-xl p-3"
              data-testid={`tracker-column-${col}`}
            >
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                {col} · {byStatus[col].length}
              </h2>
              <ul className="mt-3 space-y-2">
                {byStatus[col].map((item) => (
                  <li
                    key={item.id}
                    className="rounded-lg border border-[var(--line)] bg-[var(--bg-0)] p-2.5"
                    data-testid="tracker-card"
                    data-job-id={item.job_id}
                    data-status={item.status}
                  >
                    <p className="text-sm font-medium leading-snug">{item.title}</p>
                    <p className="text-xs text-[var(--muted)]">
                      {item.company} · via {item.source}
                      {item.score != null ? ` · ${item.score}` : ""}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      <a
                        href={item.apply_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-[var(--accent)] hover:underline"
                      >
                        Apply
                      </a>
                      <select
                        data-testid="tracker-status"
                        className="ml-auto rounded border border-[var(--line)] bg-transparent text-[10px]"
                        value={item.status}
                        onChange={(e) => void move(item.id, e.target.value as TrackerStatus)}
                      >
                        {COLUMNS.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="text-[10px] text-[var(--danger)]"
                        onClick={() => void remove(item.id)}
                      >
                        ×
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {!loading && view === "table" && (
        <div className="glass overflow-x-auto rounded-xl">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wider text-[var(--muted)]">
              <tr>
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Source</th>
                <th className="px-3 py-2 font-medium">Score</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-[var(--line)]/60">
                  <td className="px-3 py-2">
                    <div className="font-medium">{item.title}</div>
                    <div className="text-xs text-[var(--muted)]">{item.company}</div>
                  </td>
                  <td className="px-3 py-2 text-[var(--muted)]">{item.source}</td>
                  <td className="px-3 py-2 tabular-nums">{item.score ?? "—"}</td>
                  <td className="px-3 py-2">
                    <select
                      className="rounded border border-[var(--line)] bg-transparent px-1 py-0.5"
                      value={item.status}
                      onChange={(e) => void move(item.id, e.target.value as TrackerStatus)}
                    >
                      {COLUMNS.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <a
                      href={item.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--accent)] hover:underline"
                    >
                      Apply
                    </a>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-[var(--muted)]">
                    No tracked roles yet. Run the agent or save from a job card.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
