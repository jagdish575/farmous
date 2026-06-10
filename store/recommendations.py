from django.db.models import Count, Q

from .models import Medicine, OrderItem, ProductView


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _viewer_filter(request):
    session_key = _session_key(request)
    if request.user.is_authenticated:
        return Q(user=request.user) | Q(session_key=session_key)
    return Q(session_key=session_key)


def track_product_view(request, medicine):
    ProductView.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=_session_key(request),
        medicine=medicine,
        category=medicine.category,
    )
    session_key = _session_key(request)
    keep_ids = list(
        ProductView.objects.filter(session_key=session_key)
        .order_by("-viewed_at")
        .values_list("pk", flat=True)[:50]
    )
    if keep_ids:
        ProductView.objects.filter(session_key=session_key).exclude(pk__in=keep_ids).delete()


def _active_medicines(queryset=None):
    base = Medicine.objects.filter(is_active=True).select_related("category")
    if queryset is None:
        return base
    return base.filter(pk__in=queryset)


def get_recently_viewed(request, exclude=None, limit=8):
    viewer = _viewer_filter(request)
    views = ProductView.objects.filter(viewer).select_related("medicine", "medicine__category")
    if exclude:
        views = views.exclude(medicine_id=exclude)
    ids = []
    seen = set()
    for view in views.order_by("-viewed_at")[: limit * 3]:
        if view.medicine_id in seen:
            continue
        seen.add(view.medicine_id)
        ids.append(view.medicine_id)
        if len(ids) >= limit:
            break
    if not ids:
        return Medicine.objects.none()
    preserved = {pk: index for index, pk in enumerate(ids)}
    medicines = _active_medicines(ids)
    return sorted(medicines, key=lambda med: preserved.get(med.pk, 999))


def get_keep_shopping_for(request, limit=8):
    viewer = _viewer_filter(request)
    viewed_category_ids = (
        ProductView.objects.filter(viewer)
        .values_list("category_id", flat=True)
        .distinct()
    )
    if not viewed_category_ids:
        return Medicine.objects.none()

    purchased_category_ids = set()
    if request.user.is_authenticated:
        purchased_category_ids = set(
            OrderItem.objects.filter(order__user=request.user)
            .values_list("medicine__category_id", flat=True)
            .distinct()
        )

    target_categories = [cid for cid in viewed_category_ids if cid not in purchased_category_ids]
    if not target_categories:
        target_categories = list(viewed_category_ids)

    recently_viewed_ids = set(
        ProductView.objects.filter(viewer).values_list("medicine_id", flat=True)[:30]
    )
    return (
        _active_medicines()
        .filter(category_id__in=target_categories)
        .exclude(pk__in=recently_viewed_ids)
        .order_by("-is_featured", "name")[:limit]
    )


def get_similar_products(medicine, limit=8):
    return (
        _active_medicines()
        .filter(category=medicine.category)
        .exclude(pk=medicine.pk)
        .order_by("-is_featured", "name")[:limit]
    )


def get_browsing_recommendations(request, limit=8):
    viewer = _viewer_filter(request)
    category_ids = list(
        ProductView.objects.filter(viewer)
        .values_list("category_id", flat=True)
        .distinct()[:5]
    )
    if not category_ids:
        return Medicine.objects.none()

    viewed_ids = set(ProductView.objects.filter(viewer).values_list("medicine_id", flat=True)[:40])
    return (
        _active_medicines()
        .filter(category_id__in=category_ids)
        .exclude(pk__in=viewed_ids)
        .order_by("-is_featured", "-stock_quantity")[:limit]
    )


def get_customers_also_viewed(medicine, request, limit=8):
    sessions = (
        ProductView.objects.filter(medicine=medicine)
        .values_list("session_key", flat=True)
        .distinct()[:100]
    )
    if not sessions:
        return get_similar_products(medicine, limit)

    co_viewed_ids = (
        ProductView.objects.filter(session_key__in=sessions)
        .exclude(medicine=medicine)
        .values("medicine_id")
        .annotate(view_count=Count("medicine_id"))
        .order_by("-view_count")
        .values_list("medicine_id", flat=True)[: limit * 2]
    )
    medicines = list(_active_medicines(co_viewed_ids)[:limit])
    if medicines:
        return medicines
    return get_similar_products(medicine, limit)


def get_frequently_bought_together(medicine, limit=4):
    order_ids = OrderItem.objects.filter(medicine=medicine).values_list("order_id", flat=True)
    if not order_ids:
        return Medicine.objects.none()

    companion_ids = (
        OrderItem.objects.filter(order_id__in=order_ids)
        .exclude(medicine=medicine)
        .values("medicine_id")
        .annotate(freq=Count("medicine_id"))
        .order_by("-freq")
        .values_list("medicine_id", flat=True)[:limit]
    )
    return _active_medicines(companion_ids)
