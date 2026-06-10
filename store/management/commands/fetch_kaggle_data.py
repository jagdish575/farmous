from django.core.management.base import BaseCommand

from store.kaggle_catalog import load_kaggle_catalog


class Command(BaseCommand):
    help = (
        "Download the Kaggle 11000-medicine-details dataset and import all medicines "
        "into the database (Neon PostgreSQL or local DB)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing medicines and categories before import",
        )
        parser.add_argument(
            "--csv",
            default="",
            help="Optional path to Medicine_Details.csv (skips kagglehub download)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Downloading Kaggle medicine dataset..."))

        def progress(done, total):
            self.stdout.write(f"  Imported {done}/{total} medicines...")

        try:
            imported, csv_path = load_kaggle_catalog(
                csv_path=options["csv"],
                limit=0,
                reset=options["reset"],
                progress_callback=progress,
            )
        except FileNotFoundError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.NOTICE(f"Source: {csv_path}"))
        self.stdout.write(self.style.SUCCESS(f"Stored {imported} medicines in the database."))
