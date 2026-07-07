"""نماذج الكاتالوج: التصنيفات والمنتجات وصورها.

قرارات التصميم:
- الأسعار DecimalField بلا كسور (الليرة السورية لا تُستعمل بكسور عملياً)
  و max_digits=12 يستوعب الأسعار الكبيرة.
- slug يُولَّد تلقائياً من الاسم العربي (allow_unicode) إن تُرك فارغاً.
- حذف تصنيف فيه منتجات ممنوع (PROTECT) — حماية من فقدان بيانات بالغلط.
- specs حقل JSON مرن: مواصفات تختلف من منتج لآخر (مقاس، لون، واط…)
  بدون ما نضيف عمود جديد لكل مواصفة.
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
    name = models.CharField("الاسم", max_length=200)
    slug = models.SlugField(
        "المعرّف بالرابط", max_length=220, unique=True, blank=True,
        allow_unicode=True,
        help_text="يُولّد تلقائياً من الاسم إذا تُرك فارغاً.",
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
        self.search_text = normalize(f"{self.name} {self.description}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product", args=[self.slug])

    @property
    def in_stock(self):
        """هل المنتج متوفر للشراء الآن؟"""
        return self.is_active and self.stock > 0

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
