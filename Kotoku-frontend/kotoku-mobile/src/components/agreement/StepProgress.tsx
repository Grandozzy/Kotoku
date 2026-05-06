import { Check } from "lucide-react-native";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/theme/tokens";

const STEP_LABELS = ["Parties", "Details", "Evidence", "Review", "Consent"];

interface StepProgressProps {
  currentIndex: number;
  onStepPress?: (index: number) => void;
}

export function StepProgress({ currentIndex, onStepPress }: StepProgressProps) {
  const insets = useSafeAreaInsets();

  return (
    <View
      className="items-center bg-surface-card border-b border-border-subtle"
      style={{ paddingTop: insets.top + 12, paddingBottom: 12 }}
    >
      <View className="flex-row items-center">
        {STEP_LABELS.map((label, idx) => {
          const done = idx < currentIndex;
          const active = idx === currentIndex;
          const tappable = done && onStepPress;

          return (
            <View key={label} className="flex-row items-center">
              <Pressable
                onPress={() => onStepPress?.(idx)}
                disabled={!tappable}
                className="items-center"
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                style={({ pressed }) => pressed && tappable ? { opacity: 0.7 } : undefined}
              >
                <View
                  className={[
                    "w-7 h-7 rounded-pill items-center justify-center",
                    done
                      ? "bg-brand-primary"
                      : active
                        ? "bg-brand-primary"
                        : "bg-surface-subtle border border-border-subtle",
                  ].join(" ")}
                >
                  {done ? (
                    <Check size={14} color={colors.bgCard} strokeWidth={2.5} />
                  ) : (
                    <Text
                      className={
                        active ? "text-xs font-semibold text-white" : "text-xs text-ink-muted"
                      }
                    >
                      {idx + 1}
                    </Text>
                  )}
                </View>
                <Text
                  className={[
                    "text-xs mt-xs",
                    active ? "text-brand-primary font-semibold" : "text-ink-muted",
                  ].join(" ")}
                  numberOfLines={1}
                >
                  {label}
                </Text>
              </Pressable>

              {idx < STEP_LABELS.length - 1 && (
                <View
                  className={[
                    "h-px w-6 mx-xs mb-4",
                    done ? "bg-brand-primary" : "bg-border-subtle",
                  ].join(" ")}
                />
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}
