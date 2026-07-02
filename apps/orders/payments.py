"""طرق الدفع المتاحة — نقطة الوصل الوحيدة لإضافة شام كاش لاحقاً.

اليوم: الدفع عند الاستلام فقط.
عند وصول API شام كاش: أضف "shamcash" للقائمة أدناه واكتب بوابة الدفع
هنا — الفورم وصفحة الدفع يلتقطون التغيير تلقائياً بدون تعديل بمكان آخر.
"""

from .models import Order

# الطرق المفعّلة حالياً (مفتاح من Order.PaymentMethod)
ENABLED_METHODS = [Order.PaymentMethod.COD]


def available_payment_choices():
    """خيارات الدفع للفورم: [(القيمة، التسمية)، …] — المفعّلة فقط."""
    return [(m.value, m.label) for m in ENABLED_METHODS]


# ---------------------------------------------------------------------------
# بوابة شام كاش (هيكل جاهز — يُملأ عند استلام الـAPI والتوثيق)
# ---------------------------------------------------------------------------
# class ShamCashGateway:
#     """تُنشئ عملية دفع لدى شام كاش وتتحقق من نتيجتها."""
#
#     def __init__(self):
#         self.api_key = os.environ["SHAMCASH_API_KEY"]   # من .env
#
#     def start_payment(self, order):  # يرجع رابط/رمز الدفع
#         raise NotImplementedError
#
#     def verify_payment(self, order, payload):  # يتحقق من الإشعار
#         raise NotImplementedError
