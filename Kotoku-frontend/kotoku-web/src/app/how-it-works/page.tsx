import Link from "next/link";
import { PublicNav } from "@/components/layout/PublicNav";

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <PublicNav />

      <main className="max-w-3xl mx-auto px-6 py-16 flex flex-col gap-16">
        <div>
          <p className="text-sm font-medium text-emerald-600 uppercase tracking-wide mb-3">
            The process
          </p>
          <h1 className="text-4xl font-bold tracking-tight leading-tight">
            How Kotoku works
          </h1>
          <p className="mt-4 text-neutral-500 text-lg leading-relaxed">
            From the moment you open the app to the moment both parties walk away
            with a sealed vault entry — here&apos;s what happens.
          </p>
        </div>

        {[
          {
            number: "01",
            title: "Create the agreement",
            body: "Choose a scenario — used vehicle sale, room rental, or custom. Give the agreement a clear title. This creates a draft that only you can see until parties are added.",
            detail:
              "The scenario sets which template fields appear (make, model, year for a vehicle; address, monthly rent, deposit for a room) and which evidence is required before sealing.",
          },
          {
            number: "02",
            title: "Add both parties",
            body: "Each party needs a full name, phone number, and ID document details (Ghana Card number is standard). These are stored and linked to the sealed record.",
            detail:
              "Roles are scenario-specific: buyer + seller for a vehicle; landlord + tenant for a room. A witness can be added optionally. Every non-witness party must have ID details before sealing.",
          },
          {
            number: "03",
            title: "Capture evidence",
            body: "Upload photos of the asset, ID documents for each party, and any supporting files. On the web you can drag-and-drop multiple files at once. On mobile, use the camera.",
            detail:
              "Each file is uploaded directly to encrypted cloud storage via a presigned URL. The backend records a file hash and confirms the upload before the item counts towards sealing requirements.",
          },
          {
            number: "04",
            title: "Fill in the details",
            body: "Complete the scenario-specific fields — vehicle condition, agreed price, payment method, handover date for a car sale; rent amount, deposit, lease dates for a room.",
            detail:
              "These fields are stored as structured data alongside the agreement, making the sealed PDF readable and searchable. All data is captured before consent is requested.",
          },
          {
            number: "05",
            title: "Both parties confirm by OTP",
            body: "One party triggers the consent request — this sends an SMS OTP to every party's verified phone number. Each party enters their own code independently.",
            detail:
              "No single party can seal the agreement alone. The OTP acts as an electronic signature under Ghana's Electronic Transactions Act (Act 772, Section 9). Each confirmation is timestamped and stored as a ConsentRecord.",
          },
          {
            number: "06",
            title: "The agreement is sealed",
            body: "Once all parties confirm, the backend computes a SHA-256 hash over the full agreement snapshot and stores an immutable VaultEntry. The agreement status changes to Sealed.",
            detail:
              "The seal hash is deterministic — the same inputs always produce the same hash. Any change to the agreement after sealing would produce a different hash, making tampering immediately detectable.",
          },
          {
            number: "07",
            title: "Download the PDF and keep your vault",
            body: "A PDF export is generated automatically — it includes all parties, evidence thumbnails, agreed terms, consent timestamps, and the full seal hash. Store it, share it, or print it.",
            detail:
              "The vault entry is retained for your free retention period and then archived. Archived entries remain stored; they just move out of your active vault view. You can retrieve them at any time.",
          },
        ].map(({ number, title, body, detail }) => (
          <div key={number} className="flex gap-6">
            <div className="shrink-0">
              <span className="text-5xl font-bold text-neutral-100">{number}</span>
            </div>
            <div className="flex flex-col gap-2 pt-2">
              <h2 className="text-xl font-bold">{title}</h2>
              <p className="text-neutral-600 leading-relaxed">{body}</p>
              <p className="text-sm text-neutral-400 leading-relaxed border-l-2 border-neutral-100 pl-4 mt-1">
                {detail}
              </p>
            </div>
          </div>
        ))}

        <div className="rounded-2xl bg-neutral-900 text-white px-8 py-8 text-center">
          <p className="text-2xl font-bold mb-2">Record it today. Rest easy tomorrow.</p>
          <p className="text-neutral-400 mb-6">
            Good agreements make good friends — but sealed agreements make better ones.
          </p>
          <Link
            href="/login"
            className="inline-block px-6 py-3 rounded-full bg-white text-neutral-900 font-medium hover:bg-neutral-100 transition-colors"
          >
            Seal your first agreement →
          </Link>
        </div>
      </main>
    </div>
  );
}
