import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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

export const metadata: Metadata = {
  title: "Kotoku — Agreement Evidence",
  description:
    "Don't take their word for it. Take evidence for it. Seal agreements with photos, bilateral OTP consent, and a tamper-proof vault.",
  openGraph: {
    title: "Kotoku — Agreement Evidence",
    description: "Seal agreements with evidence. Both parties confirm. Everything stored.",
    siteName: "Kotoku",
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-white text-neutral-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
