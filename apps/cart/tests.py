"""اختبارات السلة: منطق Cart + الواجهات (عادي وHTMX)."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product

from .cart import Cart


def make_product(name="سماعة لاسلكية", price="250000", stock=5, **kwargs):
    category = kwargs.pop("category", None) or Category.objects.create(name="إلكترونيات")
    return Product.objects.create(
        category=category, name=name, price=Decimal(price), stock=stock, **kwargs
    )


class CartClassTests(TestCase):
    """منطق السلة نفسها — بمعزل عن الواجهات."""

    def setUp(self):
        self.product = make_product()
        # طلب حقيقي بجلسة حقيقية (بدل بناء واحدة يدوياً)
        self.request = self.client.get("/").wsgi_request

    def test_add_accumulates_quantity(self):
        cart = Cart(self.request)
        cart.add(self.product)
        cart.add(self.product, 2)
        self.assertEqual(cart.total_quantity, 3)

    def test_quantity_is_clamped_to_stock(self):
        cart = Cart(self.request)
        cart.add(self.product, 99)                    # المخزون 5 فقط
        self.assertEqual(cart.total_quantity, 5)

    def test_set_zero_removes_item(self):
        cart = Cart(self.request)
        cart.add(self.product, 2)
        cart.set(self.product, 0)
        self.assertEqual(cart.total_quantity, 0)
        self.assertEqual(cart.items(), [])

    def test_totals(self):
        cart = Cart(self.request)
        cart.add(self.product, 2)                     # 2 × 250,000
        self.assertEqual(cart.total_price, Decimal("500000"))
        self.assertEqual(cart.total_price_display, "500,000")


class CartViewsTests(TestCase):
    """الواجهات: إضافة/تعديل/حذف — بنمطَي HTMX والنموذج العادي."""

    def setUp(self):
        self.product = make_product()
        self.add_url = reverse("cart:add", args=[self.product.id])
        self.update_url = reverse("cart:update", args=[self.product.id])
        self.remove_url = reverse("cart:remove", args=[self.product.id])

    def test_plain_form_add_redirects_to_cart_page(self):
        resp = self.client.post(self.add_url)
        self.assertRedirects(resp, reverse("cart:detail"))

    def test_htmx_add_returns_oob_badges(self):
        resp = self.client.post(self.add_url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="cart-count-top"')
        self.assertContains(resp, 'hx-swap-oob="true"')
        self.assertContains(resp, ">1<")               # العدّاد صار 1

    def test_htmx_add_shows_toast(self):
        resp = self.client.post(self.add_url, HTTP_HX_REQUEST="true")
        self.assertContains(resp, 'id="toast"')
        self.assertContains(resp, "أُضيف للسلة")

    def test_update_does_not_show_toast(self):
        """تعديل الكمية من صفحة السلة ما بدو توست — التغيير ظاهر قدامك."""
        self.client.post(self.add_url)
        resp = self.client.post(self.update_url, {"quantity": 2},
                                HTTP_HX_REQUEST="true")
        self.assertNotContains(resp, "أُضيف للسلة")

    def test_add_get_not_allowed(self):
        self.assertEqual(self.client.get(self.add_url).status_code, 405)

    def test_add_inactive_product_404(self):
        hidden = make_product(name="مخفي", is_active=False)
        resp = self.client.post(reverse("cart:add", args=[hidden.id]))
        self.assertEqual(resp.status_code, 404)

    def test_update_and_remove_via_htmx_rerender_cart_body(self):
        self.client.post(self.add_url)
        resp = self.client.post(
            self.update_url, {"quantity": 3}, HTTP_HX_REQUEST="true"
        )
        self.assertContains(resp, "750,000")            # 3 × 250,000
        resp = self.client.post(self.remove_url, HTTP_HX_REQUEST="true")
        self.assertContains(resp, "سلتك فاضية")          # حالة السلة الفارغة

    def test_cart_page_shows_items_and_total(self):
        self.client.post(self.add_url, {"quantity": 2})
        resp = self.client.get(reverse("cart:detail"))
        self.assertContains(resp, self.product.name)
        self.assertContains(resp, "500,000")

    def test_badge_appears_on_every_page(self):
        self.client.post(self.add_url)
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, 'id="cart-count-top"')
        self.assertContains(resp, 'id="cart-count-bottom"')
