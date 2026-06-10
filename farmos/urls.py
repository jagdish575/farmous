from django.urls import path, include
from django.views.generic import TemplateView
from store.admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    path("", include("store.urls", namespace="store")),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),
]

handler404 = "store.views.page_not_found"
handler500 = "store.views.server_error"
