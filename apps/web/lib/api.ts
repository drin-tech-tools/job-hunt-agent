/**
 * Browser client for the same-origin Next.js BFF under `/api/*`.
 *
 * FastAPI is internal-only (Vercel service binding). The UI never talks to it
 * directly and never reads `NEXT_PUBLIC_API_URL` / `API_URL`.
 */

/** Same-origin BFF prefix — maps 1:1 onto FastAPI paths (e.g. `/api/health` → `/health`). */
export const BFF_PREFIX = "/api";

export type TrackerStatus = "saved" | "applied" | "interview" | "offer" | "rejected";
export type JobSource = "Himalayas" | "Jobicy" | "JSearch";

export interface JobPosting {
  id: string;
  title: string;
  company: string;
  location?: string | null;
  description?: string | null;
  apply_url: string;
  source: JobSource;
  salary?: string | null;
  tags?: string[];
}

export interface FitScore {
  score: number;
  matched_skills: string[];
  gaps: string[];
  rationale?: string;
}

export interface CoverLetterDraft {
  subject: string;
  body: string;
  job_id?: string | null;
  job_title?: string | null;
  company?: string | null;
}

export interface ScoredJob {
  job: JobPosting;
  fit?: FitScore | null;
  cover_letter?: CoverLetterDraft | null;
}

export interface StepTrace {
  step: number;
  thought_summary: string;
  tool?: string | null;
  args: Record<string, unknown>;
  result_summary: string;
  ms: number;
  error?: string | null;
}

export interface AgentFinal {
  run_id?: string | null;
  status: string;
  message: string;
  steps: StepTrace[];
  jobs: ScoredJob[];
  model_used?: string | null;
}

export interface Resume {
  id: string;
  title: string;
  content: string;
  skills: string[];
}

export interface TrackerItem {
  id: string;
  job_id: string;
  title: string;
  company: string;
  apply_url: string;
  source: JobSource;
  status: TrackerStatus;
  score?: number | null;
  notes?: string | null;
  cover_letter?: string | null;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BFF_PREFIX}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const contentType = res.headers.get("Content-Type") || "";
  if (!contentType.includes("application/json")) {
    // e.g. an HTML login/error page served in place of the API response
    throw new Error(
      `Unexpected response from ${path} (${res.status} ${contentType || "no content type"}). ` +
        "Your session may have expired — try signing in again.",
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => json<{ status: string }>("/health"),
  listResumes: () => json<Resume[]>("/resumes"),
  createResume: (body: { title: string; content: string; skills?: string[] }) =>
    json<Resume>("/resumes", { method: "POST", body: JSON.stringify(body) }),
  deleteResume: (id: string) =>
    json<{ ok: boolean }>(`/resumes/${id}`, { method: "DELETE" }),
  listTracker: () => json<TrackerItem[]>("/tracker"),
  createTracker: (body: Omit<TrackerItem, "id">) =>
    json<TrackerItem>("/tracker", { method: "POST", body: JSON.stringify(body) }),
  updateTracker: (id: string, body: Partial<TrackerItem>) =>
    json<TrackerItem>(`/tracker/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTracker: (id: string) =>
    json<{ ok: boolean }>(`/tracker/${id}`, { method: "DELETE" }),
};

export type AgentEvent =
  | { event: "run_started"; data: { run_id: string } }
  | { event: "step"; data: StepTrace }
  | { event: "final"; data: AgentFinal }
  | { event: "error"; data: { message: string; run_id?: string } };

/** Parse SSE from the same-origin BFF streaming response. */
export async function runAgentStream(
  body: {
    resume_text?: string;
    resume_id?: string;
    query?: string;
    max_jobs?: number;
    location?: string;
    tags?: string[];
  },
  onEvent: (ev: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BFF_PREFIX}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Agent run failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n");
    buffer = chunks.pop() || "";

    for (const rawLine of chunks) {
      const line = rawLine.replace(/\r$/, "");
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const dataStr = line.slice(5).trim();
        try {
          const data = JSON.parse(dataStr);
          onEvent({ event: currentEvent, data } as AgentEvent);
        } catch {
          // ignore partial JSON
        }
      } else if (line === "") {
        currentEvent = "message";
      }
    }
  }
}
