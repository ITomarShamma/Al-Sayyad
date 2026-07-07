"""إشعارات الطلبات — بريد للمالك عند كل طلب جديد + رسالة واتساب للزبون.

قاعدتان صارمتان:
1. الإشعار لا يكسر الطلب أبداً: fail_silently — انقطاع البريد مشكلة
   ثانوية، ضياع الطلب كارثة.
2. يُرسل بعد نجاح الحفظ فعلياً (transaction.on_commit من services) —
   لا إشعار عن طلب انعمل له rollback.
"""

from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail


def _delivery_line(order):
    if order.delivery_fee is None:
        return "يُتفق هاتفياً"
    if order.delivery_fee == 0:
        return "مجاني"
    return f"{order.delivery_fee_display} ل.س"


def notify_new_order(order):
    """بريد فوري لصاحب المتجر بتفاصيل الطلب — إن كان بريد الإشعارات مضبوطاً."""
    recipient = settings.ORDER_NOTIFICATION_EMAIL
    if not recipient:
        return

    items = "\n".join(
        f"  • {item.product_name} × {item.quantity} = {item.line_total_display} ل.س"
        for item in order.items.all()
    )
    body = (
        f"طلب جديد عالصَّيَّاد 🎣\n"
        f"\n"
        f"رقم الطلب: {order.number}\n"
        f"الزبون: {order.customer_name}\n"
        f"الموبايل: {order.phone}\n"
        f"المحافظة: {order.city}\n"
        f"العنوان: {order.address}\n"
        f"الدفع: {order.get_payment_method_display()}\n"
        f"\n"
        f"المنتجات:\n{items}\n"
        f"\n"
        + (f"الخصم ({order.coupon_code}): -{order.discount_amount_display} ل.س\n"
           if order.discount_amount else "")
        + f"التوصيل: {_delivery_line(order)}\n"
        f"الإجمالي: {order.total_display} ل.س\n"
        f"\n"
        f"لوحة التحكم: /admin/orders/order/\n"
    )
    send_mail(
        subject=f"🛒 طلب جديد {order.number} — {order.total_display} ل.س",
        message=body,
        from_email=None,                  # DEFAULT_FROM_EMAIL
        recipient_list=[recipient],
        fail_silently=True,               # البريد لا يُفشل الطلب أبداً
    )


def customer_whatsapp_url(order):
    """رابط wa.me لمراسلة الزبون برسالة معبّأة — لزر «راسل الزبون» باللوحة."""
    international = "963" + order.phone[1:]        # 09xxxxxxxx ← 9639xxxxxxxx
    message = (
        f"مرحباً {order.customer_name} 👋\n"
        f"معك متجر الصَّيَّاد بخصوص طلبك رقم {order.number} "
        f"(الإجمالي {order.total_display} ل.س)."
    )
    return f"https://wa.me/{international}?text={quote(message)}"
