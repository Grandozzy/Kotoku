import { Image, Text, View } from "react-native";

type Variant = "horizontal" | "stacked" | "icon";
type Color = "navy" | "white";

interface KotokuLogoProps {
  variant?: Variant;
  /** Icon dimension in dp */
  size?: number;
  color?: Color;
}

const MARK = require("../../../assets/brand/kotoku-mark.png") as number;

/**
 * Kotoku logo lockup for React Native.
 *
 * - horizontal: icon left + wordmark right (nav bar, header)
 * - stacked: icon above + wordmark below (splash, about, welcome hero)
 * - icon: mark only
 *
 * Use color="white" on dark/navy backgrounds.
 */
export function KotokuLogo({ variant = "horizontal", size = 28, color = "navy" }: KotokuLogoProps) {
  const wordmarkColor = color === "white" ? "#FFFFFF" : "#1B2A6B";
  const wordmarkSize = variant === "stacked" ? Math.round(size * 0.3) : Math.round(size * 0.64);
  const gap = variant === "stacked" ? Math.round(size * 0.15) : 8;

  const icon = (
    <Image
      source={MARK}
      style={{ width: size, height: size, resizeMode: "contain" }}
      accessibilityLabel="Kotoku"
    />
  );

  if (variant === "icon") return icon;

  const wordmark = (
    <Text
      style={{
        fontFamily: "CormorantGaramond_400Regular",
        fontSize: wordmarkSize,
        letterSpacing: 0.05 * wordmarkSize,
        color: wordmarkColor,
        lineHeight: wordmarkSize * 1.2,
      }}
    >
      Kotoku
    </Text>
  );

  if (variant === "stacked") {
    return (
      <View style={{ alignItems: "center", gap }}>
        {icon}
        {wordmark}
      </View>
    );
  }

  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap }}>
      {icon}
      {wordmark}
    </View>
  );
}
