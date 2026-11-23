import { execSync } from "node:child_process";
import { expect, test } from "@playwright/test";

const hasTesseract = (() => {
  try {
    execSync("tesseract --version", { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
})();

test("document check: declare a document, readiness moves, nothing claims approval", async ({ page }) => {
  await page.goto("/documents");
  const options = await page.locator("#service option").allTextContents();
  await page.getByLabel("Service").selectOption({ label: options.find((o) => /pension/i.test(o))! });
  const progress = page.getByTestId("progress-text");
  await expect(progress).toContainText("0 of");
  await page.getByRole("button", { name: "I have this" }).first().click();
  await expect(progress).toContainText("1 of");
  await expect(page.getByText("Not checked", { exact: false })).toBeVisible();
  await expect(page.getByText("Not a prediction of approval")).toBeVisible();
});

test("document check: scan, review, edit, confirm (needs Tesseract)", async ({ page }) => {
  test.skip(!hasTesseract, "Tesseract not installed");
  await page.goto("/documents");
  const options = await page.locator("#service option").allTextContents();
  const pension = options.find((o) => /pension/i.test(o));
  await page.getByLabel("Service").selectOption({ label: pension! });
  await page.getByLabel(/Choose a photo or PDF: Aadhaar card/).setInputFiles("e2e/fixtures/aadhaar.png");
  await expect(page.getByRole("heading", { name: "Check what we read" })).toBeVisible();
  // The full number is never shown, only the last 4 digits.
  const val = await page.getByLabel(/Aadhaar \(last 4/).inputValue();
  expect(val).toMatch(/0124$/);
  expect(val).not.toContain("2345");
  await page.getByRole("button", { name: "Confirm and save" }).click();
  await expect(page.getByTestId("progress-text")).toContainText("1 of");
  await expect(page.getByText("Read from your upload and confirmed by you")).toBeVisible();
});
