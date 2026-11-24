import { expect, test } from "@playwright/test";

test("privacy: shows what is saved and deletes it only after the tick", async ({ page, request }) => {
  const api = "http://localhost:8100";
  const c = await (await request.post(`${api}/cases`, { data: { service_id: "delhi-old-age-pension" } })).json();
  await request.post(`${api}/cases/${c.id}/steps`, { data: { step: 4, submitted_on: "2026-11-20" } });

  await page.goto("/privacy");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "What we never keep" })).toBeVisible();
  await expect(page.getByText("Submission: 2026-11-20")).toBeVisible();

  const del = page.getByRole("button", { name: "Delete my data" });
  await expect(del).toBeDisabled();
  await page.getByLabel("I understand this cannot be undone").check();
  await del.click();
  await expect(page.getByText("All your saved data was deleted.")).toBeVisible();
  await expect(page.getByTestId("no-data")).toBeVisible();
});
