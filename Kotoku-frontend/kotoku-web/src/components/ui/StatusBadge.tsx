import type { AgreementStatus } from "@/types/agreement";

const STYLES: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-600",
  active: "bg-blue-50 text-blue-700",
  sealed: "bg-emerald-50 text-emerald-700",
  reopen_requested: "bg-amber-50 text-amber-700",
  archived: "bg-neutral-100 text-neutral-500",
  expired: "bg-neutral-100 text-neutral-500",
  closed: "bg-neutral-100 text-neutral-500",
};

const LABELS: Record<string, string> = {
  draft: "Draft",
  active: "Active",
  sealed: "Sealed",
  reopen_requested: "Reopen requested",
  archived: "Archived",
  expired: "Expired",
  closed: "Closed",
};

export function StatusBadge({ status }: { status: AgreementStatus }) {
  return (
    <span
      className={`inline-block text-xs font-medium px-2.5 py-1 rounded-full ${
        STYLES[status] ?? "bg-neutral-100 text-neutral-600"
      }`}
    >
      {LABELS[status] ?? status}
    </span>
  );
}
