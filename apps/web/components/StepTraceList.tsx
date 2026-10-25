"use client";

import type { StepTrace } from "@/lib/api";

export function StepTraceList({ steps, live }: { steps: StepTrace[]; live?: boolean }) {
  if (!steps.length) {
    return (
      <p className="text-sm text-[var(--muted)]">
        {live ? "Waiting for agent steps…" : "No steps yet."}
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {steps.map((s, i) => (
        <li
          key={`${s.step}-${s.tool}-${i}`}
          className="glass animate-fade-up rounded-lg p-3 sm:p-4"
        >
          <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
            <span className="rounded bg-[var(--bg-2)] px-1.5 py-0.5 font-mono text-[var(--accent)]">
              #{s.step}
            </span>
            {s.tool ? (
              <span className="font-mono text-[var(--text)]">{s.tool}</span>
            ) : (
              <span>response</span>
            )}
            <span className="ml-auto tabular-nums">{s.ms}ms</span>
          </div>
          {s.thought_summary ? (
            <p className="mt-2 text-sm text-[var(--text)]">{s.thought_summary}</p>
          ) : null}
          {s.result_summary ? (
            <p className="mt-1 font-mono text-xs text-[var(--muted)]">{s.result_summary}</p>
          ) : null}
          {s.error ? <p className="mt-1 text-xs text-[var(--danger)]">{s.error}</p> : null}
        </li>
      ))}
      {live && (
        <li className="flex items-center gap-2 px-1 text-xs text-[var(--muted)]">
          <span className="h-1.5 w-8 rounded-full bg-[var(--accent)] animate-pulse-line" />
          Running…
        </li>
      )}
    </ol>
  );
}
