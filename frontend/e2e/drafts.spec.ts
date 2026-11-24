import { expect, test } from "@playwright/test";

test("draft: download stays blocked until reviewed and ticked, and edits reset the review", async ({ page }) => {
  await page.goto("/drafts");
  await page.getByRole("button", { name: "RTI application" }).click();
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
  await page.goto("/drafts");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByText("Please fill in: Your name")).toBeVisible();
});
