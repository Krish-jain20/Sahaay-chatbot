import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

// A fillable PDF is read by the real backend (no model needed). A flat form or photo needs the vision
// model, which the e2e backend does not have, so those responses are mocked here. The server-side
// behaviour is covered in backend/tests/test_dynamic_forms.py.
const FIXTURE = path.join(__dirname, "fixtures", "fillable-form.pdf");
const AADHAAR = "2345 6789 0124";

async function upload(page: Page, file = FIXTURE) {
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/Form file/).setInputFiles(file);
  await page.getByRole("button", { name: "Find the fields" }).click();
  await expect(page.getByTestId("any-form-fill")).toBeVisible();
}

test("any form: a fillable PDF is read, only missing fields are asked, and download needs the tick", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("sahaay.formProfile", JSON.stringify({ name: "Asha Verma", aadhaar: "999" })));
  await upload(page);
  await expect(page.getByTestId("any-form-summary")).toContainText("Found 6 fields. 1 filled from your details, 5 left for you.");
  // The known name is not asked again; an identity number from storage is never used.
  await expect(page.getByLabel("Full name", { exact: false }).first()).not.toBeVisible();
  await expect(page.getByLabel("Aadhaar number")).toHaveValue("");
  await page.getByLabel("Date of birth").fill("01/02/2000");
  await page.getByLabel("Aadhaar number").fill(AADHAAR);
  await page.getByLabel("Mobile number").fill("9876543210");
  await page.getByLabel("I agree").check();
  await page.getByRole("button", { name: "Review", exact: true }).click();

  const review = page.getByTestId("any-form-review");
  await expect(review).toContainText("Asha Verma");
  await expect(review).toContainText("XXXX 0124");
  await expect(review).toContainText("XXXX 3210");
  await expect(review).not.toContainText("6789");
  await expect(review).not.toContainText("9876");
  await expect(page.getByText("Sahaay is an AI assistant, not an official government channel")).toBeVisible();
  const download = page.getByRole("button", { name: "Download filled form" });
  await expect(download).toBeDisabled();
  await page.getByLabel("I checked every field").check();
  await expect(download).toBeEnabled();
  const [file] = await Promise.all([page.waitForEvent("download"), download.click()]);
  expect(file.suggestedFilename()).toBe("filled-form.pdf");

  // The name typed is remembered for the next form in this tab; the Aadhaar number is not.
  const kept = await page.evaluate(() => JSON.parse(sessionStorage.getItem("sahaay.formProfile") ?? "{}"));
  expect(kept.dob).toBe("01/02/2000");
  expect(JSON.stringify(kept)).not.toContain("6789");
  expect(kept.aadhaar).toBeUndefined();

  // Editing after review removes the review and the tick.
  await page.getByLabel("Date of birth").fill("02/02/2000");
  await expect(page.locator("#any-review-h")).toHaveCount(0);
});

test("any form: a bad Aadhaar number is explained when the PDF is prepared", async ({ page }) => {
  await upload(page);
  await page.getByLabel("Aadhaar number").fill("2345 6789 0125");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await page.getByLabel("I checked every field").check();
  await page.getByRole("button", { name: "Download filled form" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("does not look valid");
});

test("any form: shows a loading status while fields are detected, then the questions", async ({ page }) => {
  await page.route("**/forms/analyze", async (route) => {
    await new Promise((r) => setTimeout(r, 700));
    await route.fulfill({
      json: {
        kind: "flat",
        pages: 1,
        fields: [{ id: "p0f0", label: "नाम", page: 0, x_norm: 0.3, y_norm: 0.2 }],
        prefilled_fields: [],
        missing_fields: [
          { id: "p0f0", label: "नाम", mapped_profile_key: "name", page: 0, required: true, kind: "text", sensitive: false, label_i18n: { en: "Full name", hi: "पूरा नाम", hn: "Poora naam" } },
        ],
        questions: [{ id: "p0f0", en: "Please enter: Full name", hi: "कृपया दर्ज करें: पूरा नाम", hn: "Please darj karein: Poora naam" }],
        sensitive_keys: ["aadhaar", "pan", "mobile", "bank_account"],
      },
    });
  });
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/Form file/).setInputFiles(path.join(__dirname, "fixtures", "aadhaar.png"));
  await page.getByRole("button", { name: "Find the fields" }).click();
  await expect(page.getByTestId("any-form-loading")).toContainText("Reading your form");
  await expect(page.getByTestId("any-form-summary")).toContainText("Found 1 fields. 0 filled from your details, 1 left for you.");
  await expect(page.getByLabel(/Full name/)).toBeVisible();
  await page.getByRole("button", { name: "Use another form" }).click();
  await expect(page.getByTestId("any-form-upload")).toBeVisible();
});

test("any form: model busy, unsupported file and no file are explained", async ({ page }) => {
  await page.route("**/forms/analyze", (route) => route.fulfill({ status: 503, json: { detail: "vision_unavailable" } }));
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find the fields" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("Choose a form file first");
  await page.getByLabel(/Form file/).setInputFiles(FIXTURE);
  await page.getByRole("button", { name: "Find the fields" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("busy right now");
  await page.unroute("**/forms/analyze");
  await page.getByLabel(/Form file/).setInputFiles({ name: "x.txt", mimeType: "text/plain", buffer: Buffer.from("not a form") });
  await page.getByRole("button", { name: "Find the fields" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("not supported");
});

test("any form: Hindi labels are shown to a Hindi user", async ({ page, context }) => {
  await context.addCookies([{ name: "sahaay_locale", value: "hi", url: "http://localhost:3100" }]);
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/फ़ॉर्म फ़ाइल/).setInputFiles(FIXTURE);
  await page.getByRole("button", { name: "फ़ील्ड ढूँढें" }).click();
  await expect(page.getByTestId("any-form-fill")).toBeVisible();
  await expect(page.getByLabel("जन्म तिथि")).toBeVisible();
  await expect(page.getByLabel("आधार नंबर")).toBeVisible();
});

test("any form: the Delhi income certificate preset is one click away", async ({ page }) => {
  await page.goto("/forms");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Delhi income certificate form" }).click();
  await expect(page.getByLabel("Name of beneficiary")).toBeVisible();
  await page.getByRole("button", { name: "Upload any form" }).click();
  await expect(page.getByTestId("any-form-upload")).toBeVisible();
});
