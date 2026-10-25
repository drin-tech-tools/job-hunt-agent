import { Then, When } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { CustomWorld } from "../support/world.ts";
import { SAMPLE_RESUME } from "../support/sample_resume.ts";

When(
  "I paste a sample resume titled {string}",
  async function (this: CustomWorld, title: string) {
    await this.page.getByTestId("resume-title").fill(title);
    await this.page.getByTestId("resume-content").fill(SAMPLE_RESUME);
  },
);

When("I paste resume text {string}", async function (this: CustomWorld, text: string) {
  await this.page.getByTestId("resume-content").fill(text);
});

When("I save the resume", async function (this: CustomWorld) {
  await this.page.getByTestId("resume-save").click();
});

Then("I should see a resume saved confirmation", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("resume-status")).toContainText(/Saved/i, {
    timeout: 15_000,
  });
});

Then(
  "the resume content should persist in the session",
  async function (this: CustomWorld) {
    await this.page.goto("/agent");
    const resume = this.page.getByTestId("agent-resume");
    await expect(resume).toContainText("Jane Doe", { timeout: 10_000 });
  },
);

Then("I should see resume validation feedback", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("resume-status")).toContainText(/20\+|short/i);
});
