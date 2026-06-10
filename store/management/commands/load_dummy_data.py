import json
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from store.models import CartItem, Category, Medicine, OrderItem, ProductView, SiteSettings


class Command(BaseCommand):
    help = (
        "Load dummy pharmacy data from JSON. "
        "Use Django fixture (dummy_data.json) or easy-edit catalog (catalog.json)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="dummy_data",
            help="Fixture name without .json (default: dummy_data) or path to catalog.json",
        )
        parser.add_argument(
            "--format",
            choices=["fixture", "catalog"],
            default="fixture",
            help="fixture = Django loaddata format, catalog = simple store/data/catalog.json format",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing categories, medicines, and site settings before loading",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_store_data()

        if options["format"] == "catalog":
            path = self._resolve_catalog_path(options["file"])
            self._load_catalog(path)
            self.stdout.write(self.style.SUCCESS(f"Loaded catalog data from {path.name}"))
            return

        fixture_name = options["file"].replace(".json", "")
        if "/" in fixture_name or "\\" in fixture_name:
            raise CommandError("For custom paths use --format catalog")
        self.stdout.write(self.style.NOTICE(f"Loading fixture: {fixture_name}.json"))
        call_command("loaddata", fixture_name)
        self.stdout.write(self.style.SUCCESS("Dummy data loaded successfully."))

    def _reset_store_data(self):
        self.stdout.write(self.style.WARNING("Removing existing store catalog data..."))
        CartItem.objects.all().delete()
        OrderItem.objects.all().delete()
        ProductView.objects.all().delete()
        Medicine.objects.all().delete()
        Category.objects.all().delete()
        SiteSettings.objects.all().delete()

    def _resolve_catalog_path(self, file_arg):
        if file_arg == "dummy_data" or file_arg == "catalog":
            path = Path(__file__).resolve().parents[2] / "data" / "catalog.json"
        else:
            path = Path(file_arg)
            if not path.is_absolute():
                path = Path.cwd() / path
        if not path.exists():
            raise CommandError(f"Catalog file not found: {path}")
        return path

    @transaction.atomic
    def _load_catalog(self, path):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        settings_data = data.get("site_settings", {})
        if settings_data:
            settings = SiteSettings.objects.first()
            if settings is None:
                settings = SiteSettings.objects.create(**settings_data)
            else:
                for key, value in settings_data.items():
                    setattr(settings, key, value)
                settings.save()

        category_map = {}
        for item in data.get("categories", []):
            category, _ = Category.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "image": item.get("image", ""),
                },
            )
            category_map[item["slug"]] = category

        for item in data.get("medicines", []):
            category_slug = item.get("category")
            if not category_slug or category_slug not in category_map:
                raise CommandError(
                    f"Medicine '{item.get('name')}' references unknown category '{category_slug}'"
                )
            Medicine.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "category": category_map[category_slug],
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "manufacturer": item.get("manufacturer", ""),
                    "image": item.get("image", ""),
                    "price": Decimal(str(item.get("price", 0))),
                    "stock_quantity": int(item.get("stock_quantity", 0)),
                    "prescription_required": bool(item.get("prescription_required", False)),
                    "is_featured": bool(item.get("is_featured", False)),
                    "is_active": bool(item.get("is_active", True)),
                },
            )

        self.stdout.write(
            self.style.NOTICE(
                f"Categories: {Category.objects.count()}, Medicines: {Medicine.objects.count()}"
            )
        )
