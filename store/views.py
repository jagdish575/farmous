import json
import urllib.parse
from django.conf import settings
from django.db import models
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import AddressForm, MobileLoginForm, NotificationSettingsForm, OtpVerifyForm, ProfileForm
from .razorpay_utils import RazorpayError, create_razorpay_order, is_razorpay_configured, verify_payment_signature
from .twilio_verify import TwilioVerifyError, check_verification_code, send_verification_code
from .models import (Address, Cart, CartItem, Category, Medicine, Order, OrderItem,
                     SiteSettings)
from . import recommendations as rec
from .india_locations import CITIES_BY_STATE, STATE_ALIASES
from .order_messages import format_cancel_whatsapp_message, format_order_whatsapp_message

User = get_user_model()

def get_settings():
    settings = SiteSettings.objects.first()
    if settings is None:
        settings = SiteSettings.objects.create()
    return settings

def get_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart

def serialize_cart(cart):
    items = []
    for item in cart.items.select_related("medicine", "medicine__category"):
        items.append({
            "id": item.id,
            "medicine_name": item.medicine.name,
            "category": item.medicine.category.name,
            "image": item.medicine.display_image,
            "price": float(item.price),
            "quantity": item.quantity,
            "item_total": float(item.total_price),
        })
    return {
        "cart_count": cart.total_items,
        "cart_total": float(cart.total_price),
        "items": items,
    }

def build_whatsapp_url(message_lines):
    settings = get_settings()
    message = urllib.parse.quote("\n".join(message_lines))
    phone = settings.whatsapp_number.lstrip("+")
    return f"https://wa.me/{phone}?text={message}"


def home(request):
    categories = Category.objects.all()[:8]
    featured = Medicine.objects.filter(is_active=True, is_featured=True).order_by("name")[:8]
    popular = Medicine.objects.filter(is_active=True).order_by("-stock_quantity", "name")[:8]
    context = {
        "categories": categories,
        "featured": featured,
        "popular": popular,
        "recently_viewed": rec.get_recently_viewed(request),
        "keep_shopping": rec.get_keep_shopping_for(request),
        "browsing_recommendations": rec.get_browsing_recommendations(request),
        "shop_url": reverse("store:medicine_list"),
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
    rec.track_product_view(request, medicine)
    context = {
        "medicine": medicine,
        "similar_products": rec.get_similar_products(medicine),
        "also_viewed": rec.get_customers_also_viewed(medicine, request),
        "frequently_bought_together": rec.get_frequently_bought_together(medicine),
        "recently_viewed": rec.get_recently_viewed(request, exclude=medicine.pk),
    }
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
    context = {
        "form": form,
        "address": address,
        "cities_by_state_json": json.dumps(CITIES_BY_STATE),
        "state_aliases_json": json.dumps(STATE_ALIASES),
    }
    return render(request, "store/address_form.html", context)

def _prepare_checkout_order(user):
    cart = get_cart(user)
    if not cart.items.exists():
        return None, "Add items to cart before checkout."
    address = user.addresses.first()
    if address is None:
        return None, "address_missing"
    if address.mobile_number != user.mobile_number:
        address.mobile_number = user.mobile_number
        address.save(update_fields=["mobile_number"])
    order = Order.objects.create(user=user, address=address, payment_status="unpaid", status="pending")
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            medicine=item.medicine,
            quantity=item.quantity,
            price=item.price,
        )
    return order, None


@login_required
def checkout(request):
    if not is_razorpay_configured():
        messages.error(request, "Online payment is not configured. Add Razorpay keys to your .env file.")
        return redirect("store:cart")

    order, error = _prepare_checkout_order(request.user)
    if error == "address_missing":
        messages.warning(request, "Please add your delivery address before checkout.")
        return redirect("store:address_list")
    if error:
        messages.error(request, error)
        return redirect("store:cart")

    try:
        razorpay_order = create_razorpay_order(order)
        order.razorpay_order_id = razorpay_order["id"]
        order.save(update_fields=["razorpay_order_id"])
    except RazorpayError as exc:
        order.delete()
        messages.error(request, str(exc))
        return redirect("store:cart")

    request.session["pending_order_id"] = order.pk
    amount_paise = int(order.total_price * 100)
    return render(request, "store/checkout.html", {
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": amount_paise,
        "user_name": request.user.full_name or "Customer",
        "user_email": "",
        "user_phone": f"+91{request.user.mobile_number}",
    })


@login_required
def payment_verify(request):
    if request.method != "POST":
        return redirect("store:cart")

    order_pk = request.session.get("pending_order_id")
    order = get_object_or_404(Order, pk=order_pk, user=request.user) if order_pk else None
    if not order:
        messages.error(request, "Checkout session expired. Please try again.")
        return redirect("store:cart")

    razorpay_order_id = request.POST.get("razorpay_order_id", "")
    razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
    razorpay_signature = request.POST.get("razorpay_signature", "")

    try:
        verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
        order.razorpay_payment_id = razorpay_payment_id
        order.payment_status = "paid"
        order.status = "confirmed"
        order.save(update_fields=["razorpay_payment_id", "payment_status", "status"])
        get_cart(request.user).items.all().delete()
        request.session.pop("pending_order_id", None)
        message_lines = format_order_whatsapp_message(order, order.address, request.user)
        message_lines.insert(6, f"💳 *Payment:* Paid via Razorpay ({razorpay_payment_id})")
        request.session["whatsapp_checkout_url"] = build_whatsapp_url(message_lines)
        messages.success(request, "Payment successful! Your order is confirmed.")
        return redirect("store:order_success", pk=order.pk)
    except Exception:
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])
        messages.error(request, "Payment verification failed. Please try again or contact support.")
        return redirect("store:cart")


@login_required
def place_order(request):
    """Legacy route — redirects to Razorpay checkout."""
    return redirect("store:checkout")


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    whatsapp_url = request.session.pop("whatsapp_checkout_url", None)
    return render(request, "store/order_success.html", {
        "order": order,
        "whatsapp_url": whatsapp_url,
    })

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
    message_lines = format_cancel_whatsapp_message(order, request.user)
    request.session["whatsapp_checkout_url"] = build_whatsapp_url(message_lines)
    messages.success(request, "Order cancelled. WhatsApp will open in a new tab to notify the pharmacy.")
    return redirect("store:order_success", pk=order.pk)

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

def _login_or_create_user(request, mobile):
    user = User.objects.filter(mobile_number=mobile).first()
    if not user:
        user = User.objects.create_user(mobile_number=mobile, full_name="Valued Customer")
    user = authenticate(request, mobile_number=mobile)
    if not user:
        return None
    login(request, user, backend="store.auth_backends.MobileBackend")
    request.session.pop("otp_mobile", None)
    request.session.pop("otp_sent_at", None)
    return user


def login_mobile(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url:
        request.session["login_next"] = next_url
    if request.method == "POST":
        form = MobileLoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data["mobile_number"]
            # --- Direct login (OTP disabled for now) ---
            user = _login_or_create_user(request, mobile)
            if user:
                redirect_url = request.session.pop("login_next", None) or reverse("store:home")
                messages.success(request, "Welcome back!")
                return redirect(redirect_url)
            messages.error(request, "Unable to login with this mobile number.")

            # --- Twilio OTP login (uncomment to enable) ---
            # try:
            #     send_verification_code(mobile)
            #     request.session["otp_mobile"] = mobile
            #     messages.success(request, f"Verification code sent to +91 {mobile}.")
            #     return redirect("store:verify_otp")
            # except TwilioVerifyError as exc:
            #     messages.error(request, str(exc))
    else:
        form = MobileLoginForm()
    return render(request, "store/login_mobile.html", {"form": form, "next": next_url})


def verify_otp(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    mobile = request.session.get("otp_mobile")
    if not mobile:
        messages.warning(request, "Enter your mobile number to receive a verification code.")
        return redirect("store:login")

    if request.method == "POST":
        action = request.POST.get("action", "verify")
        if action == "resend":
            try:
                send_verification_code(mobile)
                messages.success(request, f"New verification code sent to +91 {mobile}.")
            except TwilioVerifyError as exc:
                messages.error(request, str(exc))
            return redirect("store:verify_otp")

        form = OtpVerifyForm(request.POST)
        if form.is_valid():
            try:
                check_verification_code(mobile, form.cleaned_data["otp_code"])
                user = _login_or_create_user(request, mobile)
                if user:
                    next_url = request.session.pop("login_next", None) or request.GET.get("next") or reverse("store:home")
                    messages.success(request, "Mobile number verified. Welcome back!")
                    return redirect(next_url)
                messages.error(request, "Unable to complete login. Please try again.")
            except TwilioVerifyError as exc:
                messages.error(request, str(exc))
    else:
        form = OtpVerifyForm()

    masked = f"******{mobile[-4:]}"
    return render(request, "store/verify_otp.html", {
        "form": form,
        "mobile": mobile,
        "masked_mobile": masked,
    })

def logout_view(request):
    logout(request)
    return redirect("store:home")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
