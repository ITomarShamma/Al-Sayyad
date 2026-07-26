"""إنشاء الطلب — منطق العمل الحسّاس بمعزل عن الواجهات (service layer).

لماذا ملف منفصل؟ الواجهة (view) وظيفتها استقبال الطلب وعرض الرد فقط.
تحويل سلة إلى طلب — بقفل المخزون وخصمه وتثبيت الأسعار — منطق عمل
يُختبر لوحده، ويُستدعى مستقبلاً من أي مكان (API موبايل مثلاً) بلا تكرار.
"""

from django.db import transaction
from django.utils.translation import gettext as _

from apps.catalog.models import Product, ProductVariant

from .models import Coupon, Order, OrderItem
from .notifications import notify_new_order


class OutOfStockError(Exception):
    """الكمية المطلوبة لم تعد متوفرة — نخبر الزبون بدل أن نبيع الوهم."""


@transaction.atomic
def create_order_from_cart(cart, order, coupon=None):
    """يحوّل السلة إلى طلب مؤكد: قفل مخزون ← تحقق ← إنشاء ← خصم ← تفريغ.

    transaction.atomic: كل الخطوات تنجح معاً أو تفشل معاً —
    مستحيل يُخصم مخزون بلا طلب، أو يُنشأ طلب بلا خصم.
    """
    items = cart.items()
    if not items:
        raise ValueError("السلة فارغة")

    # 1) قفل صفوف المنتجات والتركيبات حتى نهاية العملية (select_for_update):
    #    لو زبونان طلبا آخر قطعة بنفس اللحظة، أحدهما ينتظر الآخر —
    #    لا بيع مزدوج لنفس القطعة. المخزون الحقيقي للمنتج ذي المقاسات
    #    موجود على التركيبة، فالقفل لازم يشملها هي أيضاً.
    ids = [i["product"].id for i in items]
    locked = Product.objects.select_for_update().filter(id__in=ids, is_active=True)
    products = {p.id: p for p in locked}

    variant_ids = [i["variant"].id for i in items if i["variant"]]
    variants = {}
    if variant_ids:
        variants = {
            v.id: v for v in ProductVariant.objects.select_for_update()
            .filter(id__in=variant_ids, is_active=True)
        }

    # 2) تحقق نهائي من المخزون (قد يكون تغيّر منذ عبّأ الزبون سلته) —
    #    لكل سطر نفحص مخزونه هو: التركيبة إن وُجدت، وإلا المنتج نفسه.
    unavailable = []
    for i in items:
        product = products.get(i["product"].id)
        if product is None:
            unavailable.append(i["product"].name)
            continue
        if i["variant"]:
            variant = variants.get(i["variant"].id)
            if variant is None or variant.stock < i["quantity"]:
                unavailable.append(f"{product.name} ({i['variant'].short_label})")
        elif product.stock < i["quantity"]:
            unavailable.append(product.name)

    if unavailable:
        raise OutOfStockError(
            _("الكمية المتوفرة تغيّرت لهالمنتجات: %(names)s — حدّث سلتك وجرّب مرة ثانية.")
            % {"names": "، ".join(unavailable)}
        )

    items_total = sum(i["line_total"] for i in items)

    # 3) الكوبون — تحقق نهائي تحت قفل صف الكوبون نفسه: كوبون محدود
    #    الاستخدام لا يمكن أن يُصرف أكثر من حدّه حتى بطلبين متزامنين.
    discount = 0
    if coupon is not None:
        locked_coupon = Coupon.objects.select_for_update().get(pk=coupon.pk)
        locked_coupon.ensure_valid(items_total)        # يرمي CouponError
        discount = locked_coupon.discount_for(items_total)
        order.coupon_code = locked_coupon.code         # لقطة
        order.discount_amount = discount
        locked_coupon.used_count += 1                  # حجز الاستخدام
        locked_coupon.save(update_fields=["used_count", "updated_at"])

    # 4) إنشاء الطلب وأسطره — الاسم والسعر لقطة لحظة الشراء
    # الإجمالي = المنتجات − الخصم + رسم التوصيل (NULL = يُتفق هاتفياً)
    order.total = items_total - discount + (order.delivery_fee or 0)
    order.save()
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=products[i["product"].id],
            variant=variants.get(i["variant"].id) if i["variant"] else None,
            product_name=i["product"].name,
            # لقطة التركيبة نصاً — تبقى مقروءة حتى لو تغيّرت المقاسات لاحقاً
            variant_label=i["variant"].label if i["variant"] else "",
            # سعر السطر كما حُسب بالسلة: سعر التركيبة الخاص إن وُجد
            unit_price=i["unit_price"],
            quantity=i["quantity"],
        )
        for i in items
    )

    # 5) خصم المخزون من مكانه الصحيح: التركيبة أو المنتج.
    #    حفظ التركيبة يعيد جمع مخزون المنتج تلقائياً (sync_stock).
    for i in items:
        if i["variant"]:
            variant = variants[i["variant"].id]
            variant.stock -= i["quantity"]
            variant.save(update_fields=["stock"])
        else:
            product = products[i["product"].id]
            product.stock -= i["quantity"]
            product.save(update_fields=["stock"])

    # 6) تفريغ السلة — الطلب صار هو السجل الرسمي
    cart.clear()

    # 7) إشعار المالك — on_commit: يُرسل فقط بعد نجاح الحفظ الفعلي بالقاعدة.
    #    لو فشلت المعاملة وانعمل rollback، لا يخرج أي إشعار كاذب.
    transaction.on_commit(lambda: notify_new_order(order))
    return order
