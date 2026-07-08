import { useRouter } from "expo-router";
import { ChevronRight, FileText, Lock } from "lucide-react-native";
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

function sealedDateLabel(sealedAt: string): string {
  return new Date(sealedAt).toLocaleDateString("en-GH", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function partySummary(record: VaultRecord): string {
  if (record.parties.length >= 2) {
    return `${record.parties[0].displayName} · ${record.parties[1].displayName}`;
  }
  if (record.parties.length === 1) {
    return record.parties[0].displayName;
  }
  return "Sealed agreement";
}

function pdfBadge(record: VaultRecord): {
  label: string;
  variant: "default" | "success" | "warning" | "error" | "info";
} {
  if (record.pdfStatus === "ready") return { label: "PDF ready", variant: "success" };
  if (record.pdfStatus === "generating") return { label: "Generating", variant: "info" };
  if (record.pdfStatus === "failed") return { label: "PDF failed", variant: "error" };
  return { label: "PDF pending", variant: "default" };
}

interface VaultCardProps {
  record: VaultRecord;
  title: string;
  counterpartyName?: string;
}

export function VaultCard({
  record,
  title,
  counterpartyName,
}: VaultCardProps) {
  const router = useRouter();
  const expired = record.status === "expired";
  const pdf = pdfBadge(record);

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
        "flex-row items-center gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg active:opacity-70",
        borderClass,
      ].join(" ")}
    >
      {/* Icon */}
      <View
        className={[
          "h-12 w-12 items-center justify-center rounded-2xl",
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
        <View className="flex-row items-center gap-sm">
          <Badge label={badgeLabel} variant={badgeVariant} />
          <Badge label={pdf.label} variant={pdf.variant} />
        </View>
        <Text
          className="text-md font-semibold text-ink-primary"
          numberOfLines={1}
        >
          {title}
        </Text>
        <Text className="text-xs text-ink-secondary" numberOfLines={1}>
          {counterpartyName ? `With ${counterpartyName}` : partySummary(record)}
        </Text>
        {counterpartyName && (
          <Text className="text-xs text-ink-muted" numberOfLines={1}>
            {partySummary(record)}
          </Text>
        )}
        <Text className="text-xs text-ink-muted">
          Sealed {sealedDateLabel(record.sealedAt)} · Retention {retentionLabel(record.retentionExpiresAt)}
        </Text>
        <View className="mt-xs flex-row items-center gap-xs">
          <View className="ml-auto flex-row items-center gap-xs rounded-full bg-surface-subtle px-sm py-xs">
            <FileText size={12} color={colors.inkMuted} />
            <Text className="text-xs text-ink-muted">Open</Text>
          </View>
        </View>
      </View>

      <ChevronRight size={16} color={colors.inkMuted} />
    </Pressable>
  );
}
