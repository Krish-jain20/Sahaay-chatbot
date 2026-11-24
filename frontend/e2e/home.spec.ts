import { expect, test } from "@playwright/test";

test("home: hero, how it works, tools, services, trust and footer are all there", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("From confusion to action");
  await expect(page.getByRole("link", { name: "Start a chat" })).toHaveAttribute("href", "/chat");
  await expect(page.getByRole("heading", { name: "Three steps from question to submitted form" })).toBeVisible();
  for (const id of ["chat", "compare", "documents", "drafts", "forms", "help", "case"]) {
    await expect(page.getByTestId(`tool-${id}`)).toBeVisible();
  }
  await expect(page.getByTestId("tool-help")).toHaveAttribute("href", "/help");
  await expect(page.getByRole("heading", { name: "Careful with facts, careful with your data" })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("not an official government channel");
});

test("home: the sample chat is decorative and hidden from assistive tech", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("figure > [aria-hidden='true']").getByText("Old-age pension, Delhi")).toBeAttached();
});

test("home: a popular service opens its Compare card", async ({ page }) => {
  await page.goto("/");
  const first = page.getByTestId("popular-services").getByRole("link").first();
  await expect(first).toBeVisible();
  const href = await first.getAttribute("href");
  await first.click();
  await expect(page).toHaveURL(new RegExp(`${href!.replace("/", "\\/")}$`));
  await expect(page.getByRole("region").first()).toBeVisible();
  await expect(page.locator("[data-testid=service-card] [role=region]:not([hidden])")).toHaveCount(1);
});

test("home: tool card opens its page", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("tool-documents").click();
  await expect(page).toHaveURL(/\/documents$/);
});

test("home: Hindi copy and no horizontal scroll on a phone", async ({ page, context }) => {
  await context.addCookies([{ name: "sahaay_locale", value: "hi", url: "http://localhost:3100" }]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByTestId("tool-chat")).toContainText("सरल शब्दों में पूछिए");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("home: screenshots", async ({ page }) => {
  test.skip(!process.env.SHOTS, "only when SHOTS is set");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `${process.env.SHOTS}/home-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `${process.env.SHOTS}/home-phone.png`, fullPage: true });
});
