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

    def test_home_loads_design_tokens_and_brand(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "css/tokens.css")   # نظام التصميم محمّل
        self.assertContains(resp, "الصَّيَّاد")          # اسم البراند ظاهر
