# Consent Hardening

Status date: 2026-06-18

This guide defines Kotoku's production consent model: bilateral consent remains participant-driven, but counterparties can confirm through a lightweight view-only web screen instead of installing the mobile app.

## Product Rule

- The agreement creator may request consent codes.
- Each party receives a separate OTP by SMS.
- Each party must submit only their own OTP.
- The creator must not confirm consent for the counterparty.
- The agreement can be sealed only after every required party has granted consent.
- The sealed agreement is then transferred to Vault through the existing seal flow.

## Counterparty Consent Link

When consent codes are requested, each SMS should contain:

- The OTP.
- A signed, expiring consent link.
- Clear instruction that the party should review the agreement and enter their own code.

Example:

```text
Your Kotoku consent code is 12345678. Review and confirm: https://kotoku.app/consent/<token>. Valid for 10 minutes.
```

## Public Consent Screen

The public screen must be view-only:

- Shows agreement title and scenario.
- Shows parties and roles.
- Shows key agreement details.
- Shows the current party's phone/role.
- Provides one OTP field for that party only.
- Provides no edit, delete, upload, seal, or vault actions.

## Backend Contract

Add unauthenticated public endpoints protected by a signed token:

- `GET /api/consent-links/{token}/`
  - Validates token.
  - Returns read-only agreement summary, parties, field data, party role/phone, and consent status.
- `POST /api/consent-links/{token}/confirm/`
  - Validates token.
  - Confirms only the token party's OTP.
  - Returns updated consent record and `all_consented`.

The token must include:

- `agreement_id`
- `party_id`
- `purpose`

The token must not grant consent by itself. OTP is still required.

## Security Rules

- Token must be signed and expiring.
- OTP must remain hashed in the database.
- Public response must not expose ID numbers, evidence URLs, storage keys, or internal audit metadata.
- Public confirm must not require full app authentication, but it must require the OTP.
- Public confirm must only operate on the party encoded in the signed token.
- Reissuing OTP may keep the same link semantics, but only the latest ungranted OTP record should confirm.

## UX Checklist

- [x] Creator can request consent codes from the mobile Consent tab.
- [x] Party B can consent without installing the app.
- [x] Public consent page is read-only.
- [x] Public confirm requires Party B's OTP.
- [x] Creator cannot submit Party B's code from the mobile app.
- [ ] Mobile Consent tab polls or refreshes status after Party B confirms.
- [ ] Creator sees “Ready to seal” only after backend `all_consented` is true.
- [ ] Manual QA covers Party A app confirm + Party B public link confirm + seal + Vault.

## Implementation Order

1. Add signed consent-link helpers on the backend.
2. Include public consent link in OTP SMS.
3. Add public detail and confirm endpoints.
4. Add a public web route `/consent/[token]`.
5. Keep mobile participant-driven confirmation unchanged.
6. Add consent status refresh/polling on the creator's Consent tab.

