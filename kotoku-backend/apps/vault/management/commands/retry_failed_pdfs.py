"""Management command: re-enqueue failed or stuck vault PDF exports.

Use this after fixing an S3 credential issue (or any infrastructure outage)
to recover entries that ended up in FAILED or stuck-GENERATING state:

    # Re-queue all failed PDFs
    python manage.py retry_failed_pdfs

    # Re-queue specific vault entries
    python manage.py retry_failed_pdfs --ids 1 2

    # Dry-run to see what would be re-queued without actually doing it
    python manage.py retry_failed_pdfs --dry-run
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Re-enqueue vault PDF exports that are in FAILED or stuck GENERATING state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ids",
            nargs="+",
            type=int,
            metavar="ID",
            help="Specific vault entry IDs to retry (default: all failed entries).",
        )
        parser.add_argument(
            "--include-stuck",
            action="store_true",
            default=True,
            help="Also re-enqueue entries stuck in GENERATING for >5 minutes (default: true).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be re-queued without enqueuing anything.",
        )

    def handle(self, *args, **options):
        from apps.vault.models import VaultEntry
        from apps.vault.tasks import generate_pdf_export

        ids = options["ids"]
        dry_run = options["dry_run"]

        if ids:
            qs = VaultEntry.objects.filter(pk__in=ids)
        else:
            failed_qs = VaultEntry.objects.filter(pdf_status=VaultEntry.PdfStatus.FAILED)
            if options["include_stuck"]:
                cutoff = timezone.now() - timedelta(minutes=5)
                stuck_qs = VaultEntry.objects.filter(
                    pdf_status=VaultEntry.PdfStatus.GENERATING,
                    updated_at__lt=cutoff,
                )
                qs = (failed_qs | stuck_qs).distinct()
            else:
                qs = failed_qs

        entries = list(qs.select_related("agreement"))

        if not entries:
            self.stdout.write(self.style.WARNING("No entries found to retry."))
            return

        self.stdout.write(f"Found {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to retry:")
        for entry in entries:
            self.stdout.write(f"  vault_entry={entry.pk}  agreement={entry.agreement_id}  status={entry.pdf_status}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing enqueued."))
            return

        qs.filter(pk__in=[e.pk for e in entries]).update(pdf_status=VaultEntry.PdfStatus.PENDING)

        for entry in entries:
            generate_pdf_export.delay(entry.pk)

        self.stdout.write(self.style.SUCCESS(f"Re-enqueued {len(entries)} PDF export(s)."))
