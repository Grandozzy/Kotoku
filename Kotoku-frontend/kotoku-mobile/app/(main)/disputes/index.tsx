import { Text, View, FlatList, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Card } from '@/components/ui';
import { useDisputes, Dispute } from '@/hooks/useDisputes';

export default function DisputesIndexScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { disputes, loading } = useDisputes();

  const renderItem = ({ item }: { item: Dispute }) => (
    <TouchableOpacity onPress={() => router.push(`/disputes/${item.id}`)}>
      <Card elevation="sm" className="mb-sm">
        <View className="flex-row justify-between items-center">
          <View>
            <Text className="text-base font-medium text-ink-primary">
              {item.agreement_type || 'Agreement'}
            </Text>
            <Text className="text-sm text-ink-secondary">
              Raised by {item.raised_by_display_name}
            </Text>
          </View>
          <View className={`px-sm py-xs rounded ${
            item.status === 'open' ? 'bg-warning/20' :
            item.status === 'resolved' ? 'bg-success/20' : 'bg-ink-muted/20'
          }`}>
            <Text className={`text-xs font-medium ${
              item.status === 'open' ? 'text-warning' :
              item.status === 'resolved' ? 'text-success' : 'text-ink-muted'
            }`}>
              {item.status}
            </Text>
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View className="flex-1 justify-center items-center bg-surface-canvas">
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg pb-2xl gap-lg"
      contentContainerStyle={{ paddingTop: insets.top + 12 }}
    >
      <View>
        <Text className="text-2xl font-semibold text-ink-primary">Disputes</Text>
        <Text className="text-sm text-ink-secondary mt-xs">
          Raise or track a dispute on a sealed agreement
        </Text>
      </View>

      {disputes.length === 0 ? (
        <Card elevation="sm">
          <Text className="text-sm text-ink-muted text-center py-lg">
            No disputes yet.
          </Text>
        </Card>
      ) : (
        <FlatList
          data={disputes}
          renderItem={renderItem}
          keyExtractor={(item) => String(item.id)}
          scrollEnabled={false}
        />
      )}
    </ScrollView>
  );
}