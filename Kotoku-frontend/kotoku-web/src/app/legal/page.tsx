import Link from "next/link";
import { PublicNav } from "@/components/layout/PublicNav";

export default function LegalPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <PublicNav />

      <main className="max-w-3xl mx-auto px-6 py-16 flex flex-col gap-12">
        <div>
          <p className="text-sm font-medium text-emerald-600 uppercase tracking-wide mb-3">
            Legal reference
          </p>
          <h1 className="text-4xl font-bold tracking-tight">
            Ghana Digital Evidence Law
          </h1>
          <p className="mt-4 text-neutral-500 text-lg leading-relaxed">
            How Kotoku&apos;s sealed records relate to Ghanaian law — and what gives them
            standing as evidence.
          </p>
        </div>

        {/* Core legislation */}
        <section className="flex flex-col gap-5">
          <h2 className="text-2xl font-bold">Core legislation</h2>
          <div className="grid gap-4">
            {[
              {
                act: "Electronic Transactions Act, 2008 (Act 772)",
                summary:
                  "Primary framework. Establishes that electronic records cannot be denied admissibility solely because they are electronic. Governs evidential weight, integrity, and originator identification.",
              },
              {
                act: "Electronic Transactions Regulations, 2011 (LI 1902)",
                summary:
                  "Implementing regulations specifying technical standards for electronic signatures and records kept under Act 772.",
              },
              {
                act: "Evidence Act, 1975 (NRCD 323)",
                summary:
                  "Foundational evidence law. The business records exception is relevant — Kotoku's append-only audit log functions as a business record of each transaction.",
              },
              {
                act: "Data Protection Act, 2012 (Act 843)",
                summary:
                  "Governs how personal data (phone numbers, ID documents, agreement terms) may be processed. Kotoku's OTP-based consent mechanism satisfies the explicit consent requirement.",
              },
              {
                act: "Alternative Dispute Resolution Act, 2010 (Act 798)",
                summary:
                  "Ghana's ADR framework. Kotoku's dispute module is designed as a pre-mediation evidence pack, providing mediators with a structured factual record.",
              },
            ].map(({ act, summary }) => (
              <div
                key={act}
                className="rounded-xl border border-neutral-100 p-4"
              >
                <p className="font-semibold text-sm">{act}</p>
                <p className="mt-1 text-sm text-neutral-500 leading-relaxed">
                  {summary}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Act 772 deep-dive */}
        <section className="flex flex-col gap-5">
          <h2 className="text-2xl font-bold">
            Electronic Transactions Act, 2008 — Key sections
          </h2>

          {[
            {
              section: "Section 7 — Legal recognition",
              text: "An electronic communication or electronic record shall not be denied legal effect, validity, or enforceability solely on the ground that it is in electronic form.",
            },
            {
              section: "Section 8 — Writing requirement",
              text: "Where any law requires information to be in writing, that requirement is satisfied by an electronic record if the information is accessible for subsequent reference.",
            },
            {
              section: "Section 9 — Signature requirement",
              text: "Where any law requires a signature, an electronic signature satisfies that requirement if it is reliable and appropriate in the circumstances. Kotoku's bilateral SMS OTP — issued to a verified phone number tied to a named party — constitutes an electronic signature under this section.",
            },
            {
              section: "Section 12 — Admissibility and evidential weight",
              text: '"An electronic record shall not be denied admissibility in any legal proceedings on the sole ground that it is in electronic form." Evidential weight depends on: (1) reliability of the method used to generate or store the record; (2) reliability of the method used to ensure integrity; (3) the method used to identify the originator; (4) any other relevant factor.',
            },
          ].map(({ section, text }) => (
            <div key={section}>
              <p className="font-semibold text-sm text-neutral-700">{section}</p>
              <p className="mt-1 text-sm text-neutral-500 leading-relaxed italic border-l-2 border-neutral-200 pl-4">
                {text}
              </p>
            </div>
          ))}
        </section>

        {/* How Kotoku satisfies Section 12 */}
        <section className="flex flex-col gap-5">
          <h2 className="text-2xl font-bold">
            How Kotoku satisfies Section 12
          </h2>
          <p className="text-neutral-500 text-sm leading-relaxed">
            Every design decision in Kotoku traces back to one of the four
            evidential weight factors in Act 772 Section 12.
          </p>
          <div className="rounded-2xl border border-neutral-100 overflow-hidden">
            <div className="grid grid-cols-2 bg-neutral-50 px-4 py-2 border-b border-neutral-100">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Act 772 requirement
              </p>
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Kotoku implementation
              </p>
            </div>
            {[
              [
                "Reliable generation",
                "Agreement state is written atomically. Every field, party, and evidence item is persisted before the seal hash is computed.",
              ],
              [
                "Integrity / tamper-evidence",
                "SHA-256 hash computed over the full agreement snapshot at sealing, stored in VaultEntry. Re-computable for verification. Any post-seal change produces a different hash.",
              ],
              [
                "Immutable storage",
                "VaultEntry is append-only. No in-place edits after sealing. Archived entries remain stored; they cannot be deleted by users.",
              ],
              [
                "Originator identification",
                "Ghana Card photo + masked ID number per party. Phone verified via SMS OTP before any party can consent. sealed_at ISO 8601 timestamp recorded.",
              ],
              [
                "Audit trail",
                "Append-only AuditLog records every state transition with actor, timestamp, and metadata. Cannot be deleted or modified.",
              ],
              [
                "Electronic signature",
                "One OTP per party, purpose-scoped, tied to verified phone, stored in ConsentRecord with confirmed_at timestamp.",
              ],
            ].map(([req, impl]) => (
              <div
                key={req}
                className="grid grid-cols-2 px-4 py-3 border-b border-neutral-50 last:border-0"
              >
                <p className="text-sm text-neutral-600">{req}</p>
                <p className="text-sm text-neutral-500">{impl}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Practical standing */}
        <section className="flex flex-col gap-4">
          <h2 className="text-2xl font-bold">Practical standing</h2>
          <p className="text-neutral-500 text-sm leading-relaxed">
            Kotoku&apos;s sealed record does not replace a lawyer-drafted contract for
            complex commercial transactions. What it provides:
          </p>
          <ul className="flex flex-col gap-2">
            {[
              "A timestamped, hashed, party-consented record that a magistrate, mediator, or arbitrator can examine.",
              "Clear identification of who agreed, when, and to what specific terms.",
              "Photo evidence of the asset's condition at the time of handover.",
              "An audit trail showing no modifications were made after sealing.",
              "A structured PDF evidence pack ready for ADR proceedings under Act 798.",
            ].map((point) => (
              <li key={point} className="flex gap-2 text-sm text-neutral-600">
                <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>
                {point}
              </li>
            ))}
          </ul>
          <p className="text-sm text-neutral-500 leading-relaxed mt-2">
            This is materially stronger than a verbal agreement or an unsigned
            WhatsApp message, and it is designed to be admissible under Act 772
            Section 12.
          </p>
        </section>

        {/* Data protection */}
        <section className="flex flex-col gap-4">
          <h2 className="text-2xl font-bold">Data Protection Act, 2012 (Act 843)</h2>
          <p className="text-neutral-500 text-sm leading-relaxed">
            Kotoku processes personal data (phone numbers, identity photos, agreement
            terms) under the lawful basis of <strong>explicit consent</strong>. Each
            party provides an OTP-confirmed consent record before their data is included
            in a sealed agreement.
          </p>
          <ul className="flex flex-col gap-2">
            {[
              "Data is collected for a specific, explicit purpose — the named agreement only.",
              "Retention periods are enforced automatically. Expired entries are archived by a scheduled task.",
              "Parties can raise disputes or add annotations to the sealed record without modifying the original.",
              "No data is shared with third parties except where required for the SMS OTP delivery.",
            ].map((point) => (
              <li key={point} className="flex gap-2 text-sm text-neutral-600">
                <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>
                {point}
              </li>
            ))}
          </ul>
        </section>

        <div className="rounded-2xl bg-neutral-50 px-6 py-6 text-center">
          <p className="text-sm text-neutral-500">
            Questions about the legal framework?{" "}
            <Link href="/login" className="text-emerald-600 underline">
              Sign in
            </Link>{" "}
            and raise a question through your agreement&apos;s annotation panel, or
            consult a qualified Ghanaian legal practitioner.
          </p>
        </div>
      </main>
    </div>
  );
}
