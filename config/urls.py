"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.catalog.sitemaps import CategorySitemap, ProductSitemap
from apps.pages.sitemaps import StaticPagesSitemap
from apps.pages.views import robots_txt

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "pages": StaticPagesSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cart/", include("apps.cart.urls")),
    path("account/", include("apps.accounts.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps},
         name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("", include("apps.orders.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.pages.urls")),
]

# During development, let Django serve uploaded media files (product images).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
