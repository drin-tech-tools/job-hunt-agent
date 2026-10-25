import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Sora } from "next/font/google";
import { Nav } from "@/components/Nav";
import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Job Hunt Agent",
  description: "AI agent that searches, scores, and tracks remote AI engineering roles.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sora.variable} ${plex.variable} ${plexMono.variable}`}>
      <body
        style={
          {
            "--font-display": "var(--font-sora)",
            "--font-body": "var(--font-plex)",
            "--font-mono": "var(--font-plex-mono)",
          } as React.CSSProperties
        }
      >
        <div className="min-h-screen">
          <Nav />
          <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:px-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
