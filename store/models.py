from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

class UserManager(BaseUserManager):
    def create_user(self, mobile_number, full_name="", password=None, **extra_fields):
        if not mobile_number:
            raise ValueError("Users must have a mobile number")
        mobile_number = str(mobile_number).strip()
        user = self.model(mobile_number=mobile_number, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, full_name, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(mobile_number, full_name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=20, unique=True)
    notify_order_updates = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=True)
    notify_refill_reminders = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "mobile_number"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.full_name or self.mobile_number}"

class SiteSettings(models.Model):
    whatsapp_number = models.CharField(max_length=20, blank=True, default="+911234567890")
    support_email = models.EmailField(blank=True, default="support@farmos.com")
    support_phone = models.CharField(max_length=20, blank=True, default="+91 98765 43210")

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Global Settings"

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    image = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    @property
    def display_image(self):
        from store.medicine_images import category_image_url

        if self.image:
            return self.image
        return category_image_url(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Medicine(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="medicines")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    image = models.URLField(blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    prescription_required = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def display_image(self):
        from store.medicine_images import resolve_medicine_image

        return resolve_medicine_image(self.image, self.name, self.category.slug)

    def get_absolute_url(self):
        return reverse("store:medicine_detail", args=[self.slug])

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=20)
    address_line = models.TextField()
    landmark = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.full_name} • {self.city}, {self.state}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.quantity * item.price for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        unique_together = ("cart", "medicine")

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.price = self.medicine.price
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        return self.quantity * self.price

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]
    order_id = models.CharField(max_length=30, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid")
    razorpay_order_id = models.CharField(max_length=120, blank=True)
    razorpay_payment_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_id

    def save(self, *args, **kwargs):
        if not self.order_id:
            prefix = "ORD"
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.order_id = f"{prefix}{timestamp}{self.user.pk}"
        super().save(*args, **kwargs)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.quantity * item.price for item in self.items.all())

class ProductView(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="product_views"
    )
    session_key = models.CharField(max_length=40, db_index=True)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="views")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["session_key", "viewed_at"]),
            models.Index(fields=["user", "viewed_at"]),
            models.Index(fields=["medicine", "viewed_at"]),
        ]

    def __str__(self):
        return f"{self.medicine.name} viewed at {self.viewed_at}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"

    def total_price(self):
        return self.quantity * self.price
