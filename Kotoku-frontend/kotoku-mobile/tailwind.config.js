// tailwind.config.js
// Values are imported from src/theme/tokens.ts so Tailwind classes
// and StyleSheet objects always reference the same design tokens.

const { colors, spacing, radii, typography } = require("./src/theme/tokens");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./App.{js,jsx,ts,tsx}",
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: colors.brandPrimary,
          primarySoft: colors.brandPrimarySoft,
          secondary: colors.brandSecondary,
        },
        orange: {
          50: "#FFF7ED",
          100: "#FFEDD5",
          200: "#FED7AA",
          300: "#FDBA74",
          400: "#FB923C",
          500: colors.brandSecondary,
          600: "#EA580C",
        },
        semantic: {
          success: colors.success,
          warning: colors.warning,
          error: colors.error,
          info: colors.info,
        },
        ink: {
          primary: colors.inkPrimary,
          secondary: colors.inkSecondary,
          muted: colors.inkMuted,
        },
        surface: {
          canvas: colors.bgCanvas,
          card: colors.bgCard,
          subtle: colors.bgSubtle,
        },
        border: {
          subtle: colors.borderSubtle,
          strong: colors.borderStrong,
        },
      },
      borderRadius: {
        sm: `${radii.sm}px`,
        md: `${radii.md}px`,
        lg: `${radii.lg}px`,
        pill: `${radii.pill}px`,
      },
      fontSize: {
        xs: typography.fontSize.xs,
        sm: typography.fontSize.sm,
        md: typography.fontSize.md,
        lg: typography.fontSize.lg,
        xl: typography.fontSize.xl,
        "2xl": typography.fontSize["2xl"],
      },
      spacing: {
        xs: spacing.xs,
        sm: spacing.sm,
        md: spacing.md,
        lg: spacing.lg,
        xl: spacing.xl,
        "2xl": spacing["2xl"],
        "3xl": spacing["3xl"],
      },
    },
  },
  plugins: [],
};
