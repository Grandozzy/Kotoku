import { useEffect, useRef } from "react";
import { Animated, View, ViewStyle } from "react-native";

interface SkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  rounded?: "sm" | "md" | "lg" | "full";
  style?: ViewStyle;
}

const RADII = { sm: 6, md: 10, lg: 16, full: 999 };

export function Skeleton({ width = "100%", height = 16, rounded = "md", style }: SkeletonProps) {
  const opacity = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.4, duration: 700, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, [opacity]);

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius: RADII[rounded],
          backgroundColor: "#E2E8F0",
          opacity,
        },
        style,
      ]}
    />
  );
}

export function CardSkeleton() {
  return (
    <View className="bg-surface-card rounded-xl border border-border-subtle p-lg gap-sm">
      <Skeleton height={14} width="60%" rounded="md" />
      <Skeleton height={12} width="40%" rounded="md" />
    </View>
  );
}
