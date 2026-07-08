"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

const NAV_LINKS = [
  { label: "How it works", href: "/how-it-works" },
  { label: "Pricing", href: "/pricing" },
];

export function PublicNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-10 border-b border-neutral-100 bg-white/80 px-4 py-4 backdrop-blur-sm sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="flex items-center">
          <KotokuLogo variant="horizontal" color="navy" size={28} />
        </Link>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-5">
          <div className="-mx-1 flex items-center gap-4 overflow-x-auto px-1 pb-1 sm:mx-0 sm:px-0 sm:pb-0">
            {NAV_LINKS.map(({ label, href }) => {
              const isActive = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  className={`shrink-0 text-sm transition-colors ${
                    isActive
                      ? "font-semibold text-slate-900 underline underline-offset-4"
                      : "font-medium text-slate-700 hover:text-slate-900"
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </div>
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-700"
          >
            Sign in
          </Link>
        </div>
      </div>
    </nav>
  );
}
