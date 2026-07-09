from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("styleguide/", views.styleguide, name="styleguide"),
    # PWA (M27): البيان وعامل الخدمة وصفحة الانقطاع
    path("manifest.webmanifest", views.webmanifest, name="webmanifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
]
