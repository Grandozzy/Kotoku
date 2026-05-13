Here is a Claude-ready pricing copy + brief that bakes in all the constraints, caps, and edge cases. You can drop this into a `pricing_page_section.md` (or similar) and let Claude Code turn it into components.

***

## Context for Claude (do not show to users)

- Product: Kotoku – mobile-first agreement and evidence app (React Native + Django).
- Market: Ghana first, then similar markets.
- Billing: GHS, mobile-money friendly, prices below are monthly.
- Two families:
  - **Personal**: Individuals, side-hustlers, very small landlords.
  - **Enterprise**: Dealers, agencies, landlord portfolios, platforms.
- Core constraint: SMS (OTP) is the main marginal cost. Must avoid heavy usage on cheap plans.
- Non-goal: Don’t talk about GB, storage classes, or internal cost in the UI.

Claude: treat everything under “User-facing copy” as content to render, and everything under “Implementation notes” as constraints for behavior, feature flags, and edge cases.

***

## User-facing copy

### Section: Simple plans for safer agreements

Headline:  
**Protect your deals with clear, affordable plans**

Subheading:  
Whether you’re buying a single car, renting out one room, or managing a whole lot of deals every month, Kotoku has a plan that protects your agreements without stressing your pocket.

Short bullet intro:

- Personal plans are for **individuals** who need to protect a few important deals.
- Enterprise plans are for **business use** with **higher volume** and **team access**.
- All plans include: sealed agreements, photo and ID evidence, and downloadable PDFs.

***

### Personal plans (for individuals)

Cards for three plans under the “Personal” tab.

#### Personal Basic

Label: **Personal Basic**  
Tagline: **Protect one important deal each month**

Highlights:

- Up to **1 sealed agreement per month**
- Keep each agreement for **12 months**
- Photos, IDs, and voice notes included
- Downloadable PDF summary for each sealed agreement

Price row:

- **10 GHS / month**

Helper text:

> Perfect if you just want to protect a single serious transaction – like a used car purchase or a room rental – and keep a clear record in case anything comes up later.

Limit text (small, under card):

> Personal Basic is for individuals. If you regularly seal more than 1 agreement per month, you’ll need to upgrade to a higher plan.

***

#### Personal Plus

Label: **Personal Plus**  
Tagline: **Ideal for side hustles and small landlords**

Highlights:

- Up to **3 sealed agreements per month**
- Keep each agreement for **24 months**
- Photos, IDs, and voice notes included
- Priority PDF generation for sealed agreements

Price row:

- **25 GHS / month**

Helper text:

> Made for people who handle a few deals every month – small traders, agents, or landlords who want proof of what was agreed, without jumping into a full business plan.

Limit text:

> Personal Plus is still for individual use. For higher volume, teams, or ongoing business operations, see Enterprise plans.

***

#### Personal Protect

Label: **Personal Protect**  
Tagline: **For serious individual dealmakers**

Highlights:

- Up to **7 sealed agreements per month**
- Keep each agreement for **36 months**
- Photos, IDs, and voice notes included
- Fast PDF generation and export
- Priority in-app support

Price row:

- **60 GHS / month**

Helper text:

> For people who do deals regularly – such as active car traders or serious landlords – and need their agreements and evidence available for longer.

Limit text:

> Personal Protect is designed for high-value personal use. If you’re running a dealership, agency, or property portfolio, you belong on an Enterprise plan.

***

### Enterprise plans (for businesses)

Cards under the “Enterprise” tab.

#### Enterprise Standard

Label: **Enterprise Standard**  
Tagline: **Run your operation on solid agreements**

Highlights:

- Around **20 sealed agreements per month** included
- Up to **3 team members**
- Keep agreements for **5 years**
- Bulk PDF exports and case packs
- Basic reporting (per month, per team member, per scenario)
- Email + chat support

Price row:

- **400 GHS / month**

Helper text:

> Built for small used-car dealers, agencies, and landlord groups who need to protect every deal, work as a team, and be able to pull records quickly when something goes wrong.

CTA line:

> Need more volume or integrations? Contact us about Enterprise Plus.

***

#### Enterprise Plus

Label: **Enterprise Plus**  
Tagline: **For high-volume dealers and platforms**

Highlights:

- Around **80 sealed agreements per month** included
- Up to **10 team members**
- Keep agreements for **10 years**
- Archive search and advanced filters
- Full audit bundles and exportable case packs
- Priority support with SLA
- Optional integration/API access (pilot)

Price row:

- **1,200 GHS / month**

Helper text:

> Designed for larger dealers, property managers, cooperatives, and marketplaces that need structured records, long-term archives, and faster support.

CTA line:

> Talk to us for custom volume or integration needs.

***

### Add-ons (for when you grow)

Short section beneath the plans.

Headline: **Add just what you need**

Bullets:

- **Extra agreements**  
  Hit your monthly limit? Buy **extra agreement packs** to cover peak months without changing your main plan.

- **Longer storage**  
  Keep a specific agreement longer than your plan’s default by adding **extra storage years**.

- **Case packs for disputes**  
  Generate a **fully bundled case pack** (agreement, timestamps, and evidence log) for use in mediation or dispute handling.

Sentence:

> Add-ons are available on both Personal and Enterprise plans, with clear pricing shown in-app before you confirm any purchase.

***

### Small print / fair use (visible but compact)

> **Fair use and business usage**  
> Personal plans are for individual use only. If you regularly seal more agreements than your Personal plan allows, or run your day-to-day business on Kotoku, we may ask you to switch to an Enterprise plan so we can keep SMS, storage, and support sustainable for everyone.

***

## Implementation notes (for Claude / dev only, not user-facing)

These are constraints and edge cases the UI and backend should respect.

### 1. Caps and enforcement – Personal

- Personal Basic:
  - Max **1 sealed agreement per calendar month**.
- Personal Plus:
  - Max **3 sealed agreements per month**.
- Personal Protect:
  - Max **7 sealed agreements per month**.

Edge case logic (client + server):

- When the user tries to seal beyond the monthly cap:
  - Block sealing.
  - Show a clear message:
    - “You’ve reached your X agreement limit for this month on [Tier]. Upgrade to a higher plan or wait until next month.”
  - Offer:
    - CTA to upgrade, and/or
    - CTA to purchase an extra agreement pack (once add-ons are implemented).

- Unused allowances **do not roll over** to the next month.

- All Personal tiers:
  - No team seats.
  - No bulk upload/batch agreement creation.
  - No advanced reporting.
  - No archive search across large history.

### 2. Caps and enforcement – Enterprise

- Enterprise Standard:
  - Soft cap: ~20 sealed agreements/month.
  - Enterprise Plus:
    - Soft cap: ~80 sealed agreements/month.

Soft cap behavior:

- Do not hard-block at Enterprise caps initially.
- Instead:
  - Track usage vs included agreements.
  - If customers consistently exceed caps, trigger:
    - in-product “usage high” notice,
    - internal alert for future plan adjustment.

### 3. Plan detection and business misuse

On the backend:

- Track:
  - agreements sealed per month per account,
  - number of months above cap,
  - IP/device patterns,
  - whether the account has multiple recurring counterparties.

Business misuse heuristic (not strict, but for prompt):

- If a Personal account:
  - hits its cap for **3 months in a row**, or
  - seals more than **15 agreements over 3 months** on any Personal tier,

Then:

- Show a banner:
  - “You’re using Kotoku like a business. To keep things fair and sustainable, please switch to an Enterprise plan designed for ongoing operations.”
- Optionally:
  - enforce a maximum cumulative agreement count on Personal (e.g. 100 lifetime), after which **Enterprise is required**.

### 4. Pricing alignment and labels

- The **only prices shown in UI** are:
  - 10 / 25 / 60 GHS per month for Personal.
  - 400 / 1,200 GHS per month for Enterprise.
- No mention of:
  - storage size in GB,
  - internal cost structure,
  - SMS counts.

The benefits are expressed as:
- number of agreements,
- retention period,
- features (PDF, team seats, reporting).

### 5. Add-ons initial behavior

Until add-ons are fully implemented:

- If the user hits monthly agreement cap on Personal:
  - Only show upgrade path (no extra pack).
- When add-ons are active:
  - Show clear price per extra agreement pack before confirmation.
  - Never auto-purchase add-ons.

### 6. Edge cases

- User downgrading from a higher plan to a lower plan:
  - Existing sealed agreements keep their original retention duration.
  - The new cap applies to **future monthly usage only**, not historically sealed agreements.
- User upgrading mid-month:
  - New cap applies immediately for that month.
  - Do not pro-rate caps in the first version; keep it simple: “Upgrade unlocks full new cap for current month.”
- Plan change effective date:
  - Apply plan change immediately upon successful payment confirmation.

***
