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
