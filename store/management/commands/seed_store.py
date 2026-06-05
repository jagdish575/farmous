from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Load sample store data (alias for load_dummy_data)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing catalog data before loading",
        )
        parser.add_argument(
            "--file",
            default="dummy_data",
            help="Fixture name (default: dummy_data)",
        )

    def handle(self, *args, **options):
        call_command(
            "load_dummy_data",
            file=options["file"],
            reset=options["reset"],
        )
