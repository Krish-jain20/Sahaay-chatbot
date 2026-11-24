import { expect, test } from "@playwright/test";

test("draft: download stays blocked until reviewed and ticked, and edits reset the review", async ({ page }) => {
  await page.goto("/drafts");
  await page.getByTestId("draft-rti").click();
  await page.getByLabel("Your name").fill("Asha Verma");
  await page.getByLabel("Your address").fill("12 Example Lane, Delhi");
  await page.getByLabel(/Public authority/).fill("PIO, Revenue Department");
  await page.getByLabel("Information you want").fill("Status of my application. Aadhaar 2345 6789 0124");
  await page.getByRole("button", { name: "Review", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Review the draft" })).toBeVisible();
  // Identity numbers never appear in full.
  await expect(page.locator("#review-h").locator("..").getByText("2345 6789 0124")).toHaveCount(0);
  await expect(page.locator("#review-h").locator("..").getByText("0124")).toBeVisible();
  const download = page.getByRole("button", { name: "Download PDF" });
  await expect(download).toBeDisabled();

  await page.getByLabel("I checked every field").check();
  await expect(download).toBeEnabled();

  // Editing after review removes the review and blocks the download again.
  await page.getByLabel("Your name").fill("Asha V");
  await expect(page.getByRole("heading", { name: "Review the draft" })).toHaveCount(0);
});

test("draft: missing required fields are named", async ({ page }) => {
  await page.goto("/drafts?kind=complaint");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByText("Please fill in: Your name")).toBeVisible();
});

test("drafts: cards are grouped, searchable and filterable", async ({ page }) => {
  await page.goto("/drafts");
  await expect(page.getByTestId("draft-pension_delay")).toBeVisible();
  const all = await page.locator("[data-testid^=draft-]").count();
  expect(all).toBeGreaterThanOrEqual(15);

  await page.getByLabel("Search drafts").fill("bill");
  await expect(page.getByTestId("draft-electricity_bill")).toBeVisible();
  await expect(page.getByTestId("draft-water_bill")).toBeVisible();
  await expect(page.getByTestId("draft-rti")).toHaveCount(0);

  await page.getByLabel("Search drafts").fill("zzzz nothing");
  await expect(page.getByText("No draft matches")).toBeVisible();
  await page.getByRole("button", { name: "Clear search" }).first().click();

  await page.getByRole("button", { name: /^Police and fraud/ }).click();
  await expect(page.getByTestId("draft-police_complaint")).toBeVisible();
  await expect(page.getByTestId("draft-cyber_fraud")).toBeVisible();
  await expect(page.getByTestId("draft-rti")).toHaveCount(0);
});

test("drafts: a new type works end to end with a date and a choice, and the link survives a reload", async ({ page }) => {
  await page.goto("/drafts");
  await page.getByTestId("draft-ration_issue").click();
  await expect(page).toHaveURL(/kind=ration_issue/);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Ration card problem" })).toBeVisible();

  await page.getByLabel("Your name").fill("Asha Verma");
  await page.getByLabel("Your address").fill("12 Example Lane, Delhi");
  await page.getByLabel(/Addressed to/).fill("Food Supply Officer, Circle 12");
  await page.getByText("A family member's name is missing").click();
  await page.getByLabel(/Applied on/).fill("2025-03-14");
  await page.getByLabel("What happened").fill("Name of my daughter was left out.");
  await page.getByLabel("What you are asking for").fill("Please add her name.");
  await page.getByRole("button", { name: "Review", exact: true }).click();

  const review = page.locator("#review-h").locator("..");
  await expect(review.getByText("A family member's name is missing")).toBeVisible();
  await expect(review.getByText("14/03/2025")).toBeVisible();
  await page.getByLabel("I checked every field").check();
  const [file] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
  expect(file.suggestedFilename()).toBe("sahaay-ration_issue.pdf");

  await page.getByRole("button", { name: "All drafts" }).click();
  await expect(page.getByTestId("draft-rti")).toBeVisible();
});

test("drafts: a missing choice is named", async ({ page }) => {
  await page.goto("/drafts?kind=police_complaint");
  await page.getByLabel("Your name").fill("A");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByText(/Please fill in:.*What do you need/)).toBeVisible();
});
