#!/usr/bin/env node
/**
 * Start API (uvicorn, AGENT_MOCK=1) + Web (next), wait for health, run Cucumber.
 * Usage: node scripts/run-e2e.mjs [--tags '@smoke']
 */
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const E2E_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(E2E_ROOT, "../..");
const API_DIR = path.join(REPO_ROOT, "apps/api");
const WEB_DIR = path.join(REPO_ROOT, "apps/web");

const API_PORT = Number(process.env.API_PORT || 8000);
const WEB_PORT = Number(process.env.WEB_PORT || 3000);
// Use localhost (not 127.0.0.1) so Playwright cookies / redirects share one host.
const BASE_URL = process.env.BASE_URL || `http://localhost:${WEB_PORT}`;
const API_URL = process.env.API_URL || `http://127.0.0.1:${API_PORT}`;

const children = [];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForUrl(url, { timeoutMs = 120_000, intervalMs = 1000 } = {}) {
  const start = Date.now();
  let lastErr = "";
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok || res.status < 500) return;
      lastErr = `status ${res.status}`;
    } catch (err) {
      lastErr = err instanceof Error ? err.message : String(err);
    }
    await sleep(intervalMs);
  }
  throw new Error(`Timed out waiting for ${url}: ${lastErr}`);
}

function run(cmd, args, opts = {}) {
  const child = spawn(cmd, args, {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, ...opts.env },
    cwd: opts.cwd,
    shell: false,
  });
  const label = opts.label || cmd;
  child.stdout.on("data", (d) => process.stdout.write(`[${label}] ${d}`));
  child.stderr.on("data", (d) => process.stderr.write(`[${label}] ${d}`));
  children.push(child);
  return child;
}

function shutdown() {
  for (const child of children) {
    try {
      child.kill("SIGTERM");
    } catch {
      /* ignore */
    }
  }
}

process.on("exit", shutdown);
process.on("SIGINT", () => {
  shutdown();
  process.exit(130);
});
process.on("SIGTERM", () => {
  shutdown();
  process.exit(143);
});

async function portFree(port) {
  return new Promise((resolve) => {
    const srv = createServer();
    srv.once("error", () => resolve(false));
    srv.once("listening", () => srv.close(() => resolve(true)));
    srv.listen(port, "127.0.0.1");
  });
}

async function main() {
  const extraArgs = process.argv.slice(2);

  if (!(await portFree(API_PORT))) {
    console.warn(`[e2e] Port ${API_PORT} busy — assuming API already running`);
  } else {
    const uv = process.env.UV_BIN || "uv";
    run(
      uv,
      ["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
      {
        cwd: API_DIR,
        label: "api",
        env: {
          AGENT_MOCK: "1",
          AUTH_BYPASS: "1",
          GEMINI_API_KEY: "",
          SUPABASE_URL: "",
          SUPABASE_SERVICE_ROLE_KEY: "",
          ALLOWED_ORIGINS: `http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}`,
          AGENT_MAX_STEPS: process.env.AGENT_MAX_STEPS || "8",
        },
      },
    );
  }

  if (!(await portFree(WEB_PORT))) {
    console.warn(`[e2e] Port ${WEB_PORT} busy — assuming web already running`);
  } else {
    run("npm", ["run", "dev", "--", "-p", String(WEB_PORT), "-H", "localhost"], {
      cwd: WEB_DIR,
      label: "web",
      env: {
        // Server-only BFF upstream (Route Handlers). Not NEXT_PUBLIC_*.
        API_URL,
        NODE_ENV: "development",
        AGENT_MOCK: "1",
        AUTH_BYPASS: "1",
        NEXT_PUBLIC_AUTH_BYPASS: "1",
        NEXT_PUBLIC_AGENT_MOCK: "1",
        // Placeholder public Supabase env so modules that read them do not throw at import.
        // Keep unset-looking hosts offline so middleware never hits a real Auth API in e2e.
        NEXT_PUBLIC_SUPABASE_URL:
          process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:54321",
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:
          process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "e2e-publishable-key",
      },
    });
  }

  console.log(`[e2e] Waiting for API ${API_URL}/health …`);
  await waitForUrl(`${API_URL}/health`);
  console.log(`[e2e] Waiting for Web BFF ${BASE_URL}/api/health …`);
  await waitForUrl(`${BASE_URL}/api/health`);
  console.log(`[e2e] Waiting for Web ${BASE_URL} …`);
  await waitForUrl(BASE_URL);

  const cucumberArgs = ["cucumber-js", "--config", "cucumber.mjs", ...extraArgs];
  const cucumber = spawn("npx", cucumberArgs, {
    cwd: E2E_ROOT,
    stdio: "inherit",
    env: {
      ...process.env,
      BASE_URL,
      API_URL,
      AGENT_MOCK: "1",
      AGENT_MAX_STEPS: process.env.AGENT_MAX_STEPS || "8",
      NODE_OPTIONS: [process.env.NODE_OPTIONS, "--import tsx"].filter(Boolean).join(" "),
    },
  });

  const code = await new Promise((resolve) => {
    cucumber.on("exit", (c) => resolve(c ?? 1));
  });
  shutdown();
  // Give children a moment to exit
  await sleep(500);
  process.exit(code);
}

main().catch((err) => {
  console.error(err);
  shutdown();
  process.exit(1);
});
