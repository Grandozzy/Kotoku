import { useRouter } from "expo-router";
import {
  AlertCircle,
  ChevronRight,
  FileText,
  Handshake,
  Trash2,
  TrendingUp,
} from "lucide-react-native";
import { useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Badge, BottomSheet, Button, CardSkeleton, EmptyState, ErrorState, NoticeCard } from "@/components/ui";
import { deleteDraft, getAgreement } from "@/api/agreements";
import { usePendingActions } from "@/features/agreements/usePendingActions";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { getDraftResumeStep } from "@/features/agreements/resumeStep";
import { formatCapResetDate, getCapReachedMessage } from "@/features/billing/capReached";
import { usePlan } from "@/features/billing/usePlan";
import type { ScenarioId } from "@/constants/scenarios";
import { SCENARIOS } from "@/constants/scenarios";
import { isSamePhone } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";
import { colors } from "@/theme/tokens";

const SCENARIO_LABELS: Record<string, string> = {};
for (const s of SCENARIOS) {
  SCENARIO_LABELS[s.id] = s.label;
}

type HomeAgreementItem = {
  id: number;
  title: string;
  updated_at?: string;
  scenario_template: string;
  status: string;
  parties?: Array<{ role: string; full_name: string; phone?: string }>;
};

export default function HomeScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { data, isError, isLoading, refetch } = usePendingActions();
  const { data: plan } = usePlan();

  const actionRequired = data?.action_required ?? [];
  const drafts = data?.drafts ?? [];
  const isEmpty = !isLoading && actionRequired.length === 0 && drafts.length === 0;

  const usage = plan?.usage;
  const flags = plan?.flags;
  const showUsagePill =
    plan && flags?.is_personal && usage !== undefined;
  const capReached = usage?.is_cap_reached ?? false;
  const nearCap = usage?.is_near_cap ?? false;
  const showUpgradeBanner =
    !!plan && flags?.show_upgrade_recommendation && plan.recommended_upgrades.length > 0;
  const capResetDate = formatCapResetDate(usage?.period.end);

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={refetch}
          tintColor={colors.brandPrimary}
        />
      }
    >
      <View className="flex-row items-center justify-between">
        <View>
          <Text className="text-2xl font-semibold text-ink-primary">Home</Text>
          {showUsagePill ? (
            <Text
              className={`text-sm mt-xs font-medium ${
                capReached
                  ? "text-semantic-error"
                  : nearCap
                  ? "text-amber-600"
                  : "text-ink-secondary"
              }`}
            >
              {capReached
                ? `Monthly limit reached (${plan.plan.name})`
                : `${usage!.remaining_agreements_this_period} agreement${
                    usage!.remaining_agreements_this_period === 1 ? "" : "s"
                  } left this month`}
            </Text>
          ) : (
            <Text className="text-sm text-ink-secondary mt-xs">
              Start or resume an agreement
            </Text>
          )}
        </View>
        <Button
          title="New"
          variant="primary"
          size="sm"
          onPress={() => router.push("/agreement/new")}
        />
      </View>

      {/* Upgrade banner — shown when cap reached or business misuse suspected */}
      {showUpgradeBanner && (
        <Pressable
          className="active:opacity-70"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onPress={() => router.push("/(main)/plans" as any)}
        >
          <NoticeCard
            variant="warning"
            icon={TrendingUp}
            title={
              capReached
                ? `You've reached your ${plan!.plan.max_agreements_per_month} agreement limit for ${plan!.plan.name}`
                : "You're using Kotoku like a business"
            }
            body={
              capReached
                ? getCapReachedMessage(plan!, plan!.recommended_upgrades[0])
                : "Switch to an Enterprise plan for higher volume, team access, and longer retention."
            }
            footer={
              plan!.recommended_upgrades[0] ? (
                <Text className="text-xs font-semibold text-amber-900">
                  Next: {plan!.recommended_upgrades[0].name} — {plan!.recommended_upgrades[0].price_amount_monthly} GHS/mo
                  {capReached && capResetDate ? ` · Resets ${capResetDate}` : ""}
                </Text>
              ) : null
            }
          />
        </Pressable>
      )}

      {isLoading && (
        <View className="gap-sm">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </View>
      )}

      {isError && !isLoading && (
        <ErrorState
          title="Could not load your agreements"
          body="Check your connection and try again. Your drafts and pending actions will appear once Kotoku reconnects."
          onAction={() => refetch()}
        />
      )}

      {!isLoading && !isError && actionRequired.length > 0 && (
        <View className="gap-sm">
          <Text className="text-xs font-semibold text-amber-600 uppercase tracking-widest">
            Action required
          </Text>
          {actionRequired.map((item) => (
            <ActionCard key={item.id} item={item} onDeleted={refetch} />
          ))}
        </View>
      )}

      {!isLoading && !isError && drafts.length > 0 && (
        <View className="gap-sm">
          <Text className="text-xs font-semibold text-ink-muted uppercase tracking-widest">
            Drafts
          </Text>
          {drafts.map((item) => (
            <DraftCard key={item.id} item={item} onDeleted={refetch} />
          ))}
        </View>
      )}

      {isEmpty && !isError && (
        <EmptyState
          icon={Handshake}
          title="Your first agreement is one tap away"
          body="Seal a deal with anyone. Record evidence, collect consent via SMS, and create a tamper-proof vault entry in under five minutes."
          action={{
            label: "New agreement",
            onPress: () => router.push("/agreement/new"),
          }}
        />
      )}
    </ScrollView>
  );
}

function ActionCard({ item, onDeleted }: { item: HomeAgreementItem; onDeleted: () => void }) {
  const router = useRouter();
  const initForConsent = useAgreementStore((s) => s.initForConsent);
  const sessionPhone = useSessionStore((s) => s.phone);
  const [loading, setLoading] = useState(false);
  const [deleteSheetVisible, setDeleteSheetVisible] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handlePress = async () => {
    if (item.status === "pending_consent") {
      setLoading(true);
      try {
        const agreement = await getAgreement(item.id);
        const pA = agreement.parties[0];
        const pB = agreement.parties[1];
        initForConsent(
          agreement.id,
          agreement.scenarioId as ScenarioId,
          { fullName: pA.displayName, phone: pA.phone, idType: pA.idType ?? "ghana_card", idNumber: pA.idNumber ?? "" },
          { fullName: pB.displayName, phone: pB.phone, idType: pB.idType ?? "ghana_card", idNumber: pB.idNumber ?? "" },
        );
        router.push(`/agreement/${agreement.id}/steps/consent?scenarioId=${agreement.scenarioId}`);
      } catch {
      } finally {
        setLoading(false);
      }
    } else if (item.status === "reopen_requested") {
      router.push(`/(main)/vault/${item.id}`);
    } else {
      router.push(`/agreement/${item.id}/steps/review?scenarioId=${item.scenario_template}`);
    }
  };

  const handleDelete = () => {
    if (item.status !== "pending_consent") return;
    setDeleteError(null);
    setDeleteSheetVisible(true);
  };

  const label =
    item.status === "reopen_requested"
      ? "Reopen requested. Enter your code."
      : item.status === "pending_consent"
        ? "Pending your consent. Enter your code."
        : item.status;
  const canDeletePendingAgreement =
    item.status === "pending_consent" &&
    isSamePhone(sessionPhone, item.parties?.[0]?.phone);

  return (
    <Pressable
      onPress={handlePress}
      disabled={loading}
      accessibilityRole="button"
      accessibilityLabel={`Open ${item.title}`}
      className="bg-surface-card rounded-xl border border-amber-200 p-lg active:opacity-70"
    >
      <View className="flex-row items-start gap-md">
        <View className="flex-1">
          <View className="flex-row items-center gap-sm">
            <Text className="text-md font-semibold text-ink-primary flex-1" numberOfLines={1}>
              {item.title}
            </Text>
            <AgreementStatusBadge status={item.status} />
          </View>
          <Text className="text-sm text-amber-600 mt-xs">{label}</Text>
          <View className="flex-row items-center gap-xs mt-xs">
            <Text className="text-xs text-brand-primary">
              {loading ? "Loading…" : "Tap to continue"}
            </Text>
            {!loading && <ChevronRight size={12} color={colors.brandPrimary} strokeWidth={2} />}
          </View>
        </View>
        {canDeletePendingAgreement && (
          <Pressable
            onPress={handleDelete}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel={`Delete ${item.title}`}
            className="w-9 h-9 rounded-full bg-rose-50 items-center justify-center active:opacity-70"
          >
            <Trash2 size={16} color="#dc2626" strokeWidth={2} />
          </Pressable>
        )}
      </View>
      <BottomSheet
        visible={deleteSheetVisible}
        onClose={() => setDeleteSheetVisible(false)}
        title="Delete uncompleted agreement?"
        body={`Delete "${item.title}"? This removes the pending agreement and cannot be undone.`}
        icon={AlertCircle}
        tone="danger"
        footer={
          <>
            {deleteError ? (
              <NoticeCard
                variant="error"
                title="Could not delete agreement"
                body={deleteError}
                compact
              />
            ) : null}
            <Button
              title="Keep agreement"
              variant="secondary"
              size="lg"
              fullWidth
              onPress={() => setDeleteSheetVisible(false)}
            />
            <Button
              title="Delete agreement"
              variant="primary"
              size="lg"
              fullWidth
              onPress={async () => {
                try {
                  await deleteDraft(item.id);
                  setDeleteSheetVisible(false);
                  onDeleted();
                } catch {
                  setDeleteError(
                    "Only the creator can delete an uncompleted agreement. If you are the creator, try again.",
                  );
                }
              }}
            />
          </>
        }
      />
    </Pressable>
  );
}

function DraftCard({ item, onDeleted }: { item: HomeAgreementItem; onDeleted: () => void }) {
  const router = useRouter();
  const hydrateDraft = useAgreementStore((s) => s.hydrateDraft);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [deleteSheetVisible, setDeleteSheetVisible] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handlePress = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const agreement = await getAgreement(item.id);
      const partyA = agreement.parties[0];
      const partyB = agreement.parties[1];
      const resumeStep =
        item.status !== "draft"
          ? { step: "review" as const, index: 3 as const }
          : getDraftResumeStep(agreement);

      hydrateDraft(
        agreement.id,
        agreement.scenarioId,
        resumeStep.index,
        partyA
          ? {
              fullName: partyA.displayName,
              phone: partyA.phone,
              idType: partyA.idType ?? "ghana_card",
              idNumber: partyA.idNumber ?? "",
            }
          : undefined,
        partyB
          ? {
              fullName: partyB.displayName,
              phone: partyB.phone,
              idType: partyB.idType ?? "ghana_card",
              idNumber: partyB.idNumber ?? "",
            }
          : undefined,
        agreement.fieldData,
      );
      router.push(
        `/agreement/${agreement.id}/steps/${resumeStep.step}?scenarioId=${agreement.scenarioId}`,
      );
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    setDeleteError(null);
    setDeleteSheetVisible(true);
  };

  const relativeTime = item.updated_at ? getRelativeTime(item.updated_at) : "Recently updated";
  const scenarioLabel = SCENARIO_LABELS[item.scenario_template] ?? item.scenario_template;
  const partyNames = item.parties?.map(p => p.full_name).join(", ");

  return (
    <Pressable
      onPress={handlePress}
      disabled={loading}
      accessibilityRole="button"
      accessibilityLabel={`Continue ${item.title}`}
      className="bg-surface-card rounded-xl border border-border-subtle p-lg active:opacity-70"
    >
      <View className="flex-row items-start gap-md">
        <View className="w-9 h-9 rounded-lg bg-surface-canvas items-center justify-center mt-xs">
          <FileText size={16} color={colors.inkSecondary} strokeWidth={1.8} />
        </View>
        <View className="flex-1">
          <View className="flex-row items-center gap-sm">
            <Text className="text-md font-semibold text-ink-primary flex-1" numberOfLines={1}>
              {item.title}
            </Text>
            <AgreementStatusBadge status={item.status} />
          </View>
          <Text className="text-xs text-ink-muted mt-xs">{scenarioLabel} · {relativeTime}</Text>
          {partyNames && <Text className="text-xs text-ink-secondary mt-xs">{partyNames}</Text>}
          <View className="flex-row items-center justify-between mt-xs">
            <View className="flex-row items-center gap-xs">
              <Text className="text-xs text-brand-primary">
                {loading ? "Loading…" : "Continue"}
              </Text>
              {!loading && <ChevronRight size={12} color={colors.brandPrimary} strokeWidth={2} />}
            </View>
            <Pressable
              onPress={handleDelete}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel={`Delete ${item.title}`}
              className="flex-row items-center gap-xs rounded-full bg-rose-50 px-sm py-xs active:opacity-70"
            >
              <Trash2 size={12} color="#dc2626" strokeWidth={2} />
              <Text className="text-xs font-medium text-rose-700">Delete</Text>
            </Pressable>
          </View>
        </View>
      </View>
      {loadError ? (
        <View className="mt-md">
          <NoticeCard
            variant="error"
            title="Could not load this draft"
            body="Please try again."
            compact
          />
        </View>
      ) : null}
      <BottomSheet
        visible={deleteSheetVisible}
        onClose={() => setDeleteSheetVisible(false)}
        title="Delete draft?"
        body={`Delete "${item.title}"? This cannot be undone.`}
        icon={AlertCircle}
        tone="danger"
        footer={
          <>
            {deleteError ? (
              <NoticeCard
                variant="error"
                title="Could not delete draft"
                body={deleteError}
                compact
              />
            ) : null}
            <Button
              title="Keep draft"
              variant="secondary"
              size="lg"
              fullWidth
              onPress={() => setDeleteSheetVisible(false)}
            />
            <Button
              title="Delete draft"
              variant="primary"
              size="lg"
              fullWidth
              onPress={async () => {
                try {
                  await deleteDraft(item.id);
                  setDeleteSheetVisible(false);
                  onDeleted();
                } catch {
                  setDeleteError("Please try again.");
                }
              }}
            />
          </>
        }
      />
    </Pressable>
  );
}

function AgreementStatusBadge({ status }: { status: string }) {
  if (status === "draft") return <Badge label="Draft" variant="draft" />;
  if (status === "pending_consent") {
    return <Badge label="Awaiting consent" variant="warning" />;
  }
  if (status === "reopen_requested") {
    return <Badge label="Reopen" variant="info" />;
  }
  if (status === "active") return <Badge label="Ready" variant="success" />;
  return <Badge label={status.replaceAll("_", " ")} variant="default" />;
}

function getRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
