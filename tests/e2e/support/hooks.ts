import {
  After,
  AfterAll,
  Before,
  BeforeAll,
  setDefaultTimeout,
  Status,
} from "@cucumber/cucumber";
import type { ITestCaseHookParameter } from "@cucumber/cucumber";
import fs from "node:fs";
import { CustomWorld, REPORTS_DIR, SCREENSHOTS_DIR, baseUrl } from "./world.ts";

setDefaultTimeout(90_000);

BeforeAll(async function () {
  fs.mkdirSync(REPORTS_DIR, { recursive: true });
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
});

Before(async function (this: CustomWorld) {
  await this.openBrowser();
  // Default mock-auth seam: AAL2 admin so existing journeys stay green under AUTH_BYPASS.
  // Access-control scenarios override via explicit Given steps.
  const res = await this.page.request.get(`${baseUrl()}/api/e2e/session?as=admin`);
  if (!res.ok()) {
    throw new Error(`Failed to seed default e2e admin session: ${res.status()}`);
  }
});

After(async function (this: CustomWorld, scenario: ITestCaseHookParameter) {
  if (scenario.result?.status === Status.FAILED && this.page) {
    const name = scenario.pickle.name || "failure";
    try {
      await this.screenshot(`FAIL_${name}`);
      if (this.lastScreenshot) {
        await this.attach(fs.readFileSync(this.lastScreenshot), "image/png");
      }
    } catch {
      /* best-effort */
    }
  }
  await this.closeBrowser();
});

AfterAll(async function () {
  /* reports written by cucumber formatters */
});
