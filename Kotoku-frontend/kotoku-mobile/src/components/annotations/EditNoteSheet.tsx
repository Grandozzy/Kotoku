import { useState, useEffect } from "react";
import { KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { X } from "lucide-react-native";
import { useUpdateAnnotation } from "@/features/annotations/useUpdateAnnotation";
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

  const openWithInitialValue = (initialBody: string) => {
    setBody(initialBody);
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={handleClose}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        className="flex-1 justify-end"
      >
        <Pressable className="flex-1 bg-black/50" onPress={handleClose} />
        <ScrollView 
            className="bg-surface-canvas rounded-t-2xl p-lg gap-md" 
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="interactive"
          >
          <View className="flex-row items-center justify-between">
            <Text className="text-lg font-semibold text-ink-primary">Edit note</Text>
            <Pressable onPress={handleClose} hitSlop={8}>
              <X size={24} color={colors.inkMuted} />
            </Pressable>
          </View>

          <TextInput
            className="bg-surface-card border border-border-subtle rounded-lg p-md text-sm text-ink-primary min-h-[120px]"
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

          <View className="flex-row gap-md">
            <Pressable
              onPressIn={handleClose}
              className="flex-1 py-md border border-border-subtle rounded-lg"
            >
              <Text className="text-center text-md text-ink-primary">Cancel</Text>
            </Pressable>
            <Pressable
              onPressIn={handleSave}
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