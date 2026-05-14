import Image from "next/image";

type Variant = "horizontal" | "stacked" | "icon";
type Color = "navy" | "white";

interface KotokuLogoProps {
  variant?: Variant;
  color?: Color;
  /** Icon height in px. Wordmark scales proportionally. */
  size?: number;
  className?: string;
}

/**
 * Kotoku logo lockup component.
 *
 * - horizontal: icon left + wordmark right (navbar, header)
 * - stacked: icon above + wordmark below (splash, hero)
 * - icon: mark only (app icon contexts, favicons)
 *
 * On dark/navy backgrounds pass color="white" to render the
 * white variant per KOTOKU_LOGO_LOCKUP_RULES.md.
 */
export function KotokuLogo({
  variant = "horizontal",
  color = "navy",
  size = 28,
  className = "",
}: KotokuLogoProps) {
  const wordmarkColor = color === "white" ? "#FFFFFF" : "#1B2A6B";

  const icon = (
    <Image
      src="/brand/kotoku-mark.png"
      alt="Kotoku mark"
      width={size}
      height={size}
      priority
      style={{ width: size, height: size, objectFit: "contain" }}
    />
  );

  if (variant === "icon") return <span className={className}>{icon}</span>;

  const wordmarkSize = variant === "stacked" ? Math.round(size * 0.3) : Math.round(size * 0.64);
  const gap = variant === "stacked" ? Math.round(size * 0.15) : 8;

  const wordmark = (
    <span
      style={{
        fontFamily: "var(--font-cormorant), 'Cormorant Garamond', Georgia, serif",
        fontSize: wordmarkSize,
        fontWeight: variant === "stacked" ? 400 : 600,
        letterSpacing: "0.05em",
        color: wordmarkColor,
        lineHeight: 1,
      }}
    >
      Kotoku
    </span>
  );

  if (variant === "stacked") {
    return (
      <span
        className={`flex flex-col items-center ${className}`}
        style={{ gap }}
      >
        {icon}
        {wordmark}
      </span>
    );
  }

  // horizontal
  return (
    <span
      className={`flex items-center ${className}`}
      style={{ gap }}
    >
      {icon}
      {wordmark}
    </span>
  );
}
