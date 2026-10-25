import { Given, Then, When } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { CustomWorld } from "../support/world.ts";

When(
  "I set the agent role to {string} and location to {string}",
  async function (this: CustomWorld, role: string, location: string) {
    await this.page.getByTestId("agent-role").fill(role);
    await this.page.getByTestId("agent-location").fill(location);
    await this.page
      .getByTestId("agent-goal")
      .fill(`Find remote ${role} roles in ${location} that match my resume.`);
  },
);

When(
  "I set the agent goal to include {string}",
  async function (this: CustomWorld, marker: string) {
    const goal = this.page.getByTestId("agent-goal");
    const current = await goal.inputValue();
    await goal.fill(`${current} ${marker}`.trim());
  },
);

When("I run the job search agent", async function (this: CustomWorld) {
  await this.page.getByTestId("agent-run").click();
  // Wait until the run finishes (button enabled again) or a message appears.
  await expect(this.page.getByTestId("agent-run")).toBeEnabled({ timeout: 60_000 });
  await expect(this.page.getByTestId("agent-message")).toBeVisible({ timeout: 60_000 });
});

Given("job cards are visible", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("job-card").first()).toBeVisible({ timeout: 30_000 });
});

Then(
  "I should see a live step trace with tool calls",
  async function (this: CustomWorld) {
    const items = this.page.getByTestId("step-trace-item");
    await expect(items.first()).toBeVisible({ timeout: 30_000 });
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
    const tools = await items.evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-tool") || ""),
    );
    expect(tools.some((t) => t === "search_jobs" || t.startsWith("score_"))).toBeTruthy();
  },
);

Then(
  "I should see job cards with fit scores and gaps",
  async function (this: CustomWorld) {
    const card = this.page.getByTestId("job-card").first();
    await expect(card).toBeVisible({ timeout: 30_000 });
    await expect(card.getByTestId("job-fit-score")).toBeVisible();
    await expect(card.getByTestId("job-gaps")).toBeVisible();
  },
);

Then(
  "job cards should show Himalayas or Jobicy attribution",
  async function (this: CustomWorld) {
    const attributions = this.page.getByTestId("job-attribution");
    await expect(attributions.first()).toBeVisible();
    const texts = await attributions.allTextContents();
    expect(texts.some((t) => /Himalayas|Jobicy/i.test(t))).toBeTruthy();
    expect(texts.every((t) => /via\s+(Himalayas|Jobicy)/i.test(t))).toBeTruthy();
  },
);

Then(
  "the Apply link on a job card should open the original board URL",
  async function (this: CustomWorld) {
    const apply = this.page.getByTestId("job-apply").first();
    const href = await apply.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href!).toMatch(/^https?:\/\//);
    expect(href!).toMatch(/himalayas\.app|jobicy\.com/i);
  },
);

When(
  "I open the cover letter on the first job card",
  async function (this: CustomWorld) {
    await this.page.getByTestId("job-cover-letter").first().click();
  },
);

Then(
  "I should see the cover letter modal with a subject and body",
  async function (this: CustomWorld) {
    const modal = this.page.getByTestId("cover-letter-modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByRole("heading")).toContainText(/Application/i);
    await expect(modal.locator("pre")).toContainText(/Dear/i);
  },
);

Then("I can close the cover letter modal", async function (this: CustomWorld) {
  await this.page.getByTestId("cover-letter-modal").getByRole("button", { name: "Close" }).click();
  await expect(this.page.getByTestId("cover-letter-modal")).toHaveCount(0);
});

Then(
  "the agent message should mention max steps",
  async function (this: CustomWorld) {
    await expect(this.page.getByTestId("agent-message")).toContainText(/max steps/i, {
      timeout: 30_000,
    });
  },
);

Then(
  "the step trace should not exceed the configured max steps",
  async function (this: CustomWorld) {
    const max = Number(process.env.AGENT_MAX_STEPS || "8");
    const count = await this.page.getByTestId("step-trace-item").count();
    expect(count).toBeLessThanOrEqual(max);
    expect(count).toBeGreaterThan(0);
  },
);

Then(
  "the agent message should mention that job sources are unavailable",
  async function (this: CustomWorld) {
    await expect(this.page.getByTestId("agent-message")).toContainText(
      /unavailable|temporarily/i,
      { timeout: 30_000 },
    );
  },
);

Then("I should not see scored job cards", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("job-card")).toHaveCount(0);
});

Then("the agent message should mention timeout", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("agent-message")).toContainText(/timeout/i, {
    timeout: 30_000,
  });
});
