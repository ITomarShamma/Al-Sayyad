"""خريطة الصفحات الثابتة (الرئيسية، التصنيفات، عن الصياد…)."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticPagesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ["pages:home", "catalog:category_list", "pages:about", "pages:contact"]

    def location(self, item):
        return reverse(item)
