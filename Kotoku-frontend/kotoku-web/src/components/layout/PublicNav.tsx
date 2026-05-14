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
    <nav className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 sticky top-0 bg-white/80 backdrop-blur-sm z-10">
      <Link href="/" className="flex items-center">
        <KotokuLogo variant="horizontal" color="navy" size={28} />
      </Link>

      <div className="flex items-center gap-5">
        {NAV_LINKS.map(({ label, href }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={`text-sm transition-colors ${
                isActive
                  ? "text-slate-900 font-semibold underline underline-offset-4"
                  : "text-slate-700 font-medium hover:text-slate-900"
              }`}
            >
              {label}
            </Link>
          );
        })}
        <Link
          href="/login"
          className="text-sm font-semibold px-4 py-2 rounded-full bg-slate-900 text-white hover:bg-slate-700 transition-colors"
        >
          Sign in
        </Link>
      </div>
    </nav>
  );
}
