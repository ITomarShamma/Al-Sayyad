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


class MerchantRoleTests(TestCase):
    """M17+M18: الموافقة على التاجر وعزله بمنتجاته + مجموعات الأدوار."""

    def setUp(self):
        from apps.accounts.admin import MerchantProfileAdmin
        from apps.accounts.models import MerchantProfile
        from django.contrib.admin.sites import AdminSite

        self.cat = Category.objects.create(name="إلكترونيات")
        # تاجران بطلبين مقدَّمين
        self.m_user = User.objects.create_user("0911111111", password="x",
                                               first_name="أبو أحمد")
        Profile.objects.create(user=self.m_user, phone="0911111111")
        self.merchant = MerchantProfile.objects.create(
            user=self.m_user, store_name="متجر النور", phone="0911111111", city="دمشق")

        self.other_user = User.objects.create_user("0922222222", password="x")
        self.other = MerchantProfile.objects.create(
            user=self.other_user, store_name="متجر الشام", phone="0922222222",
            city="حلب", is_approved=True)

        # منتجات: واحد للمتجر نفسه + واحد لكل تاجر
        Product.objects.create(category=self.cat, name="بضاعة الصياد",
                               price=Decimal("1000"), stock=1)
        self.m_product = Product.objects.create(
            category=self.cat, name="بضاعة النور", price=Decimal("2000"),
            stock=1, merchant=self.merchant)
        Product.objects.create(category=self.cat, name="بضاعة الشام",
                               price=Decimal("3000"), stock=1, merchant=self.other)

        self.admin = MerchantProfileAdmin(MerchantProfile, AdminSite())

    def approve(self):
        from apps.accounts.models import MerchantProfile
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory

        request = RequestFactory().post("/")
        request.user = User.objects.create_superuser("boss", "b@b.b", "x")
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        self.admin.approve_merchants(
            request, MerchantProfile.objects.filter(pk=self.merchant.pk))
        self.merchant.refresh_from_db()
        self.m_user.refresh_from_db()

    def test_role_groups_exist_with_permissions(self):
        from django.contrib.auth.models import Group
        for name in ["مدير المتجر", "موظف الطلبات", "مدخل بيانات", "تاجر"]:
            group = Group.objects.get(name=name)
            self.assertGreater(group.permissions.count(), 0, name)
        merchant_group = Group.objects.get(name="تاجر")
        self.assertTrue(merchant_group.permissions.filter(
            codename="add_product").exists())

    def test_approval_action_grants_access(self):
        self.approve()
        self.assertTrue(self.merchant.is_approved)
        self.assertTrue(self.m_user.is_staff)
        self.assertTrue(self.m_user.groups.filter(name="تاجر").exists())
        self.assertEqual(self.m_user.profile.role, Profile.Role.MERCHANT)

    def test_merchant_sees_only_own_products_in_admin(self):
        self.approve()
        self.client.force_login(self.m_user)
        resp = self.client.get(reverse("admin:catalog_product_changelist"))
        self.assertContains(resp, "بضاعة النور")
        self.assertNotContains(resp, "بضاعة الشام")     # منتجات غيره مخفية
        self.assertNotContains(resp, "بضاعة الصياد")

    def test_merchant_new_product_assigned_to_him(self):
        self.approve()
        self.client.force_login(self.m_user)
        resp = self.client.post(reverse("admin:catalog_product_add"), {
            "category": self.cat.id, "name": "منتج جديد للنور",
            "price": "5000", "stock": "2", "is_active": "on", "specs": "{}",
            "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "1000",
        })
        self.assertEqual(resp.status_code, 302)          # حُفظ ورجع للقائمة
        product = Product.objects.get(name="منتج جديد للنور")
        self.assertEqual(product.merchant, self.merchant)  # انتسب له تلقائياً

    def test_product_page_shows_seller_name(self):
        resp = self.client.get(self.m_product.get_absolute_url())
        self.assertContains(resp, "متجر النور")
        store_product = Product.objects.get(name="بضاعة الصياد")
        resp = self.client.get(store_product.get_absolute_url())
        self.assertContains(resp, "الصَّيَّاد")


class OrderLinkingTests(TestCase):
    """الطلبات: تنربط بالمسجَّل، ويظل الزائر (guest) يطلب عادي."""

    def setUp(self):
        cat = Category.objects.create(name="إلكترونيات")
        self.product = Product.objects.create(
            category=cat, name="سماعة", price=Decimal("250000"), stock=5)
        from apps.orders.models import DeliveryZone
        self.checkout_data = {
            "customer_name": "زبون", "phone": "0912345678",
            "zone": DeliveryZone.objects.get(name="دمشق").pk,
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