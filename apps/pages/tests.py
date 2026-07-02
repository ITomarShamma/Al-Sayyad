from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    """اختبار دخان (smoke test) للصفحة الرئيسية: تشتغل وبالهوية الصحيحة."""

    def setUp(self):
        self.url = reverse("pages:home")

    def test_home_returns_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_home_uses_expected_templates(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "base.html")
        self.assertTemplateUsed(resp, "pages/home.html")

    def test_home_is_rtl_arabic(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, 'dir="rtl"')   # اتجاه عربي مفعّل
        self.assertContains(resp, 'lang="ar"')

    def test_home_stays_rtl_for_english_browsers(self):
        """متصفح يفضّل الإنجليزية لازم يظل يشوف عربي RTL (ما في ترجمة بعد)."""
        resp = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
        self.assertContains(resp, 'dir="rtl"')
        self.assertContains(resp, 'lang="ar"')

    def test_home_loads_design_tokens_and_brand(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "css/tokens.css")   # نظام التصميم محمّل
        self.assertContains(resp, "الصَّيَّاد")          # اسم البراند ظاهر


class StyleguideTests(TestCase):
    """دليل المكوّنات يعرض كل المكوّنات الأساسية وحالاتها."""

    def setUp(self):
        self.resp = self.client.get(reverse("pages:styleguide"))

    def test_styleguide_returns_200(self):
        self.assertEqual(self.resp.status_code, 200)

    def test_styleguide_shows_all_components(self):
        self.assertContains(self.resp, "btn--primary")    # زر
        self.assertContains(self.resp, "btn--secondary")  # نوع ثانوي
        self.assertContains(self.resp, "is-loading")      # حالة تحميل
        self.assertContains(self.resp, "badge--shamcash") # شارة دفع
        self.assertContains(self.resp, "field__input")    # حقل
        self.assertContains(self.resp, "product-card")    # بطاقة منتج
