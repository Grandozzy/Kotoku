import { useState } from "react";
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { X } from "lucide-react-native";
import { useAddAnnotation } from "@/features/annotations/useAddAnnotation";
import { Button, NoticeCard } from "@/components/ui";
import { colors } from "@/theme/tokens";
import { useSafeAreaInsets } from "react-native-safe-area-context";

interface Props {
  agreementId: number;
  authorPartyId: number | undefined;
  visible: boolean;
  onClose: () => void;
}

const MAX_CHARS = 1000;

export function AddNoteSheet({ agreementId, authorPartyId, visible, onClose }: Props) {
  const [body, setBody] = useState("");
  const mutation = useAddAnnotation(agreementId);
  const insets = useSafeAreaInsets();

  const handleSave = async () => {
    if (!body.trim() || !authorPartyId) return;
    try {
      await mutation.mutateAsync({
        authorPartyId,
        body: body.trim(),
      });
      setBody("");
      onClose();
    } catch {
      // error handled by mutation state
    }
  };

  const handleClose = () => {
    setBody("");
    onClose();
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={handleClose}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        className="flex-1 justify-end"
      >
        <Pressable className="flex-1 bg-black/50" onPress={handleClose} />
        <ScrollView
          className="bg-surface-canvas rounded-t-[28px]"
          contentContainerClassName="p-lg gap-md"
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="interactive"
        >
          <View className="items-center gap-md">
            <View className="w-12 h-1.5 rounded-full bg-border-subtle" />
          </View>

          <View className="flex-row items-center justify-between">
            <View className="gap-xs flex-1 pr-md">
              <Text className="text-lg font-semibold text-ink-primary">Add note</Text>
              <Text className="text-sm text-ink-secondary leading-relaxed">
                Add a clear note that stays attached to this agreement for later review.
              </Text>
            </View>
            <Pressable onPress={handleClose} hitSlop={8}>
              <X size={24} color={colors.inkMuted} />
            </Pressable>
          </View>

          <View className="bg-brand-primary/8 border border-brand-primary/10 rounded-2xl p-sm">
            <Text className="text-xs font-medium text-brand-primary">
              Keep notes factual and specific so both parties can understand the context later.
            </Text>
          </View>

          <TextInput
            className="bg-surface-card border border-border-subtle rounded-2xl p-md text-sm text-ink-primary min-h-[140px]"
            placeholder="Add a note about this agreement..."
            placeholderTextColor={colors.inkMuted}
            value={body}
            onChangeText={setBody}
            multiline
            maxLength={MAX_CHARS}
            textAlignVertical="top"
          />

          <Text className="text-xs text-ink-muted text-right">
            {body.length}/{MAX_CHARS}
          </Text>

          <View className="flex-row gap-sm">
            <View className="flex-1">
              <Button title="Cancel" variant="secondary" size="md" fullWidth onPress={handleClose} />
            </View>
            <View className="flex-1">
              <Button
                title={mutation.isPending ? "Saving..." : "Save note"}
                variant="primary"
                size="md"
                fullWidth
                loading={mutation.isPending}
                disabled={!body.trim() || !authorPartyId}
                onPress={handleSave}
              />
            </View>
          </View>

          {mutation.isError && (
            <NoticeCard
              variant="error"
              title="Could not save note"
              body="The note was not saved. Check your connection and try again."
            />
          )}

          <View style={{ height: insets.bottom }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}
