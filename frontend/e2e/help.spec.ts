import { expect, test } from "@playwright/test";

async function openCard(page: import("@playwright/test").Page, id: string) {
  const card = page.getByTestId(`help-card-${id}`);
  await card.getByRole("button", { expanded: false }).first().click();
  return card;
}

test("help: one page with three sourced sections of expandable cards", async ({ page }) => {
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  for (const s of ["complaints", "scams", "terms"]) await expect(page.getByTestId(`help-section-${s}`)).toBeVisible();
  const rti = await openCard(page, "complaints.rti");
  await expect(rti).toContainText("Delhi");
  await expect(page.getByRole("link", { name: "https://pgportal.gov.in/" }).first()).toBeVisible();
  // Opening it did not open the others, and it closes again.
  await expect(page.getByTestId("help-card-complaints.appeal").getByRole("region")).toBeHidden();
  await rti.getByRole("button", { expanded: true }).first().click();
  await expect(rti.getByRole("region")).toBeHidden();
});

test("help: fraud, Delhi routes and terms keep their sourced wording", async ({ page }) => {
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  await expect(await openCard(page, "scams.income_fee")).toContainText("NO FEE Required");
  await expect(await openCard(page, "scams.sahaay_never")).toContainText("never");
  const helpline = await openCard(page, "scams.cyber_helpline");
  await expect(helpline).toContainText("1930");
  await expect(helpline).toContainText("did not open");
  await expect(await openCard(page, "complaints.delhi_rti")).toContainText("rtionline.delhi.gov.in");
  await expect(await openCard(page, "terms.appeal")).toContainText("Poor");
});

test("help: the filter narrows cards and sections", async ({ page }) => {
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Filter the cards").fill("sub judice");
  await expect(page.getByTestId("help-card-terms.sub_judice")).toBeVisible();
  await expect(page.getByTestId("help-section-scams")).toHaveCount(0);
});

test("help: old pages redirect to the right section", async ({ page }) => {
  for (const [old, hash] of [["complaints", "complaints"], ["scams", "scams"], ["terms", "terms"]]) {
    await page.goto(`/help/${old}`);
    await expect(page).toHaveURL(new RegExp(`/help#${hash}$`));
    await expect(page.getByTestId(`help-section-${hash}`)).toBeVisible();
  }
  await page.goto("/help/unknown");
  await expect(page).toHaveURL(/\/help$/);
});

test("help: the menu has one entry for help and rights", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Main menu" });
  await expect(nav.getByRole("link", { name: "Help and rights" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Avoid fraud" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Terms explained" })).toHaveCount(0);
});

// The e2e backend has no model key, so the AI endpoints are mocked here. The real server-side
// behaviour (masking, forbidden claims, card-only grounding) is covered in backend/tests/test_help.py.
test("help: asking shows a sourced AI answer, and opens and highlights the matching card", async ({ page }) => {
  await page.route("**/help/ask", async (route) => {
    await route.fulfill({
      json: {
        answer: "File it on the RTI portal. Verify locally.",
        web: { type: "web", retrieved_on: "2026-11-24", sources: [{ n: 1, title: "rtionline.gov.in", url: "https://example.test/r", official: true, kind: "official" }] },
        matches: ["complaints.rti"],
        state: "ok",
      },
    });
  });
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Ask a question").fill("how do I file an RTI?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  const answer = page.getByTestId("help-answer");
  await expect(answer.getByTestId("help-answer-text")).toContainText("RTI portal");
  await expect(answer).toContainText("Searched on 2026-11-24");
  await expect(answer).toContainText("on Sahaay's checked official list");
  const card = page.getByTestId("help-card-complaints.rti");
  await expect(card.getByRole("region")).toBeVisible();
  await expect(card).toContainText("Matches your question");
});

test("help: with AI off, asking still points to matching cards and says so", async ({ page }) => {
  await page.route("**/help/ask", (route) => route.fulfill({ json: { answer: null, web: null, matches: ["scams.income_fee"], state: "unavailable" } }));
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Ask a question").fill("agent wants a fee");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByTestId("help-answer-none")).toContainText("not available");
  await expect(page.getByTestId("help-card-scams.income_fee").getByRole("region")).toBeVisible();
});

test("help: 'Explain in plain words' shows an AI explanation labelled as based on the card", async ({ page }) => {
  let sent: { card_id: string; situation: string } | null = null;
  await page.route("**/help/explain", async (route) => {
    sent = route.request().postDataJSON();
    await route.fulfill({ json: { text: "An RTI asks a department for records." } });
  });
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  const card = await openCard(page, "complaints.rti");
  await card.getByLabel(/Want this explained/).fill("my file is stuck");
  await card.getByRole("button", { name: "Explain in plain words" }).click();
  await expect(card.getByTestId("help-explanation")).toContainText("asks a department for records");
  await expect(card.getByTestId("help-explanation")).toContainText("based only on this card");
  expect(sent).toEqual(expect.objectContaining({ card_id: "complaints.rti", situation: "my file is stuck" }));
});

test("help: Hindi page shows Hindi cards and the new menu name", async ({ page, context }) => {
  await context.addCookies([{ name: "sahaay_locale", value: "hi", url: "http://localhost:3100" }]);
  await page.goto("/help");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("मदद और अधिकार");
  await expect(page.getByTestId("help-section-complaints")).toContainText("शिकायत");
});

test("chat: a complaint question answers with the guide, not a refusal", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("how is an RTI different from a complaint?");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("guide-card")).toBeVisible();
});

test("chat: a fraud question answers with the fraud guide", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("an agent wants money for my certificate, is this a scam?");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("guide-income_fee")).toBeVisible();
});
