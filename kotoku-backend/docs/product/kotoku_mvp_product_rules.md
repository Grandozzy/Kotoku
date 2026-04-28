# Kotoku MVP Product Rules

## 1. Scenarios

### 1.1 Scenario labels and wording

**Scenario A: Used vehicle sale**

- **ID:** `used_vehicle_sale`
- **App label:** `Used vehicle sale`
- **Short description (UI):** `Record the sale of a used car or motorbike between two people.`
- **Helper text (help / tooltip):**
  - `Use this when you are buying or selling a used vehicle privately. Kotoku helps you capture the details of the vehicle, the agreed price and payment terms, and evidence such as photos and IDs so both sides have a record of what was agreed.`

**Scenario B: Room or house rental**

- **ID:** `rental_agreement`
- **App label:** `Room or house rental`
- **Short description (UI):** `Record a simple rent agreement between landlord and tenant.`
- **Helper text (help / tooltip):**
  - `Use this when you agree to rent a room, apartment, or house. Kotoku helps you record the property details, rent amount, deposit, and basic responsibilities, plus IDs and photos, so there is proof of what both sides agreed.`

> **Note on extensibility:** Scenario IDs should remain generic (`rental_agreement`, not `room_rental`) because the template system is designed to serve any agreement type through configuration. New scenarios are added by introducing new `ScenarioTemplate` records, not new app code.


## 2. Template Field Lists (MVP)

The field lists below define the **minimum viable** information captured per scenario. They are not full legal contracts; they are practical, evidence-backed records tailored for informal transactions.

---

### 2.1 Used vehicle sale – fields

#### 2.1.1 Parties

- `seller_full_name` (string, required)
- `seller_phone` (string, required)
- `seller_id_type` (enum: `ghana_card`, `passport`, `other`; required)
- `seller_id_number` (string, required; masked in UI after save)
- `buyer_full_name` (string, required)
- `buyer_phone` (string, required)
- `buyer_id_type` (enum: `ghana_card`, `passport`, `other`; required)
- `buyer_id_number` (string, required; masked in UI after save)

#### 2.1.2 Vehicle details

- `vehicle_type` (enum: `car`, `motorbike`, `other`; required)
- `make` (string, required; e.g., `Toyota`)
- `model` (string, required; e.g., `Corolla`)
- `year_of_manufacture` (year, optional but recommended)
- `registration_number` (string, required)
- `vin_or_chassis` (string, optional but recommended)
- `current_mileage` (number, optional)
- `colour` (string, optional)

#### 2.1.3 Ownership and documents

- `seller_is_owner_confirmed` (boolean, required)
- `vehicle_not_under_finance_confirmed` (boolean, optional)
- `registration_documents_available` (boolean, optional)
- `roadworthy_valid` (boolean, optional)

#### 2.1.4 Condition and known issues

- `overall_condition` (enum: `excellent`, `good`, `fair`, `needs_repairs`; optional)
- `known_mechanical_issues` (string, optional)
- `accident_history_known` (enum: `yes`, `no`, `unknown`; optional)
- `accident_history_notes` (string, optional)
- `included_items` (string, optional; e.g., `spare tyre, jack, tools`)

#### 2.1.5 Price and payment

- `total_price_amount` (number, required)
- `total_price_currency` (enum, default `GHS`)
- `payment_type` (enum: `cash`, `mobile_money`, `bank_transfer`, `other`; required)
- `payment_timing` (enum: `on_the_spot`, `part_now_part_later`, `other`; required)
- `instalment_terms` (string, optional; required if `payment_timing = part_now_part_later`)

#### 2.1.6 Hand-over details

- `agreement_date` (date, required)
- `handover_date` (date, optional; default = `agreement_date`)
- `handover_location` (string, optional; town/area)
- `handover_odometer_reading` (number, optional)

#### 2.1.7 Evidence slots (linked to evidence module)

Minimum required evidence for `used_vehicle_sale`:

- `vehicle_photo_front` (image)
- `vehicle_photo_back` (image)
- `vehicle_photo_dashboard_or_odometer` (image)
- `seller_id_photo` (image)
- `buyer_id_photo` (image)

Optional evidence:

- `vehicle_photo_extra[]` (0–N additional images)
- `vehicle_defect_photos[]` (optional)
- `seller_voice_summary` (audio)
- `buyer_voice_summary` (audio)

---

### 2.2 Room / house rental – fields

#### 2.2.1 Parties

- `landlord_full_name` (string, required)
- `landlord_phone` (string, required)
- `landlord_id_type` (enum: `ghana_card`, `passport`, `other`; required)
- `landlord_id_number` (string, required)
- `tenant_full_name` (string, required)
- `tenant_phone` (string, required)
- `tenant_id_type` (enum: `ghana_card`, `passport`, `other`; required)
- `tenant_id_number` (string, required)

#### 2.2.2 Property details

- `property_type` (enum: `room`, `apartment`, `house`, `compound_room`; required)
- `property_address` (string, required; house no/area/town)
- `property_description` (string, optional; e.g., `Single room with shared bath`)

#### 2.2.3 Tenancy terms

- `rent_amount` (number, required)
- `rent_currency` (enum, default `GHS`)
- `rent_period` (enum: `per_month`, `per_year`, `other`; required)
- `deposit_amount` (number, required; can be 0)
- `tenancy_start_date` (date, required)
- `tenancy_end_date` (date, optional) or `initial_term_months` (number, optional)
- `payment_due_day` (string, optional; e.g., `1st of each month`)
- `late_payment_grace_period_days` (number, optional)

#### 2.2.4 Responsibilities

- `utilities_responsibility` (string, optional; e.g., `Tenant pays ECG and water`)
- `repairs_responsibility` (string, optional; e.g., `Landlord handles structural repairs; tenant handles minor fixes`)
- `house_rules` (string, optional; noise, visitors, pets, etc.)
- `early_termination_grounds` (string, optional)
- `notice_period_for_termination` (string, optional; e.g., `1 month`)

#### 2.2.5 Deposit and hand-over

- `deposit_paid` (boolean, required)
- `deposit_paid_amount` (number, required if `deposit_paid = true`)
- `move_in_condition` (enum: `new`, `good`, `worn`, `needs_repairs`; optional)
- `inventory_list` (string, optional; fixtures and items provided)

#### 2.2.6 Evidence slots

Minimum required evidence for `rental_agreement`:

- `property_photo_entrance` (image)
- `property_photo_interior` (image)
- `property_photo_bath_or_toilet` (image, if part of rental)
- `landlord_id_photo` (image)
- `tenant_id_photo` (image)

Optional evidence:

- `defect_photos[]` (e.g., existing damage)
- `landlord_voice_summary` (audio)
- `tenant_voice_summary` (audio)


## 3. MVP Policy Rules (Developer Language)

These rules describe how the system must behave for MVP across all scenarios.

### 3.1 Identity and accounts

- A **Kotoku account** is keyed by a phone number and OTP-based login.
- A **party** in an agreement is a structured record with `full_name`, `phone`, and `id` fields.
- At least two parties are required for all agreements.
- At least one party must match the logged-in user's phone number.

### 3.2 Evidence minimums for `ready_to_seal`

For an agreement to be marked `ready_to_seal` by backend validation:

**Common (all scenarios):**
- At least one ID photo attached for each party.

**Used vehicle sale (`used_vehicle_sale`):**
- At least 3 vehicle photos in total (front, back, and dashboard/odometer).
- If registration document photo is missing, the agreement is still valid but flagged `registration_evidence_missing = true`.

**Rental agreement (`rental_agreement`):**
- At least 2 property photos (entrance + at least one interior).
- If `deposit_amount > 0`: at least 1 photo documenting move-in condition (any interior or defect photo qualifies).

> Evidence minimums are defined at the level that makes the evidence pack useful for dispute resolution — not so high that capture becomes a barrier, not so low that the pack is worthless.

### 3.3 Consent and sealing

- Each agreement has a lifecycle state: `draft` → `ready_to_seal` → `sealed`.
- Sealing requires a **bilateral OTP** flow:
  - OTP A: sent to the logged-in user (initiator party).
  - OTP B: sent to the other main party's phone.
- OTP validity and retries:
  - Each OTP is valid for **10 minutes**.
  - If a party enters a wrong code 3 times, their OTP is invalidated and a new one must be requested.
- Once both OTPs are confirmed and backend validation passes, the backend transitions the agreement to `sealed` and persists a seal snapshot (state at seal time).
- After `sealed`, core fields and evidence links are immutable; only annotations and reopen flows can add new information.

### 3.4 Editing and draft rules

- Draft agreements are editable only by the initiating user.
- Drafts can be edited until one of the following:
  - the agreement is sealed,
  - the draft is explicitly cancelled,
  - or it expires by policy (no expiry in MVP).
- Sealed agreements cannot be edited; only comments, annotations, or dispute records can be added.

### 3.5 Vault and retention

- All sealed agreements are visible in the **vault** of all parties identified by phone number.
- **Free retention: 1–2 months from `sealed_at`** (configurable; default 2 months for MVP).
- After the free retention window, the user must pay to keep the agreement accessible in the vault.
- Unpaid agreements transition to `expired` state in the UI but are not physically deleted in MVP.
- PDF export is available for all `sealed` agreements; generation is asynchronous.

### 3.6 Conflict and error policies

- Permanent backend errors (e.g., `409 Conflict`, `404 Not Found` for stale IDs) should mark local sync items as `failed_permanent` and stop retrying.
- Duplicate agreement detection (same parties, same subject) is deferred to post-MVP; in MVP the backend allows duplicate drafts without restriction.


## 4. Acceptance Criteria for Core Flows

Acceptance criteria define when a flow is done. Use them directly in tickets and QA scripts.

### 4.1 Auth & OTP (login / account bootstrap)

**Flow name:** Login with phone number and OTP

- Given I enter a valid phone number and tap `Get code`, then:
  - the app calls `POST /auth/send-otp` exactly once,
  - I see a screen to enter the code, showing my phone number.
- Given a code is sent, when I enter the correct code within 10 minutes, then:
  - the app calls `POST /auth/verify-otp`,
  - I am logged in and see the home screen,
  - a session token is stored securely on the device.
- Given I enter an incorrect code 3 times, then:
  - I see a clear error that the code is invalid or expired,
  - I am offered an action to request a new code,
  - no partial session is created.
- Given I close and reopen the app within the token lifetime, then:
  - I am still logged in,
  - I do not see the OTP screen again unless I explicitly log out.

### 4.2 Create used vehicle sale draft

**Flow name:** Create a used vehicle sale agreement draft

- From the home screen, when I tap `New agreement` and choose `Used vehicle sale`, then:
  - a new draft is created, and
  - I see step 1 with the correct scenario label and description.
- When I fill in mandatory fields for parties, vehicle details, and price, then:
  - moving to the next step saves my data,
  - if I close and reopen the app, I can resume the draft from the drafts list.
- If any mandatory field is missing on a step, then:
  - the app prevents moving forward from that step,
  - I see a clear, field-specific error message.

### 4.3 Attach evidence (photos + IDs)

**Flow name:** Attach evidence to a draft

- On the evidence step for a used vehicle sale, I see slots for:
  - front and back vehicle photos,
  - dashboard/odometer photo,
  - seller ID photo,
  - buyer ID photo.
- When I tap an empty photo slot:
  - the app asks for camera/gallery permission (first time only),
  - I can take a photo or pick from gallery,
  - the chosen photo appears as a thumbnail in the slot.
- If I lose network after taking a photo, then:
  - the thumbnail stays visible in the UI,
  - the app marks the photo as `waiting to upload`,
  - when network returns, the app retries upload without losing the attachment.
- If I try to proceed to the review step without meeting the minimum evidence rules, then:
  - the app blocks progression,
  - I see a message explaining what is missing (e.g., `Add at least 3 vehicle photos and one ID per person`).

### 4.4 Review and bilateral consent (sealing)

**Flow name:** Review and seal an agreement

- On the review step, I see a read-only summary of:
  - party details,
  - vehicle/property details,
  - key terms (price, rent, dates),
  - evidence counts (e.g., `5 photos`, `2 ID photos`).
- When I tap `Request codes`:
  - OTPs are requested for both parties,
  - the UI shows two separate status indicators (`Your code`, `Other party's code`).
- When I enter my own code correctly, then:
  - my status changes to `Confirmed`.
- When the other party's code is confirmed, then:
  - their status changes to `Confirmed`.
- Only when both statuses are `Confirmed`, then:
  - the `Seal agreement` button becomes enabled,
  - tapping it sends a seal request to the backend.
- Once the backend responds with `sealed`:
  - the agreement disappears from the `Drafts` list,
  - the agreement appears in the vault list,
  - any attempt to edit core fields is blocked,
  - the UI clearly shows the `Sealed` state.

### 4.5 Vault view and PDF export

**Flow name:** Find a sealed agreement and export PDF

- When I open the vault tab, then:
  - I see a list of sealed agreements,
  - each item shows scenario type, seal date, and counterparty name.
- When I tap a sealed agreement, then:
  - I see a read-only detail view with key fields and evidence thumbnails.
- When I tap `Get PDF`:
  - if a PDF already exists, the OS share dialog appears,
  - if a PDF does not yet exist, I see a `Preparing PDF` state while generation runs.
- If PDF generation fails, then:
  - I see a clear error message,
  - I have a `Try again` option.


## 5. How to Use this Document

- **Backend:** Map scenario IDs and fields to `ScenarioTemplate` model and seed data. Implement `validate`, `seal`, and evidence minimum checks per scenario. Enforce lifecycle rules and OTP behavior per policy.
- **Frontend:** Use scenario labels and helper text in UI. Build dynamic forms from these field lists. Enforce client-side validation that mirrors backend rules. Use acceptance criteria as test and demo checklists.
- **Product / QA:** Turn each flow's acceptance criteria into test cases. Confirm behavior in staging before pilot.
