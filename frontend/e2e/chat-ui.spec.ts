import { expect, test, type Page } from "@playwright/test";

const sse = (events: [string, unknown][]) => events.map(([e, d]) => `event: ${e}\r\ndata: ${JSON.stringify(d)}\r\n\r\n`).join("");

/** Replies to every /chat POST with a short answer, optionally after a delay, and counts the requests. */
async function mockChat(page: Page, delayMs = 0) {
  const seen: string[] = [];
  await page.route("**/chat", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    seen.push(JSON.parse(route.request().postData() ?? "{}").message);
    if (delayMs) await new Promise((r) => setTimeout(r, delayMs));
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sse([
        ["status", { id: "stream", stream_id: "s1", state: "open" }],
        ["status", { id: "search", label: "Searching the web", state: "done" }],
        ["token", { text: "Here is a short answer. " }],
        ["token", { text: "Verify locally." }],
        ["done", { refused: false }],
      ]),
    });
  });
  return seen;
}

test("chat: empty state greets, offers six prompts and has no New chat button yet", async ({ page }) => {
  await page.goto("/chat");
  const empty = page.getByTestId("chat-empty");
  await expect(empty).toBeVisible();
  await expect(empty.getByRole("button")).toHaveCount(6);
  await expect(page.getByRole("button", { name: "New chat" })).toHaveCount(0);
});

test("chat: Enter sends, Shift+Enter adds a line, replies sit in a bubble with the avatar", async ({ page }) => {
  const seen = await mockChat(page);
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  const box = page.getByRole("textbox", { name: "Type your question…" });
  await box.fill("first line");
  await box.press("Shift+Enter");
  await box.type("second line");
  expect(seen).toHaveLength(0); // Shift+Enter did not send
  await expect(box).toHaveValue("first line\nsecond line");
  await box.press("Enter");

  const user = page.getByTestId("user-msg");
  await expect(user).toContainText("first line");
  await expect(user).toContainText("second line");
  const bot = page.getByTestId("bot-msg");
  await expect(bot).toContainText("Here is a short answer. Verify locally.");
  await expect(bot.getByRole("list", { name: "Steps" })).toContainText("Searching the web"); // step chips are inside the reply
  await expect(box).toHaveValue("");
  expect(seen).toEqual(["first line\nsecond line"]);

  const u = await user.locator("p").boundingBox();
  const b = await bot.locator("div.rounded-\\[20px_20px_20px_6px\\]").boundingBox();
  expect(u!.x + u!.width).toBeGreaterThan(b!.x + b!.width); // user on the right, Sahaay on the left
});

test("chat: a typing indicator shows while Sahaay works, follow-up chips come after the reply", async ({ page }) => {
  await mockChat(page, 700);
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "How do I get an income certificate in Delhi?" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Sahaay is typing" })).toBeAttached();
  await expect(page.getByTestId("bot-msg")).toContainText("Here is a short answer.");
  const follow = page.getByTestId("follow-ups");
  await expect(follow).toContainText("You could also ask");
  await expect(follow.getByRole("button")).toHaveCount(3);
  await expect(follow.getByRole("button", { name: "How do I get an income certificate in Delhi?" })).toHaveCount(0); // not the one just asked
});

test("chat: New chat clears the conversation and brings back the prompts", async ({ page }) => {
  await mockChat(page);
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("hello");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("bot-msg")).toBeVisible();
  await page.getByRole("button", { name: "New chat" }).click();
  await expect(page.getByTestId("user-msg")).toHaveCount(0);
  await expect(page.getByTestId("chat-empty")).toBeVisible();
  await expect(page.getByRole("button", { name: "New chat" })).toHaveCount(0);
});

test("chat: the conversation is an aria-live log and the view follows the newest message", async ({ page }) => {
  await mockChat(page);
  await page.setViewportSize({ width: 1280, height: 600 });
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("log", { name: "Conversation" })).toHaveAttribute("aria-live", "polite");
  for (let i = 0; i < 7; i++) {
    await page.getByRole("textbox").fill(`question number ${i}`);
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("bot-msg")).toHaveCount(i + 1);
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible(); // reply finished, not busy
  }
  await expect(page.getByTestId("user-msg").last()).toBeInViewport();
  await expect(page.getByTestId("bot-msg").last()).toBeInViewport();
  await expect(page.getByRole("textbox")).toBeInViewport(); // composer stays reachable
});

test("chat on a phone: no sideways scroll, composer pinned at the bottom, 44px send target", async ({ page }) => {
  await mockChat(page);
  await page.setViewportSize({ width: 375, height: 700 });
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  const noScroll = () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(await noScroll()).toBe(true);
  await page.getByRole("textbox").fill("a fairly long question that should wrap inside the bubble instead of running off the screen");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("bot-msg")).toBeVisible();
  expect(await noScroll()).toBe(true);
  const tb = await page.getByRole("textbox").boundingBox();
  expect(tb!.y + tb!.height).toBeLessThanOrEqual(700);
  const send = await page.getByRole("button", { name: "Send" }).boundingBox();
  expect(send!.width).toBeGreaterThanOrEqual(44);
  expect(send!.height).toBeGreaterThanOrEqual(44);
});

test("chat: Hindi labels", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "हिंदी" }).click();
  await mockChat(page);
  await page.goto("/chat");
  await page.waitForLoadState("networkidle");
  await page.getByRole("textbox").fill("नमस्ते");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "नई बातचीत" })).toBeVisible();
  await expect(page.getByRole("log", { name: "बातचीत" })).toBeVisible();
});
