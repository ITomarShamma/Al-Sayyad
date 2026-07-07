"""واجهات السلة — كل عملية تشتغل بطريقتين (تحسين تدريجي):

- طلب HTMX (هيدر HX-Request): نرجّع أجزاء HTML صغيرة تُستبدل بالصفحة
  بدون إعادة تحميل (العدّاد بالهيدر، ومحتوى السلة إن كنّا بصفحتها).
- نموذج عادي بدون JavaScript: نرجّع redirect لصفحة السلة — الموقع
  يبقى شغّالاً بالكامل حتى لو تعطّل الـJS.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders import coupons as coupon_session
from apps.orders.models import CouponError

from .cart import Cart


def _quantity(request, default=1):
    """يقرأ quantity من النموذج بأمان — أي قيمة خاطئة تصير الافتراضي."""
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


def _cart_context(request, coupon_error=None):
    """سياق السلة الموحّد: الكوبون الصالح + الخصم + الإجمالي بعده.

    يُستدعى بكل رندر للسلة — الكوبون يُعاد فحصه لأن السلة تتغيّر
    (نقص المجموع تحت الحد الأدنى مثلاً يسقطه بصمت).
    """
    cart = Cart(request)
    coupon = coupon_session.get_valid_coupon(request.session, cart.total_price)
    discount = coupon.discount_for(cart.total_price) if coupon else 0
    return {
        "coupon": coupon,
        "coupon_error": coupon_error,
        "discount_display": f"{discount:,.0f}",
        "cart_grand_display": f"{cart.total_price - discount:,.0f}",
    }


def detail(request):
    """صفحة السلة الكاملة."""
    return render(request, "cart/cart_detail.html", _cart_context(request))


@require_POST
def add(request, product_id):
    """زر «أضف للسلة» — من بطاقة منتج أو صفحته."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    Cart(request).add(product, _quantity(request))
    if request.headers.get("HX-Request"):
        # الزر يستعمل hx-swap="none" — التحديث كله OOB: العدّادان + توست تأكيد
        return render(request, "cart/partials/added_oob.html")
    return redirect("cart:detail")


@require_POST
def update(request, product_id):
    """تثبيت كمية سطر بالسلة (0 = حذف) — من صفحة السلة."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    Cart(request).set(product, _quantity(request))
    return _cart_page_response(request)


@require_POST
def remove(request, product_id):
    """حذف سطر من السلة."""
    product = get_object_or_404(Product, id=product_id)
    Cart(request).remove(product)
    return _cart_page_response(request)


def _cart_page_response(request, coupon_error=None):
    """HTMX: إعادة رسم محتوى السلة + عدّاد الهيدر. بدون JS: redirect."""
    if request.headers.get("HX-Request"):
        context = {"oob": True} | _cart_context(request, coupon_error)
        return render(request, "cart/partials/cart_body.html", context)
    return redirect("cart:detail")


@require_POST
def apply_coupon(request):
    """تطبيق كود خصم على السلة — التحقق برسائل عربية واضحة."""
    cart = Cart(request)
    error = None
    try:
        coupon_session.apply_coupon(
            request.session, request.POST.get("code", ""), cart.total_price)
    except CouponError as exc:
        error = str(exc)
        if not request.headers.get("HX-Request"):
            messages.error(request, error)
    return _cart_page_response(request, coupon_error=error)


@require_POST
def remove_coupon(request):
    """إزالة الكوبون المطبَّق."""
    coupon_session.clear_coupon(request.session)
    return _cart_page_response(request)
