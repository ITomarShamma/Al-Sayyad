"""إنشاء الطلب — منطق العمل الحسّاس بمعزل عن الواجهات (service layer).

لماذا ملف منفصل؟ الواجهة (view) وظيفتها استقبال الطلب وعرض الرد فقط.
تحويل سلة إلى طلب — بقفل المخزون وخصمه وتثبيت الأسعار — منطق عمل
يُختبر لوحده، ويُستدعى مستقبلاً من أي مكان (API موبايل مثلاً) بلا تكرار.
"""

from django.db import transaction
from django.utils.translation import gettext as _

from apps.catalog.models import Product

from .models import Order, OrderItem


class OutOfStockError(Exception):
    """الكمية المطلوبة لم تعد متوفرة — نخبر الزبون بدل أن نبيع الوهم."""


@transaction.atomic
def create_order_from_cart(cart, order):
    """يحوّل السلة إلى طلب مؤكد: قفل مخزون ← تحقق ← إنشاء ← خصم ← تفريغ.

    transaction.atomic: كل الخطوات تنجح معاً أو تفشل معاً —
    مستحيل يُخصم مخزون بلا طلب، أو يُنشأ طلب بلا خصم.
    """
    items = cart.items()
    if not items:
        raise ValueError("السلة فارغة")

    # 1) قفل صفوف المنتجات حتى نهاية العملية (select_for_update):
    #    لو زبونان طلبا آخر قطعة بنفس اللحظة، أحدهما ينتظر الآخر —
    #    لا بيع مزدوج لنفس القطعة.
    ids = [i["product"].id for i in items]
    locked = Product.objects.select_for_update().filter(id__in=ids, is_active=True)
    products = {p.id: p for p in locked}

    # 2) تحقق نهائي من المخزون (قد يكون تغيّر منذ عبّأ الزبون سلته)
    unavailable = [
        i["product"].name
        for i in items
        if i["product"].id not in products
        or products[i["product"].id].stock < i["quantity"]
    ]
    if unavailable:
        raise OutOfStockError(
            _("الكمية المتوفرة تغيّرت لهالمنتجات: %(names)s — حدّث سلتك وجرّب مرة ثانية.")
            % {"names": "، ".join(unavailable)}
        )

    # 3) إنشاء الطلب وأسطره — الاسم والسعر لقطة لحظة الشراء
    # الإجمالي = المنتجات + رسم التوصيل (إن كان محدداً؛ NULL = يُتفق هاتفياً)
    order.total = sum(i["line_total"] for i in items) + (order.delivery_fee or 0)
    order.save()
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=products[i["product"].id],
            product_name=i["product"].name,
            unit_price=i["product"].price,
            quantity=i["quantity"],
        )
        for i in items
    )

    # 4) خصم المخزون
    for i in items:
        p = products[i["product"].id]
        p.stock -= i["quantity"]
        p.save(update_fields=["stock"])

    # 5) تفريغ السلة — الطلب صار هو السجل الرسمي
    cart.clear()
    return order
