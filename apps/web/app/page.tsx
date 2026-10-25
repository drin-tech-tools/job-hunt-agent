import Link from "next/link";

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      <section className="animate-fade-up py-10 sm:py-16">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent)]">Portfolio · AI Engineer</p>
        <h1
          className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Job Hunt Agent
        </h1>
        <p className="animate-fade-up-delay mt-5 max-w-xl text-base text-[var(--muted)] sm:text-lg">
          An agent that searches Himalayas &amp; Jobicy, scores fit against your resume, drafts cover
          letters, and tracks applications — with a live step trace you can inspect.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/resume"
            className="rounded-md bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-[#04140c] transition hover:brightness-110"
          >
            Add resume
          </Link>
          <Link
            href="/agent"
            className="rounded-md border border-[var(--line)] px-4 py-2.5 text-sm text-[var(--text)] hover:bg-[var(--bg-2)]"
          >
            Run agent
          </Link>
        </div>
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          {
            title: "Tool-using loop",
            body: "Gemini native function calling with max-step, timeout, and retry guardrails.",
          },
          {
            title: "Attributed sources",
            body: "Every role carries via Himalayas / Jobicy and the original apply URL.",
          },
          {
            title: "Inspectable runs",
            body: "SSE streams each thought → tool → result summary for demos and evals.",
          },
        ].map((f, i) => (
          <div
            key={f.title}
            className="glass rounded-xl p-4"
            style={{ animation: `fade-up 0.6s ease ${0.15 + i * 0.08}s both` }}
          >
            <h2 className="text-sm font-semibold" style={{ fontFamily: "var(--font-display)" }}>
              {f.title}
            </h2>
            <p className="mt-2 text-sm text-[var(--muted)]">{f.body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
