import hashlib

# Stable free CDN URLs (medicine / pharmacy stock photos — no hosting required).
MEDICINE_IMAGE_URLS = [
    "https://images.pexels.com/photos/159211/headache-pain-pills-medicine-159211.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/40568/medical-appointment-doctor-healthcare-40568.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/3683101/pexels-photo-3683101.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/4386466/pexels-photo-4386466.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/4386467/pexels-photo-4386467.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/4386464/pexels-photo-4386464.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/3845625/pexels-photo-3845625.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/3845541/pexels-photo-3845541.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/3845950/pexels-photo-3845950.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://images.pexels.com/photos/3846026/pexels-photo-3846026.jpeg?auto=compress&cs=tinysrgb&w=600",
    "https://cdn.pixabay.com/photo/2017/01/10/19/05/pharmacy-1970789_1280.jpg",
    "https://cdn.pixabay.com/photo/2013/07/12/09/29/doctor-146060_1280.png",
    "https://cdn.pixabay.com/photo/2016/07/21/08/30/pharmacy-1533961_1280.jpg",
    "https://cdn.pixabay.com/photo/2014/12/22/10/04/pharmacist-561178_1280.jpg",
    "https://cdn.pixabay.com/photo/2017/07/31/11/21/people-2557396_1280.jpg",
]

CATEGORY_IMAGE_URLS = [
    "https://images.pexels.com/photos/3683101/pexels-photo-3683101.jpeg?auto=compress&cs=tinysrgb&w=400",
    "https://images.pexels.com/photos/4386466/pexels-photo-4386466.jpeg?auto=compress&cs=tinysrgb&w=400",
    "https://images.pexels.com/photos/3845625/pexels-photo-3845625.jpeg?auto=compress&cs=tinysrgb&w=400",
    "https://cdn.pixabay.com/photo/2017/01/10/19/05/pharmacy-1970789_1280.jpg",
    "https://cdn.pixabay.com/photo/2016/07/21/08/30/pharmacy-1533961_1280.jpg",
]

DEFAULT_MEDICINE_IMAGE = MEDICINE_IMAGE_URLS[0]
DEFAULT_CATEGORY_IMAGE = CATEGORY_IMAGE_URLS[0]


def _pick_url(key, pool):
    if not pool:
        return ""
    digest = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
    return pool[digest % len(pool)]


def medicine_image_url(name, category_slug=""):
    key = f"{name.strip().lower()}:{category_slug.strip().lower()}"
    return _pick_url(key, MEDICINE_IMAGE_URLS) or DEFAULT_MEDICINE_IMAGE


def category_image_url(category_name):
    return _pick_url(category_name.strip().lower(), CATEGORY_IMAGE_URLS) or DEFAULT_CATEGORY_IMAGE


def resolve_medicine_image(existing_url, name, category_slug=""):
    url = (existing_url or "").strip()
    if url and url.lower() not in ("nan", "none"):
        return url
    return medicine_image_url(name, category_slug)
