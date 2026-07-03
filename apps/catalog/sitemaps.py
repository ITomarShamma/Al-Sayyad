"""خرائط الموقع (sitemaps) — تخبر غوغل بكل صفحات المتجر لتُفهرس.

بدون sitemap محركات البحث تكتشف الصفحات بالزحف البطيء فقط؛
معه نعطيها القائمة كاملة مع تاريخ آخر تعديل.
"""

from django.contrib.sitemaps import Sitemap

from .models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at
