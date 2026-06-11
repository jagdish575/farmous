import hashlib
from decimal import Decimal
from pathlib import Path

import kagglehub
import pandas as pd
from django.db import transaction
from django.utils.text import slugify

from store.medicine_images import category_image_url, resolve_medicine_image
from store.models import CartItem, Category, Medicine, OrderItem, ProductView

KAGGLE_DATASET = "singhnavjot2062001/11000-medicine-details"
CSV_FILENAME = "Medicine_Details.csv"

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


def resolve_kaggle_csv(csv_arg=""):
    if csv_arg:
        path = Path(csv_arg)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")
        return path

    dataset_path = kagglehub.dataset_download(KAGGLE_DATASET)
    path = Path(dataset_path) / CSV_FILENAME
    if not path.exists():
        matches = list(Path(dataset_path).rglob(CSV_FILENAME))
        if not matches:
            raise FileNotFoundError(f"{CSV_FILENAME} not found in downloaded dataset")
        path = matches[0]
    return path


def reset_catalog():
    CartItem.objects.all().delete()
    OrderItem.objects.all().delete()
    ProductView.objects.all().delete()
    Medicine.objects.all().delete()
    Category.objects.all().delete()


@transaction.atomic
def import_medicines_dataframe(df, progress_callback=None):
    category_cache = {}
    existing_slugs = set(Medicine.objects.values_list("slug", flat=True))
    created_count = 0
    total = len(df)

    for index, row in df.iterrows():
        name = str(row.get("Medicine Name", "")).strip()
        if not name:
            continue

        uses = str(row.get("Uses", "")).strip()
        composition = str(row.get("Composition", "")).strip()
        side_effects = str(row.get("Side_effects", "")).strip()
        manufacturer = str(row.get("Manufacturer", "")).strip()
        image = str(row.get("Image URL", "")).strip()

        excellent = row.get("Excellent Review %", 0)
        try:
            excellent = float(excellent)
        except (TypeError, ValueError):
            excellent = 0

        category_name = detect_category(uses)
        category = category_cache.get(category_name)
        if category is None:
            cat_slug = slugify(category_name)
            category, created = Category.objects.get_or_create(
                slug=cat_slug,
                defaults={
                    "name": category_name,
                    "image": category_image_url(category_name),
                },
            )
            if not created and not category.image:
                category.image = category_image_url(category_name)
                category.save(update_fields=["image"])
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
        cat_slug = category.slug
        image = resolve_medicine_image(image, name, cat_slug)
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

        if progress_callback and (created_count % 250 == 0 or created_count == total):
            progress_callback(created_count, total)

    return created_count


def load_kaggle_catalog(csv_path="", limit=0, reset=False, progress_callback=None):
    path = resolve_kaggle_csv(csv_path)
    if reset:
        reset_catalog()

    df = pd.read_csv(path)
    if limit and limit > 0:
        df = df.head(limit)

    imported = import_medicines_dataframe(df, progress_callback=progress_callback)
    return imported, path
