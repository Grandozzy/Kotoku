from django.core.management.base import BaseCommand
from django.test import override_settings

from apps.vault.models import VaultEntry


class Command(BaseCommand):
    help = "Smoke test: generate PDF for a sealed vault entry and verify it succeeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--entry-id",
            type=int,
            help="Specific VaultEntry ID to test (defaults to the most recent sealed entry)",
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def handle(self, *args, **options):
        from apps.vault.tasks import generate_pdf_export

        entry_id = options.get("entry_id")
        if not entry_id:
            entry = (
                VaultEntry.objects.filter(
                    agreement__status="sealed",
                    pdf_status__in=["pending", "failed"],
                )
                .order_by("-created_at")
                .first()
            )
            if not entry:
                self.stdout.write(self.style.ERROR("No sealed vault entry found to test."))
                return
            entry_id = entry.pk

        self.stdout.write(f"Testing PDF export for vault entry {entry_id}...")

        try:
            generate_pdf_export.apply(kwargs={"vault_entry_id": entry_id})
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Task failed: {exc}"))
            return

        entry = VaultEntry.objects.get(pk=entry_id)
        if entry.pdf_status == VaultEntry.PdfStatus.READY and entry.pdf_url:
            self.stdout.write(self.style.SUCCESS("PDF export succeeded!"))
            self.stdout.write(f"  pdf_status: {entry.pdf_status}")
            self.stdout.write(f"  pdf_url:    {entry.pdf_url}")
        else:
            self.stdout.write(self.style.ERROR(
                f"PDF export did not complete. Status: {entry.pdf_status}"
            ))
