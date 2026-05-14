# KOTOKU_LOGO_LOCKUP_RULES.md

> For Claude Code and designers:
> This file defines how the Kotoku logo mark and wordmark should be
> combined, sized, spaced, and used across all product touchpoints.
> All color values reference KOTOKU_BRAND_TOKENS.md.
> Do not modify proportions, spacing, or colors outside these rules.

---

## Logo assets (required files)

Export and store these five files in /assets/brand/:

| File name                        | Contents                          | Use                                      |
|----------------------------------|-----------------------------------|------------------------------------------|
| kotoku-icon.svg                  | Icon mark only, no wordmark       | App icon base, standalone mark           |
| kotoku-logo-stacked.svg          | Icon above + "Kotoku" below       | Splash screen, onboarding, marketing     |
| kotoku-logo-horizontal.svg       | Icon left + "Kotoku" right        | Navbar, web header, email header         |
| kotoku-favicon.svg               | Simplified icon, tight crop       | Browser favicon, PWA icon                |
| kotoku-logo-white.svg            | All-white version of horizontal   | Dark backgrounds, navy/blue sections     |

---

## The mark: what it is

The Kotoku logo mark is a flat, two-color icon showing:
- A stylized open hand from above, gently placing
- A document/agreement card (with two gold horizontal lines)
- Into a rounded traditional drawstring sack (Kotoku = Akan for pocket/sack)

The mark communicates: safekeeping, trust, intentional action, and cultural
rootedness. It must never be redrawn, distorted, or recolored outside the
approved palette below.

---

## Logo colors

| Element              | Color name       | Hex       | Notes                              |
|----------------------|------------------|-----------|------------------------------------|
| Hand silhouette      | Kotoku Navy      | #1B2A6B   | Deep navy, consistent with mark    |
| Sack body            | Kotoku Navy      | #1B2A6B   | Same as hand, unified silhouette   |
| Document card        | White            | #FFFFFF   | Always white fill                  |
| Document lines       | Kotoku Gold      | #B8912A   | Gold accent, document text only    |
| Wordmark "Kotoku"    | Kotoku Navy      | #1B2A6B   | Or brand.black (#0F172A) on white  |
| Background           | White            | #FFFFFF   | Default: always white              |

### On dark backgrounds
Use the all-white variant (kotoku-logo-white.svg):
- Hand, sack, and wordmark: #FFFFFF
- Document card: semi-transparent white or light navy outline
- Document lines: #B8912A (gold holds on dark backgrounds)

### Never use
- The brand.primary blue (#2563EB) as the sack or hand fill
- Any gradient on the mark
- Drop shadows or glows on the mark
- The mark on a busy photographic background without a white container

---

## Wordmark typography

| Property       | Value                                              |
|----------------|----------------------------------------------------|
| Font family    | Cormorant Garamond, or fallback: Georgia, serif    |
| Font weight    | Regular (400) or Light (300)                       |
| Letter spacing | 0.05em (slight tracking for elegance)              |
| Case           | Sentence case: "Kotoku" — never ALL CAPS           |
| Color          | Kotoku Navy (#1B2A6B) on white backgrounds         |
| Color          | White (#FFFFFF) on dark/navy/blue backgrounds      |

The wordmark should never be set in a sans-serif font.
The serif conveys the trust and authority the product needs.

---

## Lockup 1: Horizontal (navbar and web header)

Use this in all navigation bars, web headers, and app top bars.


[icon] Kotoku


Rules:
- Icon height: 28px at base navbar size (scales proportionally)
- Gap between icon and wordmark: 8px (spacing token: sm)
- Wordmark font size: 18px (text.lg)
- Wordmark font weight: 600 (semibold)
- Vertical alignment: icon and wordmark centered on the same baseline
- The icon and wordmark should feel like one unified element, not two separate things

At smaller sizes (mobile navbar):
- Icon height: 24px
- Wordmark font size: 16px
- Gap: 6px
/* React Native / web navbar example */
<View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
<Image source={kotokuIcon} style={{ height: 28, width: 28 }} />
<Text style={{
fontFamily: 'Cormorant Garamond',
fontSize: 18,
fontWeight: '600',
color: '#1B2A6B',
letterSpacing: 0.8,
}}>
Kotoku
</Text>
</View>


---

## Lockup 2: Stacked (splash screen and marketing)

Use this on the app splash screen, onboarding screens, and marketing
materials where there is generous white space.


[icon]
Kotoku


Rules:
- Icon size: 80px × 80px at splash screen
- Gap between icon and wordmark: 12px (spacing token: md)
- Wordmark font size: 24px (text.2xl)
- Wordmark font weight: 400 (regular) — lighter weight works better at large sizes
- Horizontal alignment: icon and wordmark both centered on the same vertical axis
- White space around the full lockup: minimum 32px on all sides

At marketing/hero scale:
- Icon size: 120px
- Wordmark font size: 32px
- Letter spacing: 0.08em

---

## Lockup 3: Icon only (app icon and favicon)

Use this anywhere the wordmark cannot fit:
- Mobile app icon (all sizes)
- Browser favicon
- Push notification icon
- Small badges and chips

Rules:
- Never crop the icon — always show the full hand + document + sack
- Minimum size: 32px × 32px (below this, use a simplified single-element version)
- At 32px: the hand may be simplified to a single shape if detail is lost
- App icon container: use brand.navy (#1B2A6B) as the background with white mark
  OR white background with navy mark — test both and use whichever reads better
- Favicon: 32×32px SVG or 16×16px simplified version

App icon background options:
- Option A: White background, navy mark (clean, light)
- Option B: Navy background (#1B2A6B), white mark (bold, stands out on home screen)

Recommendation: Option B (navy background) for the mobile app icon —
it stands out better among other app icons and matches the brand's
authoritative tone.


## Clear space rules

The logo must always have minimum clear space around it equal to the
height of the "K" in the wordmark (approximately 1× the cap height).

No other element, image, or text should enter this clear space zone.
↑ 1× cap height
← 1× [KOTOKU LOGO] 1× →
↓ 1× cap height



## Size minimums

| Lockup              | Minimum size                  |
|---------------------|-------------------------------|
| Horizontal lockup   | Icon 20px height, text 14px   |
| Stacked lockup      | Icon 48px, text 16px          |
| Icon only           | 24px × 24px                   |
| Favicon             | 16px × 16px (simplified mark) |

Below these minimums, switch to icon-only. Never shrink the wordmark
to the point where it is unreadable.

---

## Navbar consistency rules (web and mobile)

> This section addresses the known issue where the Kotoku navbar
> changes links and logo treatment depending on the active page.

### Rule 1: One shared Navbar component

Use a single Navbar component across all pages and routes.
Never build page-specific navbars.

### Rule 2: Always show the horizontal lockup

The navbar always shows the horizontal lockup (icon + "Kotoku" wordmark).
The wordmark is always visible. Never show the icon alone in the navbar.

### Rule 3: Wordmark is always Kotoku Navy or brand.black

Never render the "Kotoku" wordmark in any gray, light color, or
near-white in the navbar. It must always be:
- #1B2A6B (Kotoku Navy) — preferred
- #0F172A (brand.black) — acceptable alternative

The current near-invisible gray "Kotoku" in the navbar must be fixed.

### Rule 4: Nav links are consistent on every page

The navbar always renders these links in this order:

  [Kotoku logo + wordmark]     How it works     Pricing     Sign in

All four elements appear on every page including /pricing, /how-it-works,
/login, and all authenticated app pages.

### Rule 5: Active page link styling

```css
/* default nav link */
nav a {
  color: #334155;          /* brand.ink */
  font-weight: 500;
  text-decoration: none;
}

/* active / current page */
nav a.active,
nav a[aria-current="page"] {
  color: #0F172A;          /* brand.black */
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 4px;
  text-decoration-thickness: 2px;
}

/* hover state */
nav a:hover {
  color: #1B2A6B;          /* Kotoku Navy */
}
```

### Rule 6: Sign in button is always the same

```css
nav .signin-button {
  background-color: #0F172A;   /* brand.black */
  color: #FFFFFF;
  border-radius: 999px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

nav .signin-button:hover {
  background-color: #1B2A6B;   /* Kotoku Navy on hover */
}
```

---

## What not to do

| Do not do this                                    | Do this instead                                  |
|---------------------------------------------------|--------------------------------------------------|
| Render "Kotoku" in light gray or near-white       | Always use #1B2A6B or #0F172A                    |
| Use the icon without the wordmark in the navbar   | Always use horizontal lockup in navbar           |
| Change nav links per page                         | Use one shared Navbar component everywhere       |
| Recolor the sack or hand to brand.primary blue    | Keep sack and hand in Kotoku Navy (#1B2A6B)      |
| Use a sans-serif font for the wordmark            | Always use Cormorant Garamond or serif fallback  |
| Place the logo on a busy or photographic bg       | Always use on white or surface.subtle background |
| Scale below minimum sizes                         | Switch to icon-only below minimums               |
| Stretch or distort the mark proportions           | Always scale uniformly                           |
| Add drop shadows or glows to the mark             | Flat, no effects                                 |

---

## Quick reference

| Touchpoint               | Lockup to use          | Min icon size | Wordmark color  |
|--------------------------|------------------------|---------------|-----------------|
| Web navbar               | Horizontal             | 28px          | #1B2A6B         |
| Mobile app top bar       | Horizontal             | 24px          | #1B2A6B         |
| App splash screen        | Stacked                | 80px          | #1B2A6B         |
| Onboarding screens       | Stacked                | 64px          | #1B2A6B         |
| Mobile app icon          | Icon only (navy bg)    | 1024px export | N/A             |
| Browser favicon          | Icon only              | 32px          | N/A             |
| Marketing / hero section | Stacked or horizontal  | 80px          | #1B2A6B         |
| Dark/navy sections       | White variant          | 28px          | #FFFFFF         |
| PDF exports / case packs | Horizontal             | 40px          | #1B2A6B         |
