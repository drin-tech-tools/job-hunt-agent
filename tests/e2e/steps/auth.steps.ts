import { Given, Then, When } from "@cucumber/cucumber";
import { expect } from "@playwright/test";

import { CustomWorld, apiUrl, baseUrl } from "../support/world.ts";

async function setMockAuthViaApi(
  world: CustomWorld,
  as: "anonymous" | "admin" | "client",
): Promise<void> {
  // Hit the same-origin helper so Set-Cookie lands on the browsing host
  // (avoids Playwright 127.0.0.1 vs localhost cookie mismatches).
  const res = await world.page.request.get(`${baseUrl()}/api/e2e/session?as=${as}`);
  if (!res.ok()) {
    throw new Error(`Failed to set e2e session (${as}): ${res.status()} ${await res.text()}`);
  }
}

Given("I am logged out", async function (this: CustomWorld) {
  await setMockAuthViaApi(this, "anonymous");
});

Given("I am authenticated as an admin", async function (this: CustomWorld) {
  await setMockAuthViaApi(this, "admin");
});

Given("I am authenticated as a client", async function (this: CustomWorld) {
  await setMockAuthViaApi(this, "client");
});

Given(
  "an admin has a tracker item titled {string}",
  async function (this: CustomWorld, title: string) {
    const res = await fetch(`${apiUrl()}/tracker`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer mock.mock-admin.admin.aal2",
      },
      body: JSON.stringify({
        job_id: `other-${Date.now()}`,
        title,
        company: "OtherCo",
        apply_url: "https://himalayas.app/jobs/other-secret",
        source: "Himalayas",
        status: "saved",
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to seed tracker: ${res.status} ${await res.text()}`);
    }
  },
);

When("I open the home page", async function (this: CustomWorld) {
  await this.page.goto("/");
});

When("I open the admin users page", async function (this: CustomWorld) {
  await this.page.goto("/admin/users");
});

When("I visit the tracker as the current user", async function (this: CustomWorld) {
  await this.page.goto("/tracker");
  await expect(this.page.getByRole("heading", { name: "Tracker" })).toBeVisible({
    timeout: 15_000,
  });
});

Then("I should be on the login page", async function (this: CustomWorld) {
  await expect(this.page).toHaveURL(/\/login/);
  await expect(this.page.getByTestId("login-heading")).toBeVisible();
});

Then("I should see an admin forbidden message", async function (this: CustomWorld) {
  await expect(this.page.getByTestId("admin-forbidden")).toBeVisible({
    timeout: 15_000,
  });
});

Then(
  "I should not see tracker text {string}",
  async function (this: CustomWorld, text: string) {
    await expect(this.page.getByText(text)).toHaveCount(0);
  },
);
