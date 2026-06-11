import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from store.models import Medicine


class Command(BaseCommand):
    help = (
        "Seed the store catalog on an empty database. "
        "Used during Render deploy after migrations."
    )

    def handle(self, *args, **options):
        if Medicine.objects.exists():
            count = Medicine.objects.count()
            self.stdout.write(self.style.NOTICE(f"Catalog already has {count} medicines — skipping seed."))
            return

        has_kaggle = bool(
            os.getenv("KAGGLE_API_TOKEN")
            or (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"))
        )
        if has_kaggle:
            self.stdout.write(self.style.NOTICE("Empty database — importing Kaggle medicine catalog..."))
            try:
                call_command("fetch_kaggle_data", stdout=self.stdout)
                return
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"Kaggle import failed ({exc}). Falling back to bundled data."))

        self.stdout.write(self.style.NOTICE("Loading bundled sample catalog (categories + medicines)..."))
        call_command("load_dummy_data", stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("Catalog seeded successfully."))
