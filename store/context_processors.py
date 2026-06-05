from .models import Cart, SiteSettings


def site_settings(request):
    settings = SiteSettings.objects.first()
    cart_items = []
    cart_count = 0
    cart_total = 0
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            cart_items = cart.items.select_related("medicine", "medicine__category").all()
            cart_count = cart.total_items
            cart_total = cart.total_price
        except Cart.DoesNotExist:
            cart_items = []
    return {
        "site_settings": settings,
        "cart_items": cart_items,
        "cart_count": cart_count,
        "cart_total": cart_total,
    }
