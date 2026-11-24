import { expect, test } from "@playwright/test";

test("case folder: the user records steps, reference is masked, undo works, labelled as own progress", async ({ page }) => {
  await page.goto("/case");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "Your own progress, not government status" })).toBeVisible();
  const options = await page.locator("#case-service option").allTextContents();
  await page.getByLabel("Service").selectOption({ label: options.find((o) => /pension/i.test(o))! });

  await page.getByRole("button", { name: "Mark as done: Eligibility checked" }).click();
  await expect(page.getByText(/Done · \d{4}-\d{2}-\d{2}/)).toBeVisible();
  await page.getByRole("button", { name: "Mark as done: Documents verified" }).click();
  await page.getByRole("button", { name: "Mark as done: Form filled" }).click();

  await page.getByLabel("Date you submitted").fill("2026-11-20");
  await page.getByRole("button", { name: "Mark as done: Submitted on official portal" }).click();
  await expect(page.getByText("Submitted on 2026-11-20")).toBeVisible();

  await page.getByLabel("Reference number").fill("12");
  await page.getByRole("button", { name: "Mark as done: Reference saved" }).click();
  await expect(page.getByText("at least 4 letters or digits")).toBeVisible();
  await page.getByLabel("Reference number").fill("DL/IC/998877");
  await page.getByRole("button", { name: "Mark as done: Reference saved" }).click();
  await expect(page.getByText("Saved as XXXX8877")).toBeVisible();
  await expect(page.getByText("998877", { exact: false })).toHaveCount(0);

  await page.getByRole("button", { name: "Undo: Reference saved" }).click();
  await expect(page.getByLabel("Reference number")).toBeVisible();
});
