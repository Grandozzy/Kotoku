import { View } from "react-native";
import { CardSkeleton } from "./Skeleton";

interface ScreenLoaderProps {
  rows?: number;
}

export function ScreenLoader({ rows = 3 }: ScreenLoaderProps) {
  return (
    <View className="flex-1 bg-surface-canvas px-lg pt-lg gap-sm">
      {Array.from({ length: rows }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </View>
  );
}
