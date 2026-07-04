"""حسابات المستخدمين: الملف الشخصي والأدوار.

لماذا Profile منفصل وليس User مخصص؟ نموذج المستخدم المخصص يُختار عند
بداية المشروع فقط — تبديله الآن يعني جراحة هجرات خطرة على بيانات قائمة.
النمط المعتمد: نموذج User القياسي + Profile واحد-لواحد يحمل ما نضيفه.
(الزائر Guest ليس صفاً هنا أصلاً: هو ببساطة طلب بلا user — انظر Order.user)
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.core.validators import syrian_phone


class Profile(TimeStampedModel):
    """بيانات إضافية لكل مستخدم مسجَّل + دوره بالمنصة."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", _("زبون")
        MERCHANT = "merchant", _("تاجر")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="المستخدم",
        on_delete=models.CASCADE, related_name="profile",
    )
    role = models.CharField(
        "الدور", max_length=10,
        choices=Role.choices, default=Role.CUSTOMER,
    )
    # اسم المستخدم (username) هو رقم الموبايل — هذا الحقل نسخة عرض/تواصل
    phone = models.CharField("رقم الموبايل", max_length=10, validators=[syrian_phone])
    city = models.CharField("المحافظة / المدينة", max_length=50, blank=True)

    class Meta:
        verbose_name = "ملف شخصي"
        verbose_name_plural = "الملفات الشخصية"

    def __str__(self):
        return f"{self.user.first_name or self.user.username} ({self.get_role_display()})"


class MerchantProfile(TimeStampedModel):
    """طلب/ملف تاجر — شركة أو صاحب متجر يبيع عبر المنصة.

    ينشأ «قيد المراجعة» (is_approved=False)؛ الموافقة تتم من لوحة التحكم
    (انظر admin: الإجراء يمنح صلاحيات مجموعة «تاجر» ويفعّل دخوله للوحة).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="المستخدم",
        on_delete=models.CASCADE, related_name="merchant_profile",
    )
    store_name = models.CharField("اسم المتجر", max_length=100, unique=True)
    phone = models.CharField("موبايل التواصل", max_length=10, validators=[syrian_phone])
    city = models.CharField("المحافظة / المدينة", max_length=50)
    description = models.TextField(
        "عن المتجر", blank=True,
        help_text="شو بتبيعوا؟ من متى وأنتم شغالين؟",
    )
    is_approved = models.BooleanField(
        "مقبول", default=False,
        help_text="لا يستطيع التاجر إدارة منتجاته قبل الموافقة.",
    )

    class Meta:
        verbose_name = "تاجر"
        verbose_name_plural = "التجار"
        ordering = ["is_approved", "-created_at"]   # المعلّقة أولاً

    def __str__(self):
        state = "✓" if self.is_approved else "قيد المراجعة"
        return f"{self.store_name} ({state})"
