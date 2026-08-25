import Link from "next/link";
import { ArrowRight, MessageCircle } from "lucide-react";
import { PublicNav } from "@/components/layout/PublicNav";

const WHATSAPP_URL =
  "https://wa.me/233597110983?text=Hi%2C%20I%20want%20to%20request%20deletion%20of%20my%20Kotoku%20account%20and%20associated%20data.";

export default function AccountDeletionPage() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <PublicNav />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6 sm:py-16">
        <div className="flex flex-col gap-4">
          <p className="text-sm font-medium uppercase tracking-wide text-emerald-600">
            Account deletion
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl">
            Request deletion of your Kotoku account and associated data
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-neutral-600 sm:text-lg">
            If you want your Kotoku account deleted, use the support channel below and include
            the phone number on the account so we can verify the request and process it safely.
          </p>
        </div>

        <section className="rounded-3xl border border-neutral-200 bg-neutral-50 p-6 sm:p-8">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100">
                <MessageCircle className="h-5 w-5 text-emerald-700" strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-neutral-950">Start a deletion request</h2>
                <p className="text-sm text-neutral-600">
                  Contact Kotoku support on WhatsApp at <strong>+233 59 711 0983</strong>.
                </p>
              </div>
            </div>

            <Link
              href={WHATSAPP_URL}
              className="inline-flex w-fit items-center gap-2 rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700"
            >
              Open WhatsApp support
              <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </Link>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-neutral-200 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-900">
              What to send
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              Share the phone number registered on the account and say that you want your
              Kotoku account and associated data deleted.
            </p>
          </div>
          <div className="rounded-2xl border border-neutral-200 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-900">
              What happens next
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              Kotoku support will verify ownership of the account before processing the request.
              This prevents unauthorized deletion of another person&apos;s data.
            </p>
          </div>
        </section>

        <div className="rounded-2xl border border-dashed border-neutral-300 p-5 text-sm leading-relaxed text-neutral-600">
          Need general legal information instead? Visit the{" "}
          <Link href="/legal" className="font-medium text-emerald-700 underline">
            Kotoku legal page
          </Link>
          .
        </div>
      </main>
    </div>
  );
}
