"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSessionStore } from "@/store/sessionStore";
import { useEffect } from "react";

import { Home, Loader2, Lock, Scale, User, Zap } from "lucide-react";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

const NAV = [
  { href: "/dashboard", label: "Home",     Icon: Home },
  { href: "/vault",     label: "Vault",    Icon: Lock },
  { href: "/disputes",  label: "Disputes", Icon: Scale },
  { href: "/profile",   label: "Profile",  Icon: User },
  { href: "/plans",     label: "Plans",    Icon: Zap },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const accessToken = useSessionStore((s) => s.accessToken);
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const isBootstrapping = useSessionStore((s) => s.isBootstrapping);
  const isRecoveringSession = hasHydrated && isAuthenticated && !accessToken;

  useEffect(() => {
    if (!hasHydrated || isBootstrapping || isRecoveringSession) return;
    if (!isAuthenticated) router.replace("/login");
  }, [hasHydrated, isAuthenticated, isBootstrapping, isRecoveringSession, router]);

  if (!hasHydrated || isBootstrapping || isRecoveringSession) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-neutral-300" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="sticky top-0 z-10 border-b border-neutral-100 bg-white/80 px-4 py-3 backdrop-blur-sm sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/dashboard" className="flex items-center">
            <KotokuLogo variant="horizontal" color="navy" size={24} />
          </Link>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <div className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pb-1 sm:mx-0 sm:px-0 sm:pb-0">
              {NAV.map(({ href, label, Icon }) => {
                const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-neutral-100 text-neutral-900"
                        : "text-neutral-500 hover:text-neutral-900"
                    }`}
                  >
                    <Icon size={14} strokeWidth={active ? 2.2 : 1.8} />
                    {label}
                  </Link>
                );
              })}
            </div>
            <Link
              href="/agreements/new"
              className="inline-flex items-center justify-center rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-700 sm:ml-2"
            >
              + New
            </Link>
          </div>
        </div>
      </nav>
      <main className="mx-auto flex-1 w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
