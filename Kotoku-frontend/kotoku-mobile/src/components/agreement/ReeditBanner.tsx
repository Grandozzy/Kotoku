import { AlertCircle } from "lucide-react-native";
import { Text, View } from "react-native";

import { colors } from "@/theme/tokens";

export function ReeditBanner() {
  return (
    <View className="bg-amber-50 border-b border-amber-200 px-lg py-sm flex-row items-center gap-sm">
      <AlertCircle size={16} color={colors.warning} />
      <Text className="text-sm text-amber-800 flex-1">
        Editing a previously sealed agreement. Changes require both parties&apos; consent before re-sealing.
      </Text>
    </View>
  );
}