"""نماذج الطلبات: Order (الطلب) + OrderItem (سطر لكل منتج).

أهم قرار هنا: **اللقطة (snapshot)**. سطر الطلب يخزّن اسم المنتج وسعره
لحظة الشراء، لا يكتفي بالإشارة للمنتج — لأن الأسعار بسوريا تتغيّر،
وفاتورة الزبون يجب أن تبقى كما كانت يوم طلب، مهما تعدّل الكاتالوج.
"""

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string

from apps.core.models import TimeStampedModel

# ملاحظة: التعريف الأصلي انتقل لـ apps/core/validators.py (مشترك بين التطبيقات).
# نبقي الاسم مستورداً هنا لأن هجرة orders/0001 تشير إليه بهذا المسار.
from apps.core.validators import syrian_phone  # noqa: E402  (توافق الهجرات)


class Order(TimeStampedModel):
    """طلب شراء واحد — من لحظة التأكيد حتى التسليم."""

    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار التأكيد"
        CONFIRMED = "confirmed", "مؤكّد"
        SHIPPED = "shipped", "قيد التوصيل"
        DELIVERED = "delivered", "مُسلَّم"
        CANCELLED = "cancelled", "ملغى"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "الدفع عند الاستلام"
        SHAMCASH = "shamcash", "شام كاش"

    # رقم قصير يُقرأ بسهولة عالتلفون — يتولّد تلقائياً (انظر save)
    number = models.CharField("رقم الطلب", max_length=12, unique=True, editable=False)

    # صاحب الطلب إن كان مسجَّلاً — NULL = طلب زائر (guest)، وهذا مسار مدعوم
    # دائماً. SET_NULL: حذف الحساب لا يمس سجلات الطلبات (تبقى فواتير).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="المستخدم",
        null=True, blank=True,
        on_delete=models.SET_NULL, related_name="orders",
    )

    customer_name = models.CharField("الاسم الكامل", max_length=100)
    phone = models.CharField("رقم الموبايل", max_length=10, validators=[syrian_phone])
    city = models.CharField("المحافظة / المدينة", max_length=50)
    address = models.TextField("العنوان بالتفصيل")
    notes = models.TextField("ملاحظات", blank=True)

    payment_method = models.CharField(
        "طريقة الدفع", max_length=10,
        choices=PaymentMethod.choices, default=PaymentMethod.COD,
    )
    status = models.CharField(
        "الحالة", max_length=10,
        choices=Status.choices, default=Status.PENDING,
    )
    total = models.DecimalField("الإجمالي (ل.س)", max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"طلب {self.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self._generate_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        """رقم عشوائي من 8 خانات، مضمون عدم تكراره."""
        while True:
            number = get_random_string(8, "0123456789")
            if not Order.objects.filter(number=number).exists():
                return number

    @property
    def total_display(self):
        return f"{self.total:,.0f}"

    # مسار الطلب الطبيعي بالترتيب — «ملغى» خارجه (حالة خاصة بالعرض)
    STATUS_FLOW = [Status.PENDING, Status.CONFIRMED, Status.SHIPPED, Status.DELIVERED]

    @property
    def timeline(self):
        """خطوات التتبع للعرض: [(التسمية، وصلنا لها؟، هي الحالية؟)، …]"""
        try:
            current = self.STATUS_FLOW.index(self.status)
        except ValueError:                 # ملغى — القالب يعرض تنبيهاً بدل الخط
            return []
        return [
            (status.label, i <= current, i == current)
            for i, status in enumerate(self.STATUS_FLOW)
        ]


class OrderItem(models.Model):
    """سطر بالطلب: منتج × كمية، بسعر واسم مُثبَّتين لحظة الشراء."""

    order = models.ForeignKey(
        Order, verbose_name="الطلب",
        on_delete=models.CASCADE, related_name="items",
    )
    # PROTECT: المنتج المطلوب سابقاً لا يُحذف من الكاتالوج — يُعطَّل فقط
    product = models.ForeignKey(
        "catalog.Product", verbose_name="المنتج",
        on_delete=models.PROTECT, related_name="order_items",
    )
    product_name = models.CharField("اسم المنتج وقت الطلب", max_length=200)
    unit_price = models.DecimalField("سعر القطعة وقت الطلب (ل.س)", max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField("الكمية")

    class Meta:
        verbose_name = "سطر طلب"
        verbose_name_plural = "أسطر الطلب"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def line_total_display(self):
        return f"{self.line_total:,.0f}"

    @property
    def unit_price_display(self):
        return f"{self.unit_price:,.0f}"
