"""فورم إتمام الطلب — التحقق كلّه هنا، بالسيرفر، حيث لا يمكن تجاوزه."""

from django import forms

from .models import Order
from .payments import available_payment_choices

# المستخدم السوري كثيراً ما يكتب الأرقام بالهندية (٠٩…) — نطبّعها لأسكي
ARABIC_TO_ASCII_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


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
        """يطبّع الأرقام الهندية ويشيل الفراغات قبل تحقق النمط 09xxxxxxxx."""
        phone = (self.cleaned_data["phone"] or "").strip().replace(" ", "")
        phone = phone.translate(ARABIC_TO_ASCII_DIGITS)
        # نعيد تشغيل مدقّق الموديل يدوياً لأننا عدّلنا القيمة
        for validator in self._meta.model._meta.get_field("phone").validators:
            validator(phone)
        return phone
