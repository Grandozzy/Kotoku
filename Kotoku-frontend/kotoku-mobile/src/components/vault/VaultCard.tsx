import { useRouter } from "expo-router";
import { ChevronRight, Lock } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";

import { Badge } from "@/components/ui";
import { colors } from "@/theme/tokens";
import type { VaultRecord } from "@/types/vault";

function retentionLabel(expiresAt: string): string {
  const days = Math.ceil(
    (new Date(expiresAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
  );
  if (days < 0) return "Expired";
  if (days <= 14) return `${days}d left`;
  return new Date(expiresAt).toLocaleDateString("en-GH", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

interface VaultCardProps {
  record: VaultRecord;
  title: string;
  scenarioLabel: string;
  counterpartyName?: string;
}

export function VaultCard({
  record,
  title,
  scenarioLabel,
  counterpartyName,
}: VaultCardProps) {
  const router = useRouter();
  const expired = record.status === "expired";

  let badgeLabel: string;
  let badgeVariant: "default" | "sealed";
  let borderClass = "";

  if (record.agreementStatus === "reopen_requested") {
    badgeLabel = "Reopen Requested";
    badgeVariant = "default";
  } else if (record.agreementStatus === "active") {
    badgeLabel = "Active";
    badgeVariant = "sealed";
  } else {
    badgeLabel = expired ? "Expired" : "Sealed";
    badgeVariant = expired ? "default" : "sealed";
  }

  return (
    <Pressable
      onPress={() => router.push(`/(main)/vault/${record.agreementId}`)}
      accessibilityRole="button"
      accessibilityLabel={`Open vaulted agreement ${title}`}
      className={[
        "bg-surface-card rounded-lg border border-border-subtle p-lg flex-row items-center gap-md active:opacity-70",
        borderClass,
      ].join(" ")}
    >
      {/* Icon */}
      <View
        className={[
          "w-11 h-11 rounded-lg items-center justify-center",
          expired ? "bg-surface-subtle" : "bg-brand-primarySoft",
        ].join(" ")}
      >
        <Lock
          size={20}
          color={expired ? colors.inkMuted : colors.brandPrimary}
          strokeWidth={1.8}
        />
      </View>

      {/* Content */}
      <View className="flex-1 gap-xs">
        <Text
          className="text-md font-semibold text-ink-primary"
          numberOfLines={1}
        >
          {title}
        </Text>
        <Text className="text-xs text-ink-muted">{scenarioLabel}</Text>
        {counterpartyName && (
          <Text className="text-xs text-ink-secondary">
            With {counterpartyName}
          </Text>
        )}
        <View className="flex-row items-center gap-sm mt-xs">
          <Badge label={badgeLabel} variant={badgeVariant} />
          <Text className="text-xs text-ink-muted ml-auto">
            {retentionLabel(record.retentionExpiresAt)}
          </Text>
        </View>
      </View>

      <ChevronRight size={16} color={colors.inkMuted} />
    </Pressable>
  );
}
