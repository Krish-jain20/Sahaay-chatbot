import { expect, test } from "@playwright/test";

test("my cases: start from a service, record steps, reference is masked, undo works", async ({ page }) => {
  await page.goto("/case");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: "My cases", level: 1 })).toBeVisible();

  // Start tracking the pension: one tap, and the case opens.
  await page.getByRole("button", { name: /Track this: .*pension/i }).click();
  await expect(page.getByRole("heading", { name: "Your own progress, not government status" })).toBeVisible();
  await expect(page.getByTestId("next-action")).toHaveText("Check if you qualify");

  await page.getByRole("button", { name: "Mark as done: Eligibility checked" }).click();
  await expect(page.getByText(/Done · \d{4}-\d{2}-\d{2}/)).toBeVisible();
  await expect(page.getByTestId("next-action")).toHaveText("Add your missing documents");
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

test("my cases: links, checklist, follow-up and notes live on the case", async ({ page }) => {
  await page.goto("/case");
  await page.waitForLoadState("networkidle");
  // The case from the first test is listed as a card.
  await page.getByTestId("case-delhi-old-age-pension").click();

  const links = page.getByTestId("case-links");
  await expect(links.getByRole("link", { name: "Check eligibility in chat" })).toHaveAttribute("href", /\/chat\?q=/);
  await expect(links.getByRole("link", { name: "Draft an RTI" })).toHaveAttribute("href", "/drafts?kind=rti");
  await expect(links.getByRole("link", { name: "Draft a complaint for this service" })).toHaveAttribute("href", "/drafts?kind=pension_delay");
  await expect(page.getByTestId("case-checklist").getByText("Aadhaar card")).toBeVisible();

  // Submitted long ago in the previous test: the follow-up suggestion shows once the user's own days pass.
  await page.getByLabel("Days to wait").fill("3");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText(/Follow up from/)).toBeVisible();
  await expect(page.getByTestId("follow-up-due")).toBeVisible();
  await page.getByLabel("I received a reply from the department").click();
  await expect(page.getByLabel("I received a reply from the department")).toBeChecked();
  await expect(page.getByTestId("follow-up-due")).toHaveCount(0);

  await page.getByLabel(/Add a note/).fill("Called the office, ID 2345 6789 0124");
  await page.getByRole("button", { name: "Add note" }).click();
  const notes = page.getByTestId("case-notes");
  await expect(notes).toContainText("Called the office");
  await expect(notes).not.toContainText("6789");
  await page.getByRole("button", { name: "Delete this note" }).click();
  await expect(page.getByTestId("case-notes")).toHaveCount(0);
});

test("track this: a chat service card starts a case and links to it", async ({ page }) => {
  await page.goto("/chat?q=" + encodeURIComponent("Am I eligible for income certificate?"));
  await expect(page.getByRole("textbox").first()).toHaveValue(/income certificate/);
  await page.getByRole("button", { name: /send/i }).first().click();
  await page.getByRole("button", { name: "Track this in My cases" }).click({ timeout: 30_000 });
  await page.getByRole("link", { name: "Open in My cases" }).click();
  await expect(page.getByRole("heading", { name: /income certificate/i, level: 2 })).toBeVisible();
});
