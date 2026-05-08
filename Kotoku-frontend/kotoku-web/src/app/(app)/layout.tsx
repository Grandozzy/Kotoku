"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSessionStore } from "@/store/sessionStore";
import { useEffect } from "react";

const NAV = [
  { href: "/dashboard", label: "Home" },
  { href: "/agreements/new", label: "Create" },
  { href: "/vault", label: "Vault" },
  { href: "/profile", label: "Profile" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) router.replace("/login");
  }, [isAuthenticated, router]);

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-6 py-3 border-b border-neutral-100 bg-white sticky top-0 z-10">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight">
          Kotoku
        </Link>
        <div className="flex items-center gap-1">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                pathname.startsWith(href) && href !== "/agreements/new"
                  ? "bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 hover:text-neutral-900"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </nav>
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">{children}</main>
    </div>
  );
}
