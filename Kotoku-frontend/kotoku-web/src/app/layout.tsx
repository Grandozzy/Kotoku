import type { Metadata } from "next";
import { Geist, Geist_Mono, Cormorant_Garamond } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";
import { Providers } from "@/components/layout/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const cormorantGaramond = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["300", "400", "600"],
});

export const viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "Kotoku — Agreement Evidence",
  description:
    "Don't take their word for it. Take evidence for it. Seal agreements with photos, bilateral OTP consent, and a tamper-proof vault.",
  icons: {
    icon: "/brand/kotoku-favicon.png",
    apple: "/brand/kotoku-favicon.png",
  },
  openGraph: {
    title: "Kotoku — Agreement Evidence",
    description: "Seal agreements with evidence. Both parties confirm. Everything stored.",
    siteName: "Kotoku",
    images: ["/brand/kotoku-mark.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${cormorantGaramond.variable} h-full antialiased`}
    >
      <head>
        {/* Disable the Vercel toolbar to prevent it from rendering debug JSON on-page */}
        <meta name="vercel-toolbar" content="disabled" />
      </head>
      <body className="min-h-full flex flex-col bg-white text-neutral-900">
        <Providers>{children}</Providers>
        <Analytics />
      </body>
    </html>
  );
}
