# Reopen Discovery & Home Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bilateral reopen visible to both parties — add counterparty access, home screen pending actions, vault list status badges, and fix ReopenSection.

**Architecture:** Extend backend selectors to include party-based access, add a pending-actions endpoint, then build out the home screen and update vault UI on mobile.

**Tech Stack:** Django/DRF (backend), React Native + Expo Router + React Query + NativeWind (mobile)

---

### Task 1: Extend backend agreement selectors for counterparty access

**Files:**
- Modify: `kotoku-backend/apps/agreements/selectors.py`

- [ ] **Step 1: Update `list_agreements` to include party-based access**

```python
# kotoku-backend/apps/agreements/selectors.py
from django.db.models import Q

from apps.agreements.models import Agreement


class AgreementSelector:
    @staticmethod
    def list_agreements(*, account_id=None, account_phone=None, status=None):
        qs = Agreement.objects.select_related("created_by").order_by("-created_at")
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                Q(created_by_id=account_id) | Q(parties__phone=account_phone)
            ).distinct()
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        if status is not None:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_agreement_detail(agreement_id: int, *, account_id: int = None, account_phone: str = None) -> Agreement:
        qs = Agreement.objects.prefetch_related(
            "parties__identity",
            "evidence_items",
            "consent_records",
        ).select_related("created_by")
        if account_id is not None and account_phone is not None:
            qs = qs.filter(
                Q(created_by_id=account_id) | Q(parties__phone=account_phone)
            )
        elif account_id is not None:
            qs = qs.filter(created_by_id=account_id)
        return qs.get(pk=agreement_id)

    @staticmethod
    def list_party_agreements(party_id: int):
        return (
            Agreement.objects.filter(parties__pk=party_id)
            .select_related("created_by")
            .order_by("-created_at")
            .distinct()
        )
```

- [ ] **Step 2: Update agreement views to pass `account_phone`**

In `kotoku-backend/apps/agreements/api/views.py`, update every call site that uses `AgreementSelector` to pass `account_phone=request.user.account.phone` alongside the existing `account_id`. There are 6 call sites:

1. `AgreementCollectionView.get` — `list_agreements(account_id=..., account_phone=request.user.account.phone, ...)`
2. `AgreementDetailView._get_agreement` — `get_agreement_detail(agreement_id, account_id=..., account_phone=request.user.account.phone)`
3. `ValidateView.post` — same pattern
4. `SealView.post` — same pattern
5. `ReopenRequestView.post` — same pattern
6. `ReopenOtpRequestView.post` — same pattern
7. `ReopenOtpConfirmView.post` — same pattern (two calls)

```python
# In AgreementCollectionView.get:
qs = AgreementSelector.list_agreements(
    account_id=request.user.account.pk,
    account_phone=request.user.account.phone,
    status=request.query_params.get("status"),
)

# In _get_agreement helper on every detail view:
def _get_agreement(self, agreement_id: int, account_id: int, account_phone: str):
    try:
        return AgreementSelector.get_agreement_detail(
            agreement_id, account_id=account_id, account_phone=account_phone
        )
    except Agreement.DoesNotExist:
        raise Http404 from None
```

Update `_get_agreement` calls to pass both args:
```python
agreement = self._get_agreement(
    agreement_id,
    account_id=request.user.account.pk,
    account_phone=request.user.account.phone,
)
```

- [ ] **Step 3: Verify with curl**

Run: `curl -s -H "Authorization: Token b209bc83d61218e1b7181fb853b360ad4fc7c9c6" "http://localhost:8000/api/agreements/" | python -m json.tool`

Expected: Bob now sees agreement #23 (which has `status: "reopen_requested"`).

- [ ] **Step 4: Commit**

```bash
git add kotoku-backend/apps/agreements/selectors.py kotoku-backend/apps/agreements/api/views.py
git commit -m "feat: extend agreement selectors for counterparty access"
```

---

### Task 2: Extend backend vault selectors for counterparty access

**Files:**
- Modify: `kotoku-backend/apps/vault/selectors.py`
- Modify: `kotoku-backend/apps/vault/api/views.py`

- [ ] **Step 1: Update `VaultSelector` to accept `account_phone`**

```python
# kotoku-backend/apps/vault/selectors.py
from django.db.models import Q, QuerySet

from apps.vault.models import VaultEntry


class VaultSelector:
    @staticmethod
    def get_for_agreement(*, agreement_id: int, account_id: int, account_phone: str = None) -> VaultEntry:
        qs = VaultEntry.objects.select_related(
            "agreement", "agreement__created_by"
        )
        if account_phone:
            qs = qs.filter(
                Q(agreement__created_by__pk=account_id) | Q(agreement__parties__phone=account_phone)
            )
        else:
            qs = qs.filter(agreement__created_by__pk=account_id)
        return qs.get(agreement_id=agreement_id)

    @staticmethod
    def list_for_account(*, account_id: int, account_phone: str = None) -> QuerySet:
        qs = VaultEntry.objects
        if account_phone:
            qs = qs.filter(
                Q(agreement__created_by__pk=account_id) | Q(agreement__parties__phone=account_phone)
            )
        else:
            qs = qs.filter(agreement__created_by__pk=account_id)
        return (
            qs.filter(archived=False)
            .select_related("agreement")
            .order_by("-created_at")
            .distinct()
        )
```

- [ ] **Step 2: Update vault views to pass `account_phone`**

In `kotoku-backend/apps/vault/api/views.py`, update all `VaultSelector` calls:

```python
class VaultCollectionView(APIView):
    # ...
    def get(self, request):
        qs = VaultSelector.list_for_account(
            account_id=request.user.account.pk,
            account_phone=request.user.account.phone,
        )
        # ... rest unchanged


class VaultDetailView(APIView):
    # ...
    def _get_entry(self, agreement_id: int, account_id: int, account_phone: str) -> VaultEntry:
        try:
            return VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=account_id,
                account_phone=account_phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None

    def get(self, request, agreement_id: int):
        entry = self._get_entry(
            agreement_id,
            request.user.account.pk,
            request.user.account.phone,
        )
        return ok({"vault_entry": VaultEntrySerializer(entry).data})


class VaultExportView(APIView):
    # ...
    def post(self, request, agreement_id: int):
        try:
            VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None
        # ... rest unchanged


class VaultAuditLogView(APIView):
    # ...
    def get(self, request, agreement_id: int):
        try:
            entry = VaultSelector.get_for_agreement(
                agreement_id=agreement_id,
                account_id=request.user.account.pk,
                account_phone=request.user.account.phone,
            )
        except VaultEntry.DoesNotExist:
            raise Http404 from None
        # ... rest unchanged
```

- [ ] **Step 3: Add `created_by_phone` to vault serializer**

In `kotoku-backend/apps/vault/api/serializers.py`, add the field:

```python
class AgreementSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    scenario_template = serializers.CharField()
    sealed_at = serializers.DateTimeField()
    seal_hash = serializers.CharField()
    created_by_phone = serializers.CharField()
```

We need to source this field. The serializer is used on `VaultEntry.agreement` which is an `Agreement` model. The `Agreement` model has `created_by` which is an `Account` with a `phone` field. Add `source` to the field:

```python
class AgreementSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    scenario_template = serializers.CharField()
    sealed_at = serializers.DateTimeField()
    seal_hash = serializers.CharField()
    created_by_phone = serializers.CharField(source="created_by.phone")
```

This requires the vault selectors to `select_related("agreement__created_by")` — they already do.

- [ ] **Step 4: Verify with curl**

Run: `curl -s -H "Authorization: Token b209bc83d61218e1b7181fb853b360ad4fc7c9c6" "http://localhost:8000/api/vault/" | python -m json.tool`

Expected: Bob now sees vault entry for agreement #23 with `created_by_phone: "+233500000001"`.

- [ ] **Step 5: Commit**

```bash
git add kotoku-backend/apps/vault/selectors.py kotoku-backend/apps/vault/api/views.py kotoku-backend/apps/vault/api/serializers.py
git commit -m "feat: extend vault selectors for counterparty access"
```

---

### Task 3: Add pending-actions backend endpoint

**Files:**
- Modify: `kotoku-backend/apps/agreements/api/views.py`
- Modify: `kotoku-backend/apps/agreements/api/urls.py`
- Modify: `kotoku-backend/apps/agreements/api/serializers.py`

- [ ] **Step 1: Add the view**

Add to `kotoku-backend/apps/agreements/api/views.py`:

```python
class PendingActionsView(APIView):
    """GET /agreements/pending-actions/

    Returns agreements where the authenticated user needs to take action:
      - draft agreements where they are creator
      - pending_consent agreements where they haven't consented
      - reopen_requested agreements where they haven't confirmed reopen
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.agreements.domain.enums import AgreementStatus  # noqa: PLC0415
        from apps.consent.models import ConsentRecord  # noqa: PLC0415

        account = request.user.account
        phone = account.phone

        drafts = list(
            Agreement.objects.filter(
                created_by=account,
                status=AgreementStatus.DRAFT,
            ).order_by("-updated_at")
        )

        pending_consent_qs = Agreement.objects.filter(
            status=AgreementStatus.PENDING_CONSENT,
            parties__phone=phone,
        ).exclude(
            consent_records__party__phone=phone,
            consent_records__purpose=ConsentRecord.Purpose.CONSENT,
            consent_records__granted=True,
        ).distinct().order_by("-updated_at")

        reopen_requested_qs = Agreement.objects.filter(
            status=AgreementStatus.REOPEN_REQUESTED,
            parties__phone=phone,
        ).exclude(
            consent_records__party__phone=phone,
            consent_records__purpose=ConsentRecord.Purpose.REOPEN,
            consent_records__granted=True,
        ).distinct().order_by("-updated_at")

        action_required = list(pending_consent_qs) + list(reopen_requested_qs)

        action_serializer = AgreementListSerializer(action_required, many=True)
        drafts_serializer = AgreementListSerializer(drafts, many=True)

        return ok({
            "action_required": action_serializer.data,
            "drafts": drafts_serializer.data,
        })
```

Add `PendingActionsView` to the import at top of views.py.

- [ ] **Step 2: Add the URL route**

In `kotoku-backend/apps/agreements/api/urls.py`, add BEFORE the `<int:agreement_id>` patterns (so `"pending-actions/"` doesn't get matched as an agreement_id):

```python
from .views import (
    AgreementCollectionView,
    AgreementDetailView,
    PendingActionsView,
    ReopenOtpConfirmView,
    ReopenOtpRequestView,
    ReopenRequestView,
    SealView,
    ValidateView,
)

urlpatterns = [
    path("", AgreementCollectionView.as_view(), name="agreement-collection"),
    path(
        "pending-actions/",
        PendingActionsView.as_view(),
        name="agreement-pending-actions",
    ),
    # ... rest unchanged
]
```

- [ ] **Step 3: Verify with curl**

Run for Alice:
```bash
curl -s -H "Authorization: Token 63a1a8e206fddb78a0d16620bd6407be3a32a2c7" "http://localhost:8000/api/agreements/pending-actions/" | python -m json.tool
```

Run for Bob:
```bash
curl -s -H "Authorization: Token b209bc83d61218e1b7181fb853b360ad4fc7c9c6" "http://localhost:8000/api/agreements/pending-actions/" | python -m json.tool
```

Expected: Alice sees `action_required` with agreement #23 (reopen_requested, she hasn't confirmed yet) and `drafts` with her 2 drafts. Bob sees `action_required` with agreement #23 (reopen_requested, he hasn't confirmed yet) and empty `drafts`.

- [ ] **Step 4: Commit**

```bash
git add kotoku-backend/apps/agreements/api/views.py kotoku-backend/apps/agreements/api/urls.py
git commit -m "feat: add pending-actions endpoint"
```

---

### Task 4: Update mobile vault mapper for `createdByPhone`

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/src/types/vault.ts`
- Modify: `Kotoku-frontend/kotoku-mobile/src/api/vault.ts`

- [ ] **Step 1: Add `createdByPhone` to `VaultRecord` type**

```typescript
// In src/types/vault.ts
export interface VaultRecord {
  id: number;
  agreementId: number;
  title: string;
  status: VaultStatus;
  agreementStatus: AgreementStatus;
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  sealedAt: string;
  retentionExpiresAt: string;
  createdByPhone: string;
}
```

- [ ] **Step 2: Update `RawVaultEntry` and `mapVaultRecord` in `src/api/vault.ts`**

```typescript
interface RawVaultEntry {
  id: number;
  agreement: {
    id: number;
    title: string;
    status: string;
    sealed_at: string;
    created_by_phone: string;
  };
  pdf_status: string;
  pdf_url: string | null;
  retain_until: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

function mapVaultRecord(raw: RawVaultEntry): VaultRecord {
  return {
    id: raw.id,
    agreementId: raw.agreement.id,
    title: raw.agreement.title,
    status: raw.archived ? "archived" : "active",
    agreementStatus: raw.agreement.status as VaultRecord["agreementStatus"],
    pdfStatus: raw.pdf_status as VaultRecord["pdfStatus"],
    pdfUrl: raw.pdf_url || null,
    sealedAt: raw.agreement.sealed_at,
    retentionExpiresAt: raw.retain_until,
    createdByPhone: raw.agreement.created_by_phone,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/types/vault.ts Kotoku-frontend/kotoku-mobile/src/api/vault.ts
git commit -m "feat: add createdByPhone to vault record"
```

---

### Task 5: Update VaultCard to use `agreementStatus` badge

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/src/components/vault/VaultCard.tsx`

- [ ] **Step 1: Replace status-based badge with agreementStatus-based badge**

Replace the badge section inside VaultCard:

```typescript
// Replace:
//   <Badge
//     label={record.status === "expired" ? "Expired" : "Sealed"}
//     variant={record.status === "expired" ? "default" : "sealed"}
//   />
// With:

          let badgeLabel: string;
          let badgeVariant: "default" | "sealed";
          let borderClass = "";

          if (record.agreementStatus === "reopen_requested") {
            badgeLabel = "Reopen Requested";
            badgeVariant = "default";
            borderClass = "border-l-4 border-l-amber-500";
          } else if (record.agreementStatus === "active") {
            badgeLabel = "Active";
            badgeVariant = "sealed";
          } else {
            badgeLabel = record.status === "expired" ? "Expired" : "Sealed";
            badgeVariant = record.status === "expired" ? "default" : "sealed";
          }
```

Then update the Pressable className to include `borderClass`:

```typescript
<Pressable
  onPress={() => router.push(`/(main)/vault/${record.agreementId}`)}
  className={[
    "bg-surface-card rounded-lg border border-border-subtle p-lg flex-row items-center gap-md active:opacity-70",
    borderClass,
  ].join(" ")}
>
```

And the Badge:

```typescript
<Badge label={badgeLabel} variant={badgeVariant} />
```

- [ ] **Step 2: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/components/vault/VaultCard.tsx
git commit -m "feat: vault card shows agreementStatus badge"
```

---

### Task 6: Add mobile pending-actions API + hook

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/src/api/agreements.ts`
- Create: `Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts`

- [ ] **Step 1: Add `fetchPendingActions` to agreements API**

Add to `src/api/agreements.ts`:

```typescript
export interface PendingActionItem {
  id: number;
  title: string;
  status: string;
  scenario_template: string;
  created_at: string;
  updated_at: string;
}

export interface PendingActionsResponse {
  action_required: PendingActionItem[];
  drafts: PendingActionItem[];
}

export async function fetchPendingActions(): Promise<PendingActionsResponse> {
  const res = await apiClient.get<ApiResponse<PendingActionsResponse>>(
    "/agreements/pending-actions/",
  );
  return res.data.data;
}
```

- [ ] **Step 2: Create `usePendingActions` hook**

Create `src/features/agreements/usePendingActions.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";

import { fetchPendingActions } from "@/api/agreements";

export function usePendingActions() {
  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/api/agreements.ts Kotoku-frontend/kotoku-mobile/src/features/agreements/usePendingActions.ts
git commit -m "feat: add pending-actions API and hook"
```

---

### Task 7: Rebuild home screen with pending actions

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/app/(main)/home.tsx`

- [ ] **Step 1: Replace static home screen with data-driven layout**

```tsx
import { useRouter } from "expo-router";
import { Alert, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui";
import { usePendingActions } from "@/features/agreements/usePendingActions";
import { useSessionStore } from "@/store/sessionStore";
import { colors } from "@/theme/tokens";

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data, isLoading, refetch } = usePendingActions();

  const actionRequired = data?.action_required ?? [];
  const drafts = data?.drafts ?? [];

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
      refreshControl={
        <ScrollView.refreshControl
          refreshing={isLoading}
          onRefresh={refetch}
          tintColor={colors.brandPrimary}
        />
      }
    >
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Home</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Start or resume an agreement
        </Text>
      </View>

      <Button
        title="New agreement"
        variant="primary"
        size="lg"
        fullWidth
        onPress={() => router.push("/agreement/new")}
      />

      {actionRequired.length > 0 && (
        <View className="gap-sm">
          <Text className="text-md font-semibold text-amber-600">
            Action required
          </Text>
          {actionRequired.map((item) => (
            <ActionCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {drafts.length > 0 && (
        <View className="gap-sm">
          <Text className="text-md font-semibold text-ink-primary">Drafts</Text>
          {drafts.map((item) => (
            <DraftCard key={item.id} item={item} />
          ))}
        </View>
      )}

      {actionRequired.length === 0 && drafts.length === 0 && !isLoading && (
        <View className="items-center py-xl">
          <Text className="text-sm text-ink-muted">
            No pending actions. Tap "New agreement" to start.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

function ActionCard({ item }: { item: { id: number; title: string; status: string } }) {
  const router = useRouter();

  const label =
    item.status === "reopen_requested"
      ? "Reopen requested — enter your code"
      : item.status === "pending_consent"
        ? "Pending your consent — enter code"
        : item.status;

  return (
    <Pressable
      onPress={() => {
        if (item.status === "reopen_requested") {
          router.push(`/(main)/vault/${item.id}`);
        } else {
          router.push(`/agreement/${item.id}/steps/review`);
        }
      }}
      className="bg-surface-card rounded-lg border-l-4 border-l-amber-500 border border-border-subtle p-lg active:opacity-70"
    >
      <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
        {item.title}
      </Text>
      <Text className="text-sm text-amber-600 mt-xs">{label}</Text>
      <Text className="text-xs text-brand-primary mt-xs">Tap to continue →</Text>
    </Pressable>
  );
}

function DraftCard({ item }: { item: { id: number; title: string; updated_at: string } }) {
  const router = useRouter();

  const relativeTime = getRelativeTime(item.updated_at);

  return (
    <Pressable
      onPress={() => router.push(`/agreement/${item.id}/steps/review`)}
      className="bg-surface-card rounded-lg border border-border-subtle p-lg active:opacity-70"
    >
      <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
        {item.title}
      </Text>
      <Text className="text-xs text-ink-muted mt-xs">{relativeTime}</Text>
      <Text className="text-xs text-brand-primary mt-xs">Continue →</Text>
    </Pressable>
  );
}

function getRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
```

- [ ] **Step 2: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/app/\(main\)/home.tsx
git commit -m "feat: data-driven home screen with pending actions"
```

---

### Task 8: Fix ReopenSection — use API response, creator-only button

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/src/components/vault/ReopenSection.tsx`
- Modify: `Kotoku-frontend/kotoku-mobile/app/(main)/vault/[agreementId].tsx`

- [ ] **Step 1: Add `createdByPhone` prop to ReopenSection**

Update the interface:

```typescript
interface ReopenSectionProps {
  agreementId: number;
  agreementStatus: AgreementStatus;
  createdByPhone: string;
}
```

Update the component signature:

```typescript
export function ReopenSection({ agreementId, agreementStatus, createdByPhone }: ReopenSectionProps) {
  const phone = useSessionStore((s) => s.phone);
  const isCreator = phone === createdByPhone;
```

- [ ] **Step 2: Add success state and navigation**

```typescript
import { useRouter } from "expo-router";
import { CheckCircle, Clock, RefreshCw } from "lucide-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Button, OTPInput } from "@/components/ui";
import { useSessionStore } from "@/store/sessionStore";
import { getApiErrorMessage } from "@/lib/errorHandler";
import {
  useConfirmReopen,
  useRequestReopen,
  useResendReopenOtp,
} from "@/features/vault/useReopen";
import { colors } from "@/theme/tokens";
import type { AgreementStatus } from "@/types/vault";
```

Add `reopened` state:

```typescript
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [confirmedByMe, setConfirmedByMe] = useState(false);
  const [reopened, setReopened] = useState(false);
  const router = useRouter();
```

- [ ] **Step 3: Show "Request Reopen" only for creator**

Replace the `sealed` block:

```typescript
  if (agreementStatus === "sealed") {
    if (!isCreator) return null;
    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Reopen Agreement
        </Text>
        <Text className="text-sm text-ink-secondary">
          Request to reopen this agreement. Both parties must confirm with a
          one-time code before it becomes editable again.
        </Text>
        <Button
          title="Request Reopen"
          variant="secondary"
          size="md"
          fullWidth
          loading={requestReopen.isPending}
          onPress={() => {
            requestReopen.mutate(undefined, {
              onSuccess: () => setOtpSent(true),
            });
          }}
        />
        {error && (
          <Text className="text-xs text-semantic-error text-center">{error}</Text>
        )}
      </View>
    );
  }
```

- [ ] **Step 4: Handle API response in confirm — show success when active**

Replace the `reopen_requested` block. After confirming:

```typescript
  if (agreementStatus === "reopen_requested") {
    if (reopened) {
      return (
        <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-sm">
          <View className="flex-row items-center gap-sm">
            <CheckCircle size={18} color={colors.success} />
            <Text className="text-sm font-medium text-emerald-700">
              Agreement reopened!
            </Text>
          </View>
          <Text className="text-sm text-ink-muted">
            Both parties confirmed. The agreement is now editable.
          </Text>
        </View>
      );
    }

    return (
      <View className="gap-sm">
        <Text className="text-md font-semibold text-ink-primary">
          Confirm Reopen
        </Text>
        <Text className="text-sm text-ink-secondary">
          Enter the code sent to {phone ?? "your phone"} to confirm.
        </Text>

        {confirmedByMe ? (
          <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-sm">
            <View className="flex-row items-center gap-sm">
              <CheckCircle size={18} color={colors.success} />
              <Text className="text-sm font-medium text-emerald-700">
                You&apos;ve confirmed
              </Text>
            </View>
            <View className="flex-row items-center gap-sm">
              <Clock size={16} color={colors.inkMuted} />
              <Text className="text-sm text-ink-muted">
                Waiting for the other party to confirm…
              </Text>
            </View>
          </View>
        ) : (
          <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-md">
            <OTPInput
              value={otpCode}
              onChange={(v) => {
                setOtpCode(v);
                if (confirmReopen.isError) confirmReopen.reset();
              }}
              error={error ?? undefined}
              disabled={confirmReopen.isPending}
            />
            <Button
              title="Confirm Reopen"
              variant="primary"
              size="md"
              fullWidth
              disabled={otpCode.length < 8}
              loading={confirmReopen.isPending}
              onPress={() => {
                if (!phone) return;
                confirmReopen.mutate(
                  { phone, otpCode },
                  {
                    onSuccess: (result) => {
                      if (result.agreement_status === "active") {
                        setReopened(true);
                      } else if (result.granted) {
                        setConfirmedByMe(true);
                      }
                    },
                  },
                );
              }}
            />
            <Pressable
              onPress={() => resendOtp.mutate()}
              disabled={resendOtp.isPending}
              className="flex-row items-center justify-center gap-xs"
            >
              <RefreshCw
                size={14}
                color={resendOtp.isPending ? colors.inkMuted : colors.brandPrimary}
              />
              <Text
                className={`text-sm ${resendOtp.isPending ? "text-ink-muted" : "text-brand-primary"}`}
              >
                {resendOtp.isPending ? "Sending…" : "Resend code"}
              </Text>
            </Pressable>
          </View>
        )}
      </View>
    );
  }
```

- [ ] **Step 5: Pass `createdByPhone` from vault detail screen**

In `app/(main)/vault/[agreementId].tsx`, update the ReopenSection:

```tsx
<ReopenSection
  agreementId={record.agreementId}
  agreementStatus={record.agreementStatus}
  createdByPhone={record.createdByPhone}
/>
```

- [ ] **Step 6: Commit**

```bash
git add Kotoku-frontend/kotoku-mobile/src/components/vault/ReopenSection.tsx Kotoku-frontend/kotoku-mobile/app/\(main\)/vault/\[agreementId\].tsx
git commit -m "fix: ReopenSection uses API response, creator-only request button"
```

---

### Task 9: Type check and manual test

**Files:** None

- [ ] **Step 1: Run TypeScript check on mobile**

```bash
cd Kotoku-frontend/kotoku-mobile && npx tsc --noEmit 2>&1 | Select-String -Pattern "ReopenSection|useReopen|home|VaultCard|usePendingActions|agreements\.ts"
```

Expected: Zero errors in these files. (Pre-existing errors in other files are acceptable.)

- [ ] **Step 2: Restart the dev server and test on device**

```bash
cd Kotoku-frontend/kotoku-mobile && npx expo start
```

Test scenarios:
1. Login as Alice (+233500000001) → Home screen shows "Action required" with agreement #23 (reopen_requested)
2. Tap the card → vault detail → shows ReopenSection with OTP input
3. Login as Bob (+233500000002) → Home screen shows "Action required" with agreement #23
4. Tap the card → vault detail → shows OTP input (Bob is not creator, so no "Request Reopen" button)
5. Vault list → shows agreement #23 with amber "Reopen Requested" badge and amber left border

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address type check issues"
```
