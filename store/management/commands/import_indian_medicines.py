from django.core.management.base import BaseCommand

from store.indian_medicine_catalog import import_indian_medicines_csv


class Command(BaseCommand):
    help = (
        "Import Indian medicine data from Kaggle (mohneesh7/indian-medicine-data) "
        "into the database (Neon PostgreSQL or local)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max rows to import (default: 0 = all ~195k medicines)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing catalog before import",
        )
        parser.add_argument(
            "--csv",
            default="",
            help="Optional path to medicine_data.csv (skips kagglehub download)",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Clearing existing catalog..."))

        self.stdout.write(self.style.NOTICE("Downloading / reading Indian medicine dataset..."))

        def progress(imported, processed):
            self.stdout.write(f"  Processed {processed:,} rows — stored {imported:,} medicines...")

        try:
            imported, csv_path = import_indian_medicines_csv(
                csv_path=options["csv"],
                limit=options["limit"],
                reset=options["reset"],
                progress_callback=progress,
            )
        except FileNotFoundError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.NOTICE(f"Source: {csv_path}"))
        self.stdout.write(self.style.SUCCESS(f"Stored {imported:,} medicines in the database."))
