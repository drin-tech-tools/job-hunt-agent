"use client";

import { CoverLetterModal } from "@/components/CoverLetterModal";
import { JobCard } from "@/components/JobCard";
import { StepTraceList } from "@/components/StepTraceList";
import {
  runAgentStream,
  type AgentFinal,
  type ScoredJob,
  type StepTrace,
} from "@/lib/api";
import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "jha_active_resume";

export default function AgentPage() {
  const [query, setQuery] = useState(
    "Find remote AI/ML engineering roles that match my resume and score the top fits.",
  );
  const [resumeText, setResumeText] = useState("");
  const [resumeId, setResumeId] = useState<string | undefined>();
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepTrace[]>([]);
  const [jobs, setJobs] = useState<ScoredJob[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [cover, setCover] = useState<{ subject: string; body: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { content?: string; id?: string };
      if (parsed.content) setResumeText(parsed.content);
      if (parsed.id) setResumeId(parsed.id);
    } catch {
      /* ignore */
    }
  }, []);

  async function run() {
    if (!resumeText.trim()) {
      setMessage("Add a resume first (Resume page) or paste text below.");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setRunning(true);
    setSteps([]);
    setJobs([]);
    setMessage(null);
    setModelUsed(null);

    try {
      await runAgentStream(
        {
          resume_text: resumeText,
          resume_id: resumeId,
          query,
          max_jobs: 8,
          location: "philippines",
          tags: ["ai", "python", "machine-learning"],
        },
        (ev) => {
          if (ev.event === "step") {
            setSteps((prev) => [...prev, ev.data]);
          } else if (ev.event === "final") {
            const data = ev.data as AgentFinal;
            setSteps(data.steps || []);
            setJobs(data.jobs || []);
            setMessage(data.message);
            setModelUsed(data.model_used || null);
          } else if (ev.event === "error") {
            setMessage(ev.data.message);
          }
        },
        ac.signal,
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessage(err instanceof Error ? err.message : "Run failed");
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="animate-fade-up space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
          Agent
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Live SSE trace of Gemini tool calls — search, score, draft, save — with job cards attributed
          to Himalayas / Jobicy.
        </p>
      </div>

      <div className="glass space-y-3 rounded-xl p-4 sm:p-5">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Goal</span>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={2}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-0)] px-3 py-2 outline-none focus:border-[var(--accent)]"
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Resume (used for this run)</span>
          <textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            rows={5}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-0)] px-3 py-2 font-mono text-xs outline-none focus:border-[var(--accent)]"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void run()}
            disabled={running}
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#04140c] disabled:opacity-50"
          >
            {running ? "Running…" : "Run agent"}
          </button>
          {running && (
            <button
              type="button"
              onClick={() => abortRef.current?.abort()}
              className="rounded-md border border-[var(--line)] px-3 py-2 text-sm text-[var(--muted)]"
            >
              Stop
            </button>
          )}
        </div>
        {message && <p className="text-sm text-[var(--muted)]">{message}</p>}
        {modelUsed && (
          <p className="font-mono text-xs text-[var(--muted)]">model: {modelUsed}</p>
        )}
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
            Step trace
          </h2>
          <StepTraceList steps={steps} live={running} />
        </section>
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
            Jobs
          </h2>
          <div className="space-y-3">
            {jobs.length === 0 && (
              <p className="text-sm text-[var(--muted)]">
                Scored roles will appear here after the run.
              </p>
            )}
            {jobs.map((j) => (
              <JobCard
                key={j.job.id}
                item={j}
                onShowCover={(body, subject) => setCover({ body, subject })}
              />
            ))}
          </div>
        </section>
      </div>

      {cover && (
        <CoverLetterModal
          subject={cover.subject}
          body={cover.body}
          onClose={() => setCover(null)}
        />
      )}
    </div>
  );
}
