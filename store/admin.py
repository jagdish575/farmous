from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Count, Q
from .models import (
    User,
    Category,
    Medicine,
    Address,
    Cart,
    CartItem,
    Order,
    OrderItem,
    SiteSettings,
)

class FarmosAdminSite(AdminSite):
    site_header = "Pharmos Pharmacy Admin"
    site_title = "Pharmos Admin"
    index_title = "Store Dashboard"
    index_template = "admin/dashboard.html"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({
            "total_medicines": Medicine.objects.count(),
            "total_orders": Order.objects.count(),
            "pending_orders": Order.objects.filter(status="pending").count(),
            "delivered_orders": Order.objects.filter(status="delivered").count(),
            "cancelled_orders": Order.objects.filter(status="cancelled").count(),
            "total_users": User.objects.count(),
            "low_stock": Medicine.objects.filter(stock_quantity__lte=10).count(),
        })
        return super().index(request, extra_context=extra_context)

admin_site = FarmosAdminSite(name="farmos_admin")

@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "mobile_number", "is_staff", "is_active", "created_at")
    search_fields = ("full_name", "mobile_number")
    list_filter = ("is_staff", "is_active")

@admin.register(Category, site=admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

@admin.register(Medicine, site=admin_site)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock_quantity", "is_active", "is_featured")
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "manufacturer")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Address, site=admin_site)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "state", "pincode")
    search_fields = ("user__full_name", "city", "state", "pincode")

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart, site=admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user",)
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ("medicine", "quantity", "price")
    extra = 0

@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("order_id", "user__full_name", "user__mobile_number")
    inlines = [OrderItemInline]

@admin.register(SiteSettings, site=admin_site)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("whatsapp_number", "support_email", "support_phone")

admin_site.register(OrderItem)
