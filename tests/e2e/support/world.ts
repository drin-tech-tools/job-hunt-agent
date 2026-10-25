import { setWorldConstructor, World } from "@cucumber/cucumber";
import type { IWorldOptions } from "@cucumber/cucumber";
import {
  chromium,
  type Browser,
  type BrowserContext,
  type Page,
} from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const E2E_ROOT = path.resolve(__dirname, "..");
export const REPORTS_DIR = path.join(E2E_ROOT, "reports");
export const SCREENSHOTS_DIR = path.join(REPORTS_DIR, "screenshots");

export function baseUrl(): string {
  return (process.env.BASE_URL || "http://localhost:3000").replace(/\/$/, "");
}

export function apiUrl(): string {
  return (process.env.API_URL || "http://localhost:8000").replace(/\/$/, "");
}

export class CustomWorld extends World {
  browser!: Browser;
  context!: BrowserContext;
  page!: Page;
  lastScreenshot?: string;

  constructor(options: IWorldOptions) {
    super(options);
  }

  async openBrowser(): Promise<void> {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    this.browser = await chromium.launch({
      headless: process.env.HEADED !== "1",
    });
    this.context = await this.browser.newContext({
      baseURL: baseUrl(),
      viewport: { width: 1280, height: 800 },
    });
    this.page = await this.context.newPage();
  }

  async closeBrowser(): Promise<void> {
    await this.context?.close();
    await this.browser?.close();
  }

  async screenshot(name: string): Promise<string> {
    const safe = name.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 120);
    const file = path.join(SCREENSHOTS_DIR, `${safe}.png`);
    await this.page.screenshot({ path: file, fullPage: true });
    this.lastScreenshot = file;
    return file;
  }
}

setWorldConstructor(CustomWorld);
