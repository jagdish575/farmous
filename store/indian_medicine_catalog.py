from decimal import Decimal, InvalidOperation
from pathlib import Path

import kagglehub
import pandas as pd
from django.db import transaction
from django.utils.text import slugify

from store.kaggle_catalog import deterministic_price, deterministic_stock, reset_catalog, unique_slug
from store.medicine_images import category_image_url, medicine_image_url
from store.models import Category, Medicine

INDIAN_DATASET = "mohneesh7/indian-medicine-data"
INDIAN_CSV = "medicine_data.csv"
CHUNK_SIZE = 5000
BULK_BATCH = 500


def _clean(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none") else text


def parse_price(value, fallback_name):
    text = _clean(value).replace("₹", "").replace(",", "")
    if not text:
        return deterministic_price(fallback_name)
    try:
        price = Decimal(text)
        if price <= 0:
            return deterministic_price(fallback_name)
        return price.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return deterministic_price(fallback_name)


def resolve_indian_csv(csv_arg=""):
    if csv_arg:
        path = Path(csv_arg)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")
        return path

    dataset_path = kagglehub.dataset_download(INDIAN_DATASET)
    path = Path(dataset_path) / INDIAN_CSV
    if not path.exists():
        matches = list(Path(dataset_path).rglob(INDIAN_CSV))
        if not matches:
            raise FileNotFoundError(f"{INDIAN_CSV} not found in downloaded dataset")
        path = matches[0]
    return path


def _category_for_name(name, cache):
    category_name = _clean(name) or "General Health"
    slug = slugify(category_name)[:120] or "general-health"
    if slug not in cache:
        category, created = Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": category_name[:120],
                "image": category_image_url(category_name),
            },
        )
        if not created and not category.image:
            category.image = category_image_url(category_name)
            category.save(update_fields=["image"])
        cache[slug] = category
    return cache[slug]


def _build_description(row):
    parts = []
    desc = _clean(row.get("medicine_desc"))
    salt = _clean(row.get("salt_composition"))
    side_effects = _clean(row.get("side_effects"))
    interactions = _clean(row.get("drug_interactions"))

    if desc:
        parts.append(desc)
    if salt:
        parts.append(f"Composition: {salt}")
    if side_effects:
        parts.append(f"Side effects: {side_effects}")
    if interactions:
        parts.append(f"Drug interactions: {interactions}")
    return "\n\n".join(parts)[:4000]


def _needs_prescription(category_name, description):
    text = f"{category_name} {description}".lower()
    return any(
        word in text
        for word in (
            "insulin",
            "antibiotic",
            "antidepress",
            "chemotherapy",
            "cardiac",
            "hypertension",
            "antipsych",
            "opioid",
            "steroid",
        )
    )


def _row_to_medicine(row, category_cache, existing_slugs):
    name = _clean(row.get("product_name"))
    if not name:
        return None

    category = _category_for_name(row.get("sub_category"), category_cache)
    description = _build_description(row)
    manufacturer = _clean(row.get("product_manufactured"))[:150]
    slug = unique_slug(slugify(name), existing_slugs)

    return Medicine(
        category=category,
        name=name[:200],
        slug=slug,
        description=description,
        manufacturer=manufacturer,
        image=medicine_image_url(name, category.slug),
        price=parse_price(row.get("product_price"), name),
        stock_quantity=deterministic_stock(name),
        prescription_required=_needs_prescription(category.name, description),
        is_featured=False,
        is_active=True,
    )


def import_indian_medicines_csv(csv_path="", limit=0, reset=False, progress_callback=None):
    path = resolve_indian_csv(csv_path)
    if reset:
        reset_catalog()

    category_cache = {}
    existing_slugs = set(Medicine.objects.values_list("slug", flat=True))
    imported = 0
    processed = 0

    reader = pd.read_csv(path, chunksize=CHUNK_SIZE, nrows=limit if limit and limit > 0 else None)
    for chunk in reader:
        medicines = []
        for _, row in chunk.iterrows():
            processed += 1
            medicine = _row_to_medicine(row, category_cache, existing_slugs)
            if medicine:
                medicines.append(medicine)

        if medicines:
            with transaction.atomic():
                Medicine.objects.bulk_create(medicines, batch_size=BULK_BATCH, ignore_conflicts=True)
            imported += len(medicines)

        if progress_callback:
            progress_callback(imported, processed)

    return imported, path
