"use client";

import { useState } from "react";

export function CoverLetterModal({
  subject,
  body,
  onClose,
}: {
  subject: string;
  body: string;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(body);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal
        className="glass max-h-[85vh] w-full max-w-2xl overflow-auto rounded-xl p-5 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-[var(--muted)]">Cover letter</p>
            <h2
              className="mt-1 text-lg font-semibold"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {subject}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-sm text-[var(--muted)] hover:bg-[var(--bg-2)] hover:text-[var(--text)]"
          >
            Close
          </button>
        </div>
        <pre className="mt-4 whitespace-pre-wrap font-sans text-sm leading-relaxed text-[var(--text)]">
          {body}
        </pre>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={copy}
            className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-[#04140c]"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
    </div>
  );
}
