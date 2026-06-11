from django.core.management.base import BaseCommand
from django.db import transaction

from store.medicine_images import category_image_url, medicine_image_url
from store.models import Category, Medicine

BATCH_SIZE = 1000


class Command(BaseCommand):
    help = "Set external CDN image URLs for medicines and categories missing images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Refresh images for all records, not only empty ones",
        )

    def handle(self, *args, **options):
        refresh_all = options["all"]

        cat_qs = Category.objects.all() if refresh_all else Category.objects.filter(image="")
        cat_updated = 0
        for category in cat_qs.iterator(chunk_size=BATCH_SIZE):
            category.image = category_image_url(category.name)
            category.save(update_fields=["image"])
            cat_updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {cat_updated:,} category images."))

        med_filter = {} if refresh_all else {"image": ""}
        med_qs = Medicine.objects.filter(**med_filter).select_related("category")
        batch = []
        med_updated = 0

        for medicine in med_qs.iterator(chunk_size=BATCH_SIZE):
            medicine.image = medicine_image_url(medicine.name, medicine.category.slug)
            batch.append(medicine)
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    Medicine.objects.bulk_update(batch, ["image"])
                med_updated += len(batch)
                self.stdout.write(f"  Updated {med_updated:,} medicine images...")
                batch = []

        if batch:
            with transaction.atomic():
                Medicine.objects.bulk_update(batch, ["image"])
            med_updated += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Updated {med_updated:,} medicine images."))
