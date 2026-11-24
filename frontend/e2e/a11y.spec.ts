import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Automated accessibility scan (WCAG 2.1 A/AA) of the main screens, phone and desktop widths.
// This catches contrast, labels, names and roles. It does not replace a manual keyboard and
// screen-reader pass.
const PAGES = ["/", "/chat", "/compare", "/case", "/documents", "/forms", "/drafts", "/privacy", "/help/complaints", "/help/scams", "/help/terms"];
const SIZES = [
  { name: "phone", width: 390, height: 844 },
  { name: "desktop", width: 1440, height: 900 },
];

for (const size of SIZES) {
  for (const path of PAGES) {
    test(`axe: ${path} at ${size.name}`, async ({ page }) => {
      await page.setViewportSize({ width: size.width, height: size.height });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(400); // let data-driven sections render
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
      expect(summary).toEqual([]);
    });
  }
}

test("axe really detects problems (guards against a scan that checks nothing)", async ({ page }) => {
  await page.setContent('<html lang="en"><body><img src="x.png"><button></button></body></html>');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.map((v) => v.id)).toEqual(expect.arrayContaining(["image-alt", "button-name"]));
});

test("axe: chat with an answer card, and the review screens", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: /student in Delhi, family income about 3 lakh/ }).click();
  await expect(page.locator("article").first()).toBeVisible();
  await page.getByRole("button", { name: /Yes, that's right/ }).click();
  await page.waitForTimeout(600); // entrance animations finish, so contrast is measured on settled colours
  const chat = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(chat.violations.map((v) => `${v.id}: ${v.nodes[0].target.join(" ")}`)).toEqual([]);

  await page.goto("/drafts");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "RTI application" }).click();
  await page.getByLabel("Your name").fill("Asha");
  await page.getByLabel("Your address").fill("Delhi");
  await page.getByLabel(/Public authority/).fill("PIO");
  await page.getByLabel("Information you want").fill("Status");
  await page.getByRole("button", { name: "Review", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review the draft" })).toBeVisible();
  const draft = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  expect(draft.violations.map((v) => `${v.id}: ${v.nodes[0].target.join(" ")}`)).toEqual([]);
});

test("tap targets are at least 44px on a phone (buttons, links, form controls)", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/chat", "/compare", "/case", "/documents", "/forms", "/drafts", "/privacy", "/help/complaints", "/help/scams", "/help/terms"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const small = await page.evaluate(() => {
      const out: string[] = [];
      document.querySelectorAll("button, a[href], select, input:not([type=hidden]):not(.sr-only), textarea").forEach((el) => {
        const r = (el as HTMLElement).getBoundingClientRect();
        const cs = getComputedStyle(el);
        if (r.width === 0 || r.height === 0 || cs.visibility === "hidden") return;
        // Inline text links inside a sentence are exempt (WCAG 2.5.8); standalone controls are not.
        const inline = el.tagName === "A" && cs.display === "inline";
        if (!inline && (r.height < 43.5 || r.width < 43.5) && !(el instanceof HTMLInputElement && el.type === "checkbox"))
          out.push(`${el.tagName.toLowerCase()} "${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
      });
      return out;
    });
    expect(small, path).toEqual([]);
  }
});

test("reduced motion: nothing pulses or animates when the user asks for less motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/case");
  await page.waitForLoadState("networkidle");
  const animated = await page.evaluate(() =>
    Array.from(document.querySelectorAll("*")).filter((el) => {
      const a = getComputedStyle(el).animationName;
      return a && a !== "none";
    }).length,
  );
  expect(animated).toBe(0);
});

test("keyboard: Tab reaches the main controls on the chat page with a visible focus ring", async ({ page }) => {
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  const seen = new Set<string>();
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      // The Next.js dev-tools badge only exists in development.
      if (!el || el === document.body || el.tagName === "NEXTJS-PORTAL") return null;
      const cs = getComputedStyle(el);
      const ring = cs.outlineStyle !== "none" || cs.boxShadow !== "none";
      return { tag: el.tagName, name: el.getAttribute("aria-label") || el.textContent?.trim().slice(0, 25) || "", ring };
    });
    if (info) {
      expect(info.ring, `focus ring on ${info.tag} ${info.name}`).toBe(true);
      seen.add(`${info.tag}:${info.name}`);
    }
  }
  expect(seen.size).toBeGreaterThan(4);
});
