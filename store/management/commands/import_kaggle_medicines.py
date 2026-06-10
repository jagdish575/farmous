import hashlib
import re
from decimal import Decimal
from pathlib import Path

import kagglehub
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from store.models import CartItem, Category, Medicine, OrderItem, ProductView


CATEGORY_RULES = [
    (("cancer", "tumor", "chemotherapy", "oncology"), "Cancer Care"),
    (("diabetes", "blood sugar", "insulin"), "Diabetes"),
    (("bacterial", "infection", "antibiotic", "antiviral"), "Antibiotics"),
    (("pain", "fever", "headache", "migraine", "arthritis"), "Pain Relief"),
    (("cough", "cold", "flu", "sneez", "runny nose", "congestion"), "Fever & Cold"),
    (("heart", "blood pressure", "cholesterol", "cardiac"), "Heart Care"),
    (("skin", "acne", "dermat", "eczema"), "Skin Care"),
    (("vitamin", "mineral", "supplement", "calcium", "iron"), "Vitamins"),
    (("allerg", "asthma", "respiratory"), "Allergy & Respiratory"),
    (("stomach", "acid", "gastro", "digest", "ulcer", "nausea"), "Digestive Care"),
    (("anxiety", "depression", "mental", "alzheimer", "epilepsy"), "Mental Health"),
    (("eye", "vision", "ophthalm"), "Eye Care"),
    (("pregnancy", "fertility", "hormone"), "Women's Health"),
]


def detect_category(uses_text):
    text = (uses_text or "").lower()
    for keywords, name in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return name
    return "General Health"


def unique_slug(base_slug, existing_slugs):
    slug = base_slug[:200] or "medicine"
    if slug not in existing_slugs:
        existing_slugs.add(slug)
        return slug
    counter = 2
    while True:
        candidate = f"{slug}-{counter}"[:220]
        if candidate not in existing_slugs:
            existing_slugs.add(candidate)
            return candidate
        counter += 1


def deterministic_price(name):
    digest = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16)
    return Decimal(str(25 + (digest % 1475)))


def deterministic_stock(name):
    digest = int(hashlib.md5(name.encode("utf-8")).hexdigest()[8:16], 16)
    return 5 + (digest % 195)


class Command(BaseCommand):
    help = "Import medicines from Kaggle 11000-medicine-details dataset into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Number of medicines to import (default: 500, use 0 for all)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing catalog before import",
        )
        parser.add_argument(
            "--csv",
            default="",
            help="Optional path to Medicine_Details.csv (skips kagglehub download)",
        )

    def handle(self, *args, **options):
        csv_path = self._resolve_csv_path(options["csv"])
        self.stdout.write(self.style.NOTICE(f"Reading dataset from {csv_path}"))

        if options["reset"]:
            self._reset_catalog()

        df = pd.read_csv(csv_path)
        if options["limit"] and options["limit"] > 0:
            df = df.head(options["limit"])

        imported = self._import_dataframe(df)
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} medicines from Kaggle dataset."))

    def _resolve_csv_path(self, csv_arg):
        if csv_arg:
            path = Path(csv_arg)
            if not path.exists():
                raise FileNotFoundError(f"CSV not found: {path}")
            return path
        self.stdout.write("Downloading dataset via kagglehub...")
        dataset_path = kagglehub.dataset_download("singhnavjot2062001/11000-medicine-details")
        path = Path(dataset_path) / "Medicine_Details.csv"
        if not path.exists():
            matches = list(Path(dataset_path).rglob("Medicine_Details.csv"))
            if not matches:
                raise FileNotFoundError("Medicine_Details.csv not found in downloaded dataset")
            path = matches[0]
        return path

    def _reset_catalog(self):
        self.stdout.write(self.style.WARNING("Clearing existing catalog..."))
        CartItem.objects.all().delete()
        OrderItem.objects.all().delete()
        ProductView.objects.all().delete()
        Medicine.objects.all().delete()
        Category.objects.all().delete()

    @transaction.atomic
    def _import_dataframe(self, df):
        category_cache = {}
        existing_slugs = set(Medicine.objects.values_list("slug", flat=True))
        created_count = 0

        for _, row in df.iterrows():
            name = str(row.get("Medicine Name", "")).strip()
            if not name:
                continue

            uses = str(row.get("Uses", "")).strip()
            composition = str(row.get("Composition", "")).strip()
            side_effects = str(row.get("Side_effects", "")).strip()
            manufacturer = str(row.get("Manufacturer", "")).strip()
            image = str(row.get("Image URL", "")).strip()
            if image.lower() in ("nan", "none", ""):
                image = ""

            excellent = row.get("Excellent Review %", 0)
            try:
                excellent = float(excellent)
            except (TypeError, ValueError):
                excellent = 0

            category_name = detect_category(uses)
            category = category_cache.get(category_name)
            if category is None:
                category, _ = Category.objects.get_or_create(
                    slug=slugify(category_name),
                    defaults={"name": category_name},
                )
                category_cache[category_name] = category

            description_parts = []
            if uses:
                description_parts.append(f"Uses: {uses}")
            if composition:
                description_parts.append(f"Composition: {composition}")
            if side_effects:
                description_parts.append(f"Side effects: {side_effects}")
            description = "\n\n".join(description_parts)

            slug = unique_slug(slugify(name), existing_slugs)
            prescription_required = any(
                word in uses.lower()
                for word in ("cancer", "diabetes", "heart", "blood pressure", "insulin", "chemotherapy")
            )

            Medicine.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": category,
                    "name": name[:200],
                    "description": description[:4000],
                    "manufacturer": manufacturer[:150],
                    "image": image,
                    "price": deterministic_price(name),
                    "stock_quantity": deterministic_stock(name),
                    "prescription_required": prescription_required,
                    "is_featured": excellent >= 40,
                    "is_active": True,
                },
            )
            created_count += 1

        return created_count
