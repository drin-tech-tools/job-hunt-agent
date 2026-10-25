import { Then, When } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { CustomWorld } from "../support/world.ts";

When("I save the first job to the tracker", async function (this: CustomWorld) {
  const card = this.page.getByTestId("job-card").first();
  await card.getByTestId("job-save").click();
  await expect(card.getByTestId("job-save")).toContainText(/Saved/i, { timeout: 10_000 });
});

When("I open the tracker page", async function (this: CustomWorld) {
  await this.page.goto("/tracker");
  await expect(this.page.getByRole("heading", { name: "Tracker" })).toBeVisible();
  // Agent mock auto-saves top fit; plus explicit save — wait for cards.
  await expect(this.page.getByTestId("tracker-card").first()).toBeVisible({
    timeout: 15_000,
  });
});

Then(
  "I should see the job in the {string} column",
  async function (this: CustomWorld, status: string) {
    const column = this.page.getByTestId(`tracker-column-${status}`);
    await expect(column.getByTestId("tracker-card").first()).toBeVisible({
      timeout: 10_000,
    });
  },
);

When(
  "I move the tracked job status to {string}",
  async function (this: CustomWorld, status: string) {
    // Prefer a card that is not already in the target column.
    const card = this.page.getByTestId("tracker-card").first();
    await card.getByTestId("tracker-status").selectOption(status);
    await expect(
      this.page.getByTestId(`tracker-column-${status}`).getByTestId("tracker-card").first(),
    ).toBeVisible({ timeout: 10_000 });
  },
);
