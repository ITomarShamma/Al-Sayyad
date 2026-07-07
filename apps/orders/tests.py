"""اختبارات الطلبات: الفورم، إنشاء الطلب (المخزون واللقطات)، الصفحات."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product

from .forms import CheckoutForm
from .models import Order


def make_product(name="سماعة لاسلكية", price="250000", stock=5, **kwargs):
    category = kwargs.pop("category", None) or Category.objects.create(name="إلكترونيات")
    return Product.objects.create(
        category=category, name=name, price=Decimal(price), stock=stock, **kwargs
    )


VALID_FORM = {
    "customer_name": "عمر شمّه",
    "phone": "0998625984",
    "address": "المزة، شارع الجلاء، بناء 12",
    "notes": "",
    "payment_method": "cod",
}


def valid_form(**overrides):
    """بيانات فورم صالحة + منطقة توصيل (دمشق) — تُجلب وقت النداء لأن
    المناطق تُزرع بهجرة بيانات ولا pk لها وقت استيراد الملف."""
    from .models import DeliveryZone
    zone = DeliveryZone.objects.get(name="دمشق")
    return VALID_FORM | {"zone": zone.pk} | overrides


class CheckoutFormTests(TestCase):
    def test_valid_data_passes(self):
        self.assertTrue(CheckoutForm(valid_form()).is_valid())

    def test_arabic_digits_in_phone_are_normalized(self):
        data = valid_form(phone="٠٩٩٨٦٢٥٩٨٤")
        form = CheckoutForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["phone"], "0998625984")

    def test_bad_phone_rejected(self):
        for bad in ("12345", "0898625984", "099862598", "09986259845"):
            form = CheckoutForm(valid_form(phone=bad))
            self.assertFalse(form.is_valid(), f"قبل رقماً خاطئاً: {bad}")

    def test_shamcash_not_offered_yet(self):
        form = CheckoutForm(valid_form(payment_method="shamcash"))
        self.assertFalse(form.is_valid())     # مو من الخيارات المفعّلة


class CheckoutFlowTests(TestCase):
    """المسار الكامل: سلة ← إتمام الطلب ← تأكيد."""

    def setUp(self):
        self.product = make_product(stock=5)
        # نعبّي السلة عبر الواجهة الحقيقية (يبني الجلسة صح)
        self.client.post(reverse("cart:add", args=[self.product.id]), {"quantity": 2})

    def test_checkout_with_empty_cart_redirects_to_cart(self):
        fresh = self.client_class()               # زبون جديد بلا سلة
        resp = fresh.get(reverse("orders:checkout"))
        self.assertRedirects(resp, reverse("cart:detail"))

    def test_checkout_page_shows_form_and_summary(self):
        resp = self.client.get(reverse("orders:checkout"))
        self.assertContains(resp, "الاسم الكامل")
        self.assertContains(resp, self.product.name)
        self.assertContains(resp, "500,000")       # 2 × 250,000

    def test_successful_order(self):
        resp = self.client.post(reverse("orders:checkout"), valid_form())

        order = Order.objects.get()
        # PRG: تحويل لصفحة التأكيد
        self.assertRedirects(resp, reverse("orders:confirmation", args=[order.number]))
        # الإجمالي واللقطات
        self.assertEqual(order.total, Decimal("500000"))
        item = order.items.get()
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.unit_price, Decimal("250000"))
        self.assertEqual(item.quantity, 2)
        # خصم المخزون
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        # تفريغ السلة
        resp = self.client.get(reverse("cart:detail"))
        self.assertContains(resp, "سلتك فاضية")

    def test_snapshot_survives_price_change(self):
        """غيّرنا سعر المنتج بعد الطلب؟ الفاتورة القديمة لا تتأثر."""
        self.client.post(reverse("orders:checkout"), valid_form())
        self.product.price = Decimal("999999")
        self.product.save()
        item = Order.objects.get().items.get()
        self.assertEqual(item.unit_price, Decimal("250000"))

    def test_stock_conflict_blocks_order(self):
        """المخزون نزل تحت المطلوب بعد تعبئة السلة → رسالة، بلا طلب ولا خصم."""
        self.product.stock = 1                    # بالسلة 2
        self.product.save()
        resp = self.client.post(reverse("orders:checkout"), valid_form())
        self.assertEqual(resp.status_code, 200)   # رجعنا للفورم
        self.assertContains(resp, "الكمية المتوفرة تغيّرت")
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)   # ما انخصم شي

    def test_invalid_form_creates_nothing(self):
        resp = self.client.post(reverse("orders:checkout"), valid_form(phone="123"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_confirmation_page(self):
        self.client.post(reverse("orders:checkout"), valid_form())
        order = Order.objects.get()
        resp = self.client.get(reverse("orders:confirmation", args=[order.number]))
        self.assertContains(resp, order.number)
        self.assertContains(resp, "الدفع عند الاستلام")


class DeliveryZoneTests(TestCase):
    """M21: مناطق التوصيل — الزرع، اللقطة، الإجمالي، الملخص الحي."""

    def setUp(self):
        from .models import DeliveryZone
        self.product = make_product(stock=5)          # 250,000
        self.client.post(reverse("cart:add", args=[self.product.id]), {"quantity": 2})
        self.damascus = DeliveryZone.objects.get(name="دمشق")

    def test_fourteen_governorates_seeded_with_null_fee(self):
        from .models import DeliveryZone
        self.assertEqual(DeliveryZone.objects.count(), 14)
        self.assertIsNone(self.damascus.fee)           # «يُتفق هاتفياً» افتراضياً

    def test_checkout_shows_zone_select(self):
        resp = self.client.get(reverse("orders:checkout"))
        self.assertContains(resp, 'name="zone"')
        self.assertContains(resp, "دمشق")
        self.assertContains(resp, "حلب")
        self.assertContains(resp, "التوصيل يُتفق هاتفياً")

    def test_order_snapshots_zone_fee_into_total(self):
        self.damascus.fee = Decimal("50000")
        self.damascus.save()
        self.client.post(reverse("orders:checkout"), valid_form())
        order = Order.objects.get()
        self.assertEqual(order.city, "دمشق")           # لقطة الاسم
        self.assertEqual(order.delivery_fee, Decimal("50000"))
        self.assertEqual(order.total, Decimal("550000"))   # 2×250,000 + 50,000
        self.assertEqual(order.items_subtotal, Decimal("500000"))
        # تغيير الرسم لاحقاً لا يمس الطلب القديم
        self.damascus.fee = Decimal("999999")
        self.damascus.save()
        order.refresh_from_db()
        self.assertEqual(order.delivery_fee, Decimal("50000"))

    def test_null_fee_zone_keeps_total_and_notes_phone_agreement(self):
        self.client.post(reverse("orders:checkout"), valid_form())
        order = Order.objects.get()
        self.assertIsNone(order.delivery_fee)
        self.assertEqual(order.total, Decimal("500000"))   # المنتجات فقط
        resp = self.client.get(reverse("orders:confirmation", args=[order.number]))
        self.assertContains(resp, "يُتفق هاتفياً")

    def test_free_delivery_zone_shows_free(self):
        self.damascus.fee = Decimal("0")
        self.damascus.save()
        self.client.post(reverse("orders:checkout"), valid_form())
        order = Order.objects.get()
        self.assertEqual(order.delivery_fee, Decimal("0"))
        resp = self.client.get(reverse("orders:confirmation", args=[order.number]))
        self.assertContains(resp, "مجاني")

    def test_live_summary_endpoint_returns_fee_and_grand_total(self):
        self.damascus.fee = Decimal("50000")
        self.damascus.save()
        resp = self.client.get(reverse("orders:checkout_summary"),
                               {"zone": self.damascus.pk})
        self.assertContains(resp, "50,000")
        self.assertContains(resp, "550,000")           # الإجمالي الكلي حي

    def test_inactive_zone_not_offered(self):
        self.damascus.is_active = False
        self.damascus.save()
        resp = self.client.get(reverse("orders:checkout"))
        # ملاحظة: لا نفحص النص «دمشق» — «ريف دمشق» يحتويه؛ نفحص خيار الـpk
        self.assertNotContains(resp, f'<option value="{self.damascus.pk}"')
        # ولا تُقبل بالفورم حتى لو أُرسلت يدوياً
        resp = self.client.post(reverse("orders:checkout"),
                                VALID_FORM | {"zone": self.damascus.pk})
        self.assertEqual(Order.objects.count(), 0)


class CouponTests(TestCase):
    """M23: الكوبونات — الحساب، القيود، السلة، لقطة الطلب، حجز الاستخدام."""

    def setUp(self):
        from .models import Coupon
        self.product = make_product(stock=10)               # 250,000
        self.client.post(reverse("cart:add", args=[self.product.id]), {"quantity": 2})
        self.coupon = Coupon.objects.create(code="ramadan10", kind="percent",
                                            value=Decimal("10"))

    def apply(self, code="RAMADAN10"):
        return self.client.post(reverse("cart:apply_coupon"), {"code": code},
                                HTTP_HX_REQUEST="true")

    def test_code_normalized_to_uppercase_on_save(self):
        self.assertEqual(self.coupon.code, "RAMADAN10")

    def test_discount_math_percent_and_fixed_capped(self):
        from .models import Coupon
        self.assertEqual(self.coupon.discount_for(Decimal("500000")),
                         Decimal("50000"))                  # 10%
        fixed = Coupon.objects.create(code="F", kind="fixed", value=Decimal("900000"))
        # الخصم الثابت لا يتجاوز مجموع المنتجات أبداً
        self.assertEqual(fixed.discount_for(Decimal("500000")), Decimal("500000"))

    def test_apply_on_cart_shows_discount_and_new_total(self):
        resp = self.apply()
        self.assertContains(resp, "RAMADAN10")
        self.assertContains(resp, "50,000")                 # الخصم
        self.assertContains(resp, "450,000")                # الإجمالي بعده

    def test_invalid_code_shows_friendly_error(self):
        resp = self.apply("مافي")
        self.assertContains(resp, "الكود غير صحيح")

    def test_expired_coupon_rejected(self):
        from django.utils import timezone
        self.coupon.expires_at = timezone.now() - timezone.timedelta(days=1)
        self.coupon.save()
        resp = self.apply()
        self.assertContains(resp, "انتهت صلاحية")

    def test_min_total_enforced_and_auto_removed_when_cart_shrinks(self):
        self.coupon.min_order_total = Decimal("400000")
        self.coupon.save()
        self.apply()                                        # 500,000 ≥ 400,000 ✓
        # نزّل الكمية لواحدة → 250,000 < الحد → الكوبون يسقط بصمت
        resp = self.client.post(reverse("cart:update", args=[self.product.id]),
                                {"quantity": 1}, HTTP_HX_REQUEST="true")
        self.assertNotContains(resp, "RAMADAN10")
        self.assertContains(resp, "250,000")                # الإجمالي بلا خصم

    def test_order_snapshots_coupon_and_counts_usage(self):
        self.apply()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("orders:checkout"), valid_form())
        order = Order.objects.get()
        self.assertEqual(order.coupon_code, "RAMADAN10")
        self.assertEqual(order.discount_amount, Decimal("50000"))
        self.assertEqual(order.total, Decimal("450000"))    # 500,000 − 50,000
        self.assertEqual(order.items_subtotal, Decimal("500000"))
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)         # حُجز الاستخدام
        # الكوبون خرج من الجلسة — سلة جديدة بلا خصم قديم
        self.client.post(reverse("cart:add", args=[self.product.id]))
        resp = self.client.get(reverse("cart:detail"))
        self.assertNotContains(resp, "RAMADAN10")

    def test_exhausted_coupon_blocks_checkout_without_order(self):
        self.apply()                                        # بالجلسة الآن
        self.coupon.usage_limit = 1
        self.coupon.used_count = 1                          # استُنفد بعد التطبيق
        self.coupon.save()
        resp = self.client.post(reverse("orders:checkout"), valid_form())
        self.assertEqual(resp.status_code, 200)             # رجع للفورم
        self.assertContains(resp, "حدّه الأقصى")
        self.assertEqual(Order.objects.count(), 0)          # لا طلب ولا خصم مخزون
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_admin_coupon_changelist(self):
        from django.contrib.auth import get_user_model
        admin_user = get_user_model().objects.create_superuser("t3", "t@t.t", "x")
        self.client.force_login(admin_user)
        resp = self.client.get(reverse("admin:orders_coupon_changelist"))
        self.assertContains(resp, "RAMADAN10")


class OrderNotificationTests(TestCase):
    """M22: بريد المالك عند الطلب + رابط واتساب الزبون باللوحة."""

    def setUp(self):
        self.product = make_product(stock=5)
        self.client.post(reverse("cart:add", args=[self.product.id]), {"quantity": 2})

    def place_order(self):
        # captureOnCommitCallbacks: داخل الاختبارات لا يوجد commit حقيقي —
        # هذا ينفّذ دوال on_commit كأن المعاملة نجحت فعلاً
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("orders:checkout"), valid_form())
        return Order.objects.get()

    def test_owner_email_sent_on_new_order(self):
        from django.core import mail
        with self.settings(ORDER_NOTIFICATION_EMAIL="omar@example.com"):
            order = self.place_order()
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["omar@example.com"])
        self.assertIn(order.number, email.subject)
        self.assertIn("سماعة لاسلكية × 2", email.body)
        self.assertIn("500,000", email.body)
        self.assertIn(order.phone, email.body)

    def test_no_email_when_recipient_not_configured(self):
        from django.core import mail
        with self.settings(ORDER_NOTIFICATION_EMAIL=""):
            self.place_order()
        self.assertEqual(len(mail.outbox), 0)

    def test_whatsapp_url_uses_international_number(self):
        from .notifications import customer_whatsapp_url
        order = self.place_order()                      # الهاتف 0998625984
        url = customer_whatsapp_url(order)
        self.assertIn("wa.me/963998625984", url)        # 0 ← 963
        self.assertIn(order.number, url)                # الرسالة فيها رقم الطلب

    def test_admin_changelist_shows_whatsapp_button(self):
        from django.contrib.auth import get_user_model
        self.place_order()
        admin_user = get_user_model().objects.create_superuser("t2", "t@t.t", "x")
        self.client.force_login(admin_user)
        resp = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertContains(resp, "wa.me/963998625984")
        self.assertContains(resp, "راسل الزبون")


class TrackOrderTests(TestCase):
    """صفحة «وين طلبي؟» — البحث برقم الطلب + الموبايل."""

    def setUp(self):
        make_product(stock=5)
        product = Product.objects.get()
        self.client.post(reverse("cart:add", args=[product.id]), {"quantity": 1})
        self.client.post(reverse("orders:checkout"), valid_form())
        self.order = Order.objects.get()
        self.url = reverse("orders:track")

    def test_page_renders_empty_form(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "وين طلبي؟")
        self.assertNotContains(resp, "ما لقينا طلباً")   # لسا ما بحث

    def test_correct_pair_finds_order_with_timeline(self):
        resp = self.client.get(self.url, {"number": self.order.number,
                                          "phone": self.order.phone})
        self.assertContains(resp, self.order.number)
        self.assertContains(resp, "بانتظار التأكيد")     # الحالة الحالية
        self.assertContains(resp, "is-current")          # خط الزمن مفعّل

    def test_arabic_digits_accepted(self):
        arabic_number = self.order.number.translate(
            str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
        resp = self.client.get(self.url, {"number": arabic_number,
                                          "phone": "٠٩٩٨٦٢٥٩٨٤"})
        self.assertContains(resp, self.order.number)

    def test_wrong_phone_reveals_nothing(self):
        """رقم طلب صحيح مع موبايل غلط = لا شيء (خصوصية الزبائن)."""
        resp = self.client.get(self.url, {"number": self.order.number,
                                          "phone": "0911111111"})
        self.assertContains(resp, "ما لقينا طلباً")
        self.assertNotContains(resp, VALID_FORM["customer_name"])

    def test_cancelled_order_shows_notice_not_timeline(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save()
        resp = self.client.get(self.url, {"number": self.order.number,
                                          "phone": self.order.phone})
        self.assertContains(resp, "ملغى")
        self.assertNotContains(resp, "is-current")

    def test_shipped_order_marks_progress(self):
        self.order.status = Order.Status.SHIPPED
        self.order.save()
        resp = self.client.get(self.url, {"number": self.order.number,
                                          "phone": self.order.phone})
        self.assertContains(resp, "قيد التوصيل")


class OrdersAdminTests(TestCase):
    def test_admin_changelist_opens(self):
        from django.contrib.auth import get_user_model
        admin_user = get_user_model().objects.create_superuser("t", "t@t.t", "x")
        self.client.force_login(admin_user)
        resp = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertEqual(resp.status_code, 200)
