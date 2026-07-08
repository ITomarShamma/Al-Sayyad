"""فورمات الحسابات: تسجيل جديد، دخول بالموبايل، تعديل البيانات، طلب تاجر."""

from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from apps.core.validators import normalize_digits, syrian_phone

from . import ratelimit
from .models import MerchantProfile

User = get_user_model()


class SignupForm(forms.Form):
    """إنشاء حساب: الاسم + الموبايل (هو اسم الدخول) + كلمة سر مرتين."""

    full_name = forms.CharField(label="الاسم الكامل", max_length=100)
    phone = forms.CharField(label="رقم الموبايل", max_length=15)
    password1 = forms.CharField(label="كلمة السر", widget=forms.PasswordInput)
    password2 = forms.CharField(label="تأكيد كلمة السر", widget=forms.PasswordInput)

    def clean_phone(self):
        phone = normalize_digits(self.cleaned_data["phone"])
        syrian_phone(phone)                       # نفس قاعدة 09xxxxxxxx دائماً
        if User.objects.filter(username=phone).exists():
            raise forms.ValidationError(
                _("في حساب مسجَّل بهالرقم أصلاً — جرّب تسجيل الدخول."))
        return phone

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        password_validation.validate_password(password)   # قواعد Django للقوة
        return password

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("password1") and cleaned.get("password2")
                and cleaned["password1"] != cleaned["password2"]):
            self.add_error("password2", _("كلمتا السر غير متطابقتين."))
        return cleaned


class LoginRateLimitMixin:
    """يحرس أي فورم دخول من التخمين (يُركَّب قبل AuthenticationForm).

    الترتيب بكل محاولة: مقفول؟ ارفض فوراً بلا مصادقة أصلاً.
    فشلت المصادقة؟ سجّل الفشل بالعدّادات ثم مرّر الخطأ.
    نجحت؟ صفّر العدّادات وكمّل.
    """

    def clean(self):
        username = self.cleaned_data.get("username", "")
        request = getattr(self, "request", None)
        remaining = ratelimit.seconds_locked(username, request)
        if remaining:
            minutes = remaining // 60 + 1              # تقريب لفوق: 61 ثانية = دقيقتان
            raise forms.ValidationError(
                gettext("محاولات خاطئة كتير — الدخول مقفول مؤقتاً. "
                        "جرّب بعد %(minutes)d دقيقة.") % {"minutes": minutes})
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            # نعدّ محاولات المصادقة الحقيقية فقط (لا «نسيت تعبّي الحقل»)
            if self.cleaned_data.get("password"):
                ratelimit.register_failure(username, request)
            raise
        ratelimit.reset(username, request)
        return cleaned


class PhoneLoginForm(LoginRateLimitMixin, AuthenticationForm):
    """دخول برقم الموبايل — نطبّع الأرقام الهندية قبل المطابقة."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("رقم الموبايل")
        self.fields["password"].label = _("كلمة السر")
        # رسالة خطأ واحدة مفهومة بدل رسالة Django التقنية
        self.error_messages["invalid_login"] = _(
            "الرقم أو كلمة السر غير صحيحة — تأكد وجرّب مرة ثانية."
        )

    def clean_username(self):
        return normalize_digits(self.cleaned_data.get("username"))


class RateLimitedAdminLoginForm(LoginRateLimitMixin, AdminAuthenticationForm):
    """نفس الحماية على دخول لوحة التحكم — أهم باب يجب أن يُقفل بوجه التخمين."""


class ProfileEditForm(forms.Form):
    """تعديل بيانات الحساب. تغيير الرقم غير متاح ذاتياً (هو اسم الدخول)."""

    full_name = forms.CharField(label="الاسم الكامل", max_length=100)
    city = forms.CharField(label="المحافظة / المدينة", max_length=50, required=False)


class MerchantApplyForm(forms.ModelForm):
    """طلب الانضمام كتاجر — يُراجَع من إدارة المتجر قبل التفعيل."""

    class Meta:
        model = MerchantProfile
        fields = ["store_name", "phone", "city", "description"]

    def clean_phone(self):
        phone = normalize_digits(self.cleaned_data["phone"])
        syrian_phone(phone)
        return phone
