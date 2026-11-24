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

test("documents: empty page offers to track a service, which adds its documents here", async ({ page }) => {
  await page.goto("/documents");
  await page.waitForLoadState("networkidle");
  // Whatever service is not tracked yet (tests share one user, so which one depends on earlier tests).
  const options = await page.locator("#service option").allTextContents();
  const name = options[1];
  await page.locator("#service").selectOption({ label: name });
  await expect(page.getByTestId("service-preview")).toBeVisible();
  await page.getByRole("button", { name: "Track in My cases" }).click();
  await expect(page.getByTestId("docs-cases")).toContainText(name);
  await expect(page.getByTestId("doc-list").locator("li").first()).toBeVisible();
});

test("documents: add once, it counts for every case that needs it, then remove", async ({ page, request }) => {
  const API = "http://localhost:8100";
  await request.post(`${API}/cases`, { data: { service_id: "delhi-income-certificate" } });
  await page.goto("/documents");
  await page.waitForLoadState("networkidle");
  const row = page.getByTestId("doc-aadhaar");
  // Aadhaar is needed by both the pension and the income certificate cases.
  await expect(row.getByRole("link")).toHaveCount(2);
  const summary = page.getByTestId("progress-text");
  await expect(summary).toContainText("still needed");
  await row.getByRole("button", { name: "I have this" }).click();
  await expect(row.getByText("You said you have it. Not checked")).toBeVisible();
  await expect(page.getByText("Not a prediction of approval")).toBeVisible();

  // The same document is ticked in My cases, with no second upload.
  await page.goto("/case");
  await page.waitForLoadState("networkidle");
  await page.getByTestId("case-delhi-income-certificate").click();
  await expect(page.getByTestId("case-checklist").getByText("Aadhaar card").locator("..").locator("..")).toContainText("You said you have it");

  await page.goto("/documents");
  await page.getByRole("button", { name: /Remove: Aadhaar card/ }).click();
  await page.getByRole("button", { name: "Yes, remove" }).click();
  await expect(page.getByTestId("doc-aadhaar").getByRole("button", { name: "I have this" })).toBeVisible();
});

test("documents: services you added show their own tick list", async ({ page }) => {
  await page.goto("/documents");
  await page.waitForLoadState("networkidle");
  const mine = page.getByTestId("custom-docs").filter({ hasText: "Ration card" });
  await expect(mine.getByRole("link", { name: "Manage in My cases" })).toBeVisible();
  await mine.getByLabel("Family photo").click();
  await expect(mine.getByLabel("Family photo")).toBeChecked();
});

test("document check: scan, review, edit, confirm (needs Tesseract)", async ({ page, request }) => {
  test.skip(!hasTesseract, "Tesseract not installed");
  await request.post("http://localhost:8100/cases", { data: { service_id: "delhi-old-age-pension" } });
  await page.goto("/documents");
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/Choose a photo or PDF: Aadhaar card/).setInputFiles("e2e/fixtures/aadhaar.png");
  await expect(page.getByRole("heading", { name: "Check what we read" })).toBeVisible();
  // The full number is never shown, only the last 4 digits.
  const val = await page.getByLabel(/Aadhaar \(last 4/).inputValue();
  expect(val).toMatch(/0124$/);
  expect(val).not.toContain("2345");
  await page.getByRole("button", { name: "Confirm and save" }).click();
  await expect(page.getByText("Read from your upload and confirmed by you").first()).toBeVisible();
});
