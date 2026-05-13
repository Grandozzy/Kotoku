# KOTOKU_BRAND_TOKENS.md

> For Claude Code:
> This file is the single source of truth for all Kotoku brand colors, typography,
> spacing, and visual rules. Apply these tokens consistently across all web and
> mobile components. Do not introduce colors, font sizes, or spacing values that
> are not defined here unless explicitly instructed.

---

## Brand personality

Kotoku should feel trustworthy, direct, and modern — not corporate-heavy, not
playful. It is a serious tool for real people protecting real money in informal
and semi-formal transactions. The visual system reinforces that: strong blue for
trust and action, deep black for authority, clean white for clarity, and
purposeful grays that are always readable.

---

## Core brand colors

These five colors define Kotoku. Use nothing else as a primary color.

| Token name         | Hex       | Tailwind    | Use                                                              |
|--------------------|-----------|-------------|------------------------------------------------------------------|
| brand.primary      | #2563EB   | blue-600    | Primary CTAs, links, icon fills, hero highlight text, badges     |
| brand.black        | #0F172A   | slate-900   | Brand name, main headings, CTA button backgrounds, authority text|
| brand.ink          | #334155   | slate-700   | Body copy, nav links, card text, subheadings, descriptions       |
| brand.mist         | #94A3B8   | slate-400   | Decorative/receding text ONLY (e.g. faded hero first line)       |
| brand.white        | #FFFFFF   | white       | Page backgrounds, card fills, text on dark or blue surfaces      |

### Critical rule on brand.mist

brand.mist (#94A3B8) is the LIGHTEST color permitted for any text in the product.
It must only be used for intentionally decorative or receding text — such as the
faded first line of the hero headline. Never use it for body copy, nav items,
card descriptions, legal text, or any text the user needs to read.

The current "Kotoku" wordmark in the navbar and the faded hero line are too light
and must be corrected using the values below.

---

## Extended palette (supporting UI colors)

| Token name         | Hex       | Tailwind    | Use                                              |
|--------------------|-----------|-------------|--------------------------------------------------|
| surface.canvas     | #FFFFFF   | white       | Main page background                             |
| surface.subtle     | #F8FAFC   | slate-50    | Alternating section backgrounds                  |
| surface.card       | #FFFFFF   | white       | Card backgrounds                                 |
| border.light       | #E2E8F0   | slate-200   | Card borders, dividers                           |
| border.medium      | #CBD5E1   | slate-300   | Input borders, separators                        |
| blue.soft          | #DBEAFE   | blue-100    | Icon container fills, badge backgrounds          |

---

## Semantic / status colors

Use these ONLY for functional states. Never for decorative styling.

| Token name         | Hex       | Tailwind    | Use                                              |
|--------------------|-----------|-------------|--------------------------------------------------|
| semantic.success   | #16A34A   | green-600   | Sealed agreements, confirmed states              |
| semantic.warning   | #D97706   | amber-600   | Pending states, near-cap warnings                |
| semantic.error     | #DC2626   | red-600     | Failed actions, blocked states, error messages   |

---

## Typography

### Font stack

Use the system font stack for all text. Do not introduce a custom font in v1
unless explicitly instructed.


### Font sizes

| Token          | Size  | Tailwind | Use                                  |
|----------------|-------|----------|--------------------------------------|
| text.xs        | 12px  | text-xs  | Small print, legal notes, timestamps |
| text.sm        | 14px  | text-sm  | Helper text, limit notes, badges     |
| text.base      | 16px  | text-base| Body copy, card descriptions         |
| text.lg        | 18px  | text-lg  | Card headings, subheadings           |
| text.xl        | 20px  | text-xl  | Section subheadings                  |
| text.2xl       | 24px  | text-2xl | Section headings                     |
| text.4xl       | 36px  | text-4xl | Page headings                        |
| text.6xl       | 60px  | text-6xl | Hero headline                        |

### Font weights

| Use                              | Weight       | Tailwind        |
|----------------------------------|--------------|-----------------|
| Hero headline                    | 800 (black)  | font-extrabold  |
| Section headings                 | 700 (bold)   | font-bold       |
| Card headings, nav links         | 600 (semibold)| font-semibold  |
| Body copy, descriptions          | 400 (regular)| font-normal     |
| Helper/limit text                | 400 (regular)| font-normal     |

---

## Spacing scale

Use Tailwind's default spacing scale. Do not introduce custom spacing values.
Stick to multiples of 4px.

| Common values in use |
|----------------------|
| p-4 (16px)           |
| p-6 (24px)           |
| p-8 (32px)           |
| gap-4 (16px)         |
| gap-6 (24px)         |
| gap-8 (32px)         |

---

## Border radius

| Use                     | Value     | Tailwind    |
|-------------------------|-----------|-------------|
| Cards                   | 12px      | rounded-xl  |
| Buttons (primary)       | 999px     | rounded-full|
| Buttons (secondary)     | 8px       | rounded-lg  |
| Input fields            | 8px       | rounded-lg  |
| Badges / chips          | 999px     | rounded-full|
| Icon containers         | 8px       | rounded-lg  |

---

## Shadows

| Use                          | Tailwind       |
|------------------------------|----------------|
| Cards (default)              | shadow-sm      |
| Cards (hover or elevated)    | shadow-md      |
| Modals / sheets              | shadow-xl      |
| Buttons (no shadow)          | none           |

---

## CSS custom properties (for non-Tailwind use)

```css
:root {
  /* Brand */
  --color-brand-primary:   #2563EB;
  --color-brand-black:     #0F172A;
  --color-brand-ink:       #334155;
  --color-brand-mist:      #94A3B8;
  --color-brand-white:     #FFFFFF;

  /* Surface */
  --color-surface-canvas:  #FFFFFF;
  --color-surface-subtle:  #F8FAFC;
  --color-surface-card:    #FFFFFF;

  /* Border */
  --color-border-light:    #E2E8F0;
  --color-border-medium:   #CBD5E1;

  /* Blue accent */
  --color-blue-soft:       #DBEAFE;

  /* Semantic */
  --color-success:         #16A34A;
  --color-warning:         #D97706;
  --color-error:           #DC2626;
}
```

---

## Tailwind config extension

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          primary:  "#2563EB",
          black:    "#0F172A",
          ink:      "#334155",
          mist:     "#94A3B8",
          white:    "#FFFFFF",
        },
        surface: {
          canvas:   "#FFFFFF",
          subtle:   "#F8FAFC",
          card:     "#FFFFFF",
        },
        border: {
          light:    "#E2E8F0",
          medium:   "#CBD5E1",
        },
        semantic: {
          success:  "#16A34A",
          warning:  "#D97706",
          error:    "#DC2626",
          blueSoft: "#DBEAFE",
        },
      },
    },
  },
};
```

---

## Do this / avoid this

| Do this                                              | Avoid this                                           |
|------------------------------------------------------|------------------------------------------------------|
| Use brand.black for all headings and brand name      | Using light gray for any readable text               |
| Use brand.primary (blue) for primary actions only    | Scattering blue across every card and heading        |
| Use brand.ink for all body copy                      | Using brand.mist for body copy or nav items          |
| Use brand.mist only for decorative receding text     | Using grays lighter than #94A3B8 for any text        |
| Keep backgrounds white or surface.subtle only        | Introducing off-white variants that compete visually |
| Use semantic colors only for functional states       | Using green/red/amber as section or card styling     |