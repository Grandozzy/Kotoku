import { useState } from "react";
import { Alert } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ChevronLeft, Clock, Loader2, Pencil } from "lucide-react-native";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge } from "@/components/ui";
import { useAuth } from "@/features/auth/useAuth";
import { apiClient } from "@/api/client";
import { ExportButton } from "@/components/vault/ExportButton";
import { ReopenSection } from "@/components/vault/ReopenSection";
import { getAgreement } from "@/api/agreements";
import { useAgreementStore, type PartyDraft } from "@/features/agreements/agreementStore";
import { useAuditLog, useRequestExport, useRetryExport, useVaultRecord } from "@/features/vault/useVault";
import type { ScenarioId } from "@/constants/scenarios";
import { colors } from "@/theme/tokens";

function mapPartyToDraft(fullName: string, phone: string, idType: string, idNumber: string): PartyDraft {
  return {
    fullName,
    phone,
    idType: idType as PartyDraft["idType"],
    idNumber,
  };
}

export default function VaultDetailScreen() {
  const router = useRouter();
  const { agreementId } = useLocalSearchParams<{ agreementId: string }>();
  const id = Number(agreementId);
  const insets = useSafeAreaInsets();

  const { data: record, isLoading } = useVaultRecord(id);
  const { data: auditLog } = useAuditLog(id);
  const exportMutation = useRequestExport(id);
  const retryMutation = useRetryExport(id);
  const initReopened = useAgreementStore((s) => s.initReopened);
  const { phone: currentPhone } = useAuth();

  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const isSealed = record && record.agreementStatus !== "active";
  const userParty = record?.parties.find((p) => p.phone === currentPhone);

  const handleEdit = async () => {
    setEditLoading(true);
    setEditError(null);
    try {
      const agreement = await getAgreement(id);
      let partyA: PartyDraft | undefined;
      let partyB: PartyDraft | undefined;
      if (agreement.parties.length >= 2) {
        const pA = agreement.parties[0];
        const pB = agreement.parties[1];
        partyA = mapPartyToDraft(pA.displayName, pA.phone, pA.idType ?? "ghana_card", pA.idNumber ?? "");
        partyB = mapPartyToDraft(pB.displayName, pB.phone, pB.idType ?? "ghana_card", pB.idNumber ?? "");
      }
      const scId = record!.scenarioId;
      initReopened(record!.agreementId, scId as ScenarioId, partyA, partyB, agreement.fieldData);
      router.push(`/agreement/${record!.agreementId}/steps/parties?scenarioId=${scId}`);
    } catch {
      setEditError("Failed to load agreement data");
    } finally {
      setEditLoading(false);
    }
  };

  const handleRaiseDispute = async () => {
    Alert.prompt(
      "Raise Dispute",
      "Enter the reason for this dispute (minimum 10 characters)",
      async (reason) => {
        if (!reason || reason.trim().length < 10) {
          Alert.alert("Error", "Please provide at least 10 characters");
          return;
        }
        try {
          await apiClient.post(`/v1/agreements/${id}/disputes`, {
            raised_by_party_id: userParty?.id,
            reason: reason.trim(),
          });
          Alert.alert("Success", "Dispute has been raised", [
            { text: "OK", onPress: () => router.push("/disputes") },
          ]);
        } catch {
          Alert.alert("Error", "Failed to raise dispute");
        }
      },
      "plain-text",
      "",
      "default",
    );
  };

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
              disabled={editLoading}
              onPress={handleEdit}
              className="flex-row items-center justify-center gap-sm bg-brand-primary rounded-lg py-md active:opacity-80"
            >
              {editLoading ? (
                <Loader2 size={18} color="white" />
              ) : (
                <Pencil size={18} color="white" />
              )}
              <Text className="text-md font-semibold text-white">
                {editLoading ? "Loading…" : "Edit agreement"}
              </Text>
            </Pressable>
            {editError && (
              <Text className="text-xs text-semantic-error text-center">{editError}</Text>
            )}
          </View>
        )}

        <ReopenSection
          agreementId={record.agreementId}
          agreementStatus={record.agreementStatus}
          parties={record.parties}
        />

        {/* PDF export */}
        <View className="gap-sm">
          <Text className="text-md font-semibold text-ink-primary">Export</Text>
          <ExportButton
            pdfStatus={record.pdfStatus}
            pdfUrl={record.pdfUrl}
            onRequestExport={() => exportMutation.mutate()}
            onRetryExport={() => retryMutation.mutate()}
            isRequesting={exportMutation.isPending}
            isRetrying={retryMutation.isPending}
          />
          {exportMutation.isError && (
            <Text className="text-xs text-semantic-error text-center">
              Export request failed. Please try again.
            </Text>
          )}
        </View>

        {/* Raise Dispute */}
        {isSealed && userParty && (
          <Pressable
            onPress={handleRaiseDispute}
            className="flex-row items-center justify-center gap-sm bg-semantic-warning/10 border border-semantic-warning/30 rounded-lg py-md active:opacity-80"
          >
            <Text className="text-md font-semibold text-semantic-warning">
              Raise Dispute
            </Text>
          </Pressable>
        )}

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
