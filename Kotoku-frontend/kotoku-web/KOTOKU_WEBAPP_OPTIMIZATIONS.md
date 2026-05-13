# KOTOKU_WEBAPP_OPTIMIZATIONS.md

> For Claude Code:
> This file documents all known visual issues, inconsistencies, and optimization
> tasks for the Kotoku web app at kotoku-web.vercel.app. Work through these in
> priority order. All color values reference KOTOKU_BRAND_TOKENS.md which must
> be read first. Do not introduce new colors or styles outside of those tokens.

---

## Priority 1 — Fix immediately (visible bugs and broken brand)

### 1.1 Navbar: "Kotoku" wordmark is near-invisible

**Problem:**
The "Kotoku" text next to the blue shield icon in the navbar is rendered in a
near-white or very light gray that blends into the white background. It is
practically invisible on desktop and will be unreadable on mobile.

**Fix:**
Set the navbar brand name text color to brand.black (#0F172A).

```css
/* target the Kotoku text in the navbar */
.navbar-brand span,
nav .brand-name,
nav a.logo-text {
  color: #0F172A;
  font-weight: 600;
}
```

Or in Tailwind: `text-brand-black font-semibold`

---

### 1.2 Hero headline first line: too light to read

**Problem:**
"Don't take their word for it." uses a gray that is too close to white,
making it nearly invisible against the white background. The design intent
(faded first line, bold blue second line) is correct but the current shade
fails readability.

**Fix:**
Change the faded first hero line to brand.mist (#94A3B8). This preserves
the visual hierarchy while making the line actually readable.

```css
.hero-headline-faded,
.hero-line-one {
  color: #94A3B8;
}
```

Or in Tailwind: `text-brand-mist`

The second line ("Take evidence for it.") stays brand.primary (#2563EB).
Do not change it.

---

### 1.3 Footer: Raw JSON string is rendering visibly

**Problem:**
The string `{"mode":"full","isActive":true,"isUserDisabled":false}` is
rendering as visible text at the bottom of every page. This is a debug
artifact that should not be visible to users.

**Fix:**
Find where this string is being injected into the DOM and remove it.
Check: layout components, analytics scripts, feature-flag providers,
any `dangerouslySetInnerHTML` usage, and third-party script tags in
`_document.tsx` or `layout.tsx`.

---

## Priority 2 — Navbar consistency (apply to ALL pages)

### 2.1 Navbar links are inconsistent across pages

**Problem:**
The navbar changes depending on which page is active:
- Homepage: shows "How it works" | "Pricing" | "Sign in"
- Pricing page: shows "How it works" | "Sign in" (Pricing is missing)

This inconsistency breaks navigation and makes it feel like the nav was
built page-by-page rather than as a shared component.

**Fix:**
Create or update a single shared Navbar component used on every page.
The navbar should always render the same links regardless of the active page.

**Navbar link spec (consistent across all pages):**


Rules:
- All four elements appear on every page including /pricing, /how-it-works,
  /login, and any future pages.
- The active page link should receive an active style:
  - Underline or slightly darker color (brand.black) to indicate current page.
  - Non-active nav links: brand.ink (#334155).
  - Active nav link: brand.black (#0F172A) + underline or font-semibold.
- "Sign in" is always a filled black button (brand.black background,
  white text), never a plain link.
- "Kotoku" wordmark is always brand.black (#0F172A), never gray.

**Active link styling example:**

```css
/* default nav link */
nav a {
  color: #334155;        /* brand.ink */
  font-weight: 500;
}

/* active nav link */
nav a.active,
nav a[aria-current="page"] {
  color: #0F172A;        /* brand.black */
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 4px;
}

/* sign in button — always the same */
nav .cta-button {
  background-color: #0F172A;
  color: #FFFFFF;
  border-radius: 999px;
  padding: 8px 20px;
  font-weight: 600;
}
```

---

### 2.2 "Pricing" link missing from navbar on /pricing page

This is a direct result of 2.1. Once the shared Navbar component is
corrected, "Pricing" will appear on all pages automatically.

Verify: after fix, visit /pricing and confirm all nav links are present.

---

## Priority 3 — Pricing page improvements

### 3.1 Enterprise tab is empty

**Problem:**
The pricing page has a Personal/Enterprise toggle but clicking Enterprise
shows no content. This is a broken state for any visitor who clicks it.

**Fix (two options):**

Option A — Populate the Enterprise tab with plan cards:
Build Enterprise Standard and Enterprise Plus cards matching the same
layout as Personal cards. Content is in KOTOKU_PRICING_PAGE_SECTION.md.

Option B — Hide the Enterprise tab temporarily:
If Enterprise content is not ready, remove the toggle entirely and show
only Personal plans. Add a note below the cards:

> "Enterprise plans for dealers, agencies, and landlord portfolios are
> coming soon. Contact us to be notified."

Do not leave the tab visible with empty content.

---

### 3.2 Add a closing CTA section above the footer on pricing page

**Problem:**
The pricing page ends with the fair-use note and then immediately the
footer. There is no closing call to action.

**Fix:**
Add a simple closing section above the footer:

Headline: "Ready to protect your first agreement?"
Subheading: "Join Kotoku and seal your deal in under five minutes."
CTA button: "Get started free" → links to /login
Style: white background, centered, brand.black heading, brand.ink subheading,
brand.primary button.

---

## Priority 4 — Homepage improvements

### 4.1 Add a closing CTA section above the footer on homepage

**Problem:**
The homepage ends abruptly after the legal standing section with no