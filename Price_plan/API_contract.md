Here’s a small, focused API contract for “current plan + usage” that the frontend can call to know limits, remaining agreements, and when to show upgrade prompts. It follows common SaaS/usage-tracking patterns where you expose plan metadata and usage in a single, cheap endpoint. [milvus](https://milvus.io/ai-quick-reference/what-is-usagebased-pricing-in-saas)

You can add this to your API docs as `GET /api/billing/current-plan/` (or similar).

***

## Endpoint: Get current plan and usage

**Method:** `GET`  
**Path:** `/api/billing/current-plan/`  
**Auth:** Required (user must be logged in)  

### Purpose

- Tell the app:
  - which plan the current user/account is on,
  - what family it belongs to (Personal vs Enterprise),
  - how many agreements they can still seal this month,
  - what the caps are,
  - whether they are in “heavy usage” territory (for misuse nudges),
  - what upgrade options exist.

This is a *read-only* endpoint and should be cheap and cacheable.

***

### Response – top-level shape

```json
{
  "plan": {
    "id": "personal_plus",
    "family": "personal",
    "name": "Personal Plus",
    "price_currency": "GHS",
    "price_amount_monthly": 25,
    "max_agreements_per_month": 3,
    "retention_months": 24,
    "features": {
      "team_seats": 1,
      "bulk_creation": false,
      "reporting": false,
      "archive_search": false
    }
  },
  "usage": {
    "period": {
      "start": "2026-05-01",
      "end": "2026-05-31"
    },
    "sealed_agreements_this_period": 2,
    "remaining_agreements_this_period": 1,
    "is_cap_reached": false,
    "is_near_cap": false
  },
  "flags": {
    "is_personal": true,
    "is_enterprise": false,
    "business_usage_suspected": false,
    "show_upgrade_recommendation": false
  },
  "recommended_upgrades": [
    {
      "id": "personal_protect",
      "name": "Personal Protect",
      "family": "personal",
      "price_currency": "GHS",
      "price_amount_monthly": 60,
      "max_agreements_per_month": 7
    },
    {
      "id": "enterprise_standard",
      "name": "Enterprise Standard",
      "family": "enterprise",
      "price_currency": "GHS",
      "price_amount_monthly": 400,
      "max_agreements_per_month": 20
    }
  ]
}
```

***

### Field details

#### `plan`

```json
"plan": {
  "id": "personal_plus",
  "family": "personal",
  "name": "Personal Plus",
  "price_currency": "GHS",
  "price_amount_monthly": 25,
  "max_agreements_per_month": 3,
  "retention_months": 24,
  "features": {
    "team_seats": 1,
    "bulk_creation": false,
    "reporting": false,
    "archive_search": false
  }
}
```

- `id`: one of `personal_basic`, `personal_plus`, `personal_protect`, `enterprise_standard`, `enterprise_plus`.
- `family`: `"personal"` or `"enterprise"`.
- `price_currency`: `"GHS"`.
- `price_amount_monthly`: 10 / 25 / 60 / 400 / 1200 depending on plan.
- `max_agreements_per_month`: 1 / 3 / 7 / 20 / 80 (as per pricing spec).
- `retention_months`: 12 / 24 / 36 / 60 / 120.
- `features`: basic capability flags for UI:
  - `team_seats`: integer; Personal effectively uses 1, Enterprise > 1.
  - `bulk_creation`: can they run batch agreement workflows?
  - `reporting`: show the reporting UI or not.
  - `archive_search`: show archive filters or not.

***

#### `usage`

```json
"usage": {
  "period": {
    "start": "2026-05-01",
    "end": "2026-05-31"
  },
  "sealed_agreements_this_period": 2,
  "remaining_agreements_this_period": 1,
  "is_cap_reached": false,
  "is_near_cap": false
}
```

- `period`: the current billing/calendar month window.
- `sealed_agreements_this_period`: count of agreements sealed in that window.
- `remaining_agreements_this_period`: `max_agreements_per_month - sealed_agreements_this_period` (but not below 0).
- `is_cap_reached`:
  - `true` if `sealed_agreements_this_period >= max_agreements_per_month`.
- `is_near_cap`:
  - `true` when usage is “high enough” to start warning (e.g. ≥ 80% of cap).

Frontend uses:

- `remaining_agreements_this_period` to show “X agreements left this month”.
- `is_near_cap` to show a light warning.
- `is_cap_reached` to decide when to block sealing and show upgrade CTAs.

***

#### `flags`

```json
"flags": {
  "is_personal": true,
  "is_enterprise": false,
  "business_usage_suspected": false,
  "show_upgrade_recommendation": false
}
```

- `is_personal`: `plan.family === "personal"`.
- `is_enterprise`: `plan.family === "enterprise"`.
- `business_usage_suspected`:
  - computed based on heuristics (e.g., Personal account hitting cap 3 consecutive months or >15 agreements in rolling 3 months).
- `show_upgrade_recommendation`:
  - `true` when the UI should show a persistent suggestion to move up (e.g., `business_usage_suspected` or `is_cap_reached` on Personal).

This lets the frontend show a subtle banner like “You’re using Kotoku like a business; Enterprise might fit you better” without having to re-implement heuristics in JS.

***

#### `recommended_upgrades`

```json
"recommended_upgrades": [
  {
    "id": "personal_protect",
    "name": "Personal Protect",
    "family": "personal",
    "price_currency": "GHS",
    "price_amount_monthly": 60,
    "max_agreements_per_month": 7
  }
]
```

- A small list of 1–3 plan options to show as upgrade buttons.
- For example:
  - If on Basic and near cap → suggest Plus and Protect.
  - If on Protect and business usage suspected → suggest Enterprise Standard.
- Frontend uses these to render plan cards/CTAs without hardcoding pricing numbers.

***

### Error cases

**401 Unauthorized**

- If user is not authenticated.

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**500 / generic error**

- If billing metadata can’t be retrieved.
- Frontend should:
  - hide upgrade prompts,
  - allow core flows to continue (not a hard dependency to use the app).

***

### Suggested usage pattern (frontend)

- Call `GET /api/billing/current-plan/`:
  - on app startup,
  - on entering the “New agreement” flow,
  - after sealing an agreement (to refresh `remaining_agreements_this_period`).

- Use:
  - `usage.remaining_agreements_this_period` to display something like:
    - “Agreements this month: 2 of 3 used”.
  - `usage.is_cap_reached` and `flags.is_personal` to:
    - block sealing and show the “cap reached” message.
  - `flags.show_upgrade_recommendation` + `recommended_upgrades` to:
    - show non-blocking “Upgrade” prompts on home, vault, and pricing screens.

This pattern is similar to how quota‑based APIs and SaaS products expose plan/usage info for clients to decide when to upsell or throttle, while keeping all official logic on the backend. [speakeasy](https://www.speakeasy.com/api-design/rate-limiting)

You can next draft the **Django serializer + DRF view** skeleton that returns exactly this shape, ready for Samuel to plug into the billing logic.