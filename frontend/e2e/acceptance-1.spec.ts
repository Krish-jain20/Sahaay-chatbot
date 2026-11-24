import { expect, test } from "@playwright/test";

// Acceptance flow 1 (docs/PRD.md §5): find and qualify, then compare.
test("student finds the scholarship, confirms facts, sees the chain, then compares", async ({ page }) => {
  await page.goto("/chat");
  await page.getByRole("button", { name: /student in Delhi, family income about 3 lakh/ }).click();

  // Facts said in chat are unconfirmed: nothing is "met" yet.
  const card = page.locator("article").first();
  await expect(card.getByRole("heading", { name: /Merit Scholarship/ })).toBeVisible();
  await expect(card.getByText("Unknown").first()).toBeVisible();
  await expect(card.getByText("Not an approval", { exact: false })).toBeVisible();

  // Prerequisite chain puts the income certificate first.
  await expect(card.getByRole("list").filter({ hasText: "Income Certificate" })).toContainText("Merit Scholarship");

  // Fee strip never invents values.
  await expect(card.getByText("Verify locally").first()).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain("₹[");

  // Confirm the stated fact, then answer the follow-up questions with chips.
  await page.getByRole("button", { name: /Yes, that's right/ }).click();
  await page.getByRole("button", { name: "OBC" }).click();
  // The income she mentioned (about 3 lakh) is offered back for confirmation, never assumed.
  await page.getByRole("button", { name: /Yes, that's right: ₹300,000/ }).click();
  await page.getByRole("button", { name: /60% or more last year/ }).click();

  const last = page.locator("article").last();
  await expect(last.getByText("Met")).toHaveCount(4);
  await expect(page.getByText("you meet the listed conditions", { exact: false }).last()).toBeVisible();

  // Citation chip opens a source with a link and a checked date.
  await last.locator("summary").first().click();
  await expect(last.getByRole("link", { name: /scstwelfare\.delhi\.gov\.in/ }).first()).toBeVisible();

  // Compare with another service.
  await page.goto("/compare");
  await page.getByRole("button", { name: /Old Age Assistance/ }).click();
  await page.getByLabel(/Compare: Old Age Assistance/).check();
  await page.getByRole("button", { name: /Merit Scholarship/ }).click();
  await page.getByLabel(/Compare: Merit Scholarship/).check();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("columnheader")).toHaveCount(3);
  await expect(page.getByRole("link", { name: /Financial Assistance Schemes/ }).first()).toBeVisible();
});

test("language switch changes the interface and keeps working", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "हिंदी" }).click();
  await expect(page.getByRole("link", { name: "बातचीत शुरू करें" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await page.getByRole("button", { name: "Hinglish" }).click();
  await expect(page.getByRole("link", { name: "Chat shuru karein" })).toBeVisible();
});

test("an out-of-scope question is refused, not answered from memory", async ({ page }) => {
  await page.goto("/chat");
  await page.getByLabel("Type your question…").fill("how do I renew my passport?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("www.india.gov.in/services", { exact: false })).toBeVisible();
  await expect(page.locator("article")).toHaveCount(0);
});

test("Stop cancels a running answer", async ({ page }) => {
  await page.goto("/chat");
  await page.getByLabel("Type your question…").fill("income certificate");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible();
});

test("desktop shows the nav and the details panel; confirmed facts appear in it", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/chat");
  await expect(page.getByRole("navigation", { name: "Main menu" })).toBeVisible();
  const panel = page.getByRole("complementary", { name: "Your details" });
  await expect(panel).toContainText("Details you confirm in the chat appear here");
  await page.getByRole("button", { name: /student in Delhi, family income about 3 lakh/ }).click();
  await page.getByRole("button", { name: /Yes, that's right/ }).click();
  await expect(panel).toContainText("Occupation");
  await expect(panel).toContainText("student");
  await expect(panel).toContainText("Not saved");
});

test("phone has no side nav or panel and no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/chat");
  await expect(page.getByRole("navigation", { name: "Main menu" })).toBeHidden();
  await expect(page.getByRole("complementary", { name: "Your details" })).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
});
