import { expect, test, type Page } from "@playwright/test";

async function openPreset(page: Page) {
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Delhi income certificate form" }).click();
}

test("official form: review shows only the last 4 Aadhaar digits and download needs the tick", async ({ page }) => {
  await openPreset(page);
  await expect(page.getByText("revenue.delhi.gov.in")).toBeVisible();
  await page.getByLabel("Aadhaar number (12 digits)").fill("2345 6789 0124");
  await page.getByLabel("Name of beneficiary").fill("ASHA VERMA");
  await page.getByLabel("Mobile number").fill("9876543210");
  await page.getByRole("button", { name: "Review", exact: true }).click();

  const review = page.locator("#form-review-h").locator("..");
  await expect(review.getByText("XXXX XXXX 0124")).toBeVisible();
  await expect(review.getByText("6789")).toHaveCount(0);
  const download = page.getByRole("button", { name: "Download filled form" });
  await expect(download).toBeDisabled();
  await page.getByLabel("I checked every field").check();
  await expect(download).toBeEnabled();

  const [file] = await Promise.all([page.waitForEvent("download"), download.click()]);
  expect(file.suggestedFilename()).toBe("delhi-income-certificate-application.pdf");

  // Editing after review removes the review again.
  await page.getByLabel("Name of beneficiary").fill("ASHA V");
  await expect(page.locator("#form-review-h")).toHaveCount(0);
});

test("official form: a bad Aadhaar number and non-English letters are explained", async ({ page }) => {
  await openPreset(page);
  await page.getByLabel("Name of beneficiary").fill("ASHA");
  await page.getByLabel("Aadhaar number (12 digits)").fill("2345 6789 0125");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByText("does not look valid")).toBeVisible();
  await page.getByLabel("Aadhaar number (12 digits)").fill("");
  await page.getByLabel("Name of beneficiary").fill("आशा");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByText("English letters and digits only: Name of beneficiary")).toBeVisible();
});
