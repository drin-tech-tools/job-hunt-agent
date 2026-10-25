"use client";

import { api, type Resume } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "jha_active_resume";

export default function ResumePage() {
  const [title, setTitle] = useState("Primary resume");
  const [content, setContent] = useState("");
  const [skills, setSkills] = useState("Python, FastAPI, LLM, RAG, Docker");
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function refresh() {
    try {
      setResumes(await api.listResumes());
    } catch {
      setResumes([]);
    }
  }

  useEffect(() => {
    void refresh();
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        const parsed = JSON.parse(cached) as { content?: string; title?: string };
        if (parsed.content) setContent(parsed.content);
        if (parsed.title) setTitle(parsed.title);
      } catch {
        /* ignore */
      }
    }
  }, []);

  async function onFile(file: File) {
    const text = await file.text();
    setContent(text);
    if (!title || title === "Primary resume") {
      setTitle(file.name.replace(/\.[^.]+$/, ""));
    }
  }

  async function save() {
    if (content.trim().length < 20) {
      setStatus("Paste at least a short resume (20+ chars).");
      return;
    }
    setSaving(true);
    setStatus(null);
    const skillList = skills
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ title, content, skills: skillList, savedAt: Date.now() }),
    );
    try {
      const row = await api.createResume({ title, content, skills: skillList });
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ ...row, savedAt: Date.now() }),
      );
      setStatus("Saved to API + local session.");
      await refresh();
    } catch (err) {
      setStatus(
        `Saved locally. API save failed (${err instanceof Error ? err.message : "error"}). You can still run the agent.`,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="animate-fade-up space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
          Resume
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Paste your resume or upload a `.txt` / `.md` file. It is sent with each agent run for scoring
          and cover letters.
        </p>
      </div>

      <div className="glass space-y-4 rounded-xl p-4 sm:p-6">
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Title</span>
          <input
            data-testid="resume-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-0)] px-3 py-2 outline-none focus:border-[var(--accent)]"
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Skills (comma-separated)</span>
          <input
            data-testid="resume-skills"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-0)] px-3 py-2 outline-none focus:border-[var(--accent)]"
          />
        </label>
        <label className="block text-sm">
          <span className="text-[var(--muted)]">Resume text</span>
          <textarea
            data-testid="resume-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={14}
            placeholder="Paste resume here…"
            className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--bg-0)] px-3 py-2 font-mono text-sm outline-none focus:border-[var(--accent)]"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <label className="cursor-pointer rounded-md border border-[var(--line)] px-3 py-2 text-sm hover:bg-[var(--bg-2)]">
            Upload file
            <input
              type="file"
              accept=".txt,.md,.text,text/plain"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onFile(f);
              }}
            />
          </label>
          <button
            type="button"
            data-testid="resume-save"
            onClick={() => void save()}
            disabled={saving}
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[#04140c] disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save resume"}
          </button>
          <Link href="/agent" className="text-sm text-[var(--accent)] hover:underline">
            Continue to agent →
          </Link>
        </div>
        {status && (
          <p className="text-sm text-[var(--muted)]" data-testid="resume-status">
            {status}
          </p>
        )}
      </div>

      {resumes.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-[var(--muted)]">Saved on API</h2>
          <ul className="mt-3 space-y-2">
            {resumes.map((r) => (
              <li key={r.id} className="glass flex items-center justify-between rounded-lg px-3 py-2 text-sm">
                <button
                  type="button"
                  className="text-left hover:text-[var(--accent)]"
                  onClick={() => {
                    setTitle(r.title);
                    setContent(r.content);
                    setSkills((r.skills || []).join(", "));
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(r));
                  }}
                >
                  {r.title}
                </button>
                <button
                  type="button"
                  className="text-[var(--muted)] hover:text-[var(--danger)]"
                  onClick={() => void api.deleteResume(r.id).then(refresh)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
