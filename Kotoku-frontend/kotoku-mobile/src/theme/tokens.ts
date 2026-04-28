// src/theme/tokens.ts

export const colors = {
  // Brand
  brandPrimary: "#2563EB",     // blue-600
  brandPrimarySoft: "#DBEAFE", // blue-100
  brandSecondary: "#F97316",   // orange-500

  // Semantic
  success: "#16A34A",  // green-600
  warning: "#EAB308",  // yellow-500
  error: "#DC2626",    // red-600
  info: "#0EA5E9",     // sky-500

  // Ink / Text
  inkPrimary: "#0F172A",    // slate-900
  inkSecondary: "#64748B",  // slate-500
  inkMuted: "#94A3B8",      // slate-400

  // Borders
  borderSubtle: "#E2E8F0",  // slate-200
  borderStrong: "#CBD5E1",  // slate-300

  // Surfaces
  bgCanvas: "#F8FAFC",  // slate-50
  bgCard: "#FFFFFF",
  bgSubtle: "#F1F5F9",  // slate-100
};

export const spacing = {
  none: 0,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  "2xl": 24,
  "3xl": 32,
};

export const radii = {
  sm: 6,
  md: 10,
  lg: 16,
  pill: 999,
};

export const typography = {
  fontFamily: {
    regular: "System",
    medium: "System",
    semibold: "System",
    bold: "System",
    // Replace "System" with your custom font name once added to assets/fonts/
  },
  fontSize: {
    xs: 12,
    sm: 14,
    md: 16,
    lg: 18,
    xl: 20,
    "2xl": 24,
  },
  // React Native lineHeight must be px, not a ratio.
  // These are based on fontSize × ratio, rounded to nearest even number.
  lineHeight: {
    tight: 20,    // ~16px × 1.25
    normal: 24,   // ~16px × 1.5
    relaxed: 28,  // ~16px × 1.75
  },
};

export const opacity = {
  disabled: 0.4,
  overlay: 0.6,
  ghost: 0.08,
};

// Android elevation / iOS shadow — use on Card components
export const shadow = {
  sm: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  lg: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 6,
  },
};
