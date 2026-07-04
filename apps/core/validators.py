"""مدقّقات وأدوات إدخال مشتركة بين كل التطبيقات."""

from django.core.validators import RegexValidator

# رقم موبايل سوري: 09 يتبعها 8 أرقام
syrian_phone = RegexValidator(
    r"^09\d{8}$", "أدخل رقم موبايل سوري صحيح: 09 يتبعها 8 أرقام."
)

# المستخدم السوري كثيراً ما يكتب الأرقام بالهندية (٠٩…) — نطبّعها لأسكي
ARABIC_TO_ASCII_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_digits(value):
    """يطبّع الأرقام الهندية ويشيل الفراغات — لأي حقل رقمي يدخله المستخدم."""
    return (value or "").strip().replace(" ", "").translate(ARABIC_TO_ASCII_DIGITS)
