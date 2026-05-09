# Dispute Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable parties to raise disputes on sealed agreements and generate case packs.

**Architecture:** Add sealed-agreement validation to dispute creation, add detail endpoint, add case-pack endpoint. Build frontend flow from vault detail → disputes list → dispute detail.

**Tech Stack:** Django REST Framework, Flutter (React Native)

---

## File Structure

### Backend
- `apps/disputes/api/serializers.py` — add agreement info to DisputeSerializer
- `apps/disputes/api/views.py` — add sealed check + case-pack endpoint
- `apps/disputes/api/urls.py` — add detail + case-pack routes
- `apps/disputes/services.py` — add case-pack generation logic

### Frontend
- `kotoku-mobile/src/hooks/useDisputes.ts` — fetch disputes list
- `kotoku-mobile/app/(main)/disputes.tsx` — show disputes list
- `kotoku-mobile/app/(main)/disputes/[id].tsx` — dispute detail (create new)
- `kotoku-mobile/app/(main)/vault/[agreementId].tsx` — add Raise Dispute button

---

## Task 1: Backend — Add Sealed Check + Detail Endpoint

**Files:**
- Modify: `kotoku-backend/apps/disputes/api/views.py`
- Modify: `kotoku-backend/apps/disputes/api/urls.py`
- Modify: `kotoku-backend/apps/disputes/api/serializers.py`

- [ ] **Step 1: Add DisputeSerializer with agreement info**

Edit `kotoku-backend/apps/disputes/api/serializers.py` — add after existing fields:

```python
class DisputeSerializer(serializers.ModelSerializer):
    raised_by_party_id = serializers.IntegerField(source="raised_by.pk", read_only=True)
    raised_by_display_name = serializers.CharField(
        source="raised_by.display_name", read_only=True
    )
    agreement_id = serializers.IntegerField(source="agreement.pk", read_only=True)
    agreement_type = serializers.CharField(source="agreement.scenario_template", read_only=True)
    agreement_sealed_at = serializers.DateTimeField(source="agreement.sealed_at", read_only=True)

    class Meta:
        model = Dispute
        fields = (
            "id",
            "agreement_id",
            "agreement_type",
            "agreement_sealed_at",
            "raised_by_party_id",
            "raised_by_display_name",
            "reason",
            "status",
            "resolution",
            "resolved_at",
            "created_at",
            "updated_at",
        )
```

- [ ] **Step 2: Add sealed-agreement check to DisputeCollectionView**

Edit `kotoku-backend/apps/disputes/api/views.py` — replace post method:

```python
def post(self, request, agreement_id: int):
    agreement = self._get_agreement(agreement_id, request.user.account.pk)
    if agreement.status != Agreement.Status.SEALED:
        return ok({"error": "Disputes can only be raised on sealed agreements"}, status_code=400)
    serializer = DisputeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    dispute = DisputeService.open_dispute(
        agreement_id=agreement_id,
        raised_by_party_id=serializer.validated_data["raised_by_party_id"],
        reason=serializer.validated_data["reason"],
    )
    return ok({"dispute": DisputeSerializer(dispute).data}, status_code=201)
```

- [ ] **Step 3: Add DisputeDetailView to views.py**

Add to end of `views.py`:

```python
class DisputeDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, dispute_id: int):
        try:
            dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id__created_by=request.user.account)
        except Dispute.DoesNotExist:
            raise Http404 from None
        return ok({"dispute": DisputeSerializer(dispute).data})
```

- [ ] **Step 4: Add URL routes for detail endpoint**

Edit `kotoku-backend/apps/disputes/api/urls.py`:

```python
from django.urls import path

from apps.disputes.api.views import DisputeCollectionView, DisputeDetailView

urlpatterns = [
    path("disputes/", DisputeCollectionView.as_view(), name="dispute-collection"),
    path("disputes/<int:dispute_id>/", DisputeDetailView.as_view(), name="dispute-detail"),
]
```

Note: These routes need to be included from agreements/urls.py at `/agreements/<int:agreement_id>/` prefix.

- [ ] **Step 5: Commit**

```bash
git add apps/disputes/api/serializers.py apps/disputes/api/views.py apps/disputes/api/urls.py
git commit -m "feat: add sealed check and detail endpoint for disputes"
```

---

## Task 2: Backend — Case Pack Generation

**Files:**
- Modify: `kotoku-backend/apps/disputes/api/views.py`
- Modify: `kotoku-backend/apps/disputes/api/urls.py`
- Modify: `kotoku-backend/apps/disputes/services.py`

- [ ] **Step 1: Add case_pack generation to DisputeService**

Edit `kotoku-backend/apps/disputes/services.py`:

```python
from django.utils import timezone


class DisputeService:
    @staticmethod
    def open_dispute(*, agreement_id: int, raised_by_party_id: int, reason: str) -> Dispute:
        from apps.agreements.models import Agreement
        from apps.parties.models import Party
        
        agreement = Agreement.objects.get(pk=agreement_id)
        raised_by = Party.objects.get(pk=raised_by_party_id, agreement_id=agreement_id)
        
        return Dispute.objects.create(
            agreement=agreement,
            raised_by=raised_by,
            reason=reason,
            status=Dispute.Status.OPEN,
        )

    @staticmethod
    def generate_case_pack(*, dispute: Dispute) -> dict:
        agreement = dispute.agreement
        case_pack = {
            "dispute_id": dispute.pk,
            "generated_at": timezone.now().isoformat(),
            "agreement": {
                "id": agreement.pk,
                "title": agreement.title,
                "scenario": agreement.scenario_template,
                "sealed_at": agreement.sealed_at.isoformat() if agreement.sealed_at else None,
                "seal_hash": agreement.seal_hash,
            },
            "dispute": {
                "raised_by": dispute.raised_by.display_name,
                "reason": dispute.reason,
                "status": dispute.status,
                "created_at": dispute.created_at.isoformat(),
            },
        }
        return case_pack
```

- [ ] **Step 2: Add case-pack endpoint to DisputeDetailView**

Edit `views.py` — add to DisputeDetailView:

```python
def post(self, request, dispute_id: int):
    try:
        dispute = DisputeSelector.get(dispute_id=dispute_id, agreement_id__created_by=request.user.account)
    except Dispute.DoesNotExist:
        raise Http404 from None
    case_pack = DisputeService.generate_case_pack(dispute=dispute)
    return ok({"case_pack": case_pack})
```

- [ ] **Step 3: Commit**

```bash
git add apps/disputes/services.py apps/disputes/api/views.py
git commit -m "feat: add case-pack generation for disputes"
```

---

## Task 3: Frontend — Disputes List Screen

**Files:**
- Create: `kotoku-mobile/src/hooks/useDisputes.ts`
- Modify: `kotoku-mobile/app/(main)/disputes.tsx`

- [ ] **Step 1: Create useDisputes hook**

Create `kotoku-mobile/src/hooks/useDisputes.ts`:

```typescript
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export interface Dispute {
  id: number;
  agreement_id: number;
  agreement_type: string;
  agreement_sealed_at: string;
  raised_by_party_id: number;
  raised_by_display_name: string;
  reason: string;
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  resolution?: string;
  created_at: string;
}

export function useDisputes(agreementId?: number) {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDisputes() {
      try {
        setLoading(true);
        const url = agreementId 
          ? `/agreements/${agreementId}/disputes`
          : '/disputes';
        const response = await api.get(url);
        setDisputes(response.disputes || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load disputes');
      } finally {
        setLoading(false);
      }
    }
    fetchDisputes();
  }, [agreementId]);

  return { disputes, loading, error };
}
```

- [ ] **Step 2: Update disputes.tsx with list**

Edit `kotoku-mobile/app/(main)/disputes.tsx`:

```typescript
import { Text, View, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Card } from '@/components/ui';
import { useDisputes, Dispute } from '@/hooks/useDisputes';

export default function DisputesScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { disputes, loading, error } = useDisputes();

  const renderItem = ({ item }: { item: Dispute }) => (
    <TouchableOpacity onPress={() => router.push(`/disputes/${item.id}`)}>
      <Card elevation="sm" className="mb-sm">
        <View className="flex-row justify-between items-center">
          <View>
            <Text className="text-base font-medium text-ink-primary">
              {item.agreement_type || 'Agreement'}
            </Text>
            <Text className="text-sm text-ink-secondary">
              vs {item.raised_by_display_name}
            </Text>
          </View>
          <View className={`px-sm py-xs rounded ${
            item.status === 'open' ? 'bg-warning/20' :
            item.status === 'resolved' ? 'bg-success/20' : 'bg-ink-muted/20'
          }`}>
            <Text className={`text-xs font-medium ${
              item.status === 'open' ? 'text-warning' :
              item.status === 'resolved' ? 'text-success' : 'text-ink-muted'
            }`}>
              {item.status}
            </Text>
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-surface-canvas" style={{ paddingTop: insets.top + 12 }}>
      <Text className="text-2xl font-semibold text-ink-primary px-lg mb-sm">Disputes</Text>
      {disputes.length === 0 ? (
        <Card elevation="sm" className="mx-lg">
          <Text className="text-sm text-ink-muted text-center py-lg">No disputes yet.</Text>
        </Card>
      ) : (
        <FlatList
          data={disputes}
          renderItem={renderItem}
          keyExtractor={(item) => String(item.id)}
          contentContainerClassName="px-lg pb-2xl"
        />
      )}
    </View>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add kotoku-mobile/src/hooks/useDisputes.ts kotoku-mobile/app/\(main\)/disputes.tsx
git commit -m "feat: add disputes list screen"
```

---

## Task 4: Frontend — Dispute Detail + Raise Dispute Flow

**Files:**
- Create: `kotoku-mobile/app/(main)/disputes/[id].tsx`
- Modify: `kotoku-mobile/app/(main)/vault/[agreementId].tsx`

- [ ] **Step 1: Create dispute detail screen**

Create `kotoku-mobile/app/(main)/disputes/[id].tsx`:

```typescript
import { Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useState, useEffect } from 'react';

import { Card, Button } from '@/components/ui';
import { api } from '@/lib/api';

interface DisputeDetail {
  id: number;
  agreement_id: number;
  agreement_type: string;
  agreement_sealed_at: string;
  raised_by_display_name: string;
  reason: string;
  status: string;
  resolution?: string;
  created_at: string;
}

export default function DisputeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [dispute, setDispute] = useState<DisputeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDetail() {
      try {
        const response = await api.get(`/disputes/${id}`);
        setDispute(response.dispute);
      } catch (e) {
        Alert.alert('Error', 'Failed to load dispute');
      } finally {
        setLoading(false);
      }
    }
    fetchDetail();
  }, [id]);

  const generateCasePack = async () => {
    try {
      const response = await api.post(`/disputes/${id}/case_pack`, {});
      Alert.alert('Case Pack', JSON.stringify(response.case_pack, null, 2));
    } catch (e) {
      Alert.alert('Error', 'Failed to generate case pack');
    }
  };

  if (loading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!dispute) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <Text className="text-ink-muted">Dispute not found</Text>
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl"
      style={{ paddingTop: insets.top + 12 }}
    >
      <Text className="text-2xl font-semibold text-ink-primary mb-lg">Dispute Details</Text>
      
      <Card elevation="sm" className="mb-lg">
        <View className="gap-md">
          <View>
            <Text className="text-sm text-ink-muted">Agreement</Text>
            <Text className="text-base text-ink-primary">{dispute.agreement_type}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Sealed At</Text>
            <Text className="text-base text-ink-primary">
              {new Date(dispute.agreement_sealed_at).toLocaleDateString()}
            </Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Raised By</Text>
            <Text className="text-base text-ink-primary">{dispute.raised_by_display_name}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Status</Text>
            <Text className="text-base text-ink-primary capitalize">{dispute.status}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Reason</Text>
            <Text className="text-base text-ink-primary">{dispute.reason}</Text>
          </View>
        </View>
      </Card>

      <Button onPress={generateCasePack} variant="secondary">
        <Text>Generate Case Pack</Text>
      </Button>
    </ScrollView>
  );
}
```

- [ ] **Step 2: Add Raise Dispute to vault detail**

Edit `kotoku-mobile/app/(main)/vault/[agreementId].tsx` — find the actions section and add:

```typescript
import { Alert } from 'react-native';
// ... existing imports

const raiseDispute = async () => {
  Alert.prompt(
    'Raise Dispute',
    'Enter the reason for this dispute',
    async (reason) => {
      if (!reason || reason.length < 10) {
        Alert.alert('Error', 'Please provide at least 10 characters');
        return;
      }
      try {
        await api.post(`/agreements/${agreementId}/disputes`, {
          raised_by_party_id: userPartyId,
          reason,
        });
        Alert.alert('Success', 'Dispute has been raised');
        router.push('/disputes');
      } catch (e) {
        Alert.alert('Error', 'Failed to raise dispute');
      }
    },
    'plain-text',
    '',
    'default'
  );
};

// In the actions section, add:
<Button onPress={raiseDispute} variant="secondary" className="mt-md">
  <Text>Raise Dispute</Text>
</Button>
```

- [ ] **Step 3: Commit**

```bash
git add kotoku-mobile/app/\(main\)/disputes/\[id\].tsx kotoku-mobile/app/\(main\)/vault/\[agreementId\].tsx
git commit -m "feat: add dispute detail and raise dispute flow"
```

---

## Task 5: Integration Tests

**Files:**
- Create: `kotoku-backend/apps/disputes/tests/test_disputes_api.py`

- [ ] **Step 1: Write integration tests**

Create `kotoku-backend/apps/disputes/tests/test_disputes_api.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
fromapps.accounts.models import Account
from apps.agreements.models import Agreement
from apps.parties.models import Party
from apps.disputes.models import Dispute


class DisputeAPITestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="test", password="test")
        self.account = Account.objects.create(user=self.user, phone="+233123456789")
        self.agreement = Agreement.objects.create(
            title="Test Agreement",
            scenario_template="used_vehicle_sale",
            status=Agreement.Status.SEALED,
            created_by=self.account,
            sealed_at=timezone.now(),
        )
        self.party = Party.objects.create(
            agreement=self.agreement,
            full_name="Test Party",
            role="seller",
        )

    def test_create_dispute_on_sealed_agreement(self):
        response = self.client.post(
            f"/api/v1/agreements/{self.agreement.pk}/disputes/",
            {"raised_by_party_id": self.party.pk, "reason": "Test dispute reason here"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Dispute.objects.count(), 1)

    def test_cannot_create_dispute_on_draft_agreement(self):
        draft_agreement = Agreement.objects.create(
            title="Draft Agreement",
            status=Agreement.Status.DRAFT,
            created_by=self.account,
        )
        response = self.client.post(
            f"/api/v1/agreements/{draft_agreement.pk}/disputes/",
            {"raised_by_party_id": self.party.pk, "reason": "Test dispute reason here"},
        )
        self.assertEqual(response.status_code, 400)

    def test_get_dispute_detail(self):
        dispute = Dispute.objects.create(
            agreement=self.agreement,
            raised_by=self.party,
            reason="Test reason",
        )
        response = self.client.get(f"/api/v1/disputes/{dispute.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dispute"]["reason"], "Test reason")

    def test_generate_case_pack(self):
        dispute = Dispute.objects.create(
            agreement=self.agreement,
            raised_by=self.party,
            reason="Test reason",
        )
        response = self.client.post(f"/api/v1/disputes/{dispute.pk}/case_pack/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("case_pack", response.data)
```

- [ ] **Step 2: Run tests**

```bash
cd kotoku-backend && python manage.py test apps.disputes.tests.test_disputes_api -v 2
```

- [ ] **Step 3: Commit**

```bash
git add kotoku-backend/apps/disputes/tests/test_disputes_api.py
git commit -m "test: add dispute API integration tests"
```

---

## Execution Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Backend sealed-check + detail endpoint | serializers, views, urls |
| 2 | Case pack generation | services, views |
| 3 | Frontend disputes list | useDisputes hook, disputes.tsx |
| 4 | Frontend detail + raise flow | disputes/[id].tsx, vault/[agreementId].tsx |
| 5 | Integration tests | test_disputes_api.py |

**Plan complete:** 5 tasks, ~15 steps, ~3 commits