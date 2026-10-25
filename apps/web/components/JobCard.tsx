"use client";

import type { ScoredJob } from "@/lib/api";
import { api } from "@/lib/api";
import { useState } from "react";

export function JobCard({
  item,
  onShowCover,
}: {
  item: ScoredJob;
  onShowCover?: (body: string, subject: string) => void;
}) {
  const { job, fit, cover_letter } = item;
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await api.createTracker({
        job_id: job.id,
        title: job.title,
        company: job.company,
        apply_url: job.apply_url,
        source: job.source,
        status: "saved",
        score: fit?.score ?? null,
        notes: fit?.gaps?.length ? `Gaps: ${fit.gaps.join(", ")}` : null,
        cover_letter: cover_letter?.body ?? null,
      });
      setSaved(true);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  const score = fit?.score;
  const scoreColor =
    score == null
      ? "var(--muted)"
      : score >= 75
        ? "var(--accent)"
        : score >= 55
          ? "var(--warn)"
          : "var(--danger)";

  return (
    <article className="glass animate-fade-up rounded-xl p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3
            className="text-lg font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {job.title}
          </h3>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            {job.company}
            {job.location ? ` · ${job.location}` : ""}
          </p>
        </div>
        {score != null && (
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: scoreColor }}>
              {score}
            </div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--muted)]">fit</div>
          </div>
        )}
      </div>

      <p className="mt-3 text-xs text-[var(--muted)]">
        via <span className="text-[var(--text)]">{job.source}</span>
      </p>

      {fit?.matched_skills?.length ? (
        <p className="mt-3 text-sm">
          <span className="text-[var(--muted)]">Matched: </span>
          {fit.matched_skills.slice(0, 8).join(", ")}
        </p>
      ) : null}
      {fit?.gaps?.length ? (
        <p className="mt-1 text-sm">
          <span className="text-[var(--muted)]">Gaps: </span>
          {fit.gaps.slice(0, 6).join(", ")}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <a
          href={job.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-[#04140c] transition hover:brightness-110"
        >
          Apply
        </a>
        {cover_letter && onShowCover && (
          <button
            type="button"
            onClick={() => onShowCover(cover_letter.body, cover_letter.subject)}
            className="rounded-md border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--text)] hover:bg-[var(--bg-2)]"
          >
            Cover letter
          </button>
        )}
        <button
          type="button"
          onClick={save}
          disabled={saving || saved}
          className="rounded-md border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-[var(--text)] disabled:opacity-50"
        >
          {saved ? "Saved" : saving ? "Saving…" : "Save to tracker"}
        </button>
      </div>
    </article>
  );
}
