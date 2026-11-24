import { expect, test } from "@playwright/test";

test("result card lists other services that may fit, never as an approval", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("old age pension in Delhi");
  await page.keyboard.press("Enter");
  const alts = page.getByTestId("alternatives");
  await expect(alts).toBeVisible();
  await expect(alts.locator("li").first()).toBeVisible();
  await expect(page.getByText("Needs more details").first()).toBeVisible();
  await expect(alts).not.toContainText(/approved|guaranteed/i);
});

test("scholarship card shows where to complain, each channel with a source chip", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("SC ST OBC merit scholarship in Delhi");
  await page.keyboard.press("Enter");
  const list = page.getByTestId("grievance-channels");
  await expect(list).toBeVisible();
  await expect(list).toContainText("011-23379512");
  await expect(list.getByRole("link", { name: /Public Grievances Commission/ })).toBeVisible();
});
