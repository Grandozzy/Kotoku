import { Clock, Trash2 } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";
import { useAnnotations, useDeleteAnnotation } from "@/features/annotations";
import { colors } from "@/theme/tokens";

interface Props {
  agreementId: number;
  partyId: number;
}

export function AnnotationSection({ agreementId, partyId }: Props) {
  const { data: annotations, isLoading } = useAnnotations(agreementId);
  const deleteMutation = useDeleteAnnotation(agreementId);

  const handleDelete = (annotationId: number) => {
    console.log("Deleting annotation:", annotationId, "partyId:", partyId);
    if (!partyId) {
      console.error("No partyId available");
      return;
    }
    deleteMutation.mutate({ annotationId, partyId });
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
      <View className="bg-surface-card rounded-lg border border-border-subtle overflow-hidden">
        {annotations.map((note, i) => (
          <View
            key={note.id}
            className={[
              "flex-1 px-lg py-md gap-xs",
              i < annotations.length - 1 ? "border-b border-border-subtle" : "",
            ].join(" ")}
          >
            <View className="flex-row items-center justify-between">
              <View className="flex-row items-center gap-sm flex-1">
                <Clock size={14} color={colors.inkMuted} />
                <Text className="text-xs text-ink-muted">
                  {note.authorDisplayName} · {formatRelativeTime(note.createdAt)}
                </Text>
              </View>
              {note.authorPartyId === partyId && (
                <Pressable onPressIn={() => handleDelete(note.id)} hitSlop={8}>
                  <Trash2 size={16} color={colors.semanticError} />
                </Pressable>
              )}
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