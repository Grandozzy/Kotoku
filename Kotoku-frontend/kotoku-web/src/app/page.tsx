import Link from "next/link";
import {
  Briefcase,
  Building2,
  Camera,
  Car,
  MessageSquare,
  ShieldCheck,
  Users,
} from "lucide-react";
import { PublicNav } from "@/components/layout/PublicNav";

const STEPS = [
  {
    Icon: Camera,
    step: "01",
    title: "Capture",
    body: "Photograph the asset, upload ID documents, and record the agreed terms. Every item is timestamped the moment it arrives.",
  },
  {
    Icon: MessageSquare,
    step: "02",
    title: "Confirm",
    body: "Both parties receive an SMS OTP. No one can seal the agreement alone. Both confirmations are recorded and linked to verified phone numbers.",
  },
  {
    Icon: ShieldCheck,
    step: "03",
    title: "Seal",
    body: "A tamper-evident vault entry is created — hashed, timestamped, and retrievable any time. Download the PDF or share the link.",
  },
];

const USE_CASES = [
  {
    Icon: Car,
    title: "Used vehicle sale",
    body: "Capture the car's condition before cash changes hands. No disputes about that dent six months later.",
  },
  {
    Icon: Building2,
    title: "Room rental",
    body: "Know exactly what was scratched before you moved in. Your deposit photos, your condition record, sealed.",
  },
  {
    Icon: Users,
    title: "Any informal deal",
    body: "A verbal agreement is only as good as the relationship. Kotoku is what you fall back on when the relationship changes.",
  },
  {
    Icon: Briefcase,
    title: "Small business",
    body: "Frequent transactions — goods, services, labour. Reusable templates and repeatable evidence capture.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <PublicNav />

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24">
        <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-600 text-xs font-semibold px-4 py-2 rounded-full mb-6 tracking-wide uppercase">
          <ShieldCheck size={12} strokeWidth={2.5} />
          Agreement Evidence Platform
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight max-w-3xl">
          <span className="text-slate-400">Don&apos;t take their word for it.</span>
          <br />
          <span className="text-blue-600">Take evidence for it.</span>
        </h1>
        <p className="mt-6 text-lg text-neutral-500 max-w-xl leading-relaxed">
          Capture photos, agree on terms, and seal the deal — with bilateral SMS
          confirmation and a tamper-proof vault. In under five minutes, on any device.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 items-center">
          <Link
            href="/login"
            className="px-6 py-3 rounded-full bg-neutral-900 text-white font-medium hover:bg-neutral-700 transition-colors inline-flex items-center gap-2"
          >
            Seal your first agreement
            <span aria-hidden>→</span>
          </Link>
          <Link
            href="/how-it-works"
            className="px-6 py-3 rounded-full border border-neutral-200 text-neutral-700 font-medium hover:bg-neutral-50 transition-colors"
          >
            See how it works
          </Link>
        </div>
        <p className="mt-6 text-xs text-neutral-400 inline-flex items-center gap-1.5">
          <ShieldCheck size={12} className="text-neutral-400" />
          Legally recognised under Ghana&apos;s Electronic Transactions Act (Act 772)
        </p>
      </section>

      {/* How it works */}
      <section className="bg-neutral-50 px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-3xl font-bold tracking-tight mb-12">
            The handshake, with receipts.
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {STEPS.map(({ Icon, step, title, body }) => (
              <div key={step} className="bg-white rounded-2xl p-6 shadow-sm border border-neutral-100">
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center mb-4">
                  <Icon size={20} className="text-blue-600" strokeWidth={1.8} />
                </div>
                <span className="text-xs font-bold text-neutral-300 tracking-widest">{step}</span>
                <h3 className="mt-1 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-neutral-500 leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section className="px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-3xl font-bold tracking-tight mb-12">
            Good agreements make good friends.
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {USE_CASES.map(({ Icon, title, body }) => (
              <div
                key={title}
                className="flex gap-4 p-6 rounded-2xl border border-neutral-100 hover:border-blue-100 hover:bg-blue-50/30 transition-colors"
              >
                <div className="w-10 h-10 rounded-xl bg-neutral-100 flex items-center justify-center shrink-0">
                  <Icon size={18} className="text-neutral-600" strokeWidth={1.8} />
                </div>
                <div>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1 text-sm text-neutral-500 leading-relaxed">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Legal trust bar */}
      <section className="bg-neutral-900 text-white px-6 py-14">
        <div className="max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 text-white/60 text-xs font-semibold px-4 py-2 rounded-full mb-4 tracking-widest uppercase">
            <ShieldCheck size={12} strokeWidth={2.5} />
            Legal standing
          </div>
          <h2 className="text-2xl font-bold leading-snug">
            Your sealed record is admissible evidence — not just a screenshot.
          </h2>
          <p className="mt-4 text-neutral-400 text-sm leading-relaxed">
            Kotoku&apos;s seal hash, OTP consent records, and immutable vault satisfy the
            admissibility requirements of Ghana&apos;s Electronic Transactions Act (Act 772),
            Section 12. Every sealed agreement includes originator identification, an
            integrity hash, and a full audit trail.
          </p>
          <Link
            href="/legal"
            className="mt-6 inline-flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 underline"
          >
            Read the legal reference →
          </Link>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="px-6 py-20 text-center bg-white">
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

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-neutral-100 flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-neutral-400">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-blue-600 flex items-center justify-center">
            <ShieldCheck size={10} className="text-white" strokeWidth={2.5} />
          </div>
          <span>© {new Date().getFullYear()} Kotoku. All rights reserved.</span>
        </div>
        <span className="italic">
          &ldquo;Keep all your agreements in Kotoku. Take them out tomorrow if you need to.&rdquo;
        </span>
      </footer>
    </div>
  );
}
