from django.core.management.base import BaseCommand

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
        for category in cat_qs.only("id", "name", "image"):
            category.image = category_image_url(category.name)
            category.save(update_fields=["image"])
            cat_updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {cat_updated:,} category images."))

        med_filter = {} if refresh_all else {"image": ""}
        last_id = 0
        med_updated = 0

        while True:
            batch = list(
                Medicine.objects.filter(id__gt=last_id, **med_filter)
                .select_related("category")
                .only("id", "name", "image", "category__slug")
                .order_by("id")[:BATCH_SIZE]
            )
            if not batch:
                break

            for medicine in batch:
                medicine.image = medicine_image_url(medicine.name, medicine.category.slug)

            Medicine.objects.bulk_update(batch, ["image"])
            last_id = batch[-1].id
            med_updated += len(batch)
            self.stdout.write(f"  Updated {med_updated:,} medicine images...")

        self.stdout.write(self.style.SUCCESS(f"Updated {med_updated:,} medicine images."))
