from django.conf import settings
import razorpay


class RazorpayError(Exception):
    pass


def is_razorpay_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def get_client():
    if not is_razorpay_configured():
        raise RazorpayError("Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(order):
    amount_paise = int(order.total_price * 100)
    if amount_paise < 100:
        raise RazorpayError("Order total must be at least ₹1.")
    client = get_client()
    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": order.order_id,
        "payment_capture": 1,
        "notes": {
            "farmos_order_id": order.order_id,
            "user_id": str(order.user_id),
        },
    })
    return razorpay_order


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    client = get_client()
    client.utility.verify_payment_signature({
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    })
