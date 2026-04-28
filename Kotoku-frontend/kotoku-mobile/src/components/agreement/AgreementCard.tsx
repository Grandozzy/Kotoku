import { useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { Badge } from "@/components/ui";
import { colors } from "@/theme/tokens";
import type { Agreement, AgreementStatus } from "@/types/agreement";

function statusVariant(
  status: AgreementStatus,
): "default" | "success" | "warning" | "sealed" | "draft" {
  switch (status) {
    case "sealed":
    case "annotated_post_seal":
      return "sealed";
    case "draft":
    case "awaiting_other_party":
      return "draft";
    case "ready_to_seal":
    case "ready_for_review":
      return "warning";
    default:
      return "default";
  }
}

function statusLabel(status: AgreementStatus): string {
  const map: Partial<Record<AgreementStatus, string>> = {
    draft: "Draft",
    awaiting_other_party: "Awaiting party",
    ready_for_review: "Ready for review",
    ready_to_seal: "Ready to seal",
    sealed: "Sealed",
    reopen_requested: "Reopen requested",
    archived: "Archived",
    expired: "Expired",
  };
  return map[status] ?? status;
}

interface AgreementCardProps {
  agreement: Agreement;
}

export function AgreementCard({ agreement }: AgreementCardProps) {
  const router = useRouter();

  return (
    <Pressable
      onPress={() => router.push(`/agreement/${agreement.id}/steps/review`)}
      className="bg-surface-card rounded-lg p-lg flex-row items-center justify-between border border-border-subtle active:opacity-70"
    >
      <View className="flex-1 gap-xs mr-md">
        <Text className="text-md font-semibold text-ink-primary" numberOfLines={1}>
          {agreement.title}
        </Text>
        <Text className="text-xs text-ink-muted">
          {new Date(agreement.createdAt).toLocaleDateString("en-GH", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </Text>
        <Badge
          label={statusLabel(agreement.status)}
          variant={statusVariant(agreement.status)}
        />
      </View>
      <ChevronRight size={18} color={colors.inkMuted} />
    </Pressable>
  );
}
