import { Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useState, useEffect } from "react";

import { Card, Button } from "@/components/ui";
import { apiClient } from "@/api/client";
import { colors } from "@/theme/tokens";

interface DisputeDetail {
  id: number;
  agreement_id: number;
  agreement_type: string;
  agreement_sealed_at: string;
  raised_by_display_name: string;
  reason: string;
  status: string;
  resolution?: string;
  created_at: string;
}

export default function DisputeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [dispute, setDispute] = useState<DisputeDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDetail() {
      try {
        const response = await apiClient.get(`/v1/disputes/${id}`);
        setDispute(response.data.dispute);
      } catch {
        Alert.alert("Error", "Failed to load dispute");
      } finally {
        setLoading(false);
      }
    }
    fetchDetail();
  }, [id]);

  const generateCasePack = async () => {
    try {
      const response = await apiClient.post(`/v1/disputes/${id}/case_pack`, {});
      const casePack = response.data.case_pack;
      Alert.alert("Case Pack", JSON.stringify(casePack, null, 2));
    } catch {
      Alert.alert("Error", "Failed to generate case pack");
    }
  };

  if (loading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!dispute) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <Text className="text-sm text-ink-muted">Dispute not found</Text>
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl"
      style={{ paddingTop: insets.top + 12 }}
    >
      <View className="flex-row items-center mb-lg gap-md">
        <TouchableOpacity onPress={() => router.back()} className="p-sm -ml-sm">
          <Text style={{ color: colors.inkPrimary, fontSize: 20 }}>{"<"}</Text>
        </TouchableOpacity>
        <Text className="text-2xl font-semibold text-ink-primary">Dispute Details</Text>
      </View>

      <Card elevation="sm" className="mb-lg">
        <View className="gap-md">
          <View>
            <Text className="text-sm text-ink-muted">Agreement</Text>
            <Text className="text-base text-ink-primary">{dispute.agreement_type}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Sealed At</Text>
            <Text className="text-base text-ink-primary">
              {new Date(dispute.agreement_sealed_at).toLocaleDateString()}
            </Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Raised By</Text>
            <Text className="text-base text-ink-primary">{dispute.raised_by_display_name}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Status</Text>
            <Text className="text-base text-ink-primary capitalize">{dispute.status}</Text>
          </View>
          <View>
            <Text className="text-sm text-ink-muted">Reason</Text>
            <Text className="text-base text-ink-primary">{dispute.reason}</Text>
          </View>
          {dispute.resolution && (
            <View>
              <Text className="text-sm text-ink-muted">Resolution</Text>
              <Text className="text-base text-ink-primary">{dispute.resolution}</Text>
            </View>
          )}
        </View>
      </Card>

      <Button
        title="Generate Case Pack"
        onPress={generateCasePack}
        variant="secondary"
      />
    </ScrollView>
  );
}