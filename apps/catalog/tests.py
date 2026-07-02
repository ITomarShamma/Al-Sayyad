"""اختبارات الكاتالوج: سلوك النماذج + وصول لوحة التحكم."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


def make_product(**kwargs):
    """منتج تجريبي بأقل جهد — القيم الافتراضية قابلة للتبديل."""
    category = kwargs.pop("category", None) or Category.objects.create(name="إلكترونيات")
    defaults = {"name": "سماعة لاسلكية", "price": Decimal("250000"), "stock": 5}
    defaults.update(kwargs)
    return Product.objects.create(category=category, **defaults)


class CategoryTests(TestCase):
    def test_arabic_slug_is_generated_automatically(self):
        cat = Category.objects.create(name="أدوات منزلية")
        self.assertTrue(cat.slug)                      # توليد تلقائي
        self.assertIn("أدوات", cat.slug)               # يحافظ على العربية

    def test_duplicate_names_get_unique_slugs(self):
        c1 = Category.objects.create(name="عروض")
        c2 = Category.objects.create(name="عروض", parent=c1)
        self.assertNotEqual(c1.slug, c2.slug)          # عروض / عروض-2

    def test_str_shows_tree_path(self):
        parent = Category.objects.create(name="إلكترونيات")
        child = Category.objects.create(name="سماعات", parent=parent)
        self.assertEqual(str(child), "إلكترونيات ← سماعات")


class ProductTests(TestCase):
    def test_deleting_category_with_products_is_blocked(self):
        p = make_product()
        with self.assertRaises(ProtectedError):        # حماية البيانات
            p.category.delete()

    def test_in_stock_logic(self):
        self.assertTrue(make_product(stock=3).in_stock)
        self.assertFalse(make_product(name="ب", stock=0).in_stock)
        self.assertFalse(make_product(name="ج", stock=9, is_active=False).in_stock)

    def test_price_stored_without_decimals(self):
        p = make_product(price=Decimal("175000"))
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal("175000"))


class CatalogViewsTests(TestCase):
    """صفحات المتجر: التصنيفات، صفحة تصنيف، صفحة منتج (M4)."""

    def setUp(self):
        self.electronics = Category.objects.create(name="إلكترونيات")
        self.headphones = Category.objects.create(name="سماعات", parent=self.electronics)
        self.p_active = make_product(category=self.electronics, name="سماعة لاسلكية")
        self.p_inactive = make_product(
            category=self.electronics, name="منتج مخفي", is_active=False
        )

    def test_arabic_slug_urls_resolve(self):
        """الروابط العربية (سماعة-لاسلكية) لازم تشتغل — <str:slug> وليس <slug:slug>."""
        self.assertEqual(self.client.get(self.p_active.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.electronics.get_absolute_url()).status_code, 200)

    def test_category_list_shows_root_categories_only(self):
        resp = self.client.get(reverse("catalog:category_list"))
        self.assertContains(resp, "إلكترونيات")
        self.assertNotContains(resp, "سماعات")     # الفرعي لا يظهر كجذر

    def test_category_page_shows_children_and_active_products_only(self):
        resp = self.client.get(self.electronics.get_absolute_url())
        self.assertContains(resp, "سماعات")          # التصنيف الفرعي كشريحة
        self.assertContains(resp, "سماعة لاسلكية")   # المنتج المفعّل
        self.assertNotContains(resp, "منتج مخفي")    # غير المفعّل لا يظهر

    def test_product_page_shows_price_and_payment_badges(self):
        resp = self.client.get(self.p_active.get_absolute_url())
        self.assertContains(resp, "250,000")         # السعر منسّق
        self.assertContains(resp, "ل.س")
        self.assertContains(resp, "badge--cod")      # شارات الثقة (القاعدة #5)
        self.assertContains(resp, "badge--shamcash")

    def test_inactive_product_is_404(self):
        resp = self.client.get(self.p_inactive.get_absolute_url())
        self.assertEqual(resp.status_code, 404)

    def test_out_of_stock_product_shows_disabled_state(self):
        p = make_product(category=self.electronics, name="نافد", stock=0)
        resp = self.client.get(p.get_absolute_url())
        self.assertContains(resp, "نفدت الكمية")

    def test_home_shows_latest_products_and_categories(self):
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, "سماعة لاسلكية")
        self.assertContains(resp, "إلكترونيات")
        self.assertNotContains(resp, "منتج مخفي")


class CatalogAdminTests(TestCase):
    """لوحة التحكم تفتح وتعرض نماذج الكاتالوج لمدير مسجَّل دخوله."""

    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username="testadmin", email="a@a.a", password="x"
        )
        self.client.force_login(admin_user)

    def test_admin_changelists_open(self):
        for url_name in ("admin:catalog_category_changelist",
                         "admin:catalog_product_changelist"):
            self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

    def test_admin_product_add_page_opens(self):
        resp = self.client.get(reverse("admin:catalog_product_add"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "السعر")             # الواجهة معرّبة
