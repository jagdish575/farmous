import urllib.parse


def google_maps_link(address):
    if address.latitude and address.longitude:
        return f"https://www.google.com/maps?q={address.latitude},{address.longitude}"
    parts = [
        address.address_line,
        address.landmark,
        address.city,
        address.state,
        address.pincode,
    ]
    query = ", ".join(part for part in parts if part)
    encoded = urllib.parse.quote(query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"


def format_order_whatsapp_message(order, address, user):
    lines = [
        "Hello!",
        "━━━━━━━━━━━━━━━━━━━━",
        "🛒 *NEW MEDICINE ORDER*",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📋 *Order ID:* {order.order_id}",
        f"👤 *Customer:* {user.full_name}",
        f"📱 *Mobile:* {user.mobile_number}",
        "",
        "📍 *DELIVERY ADDRESS*",
        "────────────────────",
        address.address_line,
    ]
    if address.landmark:
        lines.append(f"Landmark: {address.landmark}")
    lines.extend([
        f"{address.city}, {address.state}",
        f"Pincode: {address.pincode}",
        f"🗺️ *Map:* {google_maps_link(address)}",
        "",
        "💊 *MEDICINES*",
        "────────────────────",
    ])
    for item in order.items.select_related("medicine"):
        subtotal = item.quantity * item.price
        lines.append(
            f"• {item.medicine.name} x {item.quantity} — ₹{subtotal:,.2f}"
        )
    lines.extend([
        "────────────────────",
        f"📦 *Total Items:* {order.total_items}",
        f"💰 *ORDER TOTAL:* ₹{order.total_price:,.2f}",
        "",
        "Please confirm availability and delivery.",
        "Thank you! 🙏",
    ])
    return lines


def format_cancel_whatsapp_message(order, user):
    return [
        "Hello!",
        "━━━━━━━━━━━━━━━━━━━━",
        "❌ *ORDER CANCELLATION*",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📋 *Order ID:* {order.order_id}",
        f"👤 *Customer:* {user.full_name}",
        f"📱 *Mobile:* {user.mobile_number}",
        "",
        "Please cancel my order.",
        "Thank you! 🙏",
    ]
