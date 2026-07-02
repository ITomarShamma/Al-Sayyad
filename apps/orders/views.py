"""واجهات الطلب: صفحة إتمام الطلب + صفحة التأكيد."""

from django.shortcuts import get_object_or_404, redirect, render

from apps.cart.cart import Cart

from .forms import CheckoutForm
from .models import Order
from .services import OutOfStockError, create_order_from_cart


def checkout(request):
    """إتمام الطلب: فورم بيانات الزبون + ملخص السلة.

    نمط PRG (Post/Redirect/Get): بعد نجاح الإنشاء نعمل redirect —
    لو ضغط الزبون تحديث بصفحة التأكيد ما ينعمل الطلب مرتين.
    """
    cart = Cart(request)
    if cart.total_quantity == 0:
        return redirect("cart:detail")    # ما في شي يُطلب

    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)   # طلب مُعبَّأ، لسا ما انحفظ
        try:
            create_order_from_cart(cart, order)
        except OutOfStockError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect("orders:confirmation", number=order.number)

    return render(request, "orders/checkout.html", {"form": form})


def confirmation(request, number):
    """صفحة الشكر — رقم الطلب وملخصه وما الذي سيحدث الآن."""
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    return render(request, "orders/confirmation.html", {"order": order})
