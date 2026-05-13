"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Check,
  FileText,
  HardDrive,
  Package,
  ShieldCheck,
  Users,
  Zap,
} from "lucide-react";
import { PublicNav } from "@/components/layout/PublicNav";

// ── Plan data ────────────────────────────────────────────────────────────────

type PlanFamily = "personal" | "enterprise";

interface PlanDef {
  id: string;
  name: string;
  tagline: string;
  price: number;
  highlights: string[];
  helperText: string;
  limitNote: string;
  isPopular?: boolean;
  ctaLine?: string;
}

const PERSONAL_PLANS: PlanDef[] = [
  {
    id: "personal_basic",
    name: "Personal Basic",
    tagline: "Protect one important deal each month",
    price: 10,
    highlights: [
      "Up to 1 sealed agreement per month",
      "Keep each agreement for 12 months",
      "Photos, IDs, and voice notes included",
      "Downloadable PDF summary",
    ],
    helperText:
      "Perfect if you just want to protect a single serious transaction — like a used car purchase or a room rental — and keep a clear record in case anything comes up later.",
    limitNote:
      "Personal Basic is for individuals. If you regularly seal more than 1 agreement per month, you'll need to upgrade.",
  },
  {
    id: "personal_plus",
    name: "Personal Plus",
    tagline: "Ideal for side hustles and small landlords",
    price: 25,
    isPopular: true,
    highlights: [
      "Up to 3 sealed agreements per month",
      "Keep each agreement for 24 months",
      "Photos, IDs, and voice notes included",
      "Priority PDF generation",
    ],
    helperText:
      "Made for people who handle a few deals every month — small traders, agents, or landlords who want proof of what was agreed, without jumping into a full business plan.",
    limitNote:
      "Personal Plus is still for individual use. For higher volume, teams, or ongoing business operations, see Enterprise plans.",
  },
  {
    id: "personal_protect",
    name: "Personal Protect",
    tagline: "For serious individual dealmakers",
    price: 60,
    highlights: [
      "Up to 7 sealed agreements per month",
      "Keep each agreement for 36 months",
      "Photos, IDs, and voice notes included",
      "Fast PDF generation and export",
      "Priority in-app support",
    ],
    helperText:
      "For people who do deals regularly — such as active car traders or serious landlords — and need their agreements and evidence available for longer.",
    limitNote:
      "Personal Protect is designed for high-value personal use. If you're running a dealership, agency, or property portfolio, you belong on an Enterprise plan.",
  },
];

const ENTERPRISE_PLANS: PlanDef[] = [
  {
    id: "enterprise_standard",
    name: "Enterprise Standard",
    tagline: "Run your operation on solid agreements",
    price: 400,
    highlights: [
      "~20 sealed agreements per month included",
      "Up to 3 team members",
      "Keep agreements for 5 years",
      "Bulk PDF exports and case packs",
      "Basic reporting (by month, team member, and scenario)",
      "Email + chat support",
    ],
    helperText:
      "Built for small used-car dealers, agencies, and landlord groups who need to protect every deal, work as a team, and be able to pull records quickly when something goes wrong.",
    limitNote: "",
    ctaLine: "Need more volume or integrations? Enterprise Plus is built for that.",
  },
  {
    id: "enterprise_plus",
    name: "Enterprise Plus",
    tagline: "For high-volume dealers and platforms",
    price: 1200,
    isPopular: true,
    highlights: [
      "~80 sealed agreements per month included",
      "Up to 10 team members",
      "Keep agreements for 10 years",
      "Archive search and advanced filters",
      "Full audit bundles and exportable case packs",
      "Priority support with SLA",
      "Optional API access (pilot)",
    ],
    helperText:
      "Designed for larger dealers, property managers, cooperatives, and marketplaces that need structured records, long-term archives, and faster support.",
    limitNote: "",
    ctaLine: "Talk to us if you need custom volume or integrations.",
  },
];

const ADDONS = [
  {
    Icon: Package,
    title: "Extra agreements",
    body: "Hit your monthly limit? Buy extra agreement packs to cover peak months without changing your main plan.",
  },
  {
    Icon: HardDrive,
    title: "Longer storage",
    body: "Keep a specific agreement longer than your plan's default by adding extra storage years.",
  },
  {
    Icon: FileText,
    title: "Case packs for disputes",
    body: "Generate a fully bundled case pack — agreement, timestamps, and evidence log — for use in mediation or dispute handling.",
  },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function PlanCard({ plan, family }: { plan: PlanDef; family: PlanFamily }) {
  const isEnterprise = family === "enterprise";
  return (
    <div
      className={`relative flex flex-col rounded-2xl border p-8 ${
        plan.isPopular
          ? "border-blue-600 shadow-lg shadow-blue-600/10"
          : "border-neutral-200"
      } bg-white`}
    >
      {plan.isPopular && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="bg-blue-600 text-white text-xs font-semibold px-4 py-1 rounded-full tracking-wide uppercase">
            Most popular
          </span>
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-semibold text-neutral-900">{plan.name}</h3>
        <p className="text-sm text-neutral-500 mt-1">{plan.tagline}</p>
      </div>

      <div className="mb-8">
        <span className="text-4xl font-bold text-neutral-900">{plan.price}</span>
        <span className="text-neutral-500 ml-1.5 text-sm">GHS / month</span>
      </div>

      <ul className="space-y-3 mb-8 flex-1">
        {plan.highlights.map((h) => (
          <li key={h} className="flex items-start gap-3 text-sm text-neutral-700">
            <Check
              size={15}
              className="text-blue-600 mt-0.5 shrink-0"
              strokeWidth={2.5}
            />
            <span>{h}</span>
          </li>
        ))}
      </ul>

      <Link
        href="/login"
        className={`w-full text-center py-3 rounded-xl font-medium text-sm transition-colors ${
          plan.isPopular
            ? "bg-blue-600 text-white hover:bg-blue-700"
            : "bg-neutral-900 text-white hover:bg-neutral-700"
        }`}
      >
        {isEnterprise ? "Contact us" : "Get started"}
      </Link>

      {plan.helperText && (
        <p className="text-xs text-neutral-400 mt-4 leading-relaxed">{plan.helperText}</p>
      )}

      {plan.ctaLine && (
        <p className="text-xs text-blue-500 mt-3 font-medium">{plan.ctaLine}</p>
      )}

      {plan.limitNote && (
        <p className="text-xs text-neutral-400 mt-3 border-t border-neutral-100 pt-3 leading-relaxed">
          {plan.limitNote}
        </p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PricingPage() {
  const [tab, setTab] = useState<PlanFamily>("personal");

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <PublicNav />

      <main className="flex-1">
        {/* Header */}
        <section className="text-center px-6 pt-20 pb-12">
          <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-600 text-xs font-semibold px-4 py-2 rounded-full mb-6 tracking-wide uppercase">
            <Zap size={12} strokeWidth={2.5} />
            Simple plans for safer agreements
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-neutral-900 max-w-2xl mx-auto leading-tight">
            Protect your deals with clear, affordable plans
          </h1>
          <p className="mt-4 text-lg text-neutral-500 max-w-xl mx-auto leading-relaxed">
            Whether you&apos;re buying a single car, renting out one room, or managing many deals every month, Kotoku has a plan that protects your agreements without stressing your pocket.
          </p>

          {/* What every plan includes */}
          <div className="mt-8 flex flex-wrap justify-center gap-4 text-sm text-neutral-600">
            {[
              "Sealed agreements",
              "Photo and ID evidence",
              "Downloadable PDFs",
            ].map((item) => (
              <span key={item} className="inline-flex items-center gap-1.5">
                <Check size={13} className="text-blue-600" strokeWidth={2.5} />
                {item}
              </span>
            ))}
          </div>
        </section>

        {/* Tab toggle */}
        <div className="flex justify-center mb-10 px-6">
          <div className="inline-flex bg-neutral-100 rounded-full p-1 gap-1">
            <button
              onClick={() => setTab("personal")}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                tab === "personal"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              Personal
            </button>
            <button
              onClick={() => setTab("enterprise")}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                tab === "enterprise"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              <span className="inline-flex items-center gap-1.5">
                <Users size={13} strokeWidth={2} />
                Enterprise
              </span>
            </button>
          </div>
        </div>

        {/* Plan cards */}
        <section className="max-w-6xl mx-auto px-6 pb-20">
          {tab === "personal" ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {PERSONAL_PLANS.map((p) => (
                <PlanCard key={p.id} plan={p} family="personal" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
              {ENTERPRISE_PLANS.map((p) => (
                <PlanCard key={p.id} plan={p} family="enterprise" />
              ))}
            </div>
          )}
        </section>

        {/* Add-ons */}
        <section className="bg-neutral-50 py-20 px-6">
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold text-neutral-900 mb-2 text-center">
              Add just what you need
            </h2>
            <p className="text-sm text-neutral-500 text-center mb-10">
              Available on both Personal and Enterprise plans, with clear pricing shown before you confirm any purchase.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {ADDONS.map(({ Icon, title, body }) => (
                <div key={title} className="bg-white rounded-2xl border border-neutral-200 p-6">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center mb-4">
                    <Icon size={18} className="text-blue-600" strokeWidth={1.8} />
                  </div>
                  <h3 className="font-semibold text-neutral-900 mb-2">{title}</h3>
                  <p className="text-sm text-neutral-500 leading-relaxed">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Fair use */}
        <section className="max-w-2xl mx-auto px-6 py-16 text-center">
          <p className="text-xs text-neutral-400 leading-relaxed">
            <strong className="text-neutral-500">Fair use and business usage</strong>{" "}
            — Personal plans are for individual use only. If you regularly seal more agreements than your Personal plan allows, or run your day-to-day business on Kotoku, we may ask you to switch to an Enterprise plan so we can keep SMS, storage, and support sustainable for everyone.
          </p>
        </section>

        {/* Closing CTA */}
        <section className="px-6 py-20 text-center">
          <div className="max-w-xl mx-auto">
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight leading-snug">
              Ready to protect your first agreement?
            </h2>
            <p className="mt-4 text-base text-slate-700 leading-relaxed">
              Join Kotoku and seal your deal in under five minutes.
            </p>
            <div className="mt-8">
              <Link
                href="/login"
                className="px-8 py-3 rounded-full bg-blue-600 text-white font-semibold hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
              >
                Get started free
                <span aria-hidden>→</span>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-100 py-8 px-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center">
            <ShieldCheck size={12} className="text-white" strokeWidth={2} />
          </div>
          <span className="font-semibold text-sm">Kotoku</span>
        </div>
        <p className="text-xs text-neutral-400">
          Governed by the Electronic Transactions Act 2008 (Ghana). Prices are in GHS and billed monthly.
        </p>
      </footer>
    </div>
  );
}
