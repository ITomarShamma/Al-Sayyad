"""فورم إتمام الطلب — التحقق كلّه هنا، بالسيرفر، حيث لا يمكن تجاوزه."""

from django import forms

from apps.core.validators import normalize_digits

from .models import Order
from .payments import available_payment_choices


class TrackOrderForm(forms.Form):
    """فورم «وين طلبي؟» — رقم الطلب + الموبايل معاً (الموبايل بمثابة كلمة سر)."""

    number = forms.CharField(label="رقم الطلب", max_length=12)
    phone = forms.CharField(label="رقم الموبايل", max_length=15)

    def clean_number(self):
        return normalize_digits(self.cleaned_data["number"])

    def clean_phone(self):
        return normalize_digits(self.cleaned_data["phone"])


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer_name", "phone", "city", "address", "notes", "payment_method"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # طرق الدفع المفعّلة فقط (شام كاش ينضاف من payments.py لاحقاً)
        self.fields["payment_method"].widget = forms.RadioSelect()
        self.fields["payment_method"].choices = available_payment_choices()
        self.fields["payment_method"].initial = Order.PaymentMethod.COD

    def clean_phone(self):
        """يطبّع الأرقام الهندية قبل تحقق النمط 09xxxxxxxx."""
        phone = normalize_digits(self.cleaned_data["phone"])
        # نعيد تشغيل مدقّق الموديل يدوياً لأننا عدّلنا القيمة
        for validator in self._meta.model._meta.get_field("phone").validators:
            validator(phone)
        return phone
