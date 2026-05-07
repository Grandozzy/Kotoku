import { useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft, Clock, Pencil } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge } from "@/components/ui";
import { ExportButton } from "@/components/vault/ExportButton";
import { ReopenSection } from "@/components/vault/ReopenSection";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { useAuditLog, useRequestExport, useVaultRecord } from "@/features/vault/useVault";
import type { ScenarioId } from "@/constants/scenarios";
import { colors } from "@/theme/tokens";

export default function VaultDetailScreen() {
  const router = useRouter();
  const { agreementId } = useLocalSearchParams<{ agreementId: string }>();
  const id = Number(agreementId);
  const insets = useSafeAreaInsets();

  const { data: record, isLoading } = useVaultRecord(id);
  const { data: auditLog } = useAuditLog(id);
  const exportMutation = useRequestExport(id);
  const initReopened = useAgreementStore((s) => s.initReopened);

  if (isLoading || !record) {
    return (
      <View className="flex-1 bg-surface-canvas items-center justify-center">
        <Text className="text-sm text-ink-muted">Loading…</Text>
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="pb-2xl"
    >
      {/* Top bar */}
      <View className="flex-row items-center px-lg pb-md gap-md" style={{ paddingTop: insets.top + 12 }}>
        <Pressable onPress={() => router.back()}>
          <ChevronLeft size={24} color={colors.inkPrimary} />
        </Pressable>
        <Text className="text-xl font-semibold text-ink-primary flex-1">
          {record.title}
        </Text>
        <Badge
          label={
            record.agreementStatus === "reopen_requested"
              ? "Reopen Requested"
              : record.agreementStatus === "active"
                ? "Active"
                : record.status === "expired"
                  ? "Expired"
                  : "Sealed"
          }
          variant={
            record.agreementStatus === "reopen_requested"
              ? "default"
              : record.agreementStatus === "active"
                ? "sealed"
                : record.status === "expired"
                  ? "default"
                  : "sealed"
          }
        />
      </View>

      <View className="px-lg gap-xl">
        {/* Seal details — only shown when sealed */}
        {record.sealedAt && (
          <View className="bg-surface-card rounded-lg border border-border-subtle p-lg gap-sm">
            <DetailRow
              label="Sealed on"
              value={new Date(record.sealedAt).toLocaleDateString("en-GH", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            />
            <DetailRow
              label="Free retention until"
              value={new Date(record.retentionExpiresAt).toLocaleDateString(
                "en-GH",
                { day: "numeric", month: "short", year: "numeric" },
              )}
            />
          </View>
        )}

        {record.agreementStatus === "active" && (
          <View className="gap-sm">
            <Pressable
              onPress={() => {
                initReopened(record.agreementId, record.scenarioId as ScenarioId);
                router.push(`/agreement/${record.agreementId}/steps/parties`);
              }}
              className="flex-row items-center justify-center gap-sm bg-brand-primary rounded-lg py-md active:opacity-80"
            >
              <Pencil size={18} color="white" />
              <Text className="text-md font-semibold text-white">
                Edit agreement
              </Text>
            </Pressable>
          </View>
        )}

        <ReopenSection
          agreementId={record.agreementId}
          agreementStatus={record.agreementStatus}
          createdByPhone={record.createdByPhone}
        />

        {/* PDF export */}
        <View className="gap-sm">
          <Text className="text-md font-semibold text-ink-primary">Export</Text>
          <ExportButton
            pdfStatus={record.pdfStatus}
            pdfUrl={record.pdfUrl}
            onRequestExport={() => exportMutation.mutate()}
            isRequesting={exportMutation.isPending}
          />
          {exportMutation.isError && (
            <Text className="text-xs text-semantic-error text-center">
              Export request failed. Please try again.
            </Text>
          )}
        </View>

        {/* Audit log */}
        {auditLog && auditLog.length > 0 && (
          <View className="gap-sm">
            <Text className="text-md font-semibold text-ink-primary">
              Activity
            </Text>
            <View className="bg-surface-card rounded-lg border border-border-subtle overflow-hidden">
              {auditLog.map((event, i) => (
                <View
                  key={event.id}
                  className={[
                    "flex-row items-start px-lg py-md gap-md",
                    i < auditLog.length - 1 ? "border-b border-border-subtle" : "",
                  ].join(" ")}
                >
                  <Clock size={14} color={colors.inkMuted} style={{ marginTop: 2 }} />
                  <View className="flex-1">
                    <Text className="text-sm text-ink-primary">
                      {formatEventType(event.eventType)}
                    </Text>
                    <Text className="text-xs text-ink-muted mt-xs">
                      {new Date(event.createdAt).toLocaleString("en-GH")}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row justify-between gap-md">
      <Text className="text-sm text-ink-muted">{label}</Text>
      <Text className="text-sm font-medium text-ink-primary text-right flex-1">
        {value}
      </Text>
    </View>
  );
}

function formatEventType(type: string): string {
  return type
    .replace(/\./g, " ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
