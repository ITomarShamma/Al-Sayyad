"""اختبارات السلة: منطق Cart + الواجهات (عادي وHTMX)."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import (Category, Product, ProductOption,
                                 ProductOptionValue, ProductVariant)

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


# ==========================================================================
#  السلة والمقاسات/الألوان
# ==========================================================================

def make_variant_product(stock=4):
    """قميص بمحورَين (مقاس × لون) — كل تركيبة سطر مستقل بالسلة."""
    product = make_product(name="قميص قطن", price="85000", stock=0)
    size = ProductOption.objects.create(product=product, name="المقاس", sort_order=1)
    color = ProductOption.objects.create(product=product, name="اللون", sort_order=2)
    sizes = [ProductOptionValue.objects.create(option=size, value=v, sort_order=i)
             for i, v in enumerate(["S", "M"])]
    colors = [ProductOptionValue.objects.create(option=color, value=v, sort_order=i)
              for i, v in enumerate(["أبيض", "أسود"])]
    for s in sizes:
        for c in colors:
            ProductVariant.objects.create(product=product, value_1=s, value_2=c,
                                          stock=stock)
    product.refresh_from_db()
    return product, sizes, colors


class CartVariantTests(TestCase):
    def setUp(self):
        self.product, self.sizes, self.colors = make_variant_product()
        self.request = self.client.get("/").wsgi_request

    def _variant(self, size_i, color_i):
        return self.product.resolve_variant(
            [self.sizes[size_i].id, self.colors[color_i].id])

    def test_different_variants_are_separate_lines(self):
        cart = Cart(self.request)
        cart.add(self.product, 1, variant=self._variant(0, 0))   # S أبيض
        cart.add(self.product, 2, variant=self._variant(1, 1))   # M أسود
        self.assertEqual(len(cart.items()), 2)
        self.assertEqual(cart.total_quantity, 3)

    def test_same_variant_accumulates_into_one_line(self):
        cart = Cart(self.request)
        variant = self._variant(0, 0)
        cart.add(self.product, 1, variant=variant)
        cart.add(self.product, 2, variant=variant)
        self.assertEqual(len(cart.items()), 1)
        self.assertEqual(cart.items()[0]["quantity"], 3)

    def test_quantity_clamped_to_variant_stock_not_product_total(self):
        """المنتج فيه 16 قطعة إجمالاً، لكن مقاس S/أبيض فيه 4 فقط."""
        cart = Cart(self.request)
        cart.add(self.product, 99, variant=self._variant(0, 0))
        self.assertEqual(cart.total_quantity, 4)
        self.assertEqual(cart.items()[0]["stock_limit"], 4)

    def test_line_uses_variant_price_when_it_differs(self):
        variant = self._variant(0, 0)
        variant.price = 99000
        variant.save()
        cart = Cart(self.request)
        cart.add(self.product, 1, variant=variant)
        self.assertEqual(cart.total_price, Decimal("99000"))
        self.assertEqual(cart.items()[0]["unit_price_display"], "99,000")

    def test_removing_one_variant_keeps_the_other(self):
        cart = Cart(self.request)
        first, second = self._variant(0, 0), self._variant(1, 1)
        cart.add(self.product, 1, variant=first)
        cart.add(self.product, 1, variant=second)
        cart.remove(self.product, variant=first)
        items = cart.items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["variant"], second)

    def test_deactivated_variant_line_disappears_quietly(self):
        cart = Cart(self.request)
        variant = self._variant(0, 0)
        cart.add(self.product, 1, variant=variant)
        variant.is_active = False
        variant.save()
        self.assertEqual(Cart(self.request).items(), [])

    def test_old_session_format_still_readable(self):
        """سلة زبون كانت مفتوحة قبل التحديث («12») لا تنكسر."""
        simple = make_product(name="غلاية", price="180000", stock=3)
        session = self.client.session
        session["cart"] = {str(simple.id): 2}
        session.save()
        cart = Cart(self.client.get("/").wsgi_request)
        self.assertEqual(cart.total_quantity, 2)
        self.assertEqual(cart.items()[0]["product"], simple)
        self.assertIsNone(cart.items()[0]["variant"])


class CartVariantViewTests(TestCase):
    """الواجهات: الاختيار يُحسم بالسيرفر — يشتغل بلا جافاسكربت."""

    def setUp(self):
        self.product, self.sizes, self.colors = make_variant_product()
        self.options = list(self.product.options.all())

    def _post_add(self, size_i=0, color_i=0, **extra):
        data = {
            f"option_{self.options[0].id}": self.sizes[size_i].id,
            f"option_{self.options[1].id}": self.colors[color_i].id,
        }
        data.update(extra)
        return self.client.post(
            reverse("cart:add", args=[self.product.id]), data)

    def test_adding_with_chosen_values_creates_variant_line(self):
        response = self._post_add()
        self.assertRedirects(response, reverse("cart:detail"))
        page = self.client.get(reverse("cart:detail"))
        self.assertContains(page, "المقاس: S، اللون: أبيض")

    def test_adding_without_choosing_is_refused_with_message(self):
        # follow=True: الرسالة تُستهلك بأول عرض للصفحة، فنتبع التحويل مرة واحدة
        response = self.client.post(
            reverse("cart:add", args=[self.product.id]), {}, follow=True)
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertContains(response, "اختر المقاس/اللون أولاً")
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_adding_sold_out_variant_is_refused(self):
        self.product.variants.filter(
            value_1=self.sizes[0], value_2=self.colors[0]).update(stock=0)
        response = self._post_add(0, 0)
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_htmx_add_returns_error_toast_without_touching_cart(self):
        response = self.client.post(
            reverse("cart:add", args=[self.product.id]), {},
            headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 422)
        self.assertContains(response, "اختر المقاس/اللون أولاً", status_code=422)

    def test_update_and_remove_target_the_right_line(self):
        self._post_add(0, 0)
        self._post_add(1, 1)
        first = self.product.resolve_variant(
            [self.sizes[0].id, self.colors[0].id])
        self.client.post(reverse("cart:update", args=[self.product.id]),
                         {"variant": first.id, "quantity": 3})
        session_cart = self.client.session["cart"]
        self.assertEqual(session_cart[f"{self.product.id}:{first.id}"], 3)

        self.client.post(reverse("cart:remove", args=[self.product.id]),
                         {"variant": first.id})
        self.assertNotIn(f"{self.product.id}:{first.id}",
                         self.client.session["cart"])
