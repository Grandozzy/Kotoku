# Kotoku Coding Rules

These rules are intended for Codex, Claude Code, and human contributors working on Kotoku.

## General Rules

- Fix root causes, not symptoms.
- Keep changes minimal, readable, and localized to the requested behavior.
- Do not introduce new architectural patterns without updating the relevant architecture document.
- Preserve existing API compatibility unless a migration plan is documented.
- Prefer small feature-scoped helpers over large screen-level logic.
- Avoid silent fallback behavior in critical flows; fail explicitly with actionable errors.
- Add or update tests when a change affects contract logic, retry behavior, or navigation gates.

## Frontend Rules

- Screens in `app/` compose UI and call hooks; business logic belongs in `src/features/`.
- API calls belong in `src/api/`; components and screens must not call raw HTTP directly.
- Server state belongs in TanStack Query or API-backed hooks; avoid duplicating backend state in UI stores.
- Critical multi-step flows must have explicit states, not boolean-only loading flags.
- Navigation gates must depend on confirmed domain state, not only optimistic UI state.
- Mobile file handling must use native Expo APIs where React Native browser polyfills are incomplete.
- Web and mobile may differ in file acquisition, but they must send the same backend upload contract.

## Evidence Upload Rules

- Measure, hash, upload, and confirm the same bytes.
- Do not call confirm unless the storage upload succeeded.
- Treat timeout as failure, never as success.
- Treat backend verification mismatches as non-retryable for the current file.
- Let users replace a rejected file instead of retrying the same invalid payload.
- Recover from lost confirm responses by refetching confirmed evidence.
- Never parse S3 presigned URLs or expose storage credentials in logs.
- Log upload phase and non-secret diagnostics for supportability.

## Backend Rules

- Keep storage verification fail-closed.
- Return controlled domain errors for storage failures, not raw infrastructure exceptions.
- Prefer structured error codes over frontend string matching.
- Make externally retried operations idempotent when a successful first attempt may have lost its response.
- Log expected vs actual verification metadata without logging secrets, tokens, signatures, or full presigned URLs.

## Documentation Rules

- Update implementation guides when a production contract changes.
- Keep checklists actionable, with owners implied by file paths and platform.
- Mark completed items only after code and validation exist.
- Document manual QA steps for mobile-device-only or browser-CORS behavior that automated tests cannot fully cover.

