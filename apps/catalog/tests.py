"""اختبارات الكاتالوج: سلوك النماذج + وصول لوحة التحكم."""

import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .admin import ProductAdmin, ProductOptionForm
from .models import (Brand, Category, Product, ProductImage, ProductOption,
                     ProductOptionValue, ProductVariant)


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


class BrowseTests(TestCase):
    """M9: منتجات الشجرة كاملة + الفرز + فلتر المتوفر + حفظ الباراميترات."""

    def setUp(self):
        self.root = Category.objects.create(name="إلكترونيات")
        self.child = Category.objects.create(name="سماعات", parent=self.root)
        self.grandchild = Category.objects.create(name="سماعات لاسلكية", parent=self.child)
        self.p_root = make_product(category=self.root, name="تلفزيون", price=Decimal("900000"))
        self.p_deep = make_product(category=self.grandchild, name="سماعة عميقة", price=Decimal("100000"))
        self.p_oos = make_product(category=self.root, name="منتج نافد", stock=0)

    def test_category_page_includes_descendant_products(self):
        """منتج بالحفيد يظهر على صفحة الجد."""
        resp = self.client.get(self.root.get_absolute_url())
        self.assertContains(resp, "سماعة عميقة")

    def test_descendant_ids_walks_whole_tree(self):
        ids = self.root.descendant_ids()
        self.assertIn(self.grandchild.id, ids)
        self.assertIn(self.root.id, ids)

    def test_full_breadcrumb_chain_on_deep_category(self):
        resp = self.client.get(self.grandchild.get_absolute_url())
        self.assertContains(resp, "إلكترونيات")   # الجذر ظاهر بمسار التنقّل
        self.assertContains(resp, "سماعات")

    def test_sort_by_price_ascending(self):
        resp = self.client.get(self.root.get_absolute_url(), {"sort": "price_asc"})
        products = list(resp.context["page"].object_list)
        prices = [p.price for p in products]
        self.assertEqual(prices, sorted(prices))

    def test_bad_sort_value_falls_back_to_default(self):
        resp = self.client.get(self.root.get_absolute_url(), {"sort": "hack'--"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["sort"], "new")

    def test_available_filter_hides_out_of_stock(self):
        resp = self.client.get(self.root.get_absolute_url(), {"available": "1"})
        self.assertNotContains(resp, "منتج نافد")
        self.assertContains(resp, "تلفزيون")

    def test_search_keeps_q_with_sort(self):
        resp = self.client.get(reverse("catalog:search"),
                               {"q": "سماعه", "sort": "price_asc"})
        self.assertContains(resp, "سماعة عميقة")
        # q محفوظ بحقل مخفي بشريط الأدوات
        self.assertContains(resp, 'name="q" value="سماعه"')


def fake_image_file(name="photo.png", size=(800, 600), color=(200, 50, 50)):
    """صورة PNG حقيقية بالذاكرة — لاختبار الرفع بدون ملفات على القرص."""
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="alsayyad_test_media_"))
class ThumbnailTests(TestCase):
    """M14: توليد المصغّرات تلقائياً عند الحفظ."""

    def setUp(self):
        self.product = make_product()

    def test_thumbnail_generated_on_save(self):
        pi = ProductImage.objects.create(product=self.product, image=fake_image_file())
        self.assertTrue(pi.thumb)                        # اتولّدت
        self.assertIn("_thumb", pi.thumb.name)

    def test_thumbnail_is_small_square_jpeg(self):
        from PIL import Image
        pi = ProductImage.objects.create(product=self.product, image=fake_image_file())
        with pi.thumb.open("rb") as fh:
            img = Image.open(fh)
            self.assertEqual(img.format, "JPEG")
            self.assertLessEqual(max(img.size), 480)
            self.assertEqual(img.size[0], img.size[1])   # مربّعة (قصّ مركزي)

    def test_cards_use_thumbnail_url(self):
        ProductImage.objects.create(product=self.product, image=fake_image_file())
        self.assertIn("thumbs/", self.product.main_image_url)

    def test_metadata_edit_does_not_regenerate(self):
        pi = ProductImage.objects.create(product=self.product, image=fake_image_file())
        first_thumb = pi.thumb.name
        pi.alt_text = "وصف جديد"
        pi.save()                                        # تعديل نص فقط
        self.assertEqual(pi.thumb.name, first_thumb)     # نفس الملف، بلا توليد جديد


class SalePricingTests(TestCase):
    """M13: التخفيضات — السعر القديم والشارة والنسبة."""

    def test_on_sale_only_when_old_price_is_higher(self):
        p = make_product(price=Decimal("200000"))
        self.assertFalse(p.on_sale)                      # بلا سعر قديم
        p.compare_at_price = Decimal("150000")           # أدنى من الحالي؟ ليس تخفيضاً
        self.assertFalse(p.on_sale)
        p.compare_at_price = Decimal("250000")
        self.assertTrue(p.on_sale)

    def test_discount_percent(self):
        p = make_product(price=Decimal("200000"))
        p.compare_at_price = Decimal("250000")
        self.assertEqual(p.discount_percent, 20)         # 50/250

    def test_old_price_display_empty_when_not_on_sale(self):
        p = make_product(price=Decimal("200000"))
        self.assertEqual(p.old_price_display, "")

    def test_sale_shows_on_card_and_product_page(self):
        p = make_product(name="سماعة مخفّضة", price=Decimal("200000"))
        p.compare_at_price = Decimal("250000")
        p.save()
        home = self.client.get(reverse("pages:home"))
        self.assertContains(home, "sale-flag")           # شارة الخصم عالبطاقة
        self.assertContains(home, "250,000")             # السعر القديم مشطوب
        page = self.client.get(p.get_absolute_url())
        self.assertContains(page, "خصم 20٪")

    def test_no_sale_ui_for_normal_product(self):
        make_product(name="عادي", price=Decimal("200000"))
        home = self.client.get(reverse("pages:home"))
        self.assertNotContains(home, "sale-flag")


class ProductPageExtrasTests(TestCase):
    """M10: منتجات مشابهة + مشاركة واتساب."""

    def setUp(self):
        self.cat = Category.objects.create(name="إلكترونيات")
        self.product = make_product(category=self.cat, name="سماعة رئيسية")
        self.sibling = make_product(category=self.cat, name="سماعة شقيقة")
        self.hidden_sibling = make_product(category=self.cat, name="شقيقة مخفية",
                                           is_active=False)
        other_cat = Category.objects.create(name="أدوات منزلية")
        self.unrelated = make_product(category=other_cat, name="غلاية بعيدة")

    def get(self):
        return self.client.get(self.product.get_absolute_url())

    def test_related_shows_same_category_only(self):
        resp = self.get()
        self.assertContains(resp, "منتجات مشابهة")
        self.assertContains(resp, "سماعة شقيقة")
        self.assertNotContains(resp, "غلاية بعيدة")

    def test_related_excludes_self_and_inactive(self):
        resp = self.get()
        self.assertNotContains(resp, "شقيقة مخفية")
        # اسم المنتج نفسه يظهر مرة بالعنوان/البطاقة الرئيسية لكن ليس ببطاقات المشابهة:
        # نتأكد أن عدد البطاقات = 1 (الشقيقة فقط)
        self.assertEqual(resp.content.decode().count("product-card__name"), 1)

    def test_whatsapp_share_link_present_with_absolute_url(self):
        resp = self.get()
        self.assertContains(resp, "https://wa.me/?text=")
        self.assertContains(resp, "شارك المنتج عالواتساب")
        # الرابط المشارك مطلق (فيه الدومين) — مشفّراً داخل باراميتر النص
        # (فلتر urlencode يترك / كما هي — قانونية داخل قيمة الاستعلام)
        self.assertContains(resp, "http%3A//testserver")

    def test_no_related_section_when_alone(self):
        lonely_cat = Category.objects.create(name="فريد")
        lonely = make_product(category=lonely_cat, name="منتج وحيد")
        resp = self.client.get(lonely.get_absolute_url())
        self.assertNotContains(resp, "منتجات مشابهة")


class ReviewTests(TestCase):
    """M24: التقييمات — مشترون موثَّقون فقط، متوسط، إشراف."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        from apps.orders.models import Order, OrderItem

        self.product = make_product(name="سماعة مُقيَّمة")
        User = get_user_model()
        # مشترٍ موثَّق: عنده طلب فيه المنتج
        self.buyer = User.objects.create_user("0911111111", password="x",
                                              first_name="أبو التقييم")
        order = Order.objects.create(
            customer_name="أبو التقييم", phone="0911111111", city="دمشق",
            address="ع", total=self.product.price, user=self.buyer)
        OrderItem.objects.create(order=order, product=self.product,
                                 product_name=self.product.name,
                                 unit_price=self.product.price, quantity=1)
        # مسجَّل بلا شراء
        self.visitor = User.objects.create_user("0922222222", password="x")
        self.url = reverse("catalog:submit_review", args=[self.product.id])

    def post_review(self, rating=5, comment="ممتازة"):
        return self.client.post(self.url, {"rating": rating, "comment": comment})

    def test_guest_sees_login_prompt_not_form(self):
        resp = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(resp, "rating-input")
        self.assertContains(resp, "التقييم لمن اشترى المنتج")

    def test_non_buyer_cannot_review(self):
        self.client.force_login(self.visitor)
        resp = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(resp, "rating-input")     # لا فورم
        self.post_review()                               # ولا حتى POST مباشر
        self.assertEqual(self.product.reviews.count(), 0)

    def test_buyer_can_review_and_it_shows_with_average(self):
        self.client.force_login(self.buyer)
        resp = self.client.get(self.product.get_absolute_url())
        self.assertContains(resp, "rating-input")        # الفورم ظاهر
        self.post_review(rating=4, comment="سماعة نظيفة")
        resp = self.client.get(self.product.get_absolute_url())
        self.assertContains(resp, "سماعة نظيفة")
        self.assertContains(resp, "مشترٍ موثَّق")
        self.assertContains(resp, "4.0")                 # المتوسط

    def test_resubmit_updates_not_duplicates(self):
        self.client.force_login(self.buyer)
        self.post_review(rating=2)
        self.post_review(rating=5, comment="غيّرت رأيي")
        self.assertEqual(self.product.reviews.count(), 1)
        self.assertEqual(self.product.reviews.get().rating, 5)

    def test_cancelled_order_buyer_not_verified(self):
        from apps.orders.models import Order
        Order.objects.filter(user=self.buyer).update(status=Order.Status.CANCELLED)
        self.client.force_login(self.buyer)
        self.post_review()
        self.assertEqual(self.product.reviews.count(), 0)

    def test_unapproved_review_hidden_from_public(self):
        from .models import Review
        self.client.force_login(self.buyer)
        self.post_review(comment="تعليق مخفي")
        Review.objects.update(is_approved=False)
        self.client.logout()          # كزائر: صاحبه يظل يراه بفورم التعديل
        resp = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(resp, "تعليق مخفي")

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.buyer)
        self.post_review(rating=9)
        self.assertEqual(self.product.reviews.count(), 0)


class SearchNormalizeTests(TestCase):
    """قواعد تطبيع العربية — قلب البحث كله."""

    def test_ta_marbuta_and_alef_forms(self):
        from .search import normalize
        self.assertEqual(normalize("سماعة"), normalize("سماعه"))
        self.assertEqual(normalize("أصلي"), normalize("اصلي"))
        self.assertEqual(normalize("إبريق"), normalize("ابريق"))
        self.assertEqual(normalize("مقلى"), normalize("مقلي"))

    def test_diacritics_and_digits(self):
        from .search import normalize
        self.assertEqual(normalize("مُكَيِّف"), "مكيف")
        self.assertEqual(normalize("شاحن ٦٥ واط"), "شاحن 65 واط")

    def test_latin_lowercased_and_spaces_collapsed(self):
        from .search import normalize
        self.assertEqual(normalize("  USB-C   Charger "), "usb-c charger")


class SearchViewsTests(TestCase):
    """صفحة النتائج والاقتراحات الحية."""

    def setUp(self):
        self.p1 = make_product(name="سماعة لاسلكية أصلية")
        self.p2 = make_product(name="شاحن سريع 65 واط",
                               description="شاحن أصلي يدعم كل الأجهزة")
        self.hidden = make_product(name="سماعة مخفية", is_active=False)
        self.url = reverse("catalog:search")

    def test_search_matches_despite_spelling_variants(self):
        """«سماعه» (بالهاء) تلاقي «سماعة» (بالتاء المربوطة)."""
        resp = self.client.get(self.url, {"q": "سماعه"})
        self.assertContains(resp, self.p1.name)
        self.assertNotContains(resp, "سماعة مخفية")   # غير المفعّل لا يظهر

    def test_multiword_query_requires_all_words(self):
        resp = self.client.get(self.url, {"q": "شاحن اصلي"})
        self.assertContains(resp, self.p2.name)        # فيه الكلمتين
        self.assertNotContains(resp, self.p1.name)     # أصلية بلا شاحن

    def test_description_is_searchable(self):
        resp = self.client.get(self.url, {"q": "الأجهزة"})
        self.assertContains(resp, self.p2.name)

    def test_no_results_shows_empty_state(self):
        resp = self.client.get(self.url, {"q": "غواصة نووية"})
        self.assertContains(resp, "ما لقينا شي")

    def test_empty_query_shows_prompt(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "اكتب بشريط البحث")

    def test_editing_product_updates_search_text(self):
        self.p1.name = "مكواة بخار"
        self.p1.save()
        resp = self.client.get(self.url, {"q": "مكواه"})   # بالهاء
        self.assertContains(resp, "مكواة بخار")

    def test_suggest_returns_items_and_view_all_link(self):
        resp = self.client.get(reverse("catalog:search_suggest"), {"q": "سماعه"})
        self.assertContains(resp, self.p1.name)
        self.assertContains(resp, "كل النتائج")

    def test_suggest_short_query_is_silent(self):
        resp = self.client.get(reverse("catalog:search_suggest"), {"q": "س"})
        self.assertNotContains(resp, "search-suggest__item")


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

    def test_admin_low_stock_filter(self):
        make_product(name="نافد تماماً", stock=0)
        make_product(name="شارف يخلص", stock=2)
        make_product(name="مليان", stock=50)
        url = reverse("admin:catalog_product_changelist")

        resp = self.client.get(url, {"stock_level": "low"})
        self.assertContains(resp, "شارف يخلص")
        self.assertNotContains(resp, "مليان")

        resp = self.client.get(url, {"stock_level": "out"})
        self.assertContains(resp, "نافد تماماً")
        self.assertNotContains(resp, "شارف يخلص")


# ==========================================================================
#  المقاسات والألوان (الخيارات والمتغيّرات)
# ==========================================================================

def make_variant_product(sizes=("S", "M", "L"), colors=("أبيض", "أسود"),
                         stock=4, **kwargs):
    """منتج بمحورَين جاهزَين + متغيّر لكل تركيبة — أساس اختبارات المقاسات."""
    product = make_product(name="قميص قطن", price=Decimal("85000"),
                           stock=0, **kwargs)
    size_opt = ProductOption.objects.create(product=product, name="المقاس", sort_order=1)
    size_values = [
        ProductOptionValue.objects.create(option=size_opt, value=v, sort_order=i)
        for i, v in enumerate(sizes)
    ]
    color_values = []
    if colors:
        color_opt = ProductOption.objects.create(product=product, name="اللون", sort_order=2)
        color_values = [
            ProductOptionValue.objects.create(option=color_opt, value=v, sort_order=i)
            for i, v in enumerate(colors)
        ]
    for size in size_values:
        for color in (color_values or [None]):
            ProductVariant.objects.create(
                product=product, value_1=size, value_2=color, stock=stock)
    product.refresh_from_db()
    return product, size_values, color_values


class ProductOptionTests(TestCase):
    def test_option_limited_to_two_axes(self):
        product = make_product()
        ProductOption.objects.create(product=product, name="المقاس")
        ProductOption.objects.create(product=product, name="اللون")
        third = ProductOption(product=product, name="السعة")
        with self.assertRaises(ValidationError):
            third.full_clean()

    def test_duplicate_option_name_per_product_blocked(self):
        product = make_product()
        ProductOption.objects.create(product=product, name="المقاس")
        with self.assertRaises(IntegrityError):
            ProductOption.objects.create(product=product, name="المقاس")

    def test_values_keep_manual_order_not_alphabetical(self):
        product = make_product()
        option = ProductOption.objects.create(product=product, name="المقاس")
        for i, value in enumerate(["S", "M", "L", "XL"]):
            ProductOptionValue.objects.create(option=option, value=value, sort_order=i)
        self.assertEqual([v.value for v in option.values.all()], ["S", "M", "L", "XL"])


class ProductVariantTests(TestCase):
    def test_product_stock_is_sum_of_variant_stock(self):
        product, _, _ = make_variant_product(sizes=("S", "M"), colors=("أبيض",), stock=3)
        self.assertEqual(product.stock, 6)          # مقاسان × 3
        self.assertTrue(product.has_variants)
        self.assertTrue(product.in_stock)

    def test_stock_resyncs_when_variant_changes_or_is_removed(self):
        product, sizes, colors = make_variant_product(
            sizes=("S", "M"), colors=("أبيض",), stock=5)
        variant = product.variants.first()
        variant.stock = 1
        variant.save()
        product.refresh_from_db()
        self.assertEqual(product.stock, 6)          # 1 + 5

        variant.delete()
        product.refresh_from_db()
        self.assertEqual(product.stock, 5)

    def test_deactivated_variant_leaves_product_stock(self):
        product, _, _ = make_variant_product(sizes=("S",), colors=("أبيض",), stock=4)
        variant = product.variants.first()
        variant.is_active = False
        variant.save()
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertFalse(product.in_stock)          # ما في تركيبة تُباع

    def test_duplicate_combination_blocked_by_database(self):
        product, sizes, colors = make_variant_product(sizes=("S",), colors=("أبيض",))
        with self.assertRaises(IntegrityError):
            ProductVariant.objects.create(
                product=product, value_1=sizes[0], value_2=colors[0], stock=1)

    def test_two_values_from_same_axis_rejected(self):
        product, sizes, _ = make_variant_product(sizes=("S", "M"), colors=())
        bad = ProductVariant(product=product, value_1=sizes[0], value_2=sizes[1])
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_value_from_another_product_rejected(self):
        product, sizes, _ = make_variant_product(sizes=("S",), colors=())
        other, other_sizes, _ = make_variant_product(sizes=("XL",), colors=())
        bad = ProductVariant(product=product, value_1=other_sizes[0])
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_resolve_variant_ignores_order_of_values(self):
        product, sizes, colors = make_variant_product()
        variant = product.resolve_variant([colors[1].id, sizes[2].id])
        self.assertIsNotNone(variant)
        self.assertEqual(variant.value_1, sizes[2])
        self.assertEqual(variant.value_2, colors[1])

    def test_resolve_variant_returns_none_for_impossible_combo(self):
        product, sizes, colors = make_variant_product()
        product.variants.filter(value_1=sizes[0], value_2=colors[0]).delete()
        self.assertIsNone(product.resolve_variant([sizes[0].id, colors[0].id]))
        self.assertIsNone(product.resolve_variant([]))
        self.assertIsNone(product.resolve_variant(["مو-رقم"]))

    def test_variant_price_falls_back_to_product_price(self):
        product, sizes, colors = make_variant_product()
        cheap = product.variants.first()
        self.assertEqual(cheap.effective_price, product.price)

        pricey = product.variants.last()
        pricey.price = Decimal("99000")
        pricey.save()
        self.assertEqual(pricey.effective_price, Decimal("99000"))
        self.assertTrue(product.has_price_range)
        self.assertEqual(product.price_from_display, "85,000")

    def test_labels_read_naturally(self):
        product, sizes, colors = make_variant_product()
        variant = product.resolve_variant([sizes[0].id, colors[0].id])
        self.assertEqual(variant.short_label, "S · أبيض")
        self.assertEqual(variant.label, "المقاس: S، اللون: أبيض")


class VariantProductPageTests(TestCase):
    def test_page_shows_option_buttons_for_each_axis(self):
        product, sizes, colors = make_variant_product()
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "المقاس")
        self.assertContains(response, "اللون")
        for value in sizes + colors:
            self.assertContains(response, f'value="{value.id}"')

    def test_sold_out_value_is_disabled_in_html(self):
        """قيمة بلا أي تركيبة متوفرة تُعطَّل بالـHTML — قبل أي جافاسكربت."""
        product, sizes, colors = make_variant_product(stock=2)
        product.variants.filter(value_1=sizes[0]).update(stock=0)
        response = self.client.get(product.get_absolute_url())
        html = response.content.decode()
        marker = f'value="{sizes[0].id}"'
        self.assertIn(marker, html)
        self.assertIn("is-sold-out", html)
        # الزر المعطّل هو نفسه صاحب القيمة النافدة
        self.assertIn(f'{marker} disabled', html)

    def test_simple_product_page_has_no_picker(self):
        product = make_product()
        response = self.client.get(product.get_absolute_url())
        self.assertNotContains(response, "variant-group")

    def test_card_links_to_page_instead_of_direct_add(self):
        """بطاقة منتج بمقاسات ما فيها «أضف للسلة» — لازم يختار أولاً."""
        make_variant_product()
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, "اختر وأضف")

    def test_brand_shows_on_product_page_and_is_searchable(self):
        brand = Brand.objects.create(name="أديداس")
        product = make_product(brand=brand, name="حذاء رياضي")
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "أديداس")
        # الماركة تدخل نص البحث فيلاقيها الزبون
        found = self.client.get(reverse("catalog:search"), {"q": "أديداس"})
        self.assertContains(found, "حذاء رياضي")

    def test_sku_is_searchable(self):
        make_product(name="غلاية كهربائية", sku="KT-900")
        response = self.client.get(reverse("catalog:search"), {"q": "KT-900"})
        self.assertContains(response, "غلاية كهربائية")


class VariantAdminTests(TestCase):
    """مسار إدخال البيانات باللوحة — هذا ما يستعمله موظّف المبيعات يومياً."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser("admin", "a@a.a", "pass12345")
        self.client.force_login(self.admin)

    def test_option_values_are_created_from_comma_separated_text(self):
        """يكتب «S, M, L» بسطر واحد فتُنشأ ثلاث قيم مرتّبة."""
        product = make_product()
        option = ProductOption(product=product, name="المقاس")
        form = ProductOptionForm(
            {"name": "المقاس", "values_text": "S, M, L, XL", "sort_order": 0},
            instance=option)
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.product = product
        form.save()
        self.assertEqual([v.value for v in option.values.all()],
                         ["S", "M", "L", "XL"])

    def test_arabic_comma_and_spaces_are_handled(self):
        product = make_product()
        option = ProductOption(product=product, name="اللون")
        form = ProductOptionForm(
            {"name": "اللون", "values_text": " أحمر ، أزرق,  أخضر ", "sort_order": 0},
            instance=option)
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.product = product
        form.save()
        self.assertEqual([v.value for v in option.values.all()],
                         ["أحمر", "أزرق", "أخضر"])

    def test_removing_a_value_in_use_is_kept_not_deleted(self):
        """قيمة عليها مخزون/طلبات لا تُحذف بمجرد مسحها من النص."""
        product, sizes, _ = make_variant_product(sizes=("S", "M"), colors=())
        option = product.options.first()
        form = ProductOptionForm(
            {"name": option.name, "values_text": "S", "sort_order": 0},
            instance=option)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertIn("M", [v.value for v in option.values.all()])

    def test_generate_variants_action_creates_every_combination(self):
        product = make_product(name="قميص", stock=0)
        size = ProductOption.objects.create(product=product, name="المقاس")
        color = ProductOption.objects.create(product=product, name="اللون")
        for i, v in enumerate(["S", "M", "L"]):
            ProductOptionValue.objects.create(option=size, value=v, sort_order=i)
        for i, v in enumerate(["أبيض", "أسود"]):
            ProductOptionValue.objects.create(option=color, value=v, sort_order=i)

        response = self.client.post(
            reverse("admin:catalog_product_changelist"),
            {"action": "generate_variants", "_selected_action": [product.pk]},
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(product.variants.count(), 6)      # 3 مقاسات × لونان
        self.assertContains(response, "تم توليد 6 تركيبة")

    def test_generate_variants_is_idempotent_and_keeps_stock(self):
        product, _, _ = make_variant_product(sizes=("S", "M"), colors=("أبيض",),
                                             stock=7)
        before = product.variants.count()
        self.client.post(reverse("admin:catalog_product_changelist"),
                         {"action": "generate_variants",
                          "_selected_action": [product.pk]}, follow=True)
        self.assertEqual(product.variants.count(), before)  # ما تكرّرت
        self.assertEqual(product.variants.first().stock, 7)  # ولا انمسح مخزون

    def test_stock_field_is_locked_for_variant_products(self):
        product, _, _ = make_variant_product(sizes=("S",), colors=("أبيض",))
        response = self.client.get(
            reverse("admin:catalog_product_change", args=[product.pk]))
        self.assertIn("stock", response.context["adminform"].readonly_fields)

    def test_stock_field_stays_editable_for_simple_products(self):
        product = make_product()
        response = self.client.get(
            reverse("admin:catalog_product_change", args=[product.pk]))
        self.assertNotIn("stock", response.context["adminform"].readonly_fields)

    def test_manual_stock_edit_on_variant_product_is_corrected(self):
        """لو عدّل أحدهم المخزون يدوياً من الجدول، يُعاد حسابه فوراً."""
        product, _, _ = make_variant_product(sizes=("S", "M"), colors=("أبيض",),
                                             stock=5)
        self.assertEqual(product.stock, 10)

        request = RequestFactory().post("/admin/")
        request.user = self.admin
        product.stock = 999
        ProductAdmin(Product, admin.site).save_model(
            request=request, obj=product, form=None, change=True)
        product.refresh_from_db()
        self.assertEqual(product.stock, 10)
