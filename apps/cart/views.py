"""واجهات السلة — كل عملية تشتغل بطريقتين (تحسين تدريجي):

- طلب HTMX (هيدر HX-Request): نرجّع أجزاء HTML صغيرة تُستبدل بالصفحة
  بدون إعادة تحميل (العدّاد بالهيدر، ومحتوى السلة إن كنّا بصفحتها).
- نموذج عادي بدون JavaScript: نرجّع redirect لصفحة السلة — الموقع
  يبقى شغّالاً بالكامل حتى لو تعطّل الـJS.
"""

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product

from .cart import Cart


def _quantity(request, default=1):
    """يقرأ quantity من النموذج بأمان — أي قيمة خاطئة تصير الافتراضي."""
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


def detail(request):
    """صفحة السلة الكاملة."""
    return render(request, "cart/cart_detail.html")


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


def _cart_page_response(request):
    """HTMX: إعادة رسم محتوى السلة + عدّاد الهيدر. بدون JS: redirect."""
    if request.headers.get("HX-Request"):
        return render(request, "cart/partials/cart_body.html", {"oob": True})
    return redirect("cart:detail")
