"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Home, Lock, User } from "lucide-react";
import { useSessionStore } from "@/store/sessionStore";
import { useEffect } from "react";

const NAV = [
  { href: "/dashboard", label: "Home",    Icon: Home },
  { href: "/vault",     label: "Vault",   Icon: Lock },
  { href: "/profile",   label: "Profile", Icon: User },
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
      <nav className="flex items-center justify-between px-6 py-3 border-b border-neutral-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Lock size={13} className="text-white" strokeWidth={2.5} />
          </div>
          <span className="text-lg font-bold tracking-tight">Kotoku</span>
        </Link>

        <div className="flex items-center gap-1">
          {NAV.map(({ href, label, Icon }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
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
          <Link
            href="/agreements/new"
            className="ml-2 px-4 py-1.5 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors"
          >
            + New
          </Link>
        </div>
      </nav>
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8">{children}</main>
    </div>
  );
}
