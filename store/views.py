import urllib.parse
from django.db import models
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import AddressForm, MobileLoginForm, NotificationSettingsForm, ProfileForm
from .models import (Address, Cart, CartItem, Category, Medicine, Order, OrderItem,
                     SiteSettings)

User = get_user_model()

def get_settings():
    settings = SiteSettings.objects.first()
    if settings is None:
        settings = SiteSettings.objects.create()
    return settings

def get_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart

DEFAULT_MEDICINE_IMAGE = (
    "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=200&q=80"
)

def serialize_cart(cart):
    items = []
    for item in cart.items.select_related("medicine", "medicine__category"):
        items.append({
            "id": item.id,
            "medicine_name": item.medicine.name,
            "category": item.medicine.category.name,
            "image": item.medicine.image or DEFAULT_MEDICINE_IMAGE,
            "price": float(item.price),
            "quantity": item.quantity,
            "item_total": float(item.total_price),
        })
    return {
        "cart_count": cart.total_items,
        "cart_total": float(cart.total_price),
        "items": items,
    }

def home(request):
    categories = Category.objects.all()[:6]
    featured = Medicine.objects.filter(is_active=True, is_featured=True).order_by("name")[:8]
    popular = Medicine.objects.filter(is_active=True).order_by("-stock_quantity", "name")[:8]
    context = {
        "categories": categories,
        "featured": featured,
        "popular": popular,
    }
    return render(request, "store/home.html", context)

def search_suggestions(request):
    query = request.GET.get("q", "").strip()
    medicines = Medicine.objects.filter(is_active=True).select_related("category")
    if query:
        medicines = medicines.filter(
            models.Q(name__icontains=query)
            | models.Q(category__name__icontains=query)
            | models.Q(manufacturer__icontains=query)
            | models.Q(description__icontains=query)
        )
    total = medicines.count()
    default_image = "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?auto=format&fit=crop&w=200&q=80"
    suggestions = [
        {
            "name": med.name,
            "url": med.get_absolute_url(),
            "category": med.category.name,
            "manufacturer": med.manufacturer,
            "price": str(med.price),
            "image": med.image or default_image,
            "in_stock": med.stock_quantity > 0,
        }
        for med in medicines.order_by("-is_featured", "name")[:8]
    ]
    return JsonResponse({"results": suggestions, "total": total, "query": query})

def medicine_list(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category")
    sort = request.GET.get("sort")
    medicines = Medicine.objects.filter(is_active=True)
    categories = Category.objects.all()
    if query:
        medicines = medicines.filter(
            models.Q(name__icontains=query)
            | models.Q(category__name__icontains=query)
            | models.Q(manufacturer__icontains=query)
        )
    if category_slug:
        medicines = medicines.filter(category__slug=category_slug)
    if sort == "price_asc":
        medicines = medicines.order_by("price")
    elif sort == "price_desc":
        medicines = medicines.order_by("-price")
    else:
        medicines = medicines.order_by("name")
    total_count = medicines.count()
    paginator = Paginator(medicines, 12)
    page = request.GET.get("page")
    medicines_page = paginator.get_page(page)
    selected_category_name = ""
    if category_slug:
        selected_category_name = categories.filter(slug=category_slug).values_list("name", flat=True).first() or ""
    context = {
        "medicines": medicines_page,
        "categories": categories,
        "selected_category": category_slug,
        "selected_category_name": selected_category_name,
        "query": query,
        "sort": sort,
        "total_count": total_count,
    }
    return render(request, "store/medicine_list.html", context)

def medicine_detail(request, slug):
    medicine = get_object_or_404(Medicine, slug=slug, is_active=True)
    context = {"medicine": medicine}
    return render(request, "store/medicine_detail.html", context)

@login_required
def add_to_cart(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id, is_active=True)
    if medicine.stock_quantity < 1:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"error": "Out of stock"}, status=400)
        messages.error(request, f"{medicine.name} is currently out of stock.")
        return redirect(request.META.get("HTTP_REFERER", reverse("store:medicine_list")))
    cart = get_cart(request.user)
    quantity = int(request.POST.get("quantity", 1)) if request.method == "POST" else 1
    quantity = max(1, quantity)
    item, created = CartItem.objects.get_or_create(cart=cart, medicine=medicine, defaults={
        "quantity": quantity,
        "price": medicine.price,
    })
    if not created:
        item.quantity = item.quantity + quantity
        item.save()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        payload = serialize_cart(cart)
        payload.update({"success": True, "medicine_name": medicine.name})
        return JsonResponse(payload)
    messages.success(request, f"{medicine.name} has been added to your cart.")
    return redirect(request.META.get("HTTP_REFERER", reverse("store:cart")))

@login_required
def cart_api(request):
    cart = get_cart(request.user)
    return JsonResponse(serialize_cart(cart))

@login_required
def cart_view(request):
    cart = get_cart(request.user)
    context = {"cart": cart}
    return render(request, "store/cart.html", context)

@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    quantity = int(request.POST.get("quantity", item.quantity))
    if quantity < 1:
        item.delete()
    else:
        item.quantity = quantity
        item.save()
    cart = get_cart(request.user)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        payload = serialize_cart(cart)
        payload["item_total"] = float(item.quantity * item.price) if item.pk else 0
        return JsonResponse(payload)
    return redirect(reverse("store:cart"))

@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    cart = get_cart(request.user)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(serialize_cart(cart))
    return redirect(reverse("store:cart"))

@login_required
def address_list(request):
    addresses = request.user.addresses.all()
    return render(request, "store/address_list.html", {"addresses": addresses})

@login_required
def address_form(request, pk=None):
    address = None
    if pk:
        address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
            messages.success(request, "Saved delivery address successfully.")
            return redirect("store:address_list")
    else:
        form = AddressForm(instance=address)
        if address is None:
            form.initial.setdefault("mobile_number", request.user.mobile_number)
            form.initial.setdefault("full_name", request.user.full_name)
    return render(request, "store/address_form.html", {"form": form, "address": address})

@login_required
def place_order(request):
    cart = get_cart(request.user)
    if not cart.items.exists():
        messages.error(request, "Add items to cart before placing an order.")
        return redirect("store:cart")
    address = request.user.addresses.first()
    if address is None:
        messages.warning(request, "Please add your delivery address before placing an order.")
        return redirect("store:address_list")
    if address.mobile_number != request.user.mobile_number:
        address.mobile_number = request.user.mobile_number
        address.save(update_fields=["mobile_number"])
    order = Order.objects.create(user=request.user, address=address)
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            medicine=item.medicine,
            quantity=item.quantity,
            price=item.price,
        )
    cart.items.all().delete()
    settings = get_settings()
    message_lines = [
        "Hello,",
        "\nNEW MEDICINE ORDER\n",
        f"Order ID: {order.order_id}",
        f"Customer Name: {request.user.full_name}",
        f"Mobile Number: {request.user.mobile_number}",
        "\nDelivery Address:\n",
        f"{address.address_line}",
        f"{address.city}",
        f"{address.state}",
        f"{address.pincode}\n",
        "Medicines:\n",
    ]
    for item in order.items.all():
        message_lines.append(f"{item.medicine.name} x {item.quantity}")
    message_lines.append(f"\nTotal Items: {order.total_items}")
    message_lines.append("\nPlease confirm availability and delivery.")
    message_lines.append("\nThank You.")
    message = urllib.parse.quote("\n".join(message_lines))
    phone = settings.whatsapp_number.lstrip("+")
    return redirect(f"https://wa.me/{phone}?text={message}")

@login_required
def order_list(request):
    orders = request.user.orders.all()
    return render(request, "store/order_list.html", {"orders": orders})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "store/order_detail.html", {"order": order})

@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status not in ["pending", "confirmed"]:
        messages.error(request, "This order cannot be cancelled at this stage.")
        return redirect("store:order_detail", pk=order.pk)
    order.status = "cancelled"
    order.save()
    settings = get_settings()
    message_lines = [
        "Hello,",
        "\nORDER CANCELLATION REQUEST\n",
        f"Order ID: {order.order_id}",
        f"Customer Name: {request.user.full_name}",
        f"Mobile Number: {request.user.mobile_number}",
        "\nPlease cancel my order.",
        "\nThank You.",
    ]
    message = urllib.parse.quote("\n".join(message_lines))
    phone = settings.whatsapp_number.lstrip("+")
    return redirect(f"https://wa.me/{phone}?text={message}")

@login_required
def profile(request):
    request.user.addresses.exclude(mobile_number=request.user.mobile_number).update(
        mobile_number=request.user.mobile_number
    )
    addresses = request.user.addresses.all()
    form = ProfileForm(instance=request.user)
    settings_form = NotificationSettingsForm(instance=request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "profile")
        if form_type == "settings":
            settings_form = NotificationSettingsForm(request.POST, instance=request.user)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Notification preferences saved.")
                return redirect("store:profile")
        else:
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                old_mobile = request.user.mobile_number
                user = form.save()
                if user.mobile_number != old_mobile:
                    user.addresses.update(mobile_number=user.mobile_number)
                messages.success(request, "Profile updated successfully.")
                return redirect("store:profile")

    context = {
        "form": form,
        "settings_form": settings_form,
        "addresses": addresses,
        "default_address": addresses.first(),
        "order_count": request.user.orders.count(),
    }
    return render(request, "store/profile.html", context)

def login_mobile(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    if request.method == "POST":
        form = MobileLoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data["mobile_number"]
            user = User.objects.filter(mobile_number=mobile).first()
            if not user:
                user = User.objects.create_user(mobile_number=mobile, full_name="Valued Customer")
            user = authenticate(request, mobile_number=mobile)
            if user:
                login(request, user, backend="store.auth_backends.MobileBackend")
                return redirect("store:home")
            messages.error(request, "Unable to login with this mobile number.")
    else:
        form = MobileLoginForm()
    return render(request, "store/login_mobile.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("store:home")
