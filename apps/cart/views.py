"""واجهات السلة — كل عملية تشتغل بطريقتين (تحسين تدريجي):

- طلب HTMX (هيدر HX-Request): نرجّع أجزاء HTML صغيرة تُستبدل بالصفحة
  بدون إعادة تحميل (العدّاد بالهيدر، ومحتوى السلة إن كنّا بصفحتها).
- نموذج عادي بدون JavaScript: نرجّع redirect لصفحة السلة — الموقع
  يبقى شغّالاً بالكامل حتى لو تعطّل الـJS.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.catalog.models import Product, ProductVariant
from apps.orders import coupons as coupon_session
from apps.orders.models import CouponError

from .cart import Cart


def _quantity(request, default=1):
    """يقرأ quantity من النموذج بأمان — أي قيمة خاطئة تصير الافتراضي."""
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


def _selected_variant(request, product):
    """يحسم التركيبة المطلوبة (المقاس/اللون) من بيانات النموذج.

    يرجع (variant, error):
      - منتج بلا خيارات      → (None, None)
      - اختيار مكتمل ومتوفر  → (variant, None)
      - ناقص/غير موجود/نافد  → (None, رسالة عربية للزبون)

    الحسم هنا بالسيرفر عمداً: صفحة المنتج تعمل بلا جافاسكربت، ولا نثق
    بما يصل من المتصفّح — الرقم المرسل قد يكون لمنتج آخر أو لتركيبة نفدت.
    """
    if not product.has_variants:
        return None, None

    # صيغتان مقبولتان: أزرار الخيارات (option_<id>) أو رقم متغيّر صريح
    value_ids = [v for key, v in request.POST.items() if key.startswith("option_")]
    if value_ids:
        variant = product.resolve_variant(value_ids)
    else:
        variant = product.variants.filter(
            pk=request.POST.get("variant") or None, is_active=True).first()

    if variant is None:
        return None, _("اختر المقاس/اللون أولاً — بعدين ضيف للسلة.")
    if variant.stock <= 0:
        return None, _("هذه التركيبة نفدت — جرّب مقاساً أو لوناً غيره.")
    return variant, None


def _variant_from_post(request, product):
    """متغيّر سطر السلة عند التعديل/الحذف — من الحقل المخفي بالنموذج."""
    variant_id = request.POST.get("variant") or 0
    try:
        variant_id = int(variant_id)
    except (TypeError, ValueError):
        return None
    if not variant_id:
        return None
    return ProductVariant.objects.filter(pk=variant_id, product=product).first()


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
    """زر «أضف للسلة» — من بطاقة منتج أو صفحته (مع المقاس/اللون إن وُجد)."""
    product = get_object_or_404(
        Product.objects.prefetch_related("options"), id=product_id, is_active=True)

    variant, error = _selected_variant(request, product)
    if error:
        # ما منضيف شي غامض للسلة: نوقف ونقول للزبون شو ناقص (القاعدة #5)
        if request.headers.get("HX-Request"):
            return render(request, "cart/partials/add_error_oob.html",
                          {"error": error}, status=422)
        messages.error(request, error)
        return redirect(product.get_absolute_url())

    Cart(request).add(product, _quantity(request), variant=variant)
    if request.headers.get("HX-Request"):
        # الزر يستعمل hx-swap="none" — التحديث كله OOB: العدّادان + توست تأكيد
        return render(request, "cart/partials/added_oob.html", {"variant": variant})
    return redirect("cart:detail")


@require_POST
def update(request, product_id):
    """تثبيت كمية سطر بالسلة (0 = حذف) — من صفحة السلة."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    Cart(request).set(product, _quantity(request),
                      variant=_variant_from_post(request, product))
    return _cart_page_response(request)


@require_POST
def remove(request, product_id):
    """حذف سطر من السلة."""
    product = get_object_or_404(Product, id=product_id)
    Cart(request).remove(product, variant=_variant_from_post(request, product))
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
