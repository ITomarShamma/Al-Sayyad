"""اختبارات الحسابات: التسجيل، الدخول بالموبايل، حسابي، ربط الطلبات."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.orders.models import Order

from .models import Profile

User = get_user_model()

SIGNUP_DATA = {
    "full_name": "عمر شمّه",
    "phone": "0998625984",
    "password1": "sayyad-secret-9",
    "password2": "sayyad-secret-9",
}


def signup(client, **overrides):
    return client.post(reverse("accounts:signup"), SIGNUP_DATA | overrides)


class SignupTests(TestCase):
    def test_signup_creates_user_and_profile_and_logs_in(self):
        resp = signup(self.client)
        self.assertRedirects(resp, reverse("accounts:account"))
        user = User.objects.get(username="0998625984")
        self.assertEqual(user.first_name, "عمر شمّه")
        self.assertEqual(user.profile.role, Profile.Role.CUSTOMER)
        # مسجَّل دخوله فوراً
        self.assertContains(self.client.get(reverse("accounts:account")), "أهلاً")

    def test_arabic_digit_phone_normalized(self):
        signup(self.client, phone="٠٩٩٨٦٢٥٩٨٤")
        self.assertTrue(User.objects.filter(username="0998625984").exists())

    def test_duplicate_phone_rejected(self):
        signup(self.client)
        self.client.post(reverse("accounts:logout"))
        resp = signup(self.client, full_name="منتحل")
        self.assertContains(resp, "مسجَّل بهالرقم")
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_rejected(self):
        resp = signup(self.client, password1="1234", password2="1234")
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(resp.status_code, 200)     # رجع للفورم بأخطاء


class LoginTests(TestCase):
    def setUp(self):
        signup(self.client)
        self.client.post(reverse("accounts:logout"))

    def test_login_with_arabic_digits(self):
        resp = self.client.post(reverse("accounts:login"), {
            "username": "٠٩٩٨٦٢٥٩٨٤",
            "password": "sayyad-secret-9",
        })
        self.assertRedirects(resp, reverse("accounts:account"))

    def test_wrong_password_friendly_error(self):
        resp = self.client.post(reverse("accounts:login"), {
            "username": "0998625984", "password": "غلط",
        })
        self.assertContains(resp, "غير صحيحة")

    def test_account_requires_login(self):
        resp = self.client.get(reverse("accounts:account"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp.url)


class AccountAreaTests(TestCase):
    def setUp(self):
        signup(self.client)

    def test_edit_profile(self):
        resp = self.client.post(reverse("accounts:edit"),
                                {"full_name": "عمر الجديد", "city": "حلب"})
        self.assertRedirects(resp, reverse("accounts:account"))
        user = User.objects.get()
        self.assertEqual(user.first_name, "عمر الجديد")
        self.assertEqual(user.profile.city, "حلب")

    def test_password_change_works(self):
        resp = self.client.post(reverse("accounts:password_change"), {
            "old_password": "sayyad-secret-9",
            "new_password1": "new-sayyad-77",
            "new_password2": "new-sayyad-77",
        })
        self.assertRedirects(resp, reverse("accounts:account"))
        self.client.post(reverse("accounts:logout"))
        login_ok = self.client.login(username="0998625984", password="new-sayyad-77")
        self.assertTrue(login_ok)

    def test_merchant_apply_creates_pending_application(self):
        resp = self.client.post(reverse("accounts:merchant_apply"), {
            "store_name": "متجر النور",
            "phone": "٠٩١١١١١١١١",
            "city": "دمشق",
            "description": "",
        })
        self.assertRedirects(resp, reverse("accounts:account"))
        merchant = User.objects.get().merchant_profile
        self.assertFalse(merchant.is_approved)          # قيد المراجعة
        self.assertEqual(merchant.phone, "0911111111")  # طبّع الأرقام
        # حالته ظاهرة بحسابه
        self.assertContains(self.client.get(reverse("accounts:account")),
                            "قيد المراجعة")


class OrderLinkingTests(TestCase):
    """الطلبات: تنربط بالمسجَّل، ويظل الزائر (guest) يطلب عادي."""

    def setUp(self):
        cat = Category.objects.create(name="إلكترونيات")
        self.product = Product.objects.create(
            category=cat, name="سماعة", price=Decimal("250000"), stock=5)
        self.checkout_data = {
            "customer_name": "زبون", "phone": "0912345678", "city": "دمشق",
            "address": "العنوان", "notes": "", "payment_method": "cod",
        }

    def order(self):
        self.client.post(reverse("cart:add", args=[self.product.id]))
        return self.client.post(reverse("orders:checkout"), self.checkout_data)

    def test_guest_order_has_no_user(self):
        self.order()
        self.assertIsNone(Order.objects.get().user)     # زائر = بلا حساب

    def test_logged_in_order_linked_and_listed_in_account(self):
        signup(self.client)
        self.order()
        order = Order.objects.get()
        self.assertEqual(order.user.username, "0998625984")
        resp = self.client.get(reverse("accounts:account"))
        self.assertContains(resp, order.number)          # ظاهر بـ«طلباتي»

    def test_checkout_prefilled_for_logged_in(self):
        signup(self.client)
        self.client.post(reverse("cart:add", args=[self.product.id]))
        resp = self.client.get(reverse("orders:checkout"))
        self.assertContains(resp, 'value="عمر شمّه"')    # الاسم معبّى مسبقاً
        self.assertContains(resp, 'value="0998625984"')  # والرقم