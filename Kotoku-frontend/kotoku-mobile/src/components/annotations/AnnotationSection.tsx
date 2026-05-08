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