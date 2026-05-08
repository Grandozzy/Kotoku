import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
        <span className="text-xl font-bold tracking-tight">Kotoku</span>
        <div className="flex items-center gap-4">
          <Link
            href="/how-it-works"
            className="text-sm text-neutral-600 hover:text-neutral-900"
          >
            How it works
          </Link>
          <Link
            href="/login"
            className="text-sm font-medium px-4 py-2 rounded-full bg-neutral-900 text-white hover:bg-neutral-700 transition-colors"
          >
            Sign in
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24">
        <p className="text-sm font-medium text-emerald-600 tracking-wide uppercase mb-4">
          Agreement Evidence Platform
        </p>
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight max-w-3xl">
          Don&apos;t take their word for it.
          <br />
          <span className="text-emerald-600">Take evidence for it.</span>
        </h1>
        <p className="mt-6 text-lg text-neutral-500 max-w-xl leading-relaxed">
          Capture photos, agree on terms, and seal the deal — with bilateral SMS
          confirmation and a tamper-proof vault. In under five minutes, on any
          device.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 items-center">
          <Link
            href="/login"
            className="px-6 py-3 rounded-full bg-neutral-900 text-white font-medium hover:bg-neutral-700 transition-colors"
          >
            Seal your first agreement →
          </Link>
          <Link
            href="/how-it-works"
            className="px-6 py-3 rounded-full border border-neutral-200 text-neutral-700 font-medium hover:bg-neutral-50 transition-colors"
          >
            See how it works
          </Link>
        </div>
        <p className="mt-6 text-xs text-neutral-400">
          Legally recognised under Ghana&apos;s Electronic Transactions Act (Act 772)
        </p>
      </section>

      {/* How it works */}
      <section className="bg-neutral-50 px-6 py-20">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-3xl font-bold tracking-tight mb-12">
            The handshake, with receipts.
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Capture",
                body: "Photograph the asset, upload ID documents, and record the agreed terms. Every item is timestamped the moment it arrives.",
              },
              {
                step: "02",
                title: "Confirm",
                body: "Both parties receive an SMS OTP. No one can seal the agreement alone. Both confirmations are recorded and linked to verified phone numbers.",
              },
              {
                step: "03",
                title: "Seal",
                body: "A tamper-evident vault entry is created — hashed, timestamped, and retrievable any time. Download the PDF or share the link.",
              },
            ].map(({ step, title, body }) => (
              <div key={step} className="bg-white rounded-2xl p-6 shadow-sm">
                <span className="text-4xl font-bold text-emerald-100">{step}</span>
                <h3 className="mt-2 text-lg font-semibold">{title}</h3>
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
            {[
              {
                icon: "🚗",
                title: "Used vehicle sale",
                body: "Capture the car's condition before cash changes hands. No disputes about that dent six months later.",
              },
              {
                icon: "🏠",
                title: "Room rental",
                body: "Know exactly what was scratched before you moved in. Your deposit photos, your condition record, sealed.",
              },
              {
                icon: "🤝",
                title: "Any informal deal",
                body: "A verbal agreement is only as good as the relationship. Kotoku is what you fall back on when the relationship changes.",
              },
              {
                icon: "📋",
                title: "Small business",
                body: "Frequent transactions — goods, services, labour. Reusable templates and repeatable evidence capture.",
              },
            ].map(({ icon, title, body }) => (
              <div
                key={title}
                className="flex gap-4 p-6 rounded-2xl border border-neutral-100 hover:border-emerald-100 transition-colors"
              >
                <span className="text-3xl">{icon}</span>
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
      <section className="bg-neutral-900 text-white px-6 py-14 text-center">
        <p className="text-sm uppercase tracking-widest text-neutral-400 mb-3">
          Legal standing
        </p>
        <h2 className="text-2xl font-bold max-w-2xl mx-auto leading-snug">
          Your sealed record is admissible evidence — not just a screenshot.
        </h2>
        <p className="mt-4 text-neutral-400 text-sm max-w-xl mx-auto leading-relaxed">
          Kotoku&apos;s seal hash, OTP consent records, and immutable vault satisfy the
          admissibility requirements of Ghana&apos;s Electronic Transactions Act (Act 772),
          Section 12. Every sealed agreement includes originator identification, an
          integrity hash, and a full audit trail.
        </p>
        <Link
          href="/legal"
          className="mt-6 inline-block text-sm text-emerald-400 hover:text-emerald-300 underline"
        >
          Read the legal reference →
        </Link>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-neutral-100 flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-neutral-400">
        <span>© {new Date().getFullYear()} Kotoku. All rights reserved.</span>
        <span className="italic">
          &ldquo;Keep all your agreements in Kotoku. Take them out tomorrow if you need to.&rdquo;
        </span>
      </footer>
    </div>
  );
}
