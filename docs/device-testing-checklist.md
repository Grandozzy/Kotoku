# Kotoku — Device Testing Checklist

**For:** Samuel  
**Before:** App Store submission and Vercel deployment  
**Platforms:** iOS (physical device) + Web (browser)  
**Backend:** Must be running before starting — see Setup below

---

## Setup

### Backend (ask Oscar to confirm it is running)
The Django server must be running and reachable on the local network.
- URL: `http://192.168.129.102:8000`
- Quick check: open `http://192.168.129.102:8000/api/auth/send-otp/` in Safari on your phone — you should see `{"detail":"Method \"GET\" not allowed."}`. If you get a timeout, the server is not running.

### Mobile
1. Install **Expo Go** from the App Store if not already installed
2. Make sure your phone is on the **same Wi-Fi network** as Oscar's Mac
3. Scan the QR code from the Expo terminal (Oscar will share it)
4. The app should open — do **not** use a browser, use the Expo Go app

### Web
- Open `http://192.168.129.102:8000` → no, the web app runs separately
- Oscar will confirm the web URL (either `localhost:3000` or the production Vercel URL)

---

## How to report issues

For each item that fails, note:
1. **Screen** — which screen you were on
2. **Steps** — exactly what you tapped/typed to reproduce it
3. **Expected** — what should have happened
4. **Actual** — what happened instead (screenshot if possible)

---

## 1. Auth Flow

### Mobile
- [x] Cold launch → lands on **Welcome** screen (no blank flash or crash)
- [x] Welcome screen scrolls smoothly — all 3 step cards and legal bar visible
- [x] Tap **Get started** → goes to phone number screen
- [x] Enter number without country code (e.g. `0241234567`) → shows validation error, does not submit
- [x] Enter valid number with country code (e.g. `+233241234567`) → **Send code** button enables
- [x] Tap **Send code** → OTP SMS arrives on the phone within 30 seconds
- [x] Enter wrong 8-digit code → shows error message, does not log in
- [x] Enter correct 8-digit code → lands on **Home** screen
- [x] Kill the app completely, relaunch → stays logged in (does **not** show Welcome again)

### Web
- [ ] Open the web app → lands on **Landing page** (not dashboard)
- [ ] Landing page has no broken layout or overflowing text on desktop
- [ ] Click **Sign in** → goes to login page
- [ ] Login page shows Kotoku brand mark and Ghana ETA trust line at the bottom
- [ ] Enter phone number → OTP SMS arrives
- [ ] Enter correct 8-digit code on verify page → lands on **Dashboard**
- [ ] Reload the page → stays logged in

---

## 2. Agreement Creation

### Mobile
- [x] From Home, tap **New** (top right) → goes to scenario selection
- [x] Select a scenario (e.g. Used Vehicle Sale)
- [x] Fill in agreement title and description → tap Next
- [x] Add Party A details (full name, phone, ID type, ID number) → tap Next
- [x] Add Party B details → tap Next
- [ ] Upload at least **one evidence photo** using the camera
- [x] Upload at least **one evidence photo** from the photo gallery
- [x] Tap Next → reaches Review screen — all details show correctly
- [ ] Submit → agreement created, appears in **Home** under Drafts
- [ ] Tap the draft → can reopen and continue editing
- [ ] Resume draft → all previously entered data still intact (title, parties, photos)


### Web
- [ ] From Dashboard, tap **+ New** → goes to new agreement form
- [ ] Fill in title, scenario, parties → submit
- [ ] Agreement appears in Dashboard under Pending

---

## 3. Seal Flow (requires two accounts / two phones)

> If you only have one device, you can test this by using two browser tabs on web with different accounts, or ask Oscar to log in as the second party on his phone.

- [ ] With both parties' details added, navigate to the **Consent** step
- [ ] Tap **Send OTP to both parties** → both phones receive SMS codes
- [ ] Party A enters their code → confirmed
- [ ] Party B enters their code → confirmed
- [ ] Tap **Seal agreement** → status changes to **Sealed**
- [ ] Agreement disappears from Home Drafts and appears in **Vault**
- [ ] Vault card shows the agreement title and sealed date

---

## 4. Vault

### Mobile
- [ ] Navigate to **Vault** tab → sealed agreement appears
- [ ] Vault tab shows skeleton loader while data loads (not a spinner or blank screen)
- [ ] If vault is empty → shows empty state with lock icon and descriptive text (not a blank screen)
- [ ] Tap a sealed agreement → opens detail view
- [ ] Detail view shows: title, parties, evidence photos, seal hash, status badge

### Web
- [ ] Navigate to **Vault** in the nav → list of sealed agreements
- [ ] If vault is empty → shows lock icon empty state with "Seal your first agreement" link
- [ ] Click an entry → opens vault detail page

---

## 5. Annotations (post-seal, mobile only)

> Annotations can only be added to **sealed** agreements.

- [ ] Open a sealed agreement from Vault → annotation FAB (pen icon) is visible
- [ ] Tap FAB → annotation input sheet opens
- [ ] Type a note and submit → annotation appears in the list immediately
- [ ] Tap **Edit** on your own annotation → can change the text, saves correctly
- [ ] If logged in as Party B: Party A's annotation does **not** show an Edit option
- [ ] Tap **Delete** on your own annotation → removed from list with confirmation
- [ ] If logged in as Party B: Party A's annotation does **not** show a Delete option
- [ ] Open a **draft** (non-sealed) agreement → annotation FAB is **not** visible

---

## 6. Disputes (post-seal)

### Mobile
- [ ] Open a sealed agreement → **Raise Dispute** button is visible
- [ ] Open a **draft** agreement → **Raise Dispute** button is **not** visible
- [ ] Tap **Raise Dispute** → modal opens
- [ ] Submit with fewer than 10 characters in the reason → shows validation error, does not submit
- [ ] Submit with a valid reason (10+ characters) → dispute created
- [ ] Agreement status changes to **In Dispute** (or equivalent badge)
- [ ] Navigate to **Disputes** tab → new dispute appears in the list
- [ ] Tap the dispute → detail screen shows reason, status badge, raised-by name
- [ ] Disputes tab shows skeleton loader while loading (not a spinner)
- [ ] If no disputes → shows Scale icon empty state with descriptive text

### Web
- [ ] Open a sealed agreement → navigate to the Disputes tab within it
- [ ] Empty state shows Scale icon (not an emoji)
- [ ] Raise a dispute with a valid reason → appears in the list
- [ ] Dispute shows correct status badge

---

## 7. Offline Mode

- [ ] Enable **airplane mode** on the phone
- [ ] Offline banner appears at the top of the screen
- [ ] Attempt to create a new draft agreement → saves locally without crashing
- [ ] Make an edit to an existing draft → saves locally
- [ ] Re-enable Wi-Fi → offline banner disappears
- [ ] Local changes sync to the server (agreement appears on a second device or web)

---

## 8. Push Notifications

- [ ] On first launch, accept the notification permission prompt
- [ ] From a second account (or ask Oscar), take an action on a shared agreement (sign, annotate, raise dispute)
- [ ] Notification arrives on the first device within ~30 seconds
- [ ] Tapping the notification opens the correct screen in the app

---

## 9. Edge Cases

- [ ] Start the app with **no internet** from a cold launch → does not crash, shows offline banner
- [ ] Enter a very long agreement title (100+ characters) → truncates cleanly in all lists, no layout overflow
- [ ] Submit the dispute form with only spaces as the reason → blocked by validation (spaces don't count toward 10 chars)
- [ ] On the OTP screen, enter 7 digits → Confirm button stays disabled until 8th digit is entered
- [ ] Log out from Profile → returns to Welcome screen, cannot navigate back to app without logging in again

---

## 10. Visual & Layout Checks

### Mobile
- [ ] Welcome screen: ShieldCheck icon in blue square, bold hero headline, 3 step cards with icons, use-case pills, dark legal bar
- [ ] Tab bar: Home (house), Vault (lock), Disputes (scales), Profile (person) — active tab is bolder and blue
- [ ] Profile screen: avatar initials circle, icon rows with chevrons, red-tinted Log out row
- [ ] No raw emoji anywhere in the app (all replaced with Lucide icons)
- [ ] All screens have correct top padding (content not hidden under status bar)

### Web
- [ ] Landing page: no emoji, Lucide icons on step cards and use-case cards
- [ ] Nav: Home | Vault | Profile + **+ New** pill button on the right — no "Create" item
- [ ] Login and Verify pages: Kotoku brand mark at top, Ghana ETA trust line at bottom
- [ ] Active nav item is highlighted; agreement sub-pages do not highlight the wrong item
- [ ] No broken layouts on Safari, Chrome, and Firefox

---

## Sign-off

| Tester | Date | Result |
|--------|------|--------|
| Samuel | | ☐ Pass / ☐ Fail — notes: |

Once all items pass, hand back to Oscar to run `eas build --profile production` and submit to the App Store and Google Play.
