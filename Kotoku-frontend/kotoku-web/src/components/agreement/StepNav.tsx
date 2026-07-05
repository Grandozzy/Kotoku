"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Check } from "lucide-react";
import type { Agreement } from "@/types/agreement";
import { SCENARIO_MAP } from "@/constants/scenarios";

interface Step {
  href: string;
  label: string;
  check: (a: Agreement) => boolean | "blocked";
}

// ── Step completion helpers ─────────────────────────────────────────────────
// Each mirrors the exact validation enforced on the corresponding page.

function isPartiesComplete(a: Agreement): boolean {
  if (a.parties.length < 2) return false;
  return a.parties.every((p) => {
    const norm = p.phone.replace(/\s/g, "");
    return (
      p.display_name.trim().length >= 2 &&
      /^(\+\d{10,15}|\d{10,15})$/.test(norm) &&
      (p.id_number ?? "").trim().length >= 3
    );
  });
}

function isDetailsComplete(a: Agreement): boolean {
  if (!a.scenario_template) return true;
  const scenario = SCENARIO_MAP[a.scenario_template];
  if (!scenario) return true;
  const required = scenario.fields.filter((f) => f.required);
  if (required.length === 0) return true;
  const data = a.field_data ?? {};
  return required.every((f) => {
    const v = data[f.key];
    return v !== undefined && v !== null && v !== "";
  });
}

function isEvidenceComplete(a: Agreement): boolean {
  return (
    (a.evidence_items?.filter((e) => e.upload_status === "confirmed").length ?? 0) > 0
  );
}

function isConsentComplete(a: Agreement): boolean {
  return ["sealed", "active", "reopen_requested", "archived", "closed", "expired"].includes(
    a.status
  );
}

// ── Steps ───────────────────────────────────────────────────────────────────

function getSteps(id: number): Step[] {
  return [
    {
      href: `/agreements/${id}/parties`,
      label: "Parties",
      check: isPartiesComplete,
    },
    {
      href: `/agreements/${id}`,
      label: "Details",
      check: (a) => (!isPartiesComplete(a) ? "blocked" : isDetailsComplete(a)),
    },
    {
      href: `/agreements/${id}/evidence`,
      label: "Evidence",
      check: (a) =>
        !isPartiesComplete(a) || !isDetailsComplete(a) ? "blocked" : isEvidenceComplete(a),
    },
    {
      href: `/agreements/${id}/review`,
      label: "Review",
      check: (a) =>
        !isPartiesComplete(a) || !isDetailsComplete(a) || !isEvidenceComplete(a)
          ? "blocked"
          : isConsentComplete(a),
    },
    {
      href: `/agreements/${id}/consent`,
      label: "Consent",
      check: (a) =>
        !isPartiesComplete(a) || !isDetailsComplete(a) || !isEvidenceComplete(a)
          ? "blocked"
          : isConsentComplete(a),
    },
    {
      href: `/agreements/${id}/sealed`,
      label: "Sealed",
      check: (a) => (!isConsentComplete(a) ? "blocked" : !!a.sealed_at),
    },
  ];
}

// ── Component ────────────────────────────────────────────────────────────────

export function StepNav({ agreement }: { agreement: Agreement }) {
  const pathname = usePathname();
  const steps = getSteps(agreement.id);

  return (
    <nav className="flex flex-col gap-1">
      {steps.map((step, i) => {
        const done = step.check(agreement);
        const isBlocked = done === "blocked";
        const isActive = pathname === step.href;

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
              {done === true && !isActive ? <Check size={10} strokeWidth={3} /> : i + 1}
            </span>
            {step.label}
          </Link>
        );
      })}
    </nav>
  );
}
