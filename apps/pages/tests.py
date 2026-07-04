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


class TrustAndSeoTests(TestCase):
    """M11: صفحات الثقة + 404 مخصصة + sitemap/robots + OG."""

    def test_about_page(self):
        resp = self.client.get(reverse("pages:about"))
        self.assertContains(resp, "عن الصَّيَّاد")
        self.assertContains(resp, "موثوق")

    def test_contact_page_shows_store_contact(self):
        resp = self.client.get(reverse("pages:contact"))
        self.assertContains(resp, "wa.me/")
        self.assertContains(resp, "tel:")

    def test_footer_links_everywhere(self):
        resp = self.client.get(reverse("pages:home"))
        self.assertContains(resp, reverse("pages:about"))
        self.assertContains(resp, reverse("pages:contact"))

    def test_custom_404_page(self):
        with self.settings(DEBUG=False, ALLOWED_HOSTS=["testserver"]):
            resp = self.client.get("/صفحة-غير-موجودة/")
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "ما في شي هون!", status_code=404)

    def test_sitemap_lists_products_and_pages(self):
        from apps.catalog.models import Category, Product
        cat = Category.objects.create(name="إلكترونيات")
        product = Product.objects.create(category=cat, name="سماعة", price=1000, stock=1)
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, product.get_absolute_url())
        self.assertContains(resp, reverse("pages:about"))

    def test_robots_txt(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp["Content-Type"], "text/plain")
        self.assertContains(resp, "Disallow: /admin/")
        self.assertContains(resp, "Sitemap: http://testserver/sitemap.xml")

    def test_product_page_has_og_tags(self):
        from apps.catalog.models import Category, Product
        cat = Category.objects.create(name="إلكترونيات")
        product = Product.objects.create(category=cat, name="سماعة", price=1000, stock=1)
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, 'property="og:title"')
        self.assertContains(resp, 'content="product"')


class AdminThemeTests(TestCase):
    """M19: لوحة التحكم بهوية الصَّيَّاد."""

    def test_admin_login_uses_brand_theme(self):
        resp = self.client.get("/admin/login/")
        self.assertContains(resp, "css/admin-theme.css")
        self.assertContains(resp, "css/fonts.css")
        self.assertContains(resp, "لوحة تحكم الصَّيَّاد")
        self.assertContains(resp, "sayyad-mark")


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
