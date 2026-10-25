import { Given } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { CustomWorld } from "../support/world.ts";
import { SAMPLE_RESUME } from "../support/sample_resume.ts";

Given("I open the resume page", async function (this: CustomWorld) {
  await this.page.goto("/resume");
  await expect(this.page.getByRole("heading", { name: "Resume" })).toBeVisible();
});

Given("I open the agent page", async function (this: CustomWorld) {
  await this.page.goto("/agent");
  await expect(this.page.getByTestId("agent-form")).toBeVisible();
});

Given(
  "I have a saved sample resume in the session",
  async function (this: CustomWorld) {
    await this.page.goto("/resume");
    await this.page.getByTestId("resume-title").fill("BDD sample resume");
    await this.page.getByTestId("resume-content").fill(SAMPLE_RESUME);
    await this.page.getByTestId("resume-save").click();
    await expect(this.page.getByTestId("resume-status")).toContainText(/Saved/i, {
      timeout: 15_000,
    });
  },
);
