from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fast-clear medicine catalog (for Neon 512MB limit). Then re-import with a limit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--import-limit",
            type=int,
            default=20000,
            help="Re-import this many Indian medicines after reset (default: 20000)",
        )
        parser.add_argument(
            "--no-import",
            action="store_true",
            help="Only truncate tables, do not re-import",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Truncating catalog tables..."))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    store_cartitem,
                    store_productview,
                    store_orderitem,
                    store_medicine,
                    store_category
                RESTART IDENTITY CASCADE
                """
            )
        self.stdout.write(self.style.SUCCESS("Catalog tables cleared."))

        if options["no_import"]:
            self.stdout.write("Run: python manage.py import_indian_medicines --limit 20000")
            return

        limit = options["import_limit"]
        self.stdout.write(self.style.NOTICE(f"Re-importing {limit:,} medicines..."))
        call_command("import_indian_medicines", limit=limit, stdout=self.stdout)
