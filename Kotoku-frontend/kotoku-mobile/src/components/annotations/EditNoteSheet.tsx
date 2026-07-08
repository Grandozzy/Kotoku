import { useState, useEffect } from "react";
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { X } from "lucide-react-native";
import { useUpdateAnnotation } from "@/features/annotations/useUpdateAnnotation";
import { Button, NoticeCard } from "@/components/ui";
import { colors } from "@/theme/tokens";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQueryClient } from "@tanstack/react-query";
import type { Annotation } from "@/api/annotations";

interface Props {
  agreementId: number;
  partyId: number;
  annotation: Annotation | null;
  visible: boolean;
  onClose: () => void;
}

const MAX_CHARS = 1000;

export function EditNoteSheet({ agreementId, partyId, annotation, visible, onClose }: Props) {
  const [body, setBody] = useState("");
  const mutation = useUpdateAnnotation(agreementId);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    if (visible && annotation) {
      setBody(annotation.body);
    }
  }, [visible, annotation]);

  const handleSave = async () => {
    if (!body.trim() || !annotation) return;
    try {
      await mutation.mutateAsync({
        annotationId: annotation.id,
        partyId,
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
              <Text className="text-lg font-semibold text-ink-primary">Edit note</Text>
              <Text className="text-sm text-ink-secondary leading-relaxed">
                Update the wording without losing the original agreement context.
              </Text>
            </View>
            <Pressable onPress={handleClose} hitSlop={8}>
              <X size={24} color={colors.inkMuted} />
            </Pressable>
          </View>

          <View className="bg-brand-primary/8 border border-brand-primary/10 rounded-2xl p-sm">
            <Text className="text-xs font-medium text-brand-primary">
              Keep edits concise and accurate so the record stays easy to follow.
            </Text>
          </View>

          <TextInput
            className="bg-surface-card border border-border-subtle rounded-2xl p-md text-sm text-ink-primary min-h-[140px]"
            placeholder="Edit your note..."
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
                title={mutation.isPending ? "Saving..." : "Save changes"}
                variant="primary"
                size="md"
                fullWidth
                loading={mutation.isPending}
                disabled={!body.trim()}
                onPress={handleSave}
              />
            </View>
          </View>

          {mutation.isError && (
            <NoticeCard
              variant="error"
              title="Could not update note"
              body="The latest changes were not saved. Try again once the connection is stable."
            />
          )}

          <View style={{ height: insets.bottom }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export function useEditNoteSheet(agreementId: number) {
  const [annotation, setAnnotation] = useState<Annotation | null>(null);
  const [visible, setVisible] = useState(false);
  const queryClient = useQueryClient();

  const open = async (a: Annotation) => {
    await queryClient.invalidateQueries({ queryKey: ["annotations", agreementId] });
    const fresh = queryClient.getQueryData<Annotation[]>(["annotations", agreementId]);
    const latest = fresh?.find((n) => n.id === a.id) || a;
    setAnnotation(latest);
    setVisible(true);
  };

  const close = () => {
    setAnnotation(null);
    setVisible(false);
  };

  return { annotation, visible, open, close };
}
