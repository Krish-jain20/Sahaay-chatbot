import { expect, test } from "@playwright/test";

test("compare: services are cards that open one at a time and close again", async ({ page }) => {
  await page.goto("/compare");
  const cards = page.getByTestId("service-card");
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThanOrEqual(15);

  const income = page.getByRole("button", { name: /^Income Certificate/ });
  const ration = page.getByRole("button", { name: /^Ration card/ });
  await expect(income).toHaveAttribute("aria-expanded", "false");

  await income.click();
  await expect(income).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("region", { name: "Income Certificate" })).toBeVisible();

  await ration.click(); // opening another closes the first
  await expect(ration).toHaveAttribute("aria-expanded", "true");
  await expect(income).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("region", { name: "Income Certificate" })).toBeHidden();

  const panel = page.getByRole("region", { name: /^Ration card/ });
  await expect(panel).toContainText("Aadhaar of all family members");
  await expect(panel.getByRole("link", { name: /Ration Card FAQ/ })).toBeVisible();
  await expect(panel).toContainText("Checked 2026-11-24");

  await ration.click(); // and it closes again
  await expect(ration).toHaveAttribute("aria-expanded", "false");
});

test("compare: a card opens from the keyboard", async ({ page }) => {
  await page.goto("/compare");
  const btn = page.getByRole("button", { name: /^Domicile certificate/ });
  await btn.focus();
  await page.keyboard.press("Enter");
  await expect(btn).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("region", { name: "Domicile certificate" })).toContainText("No fee.");
  await page.keyboard.press("Space");
  await expect(btn).toHaveAttribute("aria-expanded", "false");
});

test("compare: filter narrows the list and up to three cards go side by side", async ({ page }) => {
  await page.goto("/compare");
  await page.getByLabel("Find a service").fill("licence");
  await expect(page.getByTestId("service-card")).toHaveCount(3);
  for (const name of ["Learner's driving licence", "Permanent driving licence"]) {
    await page.getByRole("button", { name: new RegExp(`^${name}`) }).click();
    await page.getByLabel(`Compare: ${name}`).check();
  }
  await expect(page.getByTestId("side-by-side")).toContainText("₹500 for one category");
  await expect(page.getByTestId("side-by-side")).toContainText("₹400");
  await page.getByRole("button", { name: "Driving licence renewal" }).click();
  await page.getByLabel("Compare: Driving licence renewal").check();
  await page.getByLabel("Find a service").fill("");
  await page.getByRole("button", { name: /^Ration card/ }).click();
  await expect(page.getByLabel(/Compare: Ration card/)).toBeDisabled(); // the fourth is not allowed
});

test("compare: card headings are translated and the English-only details say so", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "हिंदी" }).click();
  await page.goto("/compare");
  await expect(page.getByText("सेवा खोजें")).toBeVisible();
  await page.getByRole("button", { name: /^राशन कार्ड/ }).click();
  await expect(page.getByRole("region", { name: /^राशन कार्ड/ })).toContainText("केवल अंग्रेज़ी में");
});
