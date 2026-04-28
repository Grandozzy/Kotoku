import { Check } from "lucide-react-native";
import { Text, View } from "react-native";

import { colors } from "@/theme/tokens";

const STEP_LABELS = ["Parties", "Details", "Evidence", "Review", "Consent"];

interface StepProgressProps {
  currentIndex: number;
}

export function StepProgress({ currentIndex }: StepProgressProps) {
  return (
    <View className="flex-row items-center px-lg py-md bg-surface-card border-b border-border-subtle">
      {STEP_LABELS.map((label, idx) => {
        const done = idx < currentIndex;
        const active = idx === currentIndex;

        return (
          <View key={label} className="flex-row items-center flex-1">
            {/* Circle */}
            <View className="items-center">
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
            </View>

            {/* Connector — skip after last */}
            {idx < STEP_LABELS.length - 1 && (
              <View
                className={[
                  "h-px flex-1 mx-xs mb-4",
                  done ? "bg-brand-primary" : "bg-border-subtle",
                ].join(" ")}
              />
            )}
          </View>
        );
      })}
    </View>
  );
}
