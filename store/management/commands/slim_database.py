from django.core.management.base import BaseCommand
from django.db import connection, transaction

from store.models import CartItem, Medicine, OrderItem, ProductView

DELETE_BATCH = 2000


class Command(BaseCommand):
    help = (
        "Free Neon storage: shorten descriptions and optionally remove excess medicines. "
        "Run when you hit the 512 MB free-tier limit."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-medicines",
            type=int,
            default=25000,
            help="Keep this many medicines (default: 25000)",
        )
        parser.add_argument(
            "--description-length",
            type=int,
            default=350,
            help="Truncate descriptions to this length (default: 350)",
        )
        parser.add_argument(
            "--skip-delete",
            action="store_true",
            help="Only truncate descriptions, do not delete medicines",
        )

    def handle(self, *args, **options):
        max_medicines = options["max_medicines"]
        desc_len = options["description_length"]
        total_before = Medicine.objects.count()
        self.stdout.write(self.style.NOTICE(f"Medicines before: {total_before:,}"))

        # Delete first — UPDATE needs free space on a full Neon volume.
        if not options["skip_delete"] and total_before > max_medicines:
            self._trim_medicines(max_medicines)

        total_after = Medicine.objects.count()
        if total_after and desc_len > 0:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE store_medicine SET description = LEFT(description, %s)",
                        [desc_len],
                    )
                    truncated = cursor.rowcount
                self.stdout.write(
                    self.style.SUCCESS(f"Truncated {truncated:,} descriptions to {desc_len} chars.")
                )
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"Description truncate skipped: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Medicines after: {total_after:,}"))
        self.stdout.write(
            self.style.WARNING(
                "In Neon SQL Editor run: VACUUM FULL; to reclaim disk after large deletes."
            )
        )

    def _trim_medicines(self, max_medicines):
        cutoff = (
            Medicine.objects.order_by("id")
            .values_list("id", flat=True)[max_medicines - 1 : max_medicines]
        )
        cutoff = list(cutoff)
        if not cutoff:
            return
        cutoff_id = cutoff[0]
        self.stdout.write(self.style.WARNING(f"Deleting medicines with id > {cutoff_id}..."))

        deleted = 0
        while True:
            ids = list(
                Medicine.objects.filter(id__gt=cutoff_id)
                .order_by("id")
                .values_list("id", flat=True)[:DELETE_BATCH]
            )
            if not ids:
                break
            with transaction.atomic():
                CartItem.objects.filter(medicine_id__in=ids).delete()
                OrderItem.objects.filter(medicine_id__in=ids).delete()
                ProductView.objects.filter(medicine_id__in=ids).delete()
                removed, _ = Medicine.objects.filter(id__in=ids).delete()
            deleted += removed
            self.stdout.write(f"  Removed {deleted:,} rows...")
