# Sahaay: Design System

The look is: **warm, calm, trustworthy, independent.** Not a government portal, not a bank. It must feel like a helpful companion that a first-time smartphone user, a student, or a grandparent can use.

Mockups were approved with this exact language: mobile Home, Chat, Document check, desktop Case folder, and a full 3-column desktop view (a Scam checker mockup also exists). Where this file and any later idea disagree, ask before deviating.

**Scope note:** a few elements in the mockups are optional extras, not in the final functionality list (`docs/PRD.md`): the voice mic and Listen button, WhatsApp share, scam checker, and the resizer entry point. Build them only after the core stages in `docs/BACKLOG.md`. Until then, omit those buttons rather than showing dead controls. The language switch has three options: EN, हिंदी, Hinglish.

## 1. Brand

- Name: **Sahaay** (सहाय). Wordmark in Bricolage Grotesque 800, teal.
- Tagline: "Sahaay: सरकारी सेवाओं में आपका साथी".
- Logo mark: an open arch (bridge/cupped hand) in teal with a marigold dot beneath, as inline SVG. No emblem, flag, chakra or department logo, ever.
- Voice: plain, warm, short sentences. Say what to do next. Never bureaucratic, never cute about serious topics (scams, rejections).

## 2. Colour tokens

```css
:root {
  --teal-700: #0F4C5C;      /* primary: header, primary buttons, links */
  --teal-100: #E3EFF1;      /* tints: icon chips, info strips */
  --teal-050: #D3E4E8;      /* dividers on teal tint */
  --marigold-500: #F2A541;  /* accent FILL only (CTA, highlight). Text on it: ink */
  --marigold-100: #FCE8C8;  /* unknown/caution chip fill */
  --marigold-050: #FFF3DE;  /* next-step card */
  --bg: #FAF7F2;            /* app background (warm off-white) */
  --bg-sunken: #F3EEE3;     /* strips, secondary panels */
  --bg-panel: #F5F0E6;      /* right case panel */
  --surface: #FFFFFF;       /* cards, bubbles, inputs */
  --line: #E4DCCD;          /* borders */
  --ink: #1C2B33;           /* primary text */
  --ink-2: #3F4F57;         /* secondary text */
  --ink-3: #5B6B73;         /* muted text (≥4.5:1 on --bg) */
  --ok-700: #1B5E20;  --ok-500: #2E7D32;  --ok-100: #E6F2E7;     /* verified / met */
  --warn-700: #7A3F06; --warn-text: #B45309; --warn-100: #FCE8C8; /* caution / unknown */
  --bad-700: #8E1B1B; --bad-500: #C62828; --bad-100: #FCE9E9;     /* scam / not met / exclusion */
  --info-500: #1E5AA8;
}
```

Rules:
- Marigold is a **fill** with `--ink` text. Never marigold text on white (fails contrast).
- Green/amber/red always pair with an icon **and** a text label. Never colour alone.
- Status colours mean the same thing everywhere: green = verified/met/safe, amber = unknown/needs attention, red = not met/danger/scam, teal = Sahaay's own actions and progress.
- Dark mode: not in the first build; add an equivalent token set later. Keep semantic names so a theme swap is only token values.

## 3. Typography

- Headings/numbers: **Bricolage Grotesque** 600–800.
- Body/UI: **Figtree** 400–600.
- Hindi: **Noto Sans Devanagari** 400–700 (declared as fallback in every `font-family`).
- Base size 16px minimum; 15px only inside dense cards. Line-height 1.4–1.5 body, 1.1–1.2 headings. Letter-spacing −0.02em on large headings.
- Scale (px): 11 (micro labels, uppercase +0.05em) · 12.5 · 14 · 15 · 17 · 19–21 (card titles) · 24 · 31–34 (page headline).
- Never truncate Hindi mid-glyph; allow wrapping. Test every screen in `hi` and `hn`.

## 4. Spacing, shape, elevation

- 4px base grid. Common gaps: 8, 10, 12, 14, 16, 20, 24.
- Radii: chips/buttons **999px** (pill) · small cards 14–18 · large cards 20–24 · icon tiles 10–12.
- Borders 1px `--line`. Shadows only on hover/lift: `0 8–10px 20–26px rgba(15,76,92,0.10–0.14)`.
- No gradient backgrounds, no left-border accent cards, no glassmorphism, no emoji. Flat, warm, tactile.

## 5. Layout

- **Mobile (390 base):** single column, 16–20px gutters, sticky bottom input on chat. Top bar: back, logo, language.
- **Desktop (≥1200):** three columns: left nav 252px · centre chat (flex) · right Case folder 352px. Below 1200 the right panel becomes a slide-over; below 900 the left nav becomes a drawer.
- Pages fluid: no fixed pixel widths on content; `max-width` containers; stack at phone width; wide tables scroll in a box.

## 6. Iconography

Inline SVG, 24px viewBox, stroke 2px, round caps/joins, `currentColor`. `aria-hidden` when decorative, `aria-label` when alone. No icon fonts, no emoji. Core set: mic, speaker/waveform, send, paperclip, share, bookmark, shield (+check/alert), file, calendar, home, folder, user(s), briefcase, graduation cap, sprout (farmer), arrow/chevron, check, x, alert, help-circle, download, upload, image, link, lock.

## 7. Components (spec)

**Language switch:** pill segmented control (EN · हिंदी · Hinglish). Selected = teal fill, white text. Persists; sent as `preferred_language` with each request.

**Chat bubbles:** user = teal fill, white text, radius 20/20/6/20, right aligned, max 60–78%. Bot = white card with line border, radius 20/20/20/6. Bot responses may contain cards.

**Tool-call pills:** `--bg-sunken` pill, 13px. Spinner (teal) → green check. Appear in sequence ("Searching scheme rules" → "Checking eligibility" → "Mapping prerequisites"). Driven by SSE `status` events.

**Scheme card:** title (Bricolage 19–20) · verified badge (green pill with shield-check, date, citation number chip) · benefit line · eligibility rows (met = green circle check, unknown = amber "?", not met / exclusion = red x) · prerequisite chain chips (numbered, last one teal) · **fee strip** (3 columns on `--teal-100`: Official fee / At a CSC (max) / Processing time) · actions row (Listen, WhatsApp, Save, Compare, What if…).

**Verified badge states:** green "Verified from official portal · {date}" · amber "Verify locally" when `partial` or stale · never shown green without a source.

**Citation chip:** small numbered square on the badge and inline `[n]`; click opens a popover with source title, URL (allowlisted), date checked.

**Quick-reply chips:** outline teal pill, 44px high, hover fills teal. 2–4 per bot message, context-specific.

**Mini inline form:** compact card inside the bubble with dropdowns/segmented inputs and a "Check now" button; replaces 3–4 typed answers.

**Input bar:** white pill, attach, mic (with soft pulsing rings while available/listening), send (marigold circle, dark icon). Placeholder invites speaking, typing, or dropping a screenshot/document.

**Readiness ring:** SVG ring, stroke animates from 0 to value on mount, shows `n/total checks`. Copy always: "Based on your checklist. Not a prediction of approval."

**Document card:** thumbnail + title + sub-line + status chip (green "Looks fine", amber "Too old" / "Name mismatch", teal "Scanning" with progress bar and a scan line). Tap to expand details with the fix.

**Journey tracker (5 steps):** top bar segments + numbered circles. Done = teal with check, current = marigold with soft pulse, upcoming = outline grey. Always paired with the label "Your own progress, not government status". Steps: Eligibility checked · Documents verified · Form auto-filled · Submitted on official portal · Reference ID saved.

**Form review panel:** fields shown as editable chips on marigold tint; unanswered = dashed grey "Needs your answer"; checkbox "I checked every field and it is correct" must be ticked; **Download** is disabled grey until then, then teal.

**Scam verdict:** red card with shaking alert icon ("Likely a scam") + reasons with red x; link anatomy showing the real domain with the offending part highlighted; official domain shown in a green strip; actions "Report on cybercrime.gov.in" and "Call 1930". Safe verdict: green card with drawn check; still carries an OTP reminder.

**Next-step card:** `--marigold-050` surface, uppercase micro label, one action as a marigold button, secondary "Counter slip".

**Buttons:** primary = teal fill white text; accent = marigold fill ink text; secondary = white with line border; destructive only in "delete my data". Height ≥44px. Focus ring 3px `--teal-700` at 40% with 2px offset.

**Empty/error states:** friendly one-liner + a next action. Never blame the user. Errors: "I couldn't read that photo. Try again in better light." with a retake button.

## 8. Motion

Purposeful only: it must explain state.

| Where | Motion |
|---|---|
| Home mic | Two expanding soft rings (2.6s loop), gentle float, 4-bar waveform each side |
| Tool-call pills | Staggered rise-in; spinner → check |
| Eligibility ticks | Check strokes draw in sequence |
| Readiness ring | Fill on mount (1.6s ease-out) |
| Document scan | Marigold scan line sweeps the thumbnail; progress bar |
| Journey current step | Soft marigold pulse |
| Scam verdict | Red icon shakes once on reveal then rests; green check draws |
| Listen | 3 bars animate only while audio plays |
| Form fields | Typed-in reveal on first fill |
| Cards | 2–3px lift on hover |

All animations stop under `prefers-reduced-motion: reduce` (show the final state). Durations 150–600ms for UI, loops only for "listening/scanning/pulsing". No auto-playing decoration.

## 9. Accessibility (requirements, not nice-to-haves)

- WCAG 2.2 AA contrast. Text 4.5:1 (muted text uses `--ink-3`), large text 3:1.
- Every interactive element is a real `<button>`/`<a>`/`<input>` with a label; tap targets ≥44px.
- Full keyboard path through chat, cards, forms; visible focus.
- Screen-reader labels on icon-only buttons; `aria-live="polite"` on streaming replies and status pills; `aria-pressed`/`aria-expanded` on toggles.
- Never rely on colour alone; never rely on voice alone (always text equivalent).
- Language attribute switches (`lang="hi"`) for Hindi blocks.
- Voice features degrade gracefully (feature-detect; explain when unsupported on the device/browser).
- Large-text mode: respects browser font scaling up to 200% without clipping.

## 10. Content and copy rules

- Reading level ≈ Grade 6. One idea per sentence. Prefer verbs: "Get a fresh income certificate."
- Hindi and Hinglish are first-class: write natural copy, not word-for-word translation. Keep official scheme names in their original form.
- Always label: "AI assistant · not an official government channel".
- Fees and time always shown in the standard strip: Official fee · At a CSC (max) · Processing time. Missing values show "Verify locally", never a guess.
- Placeholders in mockups (`₹[fee]`, `[N] days`) must be replaced with verified data or "Verify locally"; never ship a placeholder.
- Never write "approved", "authentic", "verified document", "your status is…" about the user's application.

## 11. Screens (inventory)

Mobile and desktop screens to build: Home · Chat (with service/eligibility card) · Compare · Document check · Case folder / Dashboard (journey tracker, readiness, form review, next step) · Complaint / RTI draft review · Screenshot assistant · Privacy & My data.
Desktop: 3-column app shell (nav · chat · case folder) with the same screens as routes.
Any new screen follows these same components; no new visual language.

## 12. Implementation notes

- Tokens in `frontend/src/styles/tokens.css`, mapped into Tailwind theme. Components in `components/` use tokens only; no hard-coded hex in components.
- Fonts via `next/font` (Bricolage Grotesque, Figtree, Noto Sans Devanagari), `display: swap`.
- Animations in CSS (keyframes) or small motion helpers; no heavy animation libraries needed.
- Print stylesheet for the one-page case summary and counter slip: black on white, Noto Sans Devanagari, clear sections, source URLs printed.
