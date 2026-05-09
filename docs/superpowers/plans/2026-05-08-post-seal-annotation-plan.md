# Post-Seal Annotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add post-seal annotation feature to frontend - FAB button opens bottom sheet, save notes to API, display in Activity section.

**Architecture:** React Native + Expo, React Query for API, bottom sheet modal for input. Follow existing vault patterns.

**Tech Stack:** React Native, Expo, React Query, NativeWind

---

## File Structure

### New Files (5 files)

1. `Kotoku-frontend/kotoku-mobile/src/api/annotations.ts` — API client (create + list)
2. `Kotoku-frontend/kotoku-mobile/src/features/annotations/useAnnotations.ts` — React Query hook
3. `Kotoku-frontend/kotoku-mobile/src/features/annotations/useAddAnnotation.ts` — mutation hook
4. `Kotoku-frontend/kotoku-mobile/src/components/annotations/AnnotationSection.tsx` — notes list display
5. `Kotoku-frontend/kotoku-mobile/src/components/annotations/AddNoteSheet.tsx` — bottom sheet modal

### Modified Files (1 file)

1. `Kotoku-frontend/kotoku-mobile/app/(main)/vault/[agreementId].tsx` — add FAB + AnnotationSection

---

## Task 1: API Module

**Goal:** Create `src/api/annotations.ts` with create + list endpoints

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/api/annotations.ts`

### Step 1: Create API module

```typescript
import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface Annotation {
  id: number;
  authorPartyId: number;
  author: {
    displayName: string;
    role: string;
  };
  body: string;
  createdAt: string;
}

interface CreateAnnotationResponse {
  annotation: Annotation;
}

interface ListAnnotationsResponse {
  annotations: Annotation[];
}

export async function createAnnotation(
  agreementId: number,
  payload: { author_party_id: number; body: string },
): Promise<Annotation> {
  const res = await apiClient.post<ApiResponse<CreateAnnotationResponse>>(
    `/agreements/${agreementId}/annotations/`,
    payload,
  );
  return res.data.data.annotation;
}

export async function listAnnotations(
  agreementId: number,
): Promise<Annotation[]> {
  const res = await apiClient.get<ApiResponse<ListAnnotationsResponse>>(
    `/agreements/${agreementId}/annotations/`,
  );
  return res.data.data.annotations;
}
```

- [ ] **Step 1: Write API module**

- [ ] **Step 2: Commit**

```
feat: add annotations API module
```

---

## Task 2: React Query Hook

**Goal:** Create `useAnnotations` hook for fetching annotations list

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/features/annotations/useAnnotations.ts`

### Step 1: Create hook

```typescript
import { useQuery } from "@tanstack/react-query";
import { listAnnotations, type Annotation } from "@/api/annotations";

export function useAnnotations(agreementId: number) {
  return useQuery<Annotation[]>({
    queryKey: ["annotations", agreementId],
    queryFn: () => listAnnotations(agreementId),
  });
}
```

- [ ] **Step 1: Write useAnnotations hook**

- [ ] **Step 2: Commit**

```
feat: add useAnnotations React Query hook
```

---

## Task 3: Mutation Hook

**Goal:** Create `useAddAnnotation` hook for adding annotations

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/features/annotations/useAddAnnotation.ts`

### Step 1: Create mutation hook

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createAnnotation, type Annotation } from "@/api/annotations";

export function useAddAnnotation(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation<Annotation, Error, { author_party_id: number; body: string }>({
    mutationFn: (payload) => createAnnotation(agreementId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations", agreementId] });
    },
  });
}
```

- [ ] **Step 1: Write useAddAnnotation hook**

- [ ] **Step 2: Commit**

```
feat: add useAddAnnotation mutation hook
```

---

## Task 4: AnnotationSection Component

**Goal:** Create AnnotationSection to display notes list in Activity

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/components/annotations/AnnotationSection.tsx`

### Step 1: Create component

```typescript
import { Clock } from "lucide-react-native";
import { Text, View } from "react-native";
import { useAnnotations } from "@/features/annotations/useAnnotations";
import { colors } from "@/theme/tokens";

interface Props {
  agreementId: number;
}

export function AnnotationSection({ agreementId }: Props) {
  const { data: annotations, isLoading } = useAnnotations(agreementId);

  if (isLoading) {
    return (
      <View className="py-md">
        <Text className="text-sm text-ink-muted">Loading notes...</Text>
      </View>
    );
  }

  if (!annotations || annotations.length === 0) {
    return null;
  }

  return (
    <View className="gap-sm">
      <Text className="text-md font-semibold text-ink-primary">Notes</Text>
      <View className="bg-surface-card rounded-lg border border-border-subtle overflow-hidden">
        {annotations.map((note, i) => (
          <View
            key={note.id}
            className={[
              "flex-1 px-lg py-md gap-xs",
              i < annotations.length - 1 ? "border-b border-border-subtle" : "",
            ].join(" ")}
          >
            <View className="flex-row items-center gap-sm">
              <Clock size={14} color={colors.inkMuted} />
              <Text className="text-xs text-ink-muted">
                {note.author.displayName} · {formatRelativeTime(note.createdAt)}
              </Text>
            </View>
            <Text className="text-sm text-ink-primary">{note.body}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-GH");
}
```

- [ ] **Step 1: Write AnnotationSection component**

- [ ] **Step 2: Commit**

```
feat: add AnnotationSection component
```

---

## Task 5: AddNoteSheet Component

**Goal:** Create bottom sheet modal for adding notes

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/components/annotations/AddNoteSheet.tsx`

### Step 1: Create component

```typescript
import { useState } from "react";
import { Modal, Pressable, Text, TextInput, View } from "react-native";
import { X } from "lucide-react-native";
import { useAddAnnotation } from "@/features/annotations/useAddAnnotation";
import { colors } from "@/theme/tokens";

interface Props {
  agreementId: number;
  authorPartyId: number;
  visible: boolean;
  onClose: () => void;
}

const MAX_CHARS = 1000;

export function AddNoteSheet({ agreementId, authorPartyId, visible, onClose }: Props) {
  const [body, setBody] = useState("");
  const mutation = useAddAnnotation(agreementId);

  const handleSave = async () => {
    if (!body.trim() || !authorPartyId) return;
    try {
      await mutation.mutateAsync({
        author_party_id: authorPartyId,
        body: body.trim(),
      });
      setBody("");
      onClose();
    } catch (err) {
      // error handled by mutation state
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 justify-end bg-black/50">
        <Pressable className="flex-1" onPress={onClose} />
        <View className="bg-surface-canvas rounded-t-2xl p-lg gap-md">
          {/* Header */}
          <View className="flex-row items-center justify-between">
            <Text className="text-lg font-semibold text-ink-primary">Add note</Text>
            <Pressable onPress={onClose} hitSlop={8}>
              <X size={24} color={colors.inkMuted} />
            </Pressable>
          </View>

          {/* Text Area */}
          <TextInput
            className="bg-surface-card border border-border-subtle rounded-lg p-md text-sm text-ink-primary min-h-[120px]"
            placeholder="Add a note about this agreement..."
            placeholderTextColor={colors.inkMuted}
            value={body}
            onChangeText={setBody}
            multiline
            maxLength={MAX_CHARS}
            textAlignVertical="top"
          />

          {/* Char count */}
          <Text className="text-xs text-ink-muted text-right">
            {body.length}/{MAX_CHARS}
          </Text>

          {/* Actions */}
          <View className="flex-row gap-md">
            <Pressable
              onPress={onClose}
              className="flex-1 py-md border border-border-subtle rounded-lg"
            >
              <Text className="text-center text-md text-ink-primary">Cancel</Text>
            </Pressable>
            <Pressable
              onPress={handleSave}
              disabled={!body.trim() || mutation.isPending}
              className="flex-1 py-md bg-brand-primary rounded-lg disabled:opacity-50"
            >
              <Text className="text-center text-md font-semibold text-white">
                {mutation.isPending ? "Saving..." : "Save"}
              </Text>
            </Pressable>
          </View>

          {mutation.isError && (
            <Text className="text-xs text-semantic-error text-center">
              Failed to save note. Try again.
            </Text>
          )}
        </View>
      </View>
    </Modal>
  );
}
```

- [ ] **Step 1: Write AddNoteSheet component**

- [ ] **Step 2: Commit**

```
feat: add AddNoteSheet bottom sheet component
```

---

## Task 6: Integrate into Vault Detail

**Goal:** Add FAB + AnnotationSection to vault detail screen

**Files:**
- Modify: `Kotoku-frontend/kotoku-mobile/app/(main)/vault/[agreementId].tsx`

### Step 1: Add imports

```typescript
import { useState } from "react";
import { Plus } from "lucide-react-native";
import { AnnotationSection } from "@/components/annotations/AnnotationSection";
import { AddNoteSheet } from "@/components/annotations/AddNoteSheet";
```

### Step 2: Add state and render in component

```typescript
// Add to component:
const [noteSheetVisible, setNoteSheetVisible] = useState(false);
const canAddNote = ["sealed", "reopen_requested", "active"].includes(record.agreementStatus);

// In JSX, after Activity section:
{canAddNote && (
  <>
    <AnnotationSection agreementId={id} />
    <Pressable
      onPress={() => setNoteSheetVisible(true)}
      className="absolute bottom-lg right-lg w-14 h-14 rounded-full bg-brand-primary items-center justify-center shadow-lg"
    >
      <Plus size={24} color="white" />
    </Pressable>
    <AddNoteSheet
      agreementId={id}
      authorPartyId={record.parties[0]?.id}
      visible={noteSheetVisible}
      onClose={() => setNoteSheetVisible(false)}
    />
  </>
)}
```

- [ ] **Step 1: Import AnnotationSection + AddNoteSheet**

- [ ] **Step 2: Add noteSheetVisible state**

- [ ] **Step 3: Add canAddNote logic**

- [ ] **Step 4: Render AnnotationSection + FAB + AddNoteSheet**

- [ ] **Step 5: Commit**

```
feat: integrate annotation feature into vault detail
```

---

## Task 7: Create Annotation Directory

**Files:**
- Create: `Kotoku-frontend/kotoku-mobile/src/features/annotations/index.ts`

```typescript
export { useAnnotations } from "./useAnnotations";
export { useAddAnnotation } from "./useAddAnnotation";
```

- [ ] **Step 1: Create index.ts barrel file**

- [ ] **Step 2: Commit**

```
feat: add annotations feature barrel export
```

---

## Testing Instructions

Manual test:
1. Open app → vault → tap sealed agreement
2. Tap FAB (+) button bottom right
3. Bottom sheet opens
4. Type note → Save
5. Note appears in Activity section under "Notes"

---

## Acceptance Criteria Check

- [ ] Task 1: API module created, create + list functions
- [ ] Task 2: useAnnotations React Query hook
- [ ] Task 3: useAddAnnotation mutation hook  
- [ ] Task 4: AnnotationSection displays notes with author + time
- [ ] Task 5: AddNoteSheet bottom sheet, 1000 char limit
- [ ] Task 6: FAB + AnnotationSection in vault detail
- [ ] Task 7: Barrel export for convenience
- [ ] All code follows existing patterns (colors, spacing, components)