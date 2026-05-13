# KOTOKU_PRICING_PAGE_SECTION

> For Claude Code:  
> - This file lives in the repo root.  
> - Use the “User-facing copy” sections to build the pricing page UI.  
> - Use the “Implementation notes” section as behavioral and edge-case constraints (do not show to users).  

## User-facing copy

### Section: Simple plans for safer agreements

**Headline**  
Protect your deals with clear, affordable plans

**Subheading**  
Whether you’re buying a single car, renting out one room, or managing many deals every month, Kotoku has a plan that protects your agreements without stressing your pocket.

**Intro bullets**

- Personal plans are for **individuals** who need to protect a few important deals.
- Enterprise plans are for **business use** with **higher volume** and **team access**.
- All plans include: sealed agreements, photo and ID evidence, and downloadable PDFs.

---

### Personal plans (for individuals)

Show these as cards under a “Personal” tab or section.

#### Personal Basic

- **Name:** Personal Basic  
- **Tagline:** Protect one important deal each month  

**Highlights**

- Up to **1 sealed agreement per month**
- Keep each agreement for **12 months**
- Photos, IDs, and voice notes included
- Downloadable PDF summary for each sealed agreement

**Price**  
**10 GHS / month**

**Helper text**

> Perfect if you just want to protect a single serious transaction – like a used car purchase or a room rental – and keep a clear record in case anything comes up later.

**Limit note (small text)**

> Personal Basic is for individuals. If you regularly seal more than 1 agreement per month, you’ll need to upgrade to a higher plan.

---

#### Personal Plus

- **Name:** Personal Plus  
- **Tagline:** Ideal for side hustles and small landlords  

**Highlights**

- Up to **3 sealed agreements per month**
- Keep each agreement for **24 months**
- Photos, IDs, and voice notes included
- Priority PDF generation for sealed agreements

**Price**  
**25 GHS / month**

**Helper text**

> Made for people who handle a few deals every month – small traders, agents, or landlords who want proof of what was agreed, without jumping into a full business plan.

**Limit note**

> Personal Plus is still for individual use. For higher volume, teams, or ongoing business operations, see Enterprise plans.

---

#### Personal Protect

- **Name:** Personal Protect  
- **Tagline:** For serious individual dealmakers  

**Highlights**

- Up to **7 sealed agreements per month**
- Keep each agreement for **36 months**
- Photos, IDs, and voice notes included
- Fast PDF generation and export
- Priority in-app support

**Price**  
**60 GHS / month**

**Helper text**

> For people who do deals regularly – such as active car traders or serious landlords – and need their agreements and evidence available for longer.

**Limit note**

> Personal Protect is designed for high-value personal use. If you’re running a dealership, agency, or property portfolio, you belong on an Enterprise plan.

---

### Enterprise plans (for businesses)

Show these as cards under an “Enterprise” tab or separate section.

#### Enterprise Standard

- **Name:** Enterprise Standard  
- **Tagline:** Run your operation on solid agreements  

**Highlights**

- Around **20 sealed agreements per month** included
- Up to **3 team members**
- Keep agreements for **5 years**
- Bulk PDF exports and case packs
- Basic reporting (by month, team member, and scenario)
- Email + chat support

**Price**  
**400 GHS / month**

**Helper text**

> Built for small used-car dealers, agencies, and landlord groups who need to protect every deal, work as a team, and be able to pull records quickly when something goes wrong.

**CTA line**

> Need more volume or integrations? Enterprise Plus is built for that.

---

#### Enterprise Plus

- **Name:** Enterprise Plus  
- **Tagline:** For high-volume dealers and platforms  

**Highlights**

- Around **80 sealed agreements per month** included
- Up to **10 team members**
- Keep agreements for **10 years**
- Archive search and advanced filters
- Full audit bundles and exportable case packs
- Priority support with SLA
- Optional integration/API access (pilot)

**Price**  
**1,200 GHS / month**

**Helper text**

> Designed for larger dealers, property managers, cooperatives, and marketplaces that need structured records, long-term archives, and faster support.

**CTA line**

> Talk to us if you need custom volume or integrations.

---

### Add-ons (for when you grow)

**Headline**  
Add just what you need

**Bullets**

- **Extra agreements**  
  Hit your monthly limit? Buy **extra agreement packs** to cover peak months without changing your main plan.

- **Longer storage**  
  Keep a specific agreement longer than your plan’s default by adding **extra storage years**.

- **Case packs for disputes**  
  Generate a **fully bundled case pack** (agreement, timestamps, and evidence log) for use in mediation or dispute handling.

**Note**

> Add-ons are available on both Personal and Enterprise plans, with clear pricing shown in-app before you confirm any purchase.

---

### Fair use and business usage (small print)

> **Fair use and business usage**  
> Personal plans are for individual use only. If you regularly seal more agreements than your Personal plan allows, or run your day-to-day business on Kotoku, we may ask you to switch to an Enterprise plan so we can keep SMS, storage, and support sustainable for everyone.

---

## Implementation notes (for Claude / dev only – do not show users)

### Plan limits – Personal

- Personal Basic:
  - Max **1 sealed agreement per calendar month**.
- Personal Plus:
  - Max **3 sealed agreements per calendar month**.
- Personal Protect:
  - Max **7 sealed agreements per calendar month**.

**Behavior when cap is reached**

- When a user attempts to seal an agreement beyond the monthly cap:
  - The API should reject the seal attempt with a specific error code (e.g. `PLAN_CAP_REACHED`).
  - The app should show a friendly message and CTA:
    - “You’ve reached your X agreement limit for this month on [Tier]. Upgrade to a higher plan or wait until next month.”
  - If/when add-ons are implemented, an additional CTA may offer to purchase an extra agreement pack.

- Unused agreements in a month **do not roll over**.

**Feature limitations for Personal (all tiers)**

- No team members / shared accounts.
- No bulk or batch agreement creation.
- No advanced reporting or dashboards.
- No archive-wide search across many agreements (basic filtering/search in the vault is fine).

---

### Plan limits – Enterprise

- Enterprise Standard:
  - Soft cap: ~20 sealed agreements/month.
- Enterprise Plus:
  - Soft cap: ~80 sealed agreements/month.

**Soft cap behavior**

- Do not hard-block at Enterprise caps initially.
- Track usage vs included agreements.
- If a customer consistently exceeds caps:
  - Show a non-blocking “heavy usage” notice.
  - Optionally alert internally for future plan adjustment or upsell discussions.

---

### Business misuse heuristics (Personal)

Backend should track:

- Sealed agreements per month per account.
- Consecutive months at or near cap.
- Lifetime total agreements.
- Whether multiple counterparties and phone numbers repeat in ways typical of business usage.

Suggested rules:

- If a Personal account hits its monthly cap for **3 months in a row**, OR
- Seals more than **15 agreements in any rolling 3-month window**,

Then:

- Show a banner or modal on login and vault:

  > “You’re using Kotoku like a business. To keep things fair and sustainable, please switch to an Enterprise plan designed for ongoing operations.”

- Optionally:
  - Enforce a lifetime Personal limit (for example, maximum of 100 sealed agreements total), after which only Enterprise plans are allowed.

These checks should not silently block users the first time. They are a nudge + eventual guardrail for clear business misuse.

---

### Pricing labels and what not to show

- Show **only** these public prices:
  - Personal: 10 / 25 / 60 GHS per month.
  - Enterprise: 400 / 1,200 GHS per month.
- Do **not** show:
  - storage in GB,
  - SMS counts,
  - internal cost/margin numbers.

In UI, always express value as:

- number of agreements,
- retention period,
- and features (PDF exports, team seats, reporting, support level).

---

### Add-ons

Until add-ons are live:

- When user hits cap on a Personal tier:
  - Show only upgrade CTA or “wait until next month”.
- Once add-ons exist:
  - Show clear price per extra agreement pack.
  - Require explicit confirmation; never auto-purchase add-ons.

---

### Plan change logic

- **Upgrade mid-month**:
  - Apply new plan immediately.
  - Unlock full new cap for the current month (no partial pro-rating of caps in v1).
- **Downgrade**:
  - Existing sealed agreements keep their original retention.
  - New, lower caps apply only to future months.
- **Effective date**:
  - Treat plan changes as effective when payment returns success from the billing provider.
