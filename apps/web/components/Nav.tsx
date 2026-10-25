"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/resume", label: "Resume" },
  { href: "/agent", label: "Agent" },
  { href: "/tracker", label: "Tracker" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg-0)_85%,transparent)] backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="group flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-[var(--accent)]/15 text-[var(--accent)] transition group-hover:bg-[var(--accent)]/25">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M4 7h16M4 12h10M4 17h14"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span
            className="text-sm font-semibold tracking-tight sm:text-base"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Job Hunt Agent
          </span>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-md px-2.5 py-1.5 text-sm transition ${
                  active
                    ? "bg-[var(--bg-2)] text-[var(--text)]"
                    : "text-[var(--muted)] hover:text-[var(--text)]"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
