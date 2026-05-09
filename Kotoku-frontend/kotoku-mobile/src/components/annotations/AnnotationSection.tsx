import { useState } from "react";
import { Clock } from "lucide-react-native";
import { Text, View } from "react-native";
import { useAnnotations, useDeleteAnnotation } from "@/features/annotations";
import { colors } from "@/theme/tokens";
import { SwipeableRow } from "./SwipeableRow";
import { EditNoteSheet, useEditNoteSheet } from "./EditNoteSheet";
import type { Annotation } from "@/api/annotations";

interface Props {
  agreementId: number;
  partyId: number;
}

export function AnnotationSection({ agreementId, partyId }: Props) {
  const { data: annotations, isLoading } = useAnnotations(agreementId);
  const deleteMutation = useDeleteAnnotation(agreementId);
  const { annotation, visible: editVisible, open: openEdit, close: closeEdit } = useEditNoteSheet(agreementId);

  const handleDelete = (annotationId: number) => {
    deleteMutation.mutate({ annotationId, partyId });
  };

  const handleEdit = (note: Annotation) => {
    openEdit(note);
  };

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
      <View className="rounded-lg overflow-hidden">
        {annotations.map((note, i) => {
          const canDelete = note.authorPartyId === partyId;
          return (
            <View
              key={note.id}
              className={i < annotations.length - 1 ? "border-b border-border-subtle" : ""}
            >
              <SwipeableRow
                onDelete={() => handleDelete(note.id)}
                onEdit={() => handleEdit(note)}
                note={note}
                disabled={!canDelete}
              >
                <View className="flex-1 px-lg py-md gap-xs bg-surface-card">
                  <View className="flex-row items-center gap-sm">
                    <Clock size={14} color={colors.inkMuted} />
                    <Text className="text-xs text-ink-muted">
                      {note.authorDisplayName} · {formatRelativeTime(note.createdAt)}
                    </Text>
                  </View>
                  <Text className="text-sm text-ink-primary">{note.body}</Text>
                </View>
              </SwipeableRow>
            </View>
          );
        })}
      </View>
      <EditNoteSheet
        agreementId={agreementId}
        partyId={partyId}
        annotation={annotation}
        visible={editVisible}
        onClose={closeEdit}
      />
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