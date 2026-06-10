from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_mobile, name="login"),
    path("login/verify/", views.verify_otp, name="verify_otp"),
    path("logout/", views.logout_view, name="logout"),
    path("search/", views.medicine_list, name="medicine_list"),
    path("medicine/<slug:slug>/", views.medicine_detail, name="medicine_detail"),
    path("api/search/", views.search_suggestions, name="search_suggestions"),
    path("api/cart/", views.cart_api, name="cart_api"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:medicine_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("addresses/", views.address_list, name="address_list"),
    path("addresses/add/", views.address_form, name="address_add"),
    path("addresses/<int:pk>/edit/", views.address_form, name="address_edit"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/success/", views.order_success, name="order_success"),
    path("checkout/", views.checkout, name="checkout"),
    path("payment/verify/", views.payment_verify, name="payment_verify"),
    path("orders/place/", views.place_order, name="place_order"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("profile/", views.profile, name="profile"),
]
