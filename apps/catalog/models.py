"""نماذج الكاتالوج: الماركات والتصنيفات والمنتجات وخياراتها وصورها.

قرارات التصميم:
- الأسعار DecimalField بلا كسور (الليرة السورية لا تُستعمل بكسور عملياً)
  و max_digits=12 يستوعب الأسعار الكبيرة.
- slug يُولَّد تلقائياً من الاسم العربي (allow_unicode) إن تُرك فارغاً.
- حذف تصنيف فيه منتجات ممنوع (PROTECT) — حماية من فقدان بيانات بالغلط.
- specs حقل JSON مرن: مواصفات ثابتة للعرض فقط (المنشأ، الكفالة…).
  أما ما **يختاره الزبون ويؤثر على المخزون** (مقاس، لون) فله نظام
  الخيارات والمتغيّرات أدناه — لا يُخلَط الاثنان.

نظام الخيارات والمتغيّرات (Options & Variants):
  ProductOption       = محور اختيار للمنتج، مثل «المقاس» أو «اللون».
  ProductOptionValue  = قيمة ضمن المحور: S / M / L أو أحمر / أزرق.
  ProductVariant      = تركيبة قابلة للشراء (L + أحمر) لها **مخزونها**
                        وسعرها الخاص إن اختلف.

  - المنتج بلا خيارات يبقى كما كان تماماً (مخزون وسعر على المنتج نفسه)،
    فالبضائع البسيطة لا تدفع ثمن تعقيد لا تحتاجه.
  - محوران كحدّ أقصى (مقاس × لون) — يغطّي البيع بالتجزئة عملياً، ويسمح
    بفرض تفرّد التركيبة على مستوى قاعدة البيانات (لا تركيبتان متطابقتان).
  - `Product.stock` يبقى **مصدر الحقيقة للعرض والفلترة**: للمنتج ذي
    المتغيّرات يُحسب تلقائياً = مجموع مخزون متغيّراته المفعّلة (sync_stock)،
    فتبقى كل الاستعلامات والفلاتر القديمة تعمل بلا تعديل.
"""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

from .search import normalize


def unique_slugify(instance, value):
    """يولّد slug فريداً من نص عربي/إنجليزي؛ يضيف -2 -3 … عند التكرار."""
    base = slugify(value, allow_unicode=True) or "item"
    slug = base
    ModelClass = instance.__class__
    counter = 2
    while ModelClass.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


class Brand(TimeStampedModel):
    """ماركة/علامة تجارية — الزبون يبحث ويفلتر فيها («سامسونج»، «أديداس»)."""

    name = models.CharField("الاسم", max_length=100, unique=True)
    slug = models.SlugField(
        "المعرّف بالرابط", max_length=120, unique=True, blank=True,
        allow_unicode=True,
        help_text="يُولّد تلقائياً من الاسم إذا تُرك فارغاً.",
    )
    is_active = models.BooleanField("مفعّلة", default=True)

    class Meta:
        verbose_name = "ماركة"
        verbose_name_plural = "الماركات"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    """تصنيف شجري: تصنيف رئيسي (إلكترونيات) وتحته فرعية (سماعات…)."""

    name = models.CharField("الاسم", max_length=100)
    slug = models.SlugField(
        "المعرّف بالرابط", max_length=120, unique=True, blank=True,
        allow_unicode=True,
        help_text="يُولّد تلقائياً من الاسم إذا تُرك فارغاً.",
    )
    parent = models.ForeignKey(
        "self", verbose_name="التصنيف الأب",
        null=True, blank=True,
        on_delete=models.CASCADE, related_name="children",
        help_text="اتركه فارغاً ليكون تصنيفاً رئيسياً.",
    )
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"
        ordering = ["name"]
        constraints = [
            # لا يجوز تكرار نفس الاسم تحت نفس الأب
            models.UniqueConstraint(fields=["parent", "name"], name="uniq_category_name_per_parent"),
        ]

    def __str__(self):
        return self.name if self.parent is None else f"{self.parent} ← {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", args=[self.slug])

    @property
    def ancestors(self):
        """سلسلة الآباء من الجذر حتى الأب المباشر — لمسار التنقّل الكامل."""
        chain = []
        node = self.parent
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))

    def descendant_ids(self):
        """معرّفي + معرّفات كل التصنيفات تحتي (لأي عمق) — باستعلام واحد.

        نجلب خريطة (id ← parent_id) لكل التصنيفات مرة واحدة ثم نمشي
        الشجرة بالذاكرة — بدل استعلام لكل مستوى.
        """
        children_map = {}
        for cid, pid in Category.objects.values_list("id", "parent_id"):
            children_map.setdefault(pid, []).append(cid)

        ids, stack = [self.id], [self.id]
        while stack:
            for child_id in children_map.get(stack.pop(), []):
                ids.append(child_id)
                stack.append(child_id)
        return ids


class Product(TimeStampedModel):
    """المنتج — وحدة البيع الأساسية بالمتجر."""

    category = models.ForeignKey(
        Category, verbose_name="التصنيف",
        on_delete=models.PROTECT, related_name="products",
    )
    # بائع المنتج: NULL = بضاعة الصَّيَّاد نفسه؛ غير ذلك = تاجر بالمنصة.
    # PROTECT: التاجر يُعطَّل (is_approved=False) ولا يُحذف وله منتجات.
    merchant = models.ForeignKey(
        "accounts.MerchantProfile", verbose_name="البائع",
        null=True, blank=True,
        on_delete=models.PROTECT, related_name="products",
        help_text="اتركه فارغاً إذا المنتج من بضاعة الصَّيَّاد مباشرة.",
    )
    brand = models.ForeignKey(
        Brand, verbose_name="الماركة",
        null=True, blank=True,
        on_delete=models.SET_NULL, related_name="products",
        help_text="اتركها فارغة إذا المنتج بلا ماركة معروفة.",
    )
    name = models.CharField("الاسم", max_length=200)
    slug = models.SlugField(
        "المعرّف بالرابط", max_length=220, unique=True, blank=True,
        allow_unicode=True,
        help_text="يُولّد تلقائياً من الاسم إذا تُرك فارغاً.",
    )
    sku = models.CharField(
        "رمز المنتج (SKU)", max_length=40, blank=True,
        help_text="رمزك الداخلي للجرد — اختياري، ويظهر بالبحث.",
    )
    description = models.TextField("الوصف", blank=True)
    price = models.DecimalField(
        "السعر (ل.س)", max_digits=12, decimal_places=0,
        help_text="بالليرة السورية، بدون كسور.",
    )
    compare_at_price = models.DecimalField(
        "السعر قبل التخفيض (ل.س)", max_digits=12, decimal_places=0,
        null=True, blank=True,
        help_text="اختياري: إن وُضع وكان أعلى من السعر، يظهر المنتج «بالتخفيضات» "
                  "مع السعر القديم مشطوباً.",
    )
    # للمنتج ذي المتغيّرات: يُحسب تلقائياً (مجموع مخزون المتغيّرات) — لا يُحرَّر
    # يدوياً. للمنتج البسيط: يُدخله البائع كالعادة.
    stock = models.PositiveIntegerField("الكمية بالمخزون", default=0)
    is_active = models.BooleanField(
        "مفعّل", default=True,
        help_text="المنتج غير المفعّل لا يظهر بالمتجر إطلاقاً.",
    )
    specs = models.JSONField(
        "المواصفات", default=dict, blank=True,
        help_text='مواصفات حرّة بصيغة JSON، مثال: {"اللون": "أسود", "الضمان": "سنة"}',
    )
    # نسخة مطبَّعة من الاسم والوصف للبحث العربي — تُحدَّث تلقائياً في save
    # (انظر catalog/search.py: سماعه تلاقي سماعة، اصلي يلاقي أصلي…)
    search_text = models.TextField(editable=False, blank=True, default="")

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        # الماركة والرمز ضمن نص البحث: «أديداس» أو رمز الجرد يلاقيان المنتج
        brand_name = self.brand.name if self.brand_id else ""
        self.search_text = normalize(
            f"{self.name} {self.description} {brand_name} {self.sku}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product", args=[self.slug])

    @property
    def in_stock(self):
        """هل المنتج متوفر للشراء الآن؟

        يعمل للحالتين: البسيط (مخزونه المباشر) وذي المتغيّرات (stock
        مُزامَن = مجموع مخزون متغيّراته).
        """
        return self.is_active and self.stock > 0

    # --- الخيارات والمتغيّرات ------------------------------------------------
    @property
    def has_variants(self):
        """هل للمنتج محاور اختيار (مقاس/لون)؟ يحدّد شكل صفحة المنتج والشراء.

        نقرأ `.all()` لا `.exists()` عمداً: مع prefetch_related("options")
        تُقرأ من الذاكرة، فشبكة البطاقات لا تطلق استعلاماً لكل بطاقة (N+1).
        """
        return bool(self.options.all())

    def sync_stock(self, save=True):
        """يعيد حساب مخزون المنتج من متغيّراته المفعّلة.

        يُستدعى تلقائياً عند أي تغيير على متغيّر (حفظ/حذف)، فيبقى
        `Product.stock` صحيحاً وتبقى كل الفلاتر والتقارير القديمة تعمل.
        """
        if not self.pk or not self.options.exists():
            return self.stock
        total = sum(
            v.stock for v in self.variants.filter(is_active=True).only("stock")
        )
        if total != self.stock:
            self.stock = total
            if save:
                # update_fields: لا نلمس search_text ولا نطلق حفظاً كاملاً
                Product.objects.filter(pk=self.pk).update(stock=total)
        return total

    def purchasable_variants(self):
        """المتغيّرات القابلة للشراء الآن (مفعّلة وفيها مخزون)."""
        return self.variants.filter(is_active=True, stock__gt=0)

    def resolve_variant(self, value_ids):
        """يرجع المتغيّر المطابق تماماً لقيم الخيارات المختارة، أو None.

        نقارن **مجموعات** القيم لا الترتيب — فلا يهم أي محور أرسله المتصفح
        أولاً. عدد المتغيّرات لكل منتج صغير جداً، فالمقارنة بالذاكرة أسرع
        وأوضح من استعلام مركّب.
        """
        try:
            wanted = {int(v) for v in value_ids if str(v).strip()}
        except (TypeError, ValueError):
            return None
        if not wanted:
            return None
        for variant in self.variants.filter(is_active=True).select_related(
                "value_1", "value_2"):
            combo = {variant.value_1_id}
            if variant.value_2_id:
                combo.add(variant.value_2_id)
            if combo == wanted:
                return variant
        return None

    # --- عرض السعر (مدى عند اختلاف أسعار المتغيّرات) -------------------------
    @property
    def price_range(self):
        """(الأدنى، الأعلى) لأسعار المتغيّرات المفعّلة — أو سعر المنتج وحده."""
        # `.all()` + ترشيح بالذاكرة: مع prefetch_related("variants") لا
        # استعلام إضافي لكل بطاقة، ونعوّض السعر الفارغ بسعر المنتج هنا
        # بدل المرور على العلاقة العكسية.
        prices = [
            (v.price if v.price is not None else self.price)
            for v in self.variants.all() if v.is_active
        ]
        if not prices:
            return (self.price, self.price)
        return (min(prices), max(prices))

    @property
    def has_price_range(self):
        """هل تختلف أسعار المتغيّرات؟ (وقتها نعرض «يبدأ من»)."""
        low, high = self.price_range
        return low != high

    @property
    def price_from_display(self):
        """أدنى سعر منسّقاً — للبطاقات عند اختلاف أسعار المتغيّرات."""
        return f"{self.price_range[0]:,.0f}"

    @property
    def card_price_display(self):
        """السعر على البطاقة: أدنى أسعار المتغيّرات، أو سعر المنتج البسيط."""
        return self.price_from_display if self.has_variants else self.price_display

    @property
    def price_display(self):
        """السعر منسّقاً بفواصل الآلاف: 250,000 (العملة تُضاف بالقالب)."""
        return f"{self.price:,.0f}"

    @property
    def on_sale(self):
        """مخفَّض؟ فقط إذا السعر القديم موجود وأعلى فعلاً من الحالي."""
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def old_price_display(self):
        """السعر القديم منسّقاً — نص فارغ إن لم يكن المنتج مخفَّضاً فعلاً."""
        return f"{self.compare_at_price:,.0f}" if self.on_sale else ""

    @property
    def discount_percent(self):
        """نسبة التخفيض كعدد صحيح: 250→200 = 20%."""
        if not self.on_sale:
            return 0
        return round((1 - self.price / self.compare_at_price) * 100)

    @property
    def main_image(self):
        """الصورة الرئيسية (أول صورة حسب الترتيب) أو None."""
        return self.images.first()

    @property
    def main_image_url(self):
        """رابط الصورة الرئيسية للبطاقات — المصغّرة إن وُجدت (أخف بكثير)."""
        img = self.main_image
        if img is None:
            return ""
        return img.thumb.url if img.thumb else img.image.url


class ProductOption(TimeStampedModel):
    """محور اختيار للمنتج: «المقاس»، «اللون»، «السعة»…

    محوران كحدّ أقصى للمنتج الواحد (يُفرض في clean) — يكفيان البيع بالتجزئة
    ويسمحان بفرض تفرّد التركيبة على مستوى قاعدة البيانات.
    """

    MAX_PER_PRODUCT = 2

    product = models.ForeignKey(
        Product, verbose_name="المنتج",
        on_delete=models.CASCADE, related_name="options",
    )
    name = models.CharField(
        "اسم الخيار", max_length=50,
        help_text="مثال: المقاس، اللون، السعة.",
    )
    sort_order = models.PositiveSmallIntegerField("الترتيب", default=0)

    class Meta:
        verbose_name = "خيار منتج"
        verbose_name_plural = "خيارات المنتج"
        ordering = ["sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["product", "name"],
                                    name="uniq_option_name_per_product"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.product_id:
            return
        siblings = ProductOption.objects.filter(product_id=self.product_id)
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)
        if siblings.count() >= self.MAX_PER_PRODUCT:
            raise ValidationError(
                f"الحد الأقصى {self.MAX_PER_PRODUCT} خيارَين للمنتج الواحد "
                "(مثلاً: المقاس واللون)."
            )


class ProductOptionValue(TimeStampedModel):
    """قيمة ضمن محور اختيار: S / M / L، أو أحمر / أزرق."""

    option = models.ForeignKey(
        ProductOption, verbose_name="الخيار",
        on_delete=models.CASCADE, related_name="values",
    )
    value = models.CharField("القيمة", max_length=50)
    sort_order = models.PositiveSmallIntegerField(
        "الترتيب", default=0,
        help_text="لترتيب المقاسات منطقياً (S ثم M ثم L) لا أبجدياً.",
    )

    class Meta:
        verbose_name = "قيمة خيار"
        verbose_name_plural = "قيم الخيارات"
        ordering = ["sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["option", "value"],
                                    name="uniq_value_per_option"),
        ]

    def __str__(self):
        # يظهر بقوائم اللوحة المنسدلة — «المقاس: L» أوضح من «L» وحدها
        return f"{self.option.name}: {self.value}"


class ProductVariant(TimeStampedModel):
    """تركيبة قابلة للشراء من خيارات المنتج، لها مخزونها وسعرها.

    مثال: قميص × (المقاس: L) × (اللون: أبيض) — 7 قطع بسعر المنتج.

    `value_1` للمحور الأول و`value_2` للثاني (فارغ إذا للمنتج محور واحد).
    التفرّد مفروض بقاعدة البيانات بقيدين: واحد للحالة ذات المحورين وآخر
    للحالة ذات المحور الواحد — لأن NULL لا يساوي NULL في قيود التفرّد.
    """

    product = models.ForeignKey(
        Product, verbose_name="المنتج",
        on_delete=models.CASCADE, related_name="variants",
    )
    value_1 = models.ForeignKey(
        ProductOptionValue, verbose_name="الخيار الأول",
        on_delete=models.PROTECT, related_name="variants_as_first",
    )
    value_2 = models.ForeignKey(
        ProductOptionValue, verbose_name="الخيار الثاني",
        null=True, blank=True,
        on_delete=models.PROTECT, related_name="variants_as_second",
        help_text="اتركه فارغاً إذا للمنتج خيار واحد فقط.",
    )
    sku = models.CharField("رمز المتغيّر (SKU)", max_length=40, blank=True)
    price = models.DecimalField(
        "سعر خاص (ل.س)", max_digits=12, decimal_places=0,
        null=True, blank=True,
        help_text="اتركه فارغاً ليأخذ سعر المنتج. املأه فقط إذا هذا المقاس/اللون بسعر مختلف.",
    )
    stock = models.PositiveIntegerField("الكمية بالمخزون", default=0)
    is_active = models.BooleanField(
        "مفعّل", default=True,
        help_text="أزل التفعيل لإخفاء هذه التركيبة دون حذف سجلّها.",
    )

    class Meta:
        verbose_name = "متغيّر منتج"
        verbose_name_plural = "متغيّرات المنتج"
        ordering = ["value_1__sort_order", "value_2__sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "value_1", "value_2"],
                condition=models.Q(value_2__isnull=False),
                name="uniq_variant_two_axis",
            ),
            models.UniqueConstraint(
                fields=["product", "value_1"],
                condition=models.Q(value_2__isnull=True),
                name="uniq_variant_one_axis",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.short_label}"

    # --- العرض ---------------------------------------------------------------
    @property
    def short_label(self):
        """«L · أبيض» — مختصر لسطر السلة وبطاقات العرض."""
        parts = [self.value_1.value]
        if self.value_2_id:
            parts.append(self.value_2.value)
        return " · ".join(parts)

    @property
    def label(self):
        """«المقاس: L، اللون: أبيض» — كامل للفاتورة وسجلّ الطلب."""
        parts = [f"{self.value_1.option.name}: {self.value_1.value}"]
        if self.value_2_id:
            parts.append(f"{self.value_2.option.name}: {self.value_2.value}")
        return "، ".join(parts)

    @property
    def effective_price(self):
        """سعر هذا المتغيّر — سعره الخاص إن وُجد، وإلا سعر المنتج."""
        return self.price if self.price is not None else self.product.price

    @property
    def price_display(self):
        return f"{self.effective_price:,.0f}"

    @property
    def in_stock(self):
        return self.is_active and self.stock > 0

    @property
    def value_ids(self):
        """معرّفات القيم — يستعملها القالب لتحديد الأزرار المختارة."""
        return [self.value_1_id] + ([self.value_2_id] if self.value_2_id else [])

    # --- سلامة البيانات ------------------------------------------------------
    def clean(self):
        """يمنع التركيبات المستحيلة قبل أن تصل لقاعدة البيانات."""
        from django.core.exceptions import ValidationError
        if not self.product_id or not self.value_1_id:
            return
        options = list(self.product.options.all())
        allowed = {o.pk for o in options}

        if self.value_1.option_id not in allowed:
            raise ValidationError({"value_1": "هذه القيمة لا تنتمي لخيارات هذا المنتج."})
        if self.value_2_id:
            if self.value_2.option_id not in allowed:
                raise ValidationError({"value_2": "هذه القيمة لا تنتمي لخيارات هذا المنتج."})
            if self.value_2.option_id == self.value_1.option_id:
                raise ValidationError(
                    {"value_2": "لا يجوز اختيار قيمتين من نفس الخيار — "
                                "اختر قيمة من الخيار الثاني."}
                )
        elif len(options) > 1:
            raise ValidationError(
                {"value_2": "هذا المنتج له خيارَان — لازم تحدّد قيمة للخيار الثاني."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.sync_stock()        # مخزون المنتج = مجموع متغيّراته

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.sync_stock()


class Review(TimeStampedModel):
    """تقييم منتج — من مشترٍ موثَّق فقط (عنده طلب فيه هذا المنتج).

    تقييم واحد لكل (مشترٍ، منتج) — إعادة الإرسال تحدّث تقييمه السابق.
    ينشر فوراً (المقيّمون مشترون حقيقيون) مع إمكانية الإخفاء من اللوحة.
    """

    product = models.ForeignKey(
        Product, verbose_name="المنتج",
        on_delete=models.CASCADE, related_name="reviews",
    )
    user = models.ForeignKey(
        "auth.User", verbose_name="المستخدم",
        on_delete=models.CASCADE, related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        "التقييم",
        choices=[(i, "★" * i) for i in range(1, 6)],
    )
    comment = models.TextField("التعليق", blank=True)
    is_approved = models.BooleanField(
        "منشور", default=True,
        help_text="أزل التفعيل لإخفاء تقييم مسيء دون حذفه.",
    )

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "user"],
                                    name="uniq_review_per_buyer"),
        ]

    def __str__(self):
        return f"{self.rating}★ — {self.product}"

    @staticmethod
    def can_review(user, product):
        """موثَّق = مسجَّل وعنده طلب غير ملغى يحتوي المنتج."""
        if not user.is_authenticated:
            return False
        from apps.orders.models import Order, OrderItem
        return OrderItem.objects.filter(
            order__user=user, product=product,
        ).exclude(order__status=Order.Status.CANCELLED).exists()


class ProductImage(TimeStampedModel):
    """صورة منتج — منتج واحد ممكن يكون له عدة صور مرتّبة."""

    product = models.ForeignKey(
        Product, verbose_name="المنتج",
        on_delete=models.CASCADE, related_name="images",
    )
    image = models.ImageField("الصورة", upload_to="products/%Y/%m/")
    # مصغّرة 480px تتولّد تلقائياً عند الحفظ (انظر save و catalog/images.py)
    thumb = models.ImageField(
        "المصغّرة", upload_to="products/thumbs/%Y/%m/",
        editable=False, blank=True,
    )
    alt_text = models.CharField(
        "النص البديل", max_length=200, blank=True,
        help_text="وصف قصير للصورة (يفيد لضعاف البصر ومحركات البحث).",
    )
    is_main = models.BooleanField("رئيسية", default=False)
    sort_order = models.PositiveSmallIntegerField("الترتيب", default=0)

    class Meta:
        verbose_name = "صورة منتج"
        verbose_name_plural = "صور المنتجات"
        ordering = ["-is_main", "sort_order", "pk"]

    def __str__(self):
        return f"صورة {self.product}"

    def save(self, *args, **kwargs):
        # نولّد المصغّرة عند أول حفظ أو عند تبديل ملف الصورة فقط —
        # لا داعي لإعادة توليدها مع كل تعديل ترتيب/نص بديل.
        needs_thumb = self.image and not self.thumb
        if self.pk and self.image:
            old = ProductImage.objects.filter(pk=self.pk).values_list("image", flat=True).first()
            if old and old != self.image.name:
                needs_thumb = True
        if needs_thumb:
            from .images import make_thumbnail
            result = make_thumbnail(self.image)
            if result:
                name, content = result
                self.thumb.save(name, content, save=False)
        super().save(*args, **kwargs)
