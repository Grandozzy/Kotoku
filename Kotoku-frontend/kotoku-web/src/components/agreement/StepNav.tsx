"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Agreement } from "@/types/agreement";

interface Step {
  href: string;
  label: string;
  check: (a: Agreement) => boolean | "blocked";
}

function getSteps(id: number): Step[] {
  return [
    {
      href: `/agreements/${id}`,
      label: "Details",
      check: () => true,
    },
    {
      href: `/agreements/${id}/parties`,
      label: "Parties",
      check: (a) => a.parties.length >= 2,
    },
    {
      href: `/agreements/${id}/evidence`,
      label: "Evidence",
      check: (a) => (a.evidence_items?.filter((e) => e.upload_status === "confirmed").length ?? 0) > 0,
    },
    {
      href: `/agreements/${id}/consent`,
      label: "Consent",
      check: (a) =>
        ["sealed", "active", "reopen_requested", "archived", "closed", "expired"].includes(a.status)
          ? true
          : a.parties.length >= 2
          ? false
          : "blocked",
    },
    {
      href: `/agreements/${id}/sealed`,
      label: "Sealed",
      check: (a) => !!a.sealed_at,
    },
  ];
}

export function StepNav({ agreement }: { agreement: Agreement }) {
  const pathname = usePathname();
  const steps = getSteps(agreement.id);

  return (
    <nav className="flex flex-col gap-1">
      {steps.map((step, i) => {
        const done = step.check(agreement);
        const isBlocked = done === "blocked";
        const isActive =
          pathname === step.href ||
          (i === 0 && pathname === `/agreements/${agreement.id}`);

        return (
          <Link
            key={step.href}
            href={isBlocked ? "#" : step.href}
            aria-disabled={isBlocked}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? "bg-neutral-100 text-neutral-900"
                : isBlocked
                ? "text-neutral-300 cursor-not-allowed"
                : "text-neutral-500 hover:text-neutral-800 hover:bg-neutral-50"
            }`}
          >
            <span
              className={`flex items-center justify-center w-5 h-5 rounded-full text-xs ${
                done === true
                  ? "bg-emerald-500 text-white"
                  : isActive
                  ? "bg-neutral-900 text-white"
                  : "bg-neutral-200 text-neutral-500"
              }`}
            >
              {done === true && !isActive ? "✓" : i + 1}
            </span>
            {step.label}
          </Link>
        );
      })}
    </nav>
  );
}
