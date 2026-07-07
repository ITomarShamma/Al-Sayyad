"""واجهات الطلب: صفحة إتمام الطلب + صفحة التأكيد."""

from django import forms
from django.shortcuts import get_object_or_404, redirect, render

from apps.cart.cart import Cart

from . import coupons as coupon_session
from .forms import CheckoutForm, TrackOrderForm
from .models import Coupon, CouponError, DeliveryZone, Order
from .services import OutOfStockError, create_order_from_cart


def _summary_context(request, zone):
    """سياق ملخص الطلب: المنتجات − الخصم + رسم المنطقة = الإجمالي الكلي."""
    cart = Cart(request)
    coupon = coupon_session.get_valid_coupon(request.session, cart.total_price)
    discount = coupon.discount_for(cart.total_price) if coupon else 0
    grand = cart.total_price - discount + ((zone.fee or 0) if zone else 0)
    return {
        "cart": cart,
        "zone": zone,
        "coupon": coupon,
        "discount_display": f"{discount:,.0f}",
        "grand_total_display": f"{grand:,.0f}",
    }


def checkout(request):
    """إتمام الطلب: فورم بيانات الزبون + ملخص السلة.

    نمط PRG (Post/Redirect/Get): بعد نجاح الإنشاء نعمل redirect —
    لو ضغط الزبون تحديث بصفحة التأكيد ما ينعمل الطلب مرتين.
    """
    cart = Cart(request)
    if cart.total_quantity == 0:
        return redirect("cart:detail")    # ما في شي يُطلب

    # الزبون المسجَّل: نعبّي له بياناته مسبقاً — يأكد ويمشي
    initial = {}
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        initial = {
            "customer_name": request.user.first_name,
            "phone": profile.phone if profile else request.user.username,
        }
        if profile and profile.city:      # مدينته المحفوظة تختار منطقتها
            initial["zone"] = DeliveryZone.objects.filter(
                name=profile.city, is_active=True).first()

    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)   # طلب مُعبَّأ، لسا ما انحفظ
        # لقطة منطقة التوصيل: الاسم والرسم كما هما لحظة الطلب —
        # تغيير الرسوم لاحقاً لا يلمس الطلبات القديمة (نفس فلسفة الأسعار)
        zone = form.cleaned_data["zone"]
        order.city = zone.name
        order.delivery_fee = zone.fee
        if request.user.is_authenticated:
            order.user = request.user     # يظهر بـ«حسابي»؛ الزائر يبقى بلا user
        # الكوبون يُقرأ خاماً هنا (لا get_valid_coupon الصامتة): لو صار
        # غير صالح لازم *نوقف* ونخبر الزبون — لا نسحب الخصم بصمت ونفوّت
        # عليه طلباً بسعر ما توقعه (القاعدة #5: أظهر الحالة دايماً).
        coupon = None
        session_code = request.session.get(coupon_session.SESSION_KEY)
        if session_code:
            coupon = Coupon.objects.filter(code=session_code).first()
            if coupon is None:                             # كود انحذف من النظام
                coupon_session.clear_coupon(request.session)
        try:
            create_order_from_cart(cart, order, coupon=coupon)
        except OutOfStockError as exc:
            form.add_error(None, str(exc))
        except CouponError as exc:
            form.add_error(None, str(exc))
            coupon_session.clear_coupon(request.session)   # أُخبر الزبون؛ نزيله
        else:
            coupon_session.clear_coupon(request.session)   # الكوبون صار لقطة عالطلب
            return redirect("orders:confirmation", number=order.number)

    selected_zone = None
    if form.is_bound:
        try:
            selected_zone = form.fields["zone"].clean(form.data.get("zone"))
        except forms.ValidationError:
            selected_zone = None
    elif initial.get("zone"):
        selected_zone = initial["zone"]

    context = {"form": form} | _summary_context(request, selected_zone)
    return render(request, "orders/checkout.html", context)


def checkout_summary(request):
    """ردّ HTMX: إعادة رسم ملخص الطلب عند تغيير المحافظة (بلا إعادة تحميل)."""
    zone = DeliveryZone.objects.filter(
        pk=request.GET.get("zone") or None, is_active=True).first()
    return render(request, "orders/partials/checkout_summary.html",
                  _summary_context(request, zone))


def confirmation(request, number):
    """صفحة الشكر — رقم الطلب وملخصه وما الذي سيحدث الآن."""
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    return render(request, "orders/confirmation.html", {"order": order})


def track(request):
    """«وين طلبي؟» — بحث برقم الطلب + الموبايل (لازم يتطابقا معاً).

    GET وليس POST: البحث لا يغيّر شيئاً، والرابط يبقى قابلاً للمشاركة
    وإعادة التحميل بأمان.
    """
    order = None
    searched = False
    form = TrackOrderForm(request.GET or None)

    if form.is_bound and form.is_valid():
        searched = True
        order = (
            Order.objects.prefetch_related("items")
            .filter(number=form.cleaned_data["number"],
                    phone=form.cleaned_data["phone"])
            .first()                      # None إن لم يتطابق الاثنان معاً
        )

    return render(request, "orders/track.html", {
        "form": form,
        "order": order,
        "searched": searched,
    })
