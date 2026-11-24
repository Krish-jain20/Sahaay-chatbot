import { expect, test } from "@playwright/test";

test("help: complaint vs RTI vs appeal is shown with sources and the Delhi warning", async ({ page }) => {
  await page.goto("/help/complaints");
  await page.waitForLoadState("networkidle");
  await expect(page.getByTestId("guide-card")).toBeVisible();
  for (const id of ["grievance", "appeal", "rti"]) await expect(page.getByTestId(`guide-${id}`)).toBeVisible();
  await expect(page.getByTestId("guide-rti")).toContainText("Delhi");
  await expect(page.getByRole("link", { name: "https://pgportal.gov.in/" })).toBeVisible();
});

test("chat: a complaint question answers with the guide, not a refusal", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("how is an RTI different from a complaint?");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("guide-card")).toBeVisible();
});
