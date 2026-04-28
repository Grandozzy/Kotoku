# Kotoku Frontend Architecture Note

## Overview

Kotoku's frontend will be built in React Native using Expo managed workflow as the primary mobile client, delivered alongside a companion React web admin dashboard. This document sets the technical architecture, folder structure, state management approach, offline posture, and component model for the Kotoku frontend. It is intended to guide Yaw's development while Samuel works on the Django backend.

The React Native + Expo managed workflow is the recommended starting point for most new mobile products in 2026 because it eliminates unnecessary native configuration complexity, covers the majority of mobile app requirements including camera access, secure storage, push notifications, and biometrics, and allows a single developer to move quickly without iOS or Android platform expertise. [leanware](https://www.leanware.co/insights/react-native-vs-expo)

## Stack

| Layer | Technology | Why |
|---|---|---|
| Mobile app | React Native + Expo SDK | Cross-platform, fast iteration, managed modules, camera, storage [leanware](https://www.leanware.co/insights/react-native-vs-expo) |
| Web admin dashboard | React + Vite | Lightweight, fast, same component knowledge as React Native |
| Navigation | Expo Router | File-based, URL-aware, same structure for mobile and web [expo](https://expo.dev/blog/expo-app-folder-structure-best-practices) |
| State management | Zustand | Minimal boilerplate, predictable, works cleanly with async flows |
| Server state / data fetching | TanStack Query (React Query) | Cache, retry, sync states, offline-aware [linkedin](https://www.linkedin.com/posts/punith-manthri-ba15b4216_reactnative-offlinefirst-mobiledevelopment-activity-7410268082029588480-thH9) |
| Local persistence | SQLite via expo-sqlite | Offline draft storage, pending sync queue [relevant](https://relevant.software/blog/react-native-offline-first/) |
| Forms | React Hook Form | Efficient re-renders, schema-driven validation |
| Validation | Zod | TypeScript-first, shares types across frontend and API contract |
| Styling | NativeWind v4 (Tailwind for React Native) | Consistent utility classes, design token alignment |
| API client | Axios with interceptors | Token refresh, retry logic, queue awareness |
| Notifications | Expo Notifications | Push, local OTP reminders |
| Media capture | Expo Camera, Expo Image Picker | Evidence photo capture |
| Audio | Expo Audio | Voice note recording |
| Secure storage | Expo SecureStore | Auth tokens, sensitive session data |
| Document viewer | expo-sharing, expo-print | PDF export preview and share |

## Application Type Decision

Kotoku will be delivered as two frontends:

**Primary: React Native mobile app via Expo**
- Main user-facing product
- Target: Android first, low-end devices (minimum 2GB RAM, Android 10+)
- Evidence capture, OTP confirmation, drafts, vault

**Secondary: React web admin dashboard**
- Internal tool for Yaw and Samuel
- Monitor agreements, evidence states, vault, disputes, retention, and system health
- Deployed as a standard React + Vite web app

Both share the same Django/DRF backend API.

## Expo: Managed vs Bare

Use Expo managed workflow for MVP. It covers all Kotoku features needed in the first four sprints, including camera, microphone, secure token storage, push notifications, and file sharing, without requiring native project maintenance. [sebbie](https://sebbie.pl/expo-vs-bare-react-native-in-2026-how-to-choose-the-right-workflow-for-your-mobile-app/)

Move to bare workflow only if a specific third-party native SDK integration is required that Expo SDK cannot support.

## Folder Structure

### React Native App

```text
kotoku-mobile/
├── app/                        # Expo Router file-based navigation
│   ├── (auth)/
│   │   ├── _layout.tsx
│   │   ├── welcome.tsx
│   │   ├── send-otp.tsx
│   │   └── verify-otp.tsx
│   ├── (main)/
│   │   ├── _layout.tsx
│   │   ├── home.tsx
│   │   ├── vault/
│   │   │   ├── index.tsx
│   │   │   └── [agreementId].tsx
│   │   └── profile.tsx
│   ├── agreement/
│   │   ├── new.tsx
│   │   ├── [id]/
│   │   │   ├── steps/
│   │   │   │   ├── scenario.tsx
│   │   │   │   ├── parties.tsx
│   │   │   │   ├── details.tsx
│   │   │   │   ├── evidence.tsx
│   │   │   │   ├── review.tsx
│   │   │   │   └── consent.tsx
│   │   │   └── sealed.tsx
│   ├── _layout.tsx
│   └── +not-found.tsx
├── src/
│   ├── api/                    # API client and endpoint modules
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── agreements.ts
│   │   ├── evidence.ts
│   │   ├── consent.ts
│   │   ├── vault.ts
│   │   └── types.ts
│   ├── components/             # Shared reusable UI components
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── TextInput.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── StepIndicator.tsx
│   │   │   ├── EvidenceSlot.tsx
│   │   │   ├── OTPInput.tsx
│   │   │   └── EmptyState.tsx
│   │   ├── agreement/
│   │   │   ├── AgreementCard.tsx
│   │   │   ├── StepProgress.tsx
│   │   │   ├── PartyRow.tsx
│   │   │   └── FieldRenderer.tsx
│   │   ├── evidence/
│   │   │   ├── PhotoSlot.tsx
│   │   │   ├── AudioRecorder.tsx
│   │   │   └── IDCapture.tsx
│   │   └── vault/
│   │       ├── VaultCard.tsx
│   │       └── ExportButton.tsx
│   ├── features/               # Feature-scoped state, logic, hooks
│   │   ├── auth/
│   │   │   ├── useAuth.ts
│   │   │   ├── authStore.ts
│   │   │   └── otpFlow.ts
│   │   ├── agreements/
│   │   │   ├── useAgreements.ts
│   │   │   ├── useAgreementDraft.ts
│   │   │   ├── agreementStore.ts
│   │   │   └── stepValidation.ts
│   │   ├── evidence/
│   │   │   ├── useEvidenceUpload.ts
│   │   │   ├── evidenceQueue.ts
│   │   │   └── captureHelpers.ts
│   │   ├── consent/
│   │   │   ├── useConsentFlow.ts
│   │   │   └── consentStore.ts
│   │   └── vault/
│   │       ├── useVault.ts
│   │       └── exportHelpers.ts
│   ├── hooks/                  # Shared generic hooks
│   │   ├── useNetworkStatus.ts
│   │   ├── usePermissions.ts
│   │   ├── useSyncQueue.ts
│   │   └── useOfflineGuard.ts
│   ├── store/                  # Zustand global stores
│   │   ├── sessionStore.ts
│   │   └── syncStore.ts
│   ├── db/                     # Local SQLite persistence layer
│   │   ├── schema.ts
│   │   ├── drafts.ts
│   │   ├── syncQueue.ts
│   │   └── migrations.ts
│   ├── lib/                    # Infrastructure utilities
│   │   ├── queryClient.ts
│   │   ├── secureStore.ts
│   │   ├── logger.ts
│   │   └── errorHandler.ts
│   ├── constants/
│   │   ├── scenarios.ts
│   │   ├── routes.ts
│   │   └── config.ts
│   ├── types/
│   │   ├── agreement.ts
│   │   ├── evidence.ts
│   │   ├── vault.ts
│   │   └── api.ts
│   └── utils/
│       ├── formatters.ts
│       ├── validators.ts
│       └── network.ts
├── assets/
│   ├── images/
│   ├── fonts/
│   └── icons/
├── app.json
├── tsconfig.json
├── babel.config.js
├── .env.example
└── README.md
```

### Web Admin Dashboard

```text
kotoku-admin/
├── src/
│   ├── pages/
│   ├── components/
│   ├── api/
│   ├── features/
│   ├── hooks/
│   └── lib/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── .env.example
```

## Architecture Rules

### Rule 1: Screens are thin

Screens in `app/` should compose components and call hooks. They should not own business logic, API calls, or query definitions directly.

### Rule 2: Features own their logic

Each feature in `src/features/` owns its hooks, stores, and data operations. Cross-feature dependencies should be minimal and explicit.

### Rule 3: API client is isolated

All HTTP calls live in `src/api/`. Screens and features never call `fetch()` or `axios` directly. This makes it easy to mock, test, and modify endpoints as the backend evolves.

### Rule 4: Local persistence is a first-class concern

Drafts, pending sync actions, and evidence upload queues must survive:
- app closes,
- network drops,
- device reboots.

All agreement drafts should be written to SQLite first, then synced to the backend when connectivity allows. [relevant](https://relevant.software/blog/react-native-offline-first/)

### Rule 5: Components are always controlled

Form state lives in React Hook Form with Zod validation. Components receive values and callbacks, they do not manage their own draft state internally.

## State Management Model

Kotoku uses two distinct state layers:

**Server state → TanStack Query**
- Agreement lists and details
- Vault records
- Template definitions
- OTP confirmation results

TanStack Query handles caching, background refetching, retry logic, and sync status automatically, which makes it especially well-suited for agreement states that need to stay fresh while the user is active. [linkedin](https://www.linkedin.com/posts/punith-manthri-ba15b4216_reactnative-offlinefirst-mobiledevelopment-activity-7410268082029588480-thH9)

**Client/UI state → Zustand**
- Auth session and token
- Active agreement draft step tracking
- Sync queue visibility
- Network status flags

Keep Zustand stores small and purpose-specific. Avoid putting server data in Zustand; that belongs in TanStack Query.

## Offline-First Posture

Kotoku's real users may have intermittent connectivity. Draft saves, photo attachments, and sync must survive poor network conditions. The offline-first pattern works by writing locally first, then queuing API calls for when connectivity returns. [dev](https://dev.to/msaadullah/building-offline-first-apps-using-react-native-react-query-and-asyncstorage-1h4i)

### Draft saving

Every agreement draft step persists to SQLite immediately on change. The user never loses form progress because of a network drop.

```
User edits form step
  → write to SQLite draft record
  → background sync attempt to backend
    → success: mark record as synced
    → failure: keep in local queue, retry on reconnect
```

### Evidence upload queue

Evidence uploads are queued in SQLite. When an upload is initiated:
1. Save local file reference and metadata to SQLite queue.
2. Attempt upload immediately if online.
3. If offline, mark as pending.
4. On reconnect, drain queue with retry + backoff. [dev](https://dev.to/oghenetega_adiri/building-robust-offline-functionality-in-react-native-a-complete-guide-4174)

### Sync queue design

The sync queue in `src/db/syncQueue.ts` should store:
- action type (`CREATE_DRAFT`, `UPDATE_DRAFT`, `UPLOAD_EVIDENCE`, `CONFIRM_OTP`, `SEAL`)
- payload
- creation timestamp
- retry count
- last attempt timestamp
- status (`pending`, `in_flight`, `failed_permanent`)

Permanent failures (backend 409/404 responses) should not be retried. [dev](https://dev.to/oghenetega_adiri/building-robust-offline-functionality-in-react-native-a-complete-guide-4174)

### Network status

The `useNetworkStatus` hook wraps NetInfo and provides a reactive connectivity signal. Components can use `useOfflineGuard` to display appropriate messaging or disable destructive actions when offline.

## Agreement Builder Flow

The agreement creation is a multi-step flow driven by scenario template definitions loaded from the backend. The step sequence for used vehicle sale:

```
1. scenario.tsx    → select scenario type
2. parties.tsx     → add party name, phone, ID
3. details.tsx     → render dynamic fields from template
4. evidence.tsx    → photo slots, ID capture, audio
5. review.tsx      → read-only summary + edit button
6. consent.tsx     → OTP request + confirmation for each party
```

The step state and validation lives in `src/features/agreements/agreementStore.ts`. The component `FieldRenderer.tsx` handles dynamic field types from template definitions without needing a new screen per scenario.

## Performance Rules for Low-End Android

React Native performance on low-end Android devices requires discipline from the beginning. [reactnative](https://reactnative.dev/docs/performance)

Apply these rules throughout:
- use `FlatList` not `ScrollView` for any list longer than 10 items,
- avoid anonymous functions in render paths,
- use `React.memo` on list item components,
- compress camera images before upload (Expo ImageManipulator),
- avoid large in-memory buffers for audio,
- keep navigation stack shallow,
- use `InteractionManager.runAfterInteractions` for post-navigation heavy work,
- avoid `useEffect` chains that trigger unnecessary re-renders.

## API Client Design

The Axios client in `src/api/client.ts` should include:
- base URL from environment config,
- Authorization header injection from SecureStore session,
- token refresh interceptor on 401,
- global error normalization,
- request timeout suitable for low-speed connections (recommend 30s).

All endpoint modules (`agreements.ts`, `evidence.ts`, etc.) export typed async functions used by TanStack Query hooks.

## Security Posture

- Auth tokens stored in `expo-secure-store`, never in AsyncStorage or memory-only. [leanware](https://www.leanware.co/insights/react-native-vs-expo)