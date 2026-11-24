import { expect, test } from "@playwright/test";

// The e2e backend has no model key, so the web answer is served by a mocked /chat stream. The real
// server-side behaviour (labelling, official flags, guard, masking) is covered in backend/tests/test_web_search.py.
function sse(events: [string, unknown][]): string {
  return events.map(([e, d]) => `event: ${e}\r\ndata: ${JSON.stringify(d)}\r\n\r\n`).join("");
}

test("chat: a web answer is labelled unverified and every source says whether it is official", async ({ page }) => {
  await page.route("**/chat", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sse([
        ["status", { id: "stream", stream_id: "s1", state: "open" }],
        [
          "card",
          {
            type: "web",
            label: "From the web, not a verified Sahaay record. Verify locally.",
            retrieved_on: "2026-11-24",
            sources: [
              { n: 1, title: "revenue.delhi.gov.in", url: "https://example.test/r1", official: true },
              { n: 2, title: "someblog.example", url: "https://example.test/r2", official: false },
            ],
          },
        ],
        ["token", { text: "The page lists proof of stay. " }],
        ["token", { text: "Verify locally." }],
        ["done", { refused: false }],
      ]),
    });
  });
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("domicile certificate documents");
  await page.keyboard.press("Enter");
  const card = page.getByTestId("web-card");
  await expect(card).toBeVisible();
  await expect(card).toContainText("not a verified Sahaay record");
  await expect(card.getByRole("listitem").nth(0)).toContainText("on Sahaay's checked official list");
  await expect(card.getByRole("listitem").nth(1)).toContainText("not on Sahaay's official list");
  await expect(card).toContainText("Searched on 2026-11-24");
  await expect(page.getByText("The page lists proof of stay.")).toBeVisible();
});
