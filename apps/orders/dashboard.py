"""لوحة مبيعات المتجر — أرقام اليوم والأسبوع والشهر بنظرة واحدة.

تعريف «المبيعات» هنا: كل الطلبات غير الملغاة (الملغى وحده يسقط من
الأرقام). جدول الحالات جنباً يبيّن كم منها مُسلَّم فعلاً وكم بالطريق.

الأرقام كلها تُنسَّق نصاً بالسيرفر (f"{...:,.0f}") — درس M24: القالب
تحت اللغة العربية يطبع 4.0 كـ«٤٫٠» ويكسر الأرقام المالية.
"""

from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from apps.catalog.models import Product

from .admin import STATUS_COLORS
from .models import Order, OrderItem

LOW_STOCK_THRESHOLD = 3     # «شارف على النفاد» — نفس عتبة فلتر اللوحة
TOP_PRODUCTS_DAYS = 30      # نافذة «الأكثر مبيعاً»
CHART_DAYS = 14             # أعمدة مخطط المبيعات اليومية


def fmt(amount):
    """تنسيق مبلغ للعرض: فواصل آلاف وبلا كسور. None = صفر."""
    return f"{amount or 0:,.0f}"


def orders_count_display(n):
    """جمع «طلب» على قواعد العربية: طلب، طلبان، 3 طلبات، 11 طلباً."""
    if n == 0:
        return "بلا طلبات"
    if n == 1:
        return "طلب واحد"
    if n == 2:
        return "طلبان"
    if n <= 10:
        return f"{n} طلبات"
    return f"{n} طلباً"


def _sales(orders):
    """عدد وقيمة المبيعات لمجموعة طلبات (غير الملغاة فقط)."""
    agg = orders.exclude(status=Order.Status.CANCELLED).aggregate(
        count=Count("id"), revenue=Sum("total"))
    return {"count_display": orders_count_display(agg["count"] or 0),
            "revenue": fmt(agg["revenue"])}


def _period_cards(orders, today):
    return [
        ("اليوم", _sales(orders.filter(created_at__date=today))),
        ("آخر 7 أيام",
         _sales(orders.filter(created_at__date__gte=today - timedelta(days=6)))),
        ("هذا الشهر",
         _sales(orders.filter(created_at__date__gte=today.replace(day=1)))),
        ("منذ البداية", _sales(orders)),
    ]


def _status_rows(orders):
    """صف لكل حالة (حتى الصفرية) بترتيب مسار الطلب — بألوان اللوحة نفسها."""
    raw = {
        row["status"]: row
        for row in orders.values("status").annotate(count=Count("id"),
                                                    revenue=Sum("total"))
    }
    rows = []
    for status in Order.Status:
        row = raw.get(status.value, {})
        rows.append({
            "label": status.label,
            "color": STATUS_COLORS.get(status, "#51637A"),
            "count": row.get("count", 0),
            "revenue": fmt(row.get("revenue")),
        })
    return rows


def _daily_chart(orders, today):
    """عمود لكل يوم من آخر CHART_DAYS يوماً — الأيام بلا طلبات تظهر صفراً."""
    since = today - timedelta(days=CHART_DAYS - 1)
    raw = {
        row["day"]: row
        for row in orders.exclude(status=Order.Status.CANCELLED)
        .filter(created_at__date__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day").annotate(count=Count("id"), revenue=Sum("total"))
    }
    days, peak = [], 0
    for i in range(CHART_DAYS):
        date = since + timedelta(days=i)
        row = raw.get(date, {})
        revenue = row.get("revenue") or 0
        peak = max(peak, revenue)
        days.append({
            "label": f"{date.day}/{date.month}",
            "count": row.get("count", 0),
            "amount": revenue,
            "revenue": fmt(revenue),
        })
    for day in days:   # ارتفاع العمود نسبةً لأعلى يوم (القسمة بعد معرفة الذروة)
        day["bar"] = int(day["amount"] / peak * 100) if peak else 0
    return days


def _top_products(today):
    """الأكثر مبيعاً (آخر 30 يوماً) من لقطات أسطر الطلبات — الاسم وقت
    الشراء، فلا يتأثر بتعديل الكاتالوج ويشمل المنتجات المعطَّلة لاحقاً."""
    since = today - timedelta(days=TOP_PRODUCTS_DAYS - 1)
    rows = list(
        OrderItem.objects
        .filter(order__created_at__date__gte=since)
        .exclude(order__status=Order.Status.CANCELLED)
        .values("product_name")
        .annotate(qty=Sum("quantity"),
                  revenue=Sum(F("unit_price") * F("quantity"),
                              output_field=DecimalField(max_digits=14,
                                                        decimal_places=0)))
        .order_by("-qty")[:10]
    )
    peak = max((row["qty"] for row in rows), default=0)
    for row in rows:
        row["bar"] = int(row["qty"] / peak * 100) if peak else 0
        row["revenue"] = fmt(row["revenue"])
    return rows


@staff_member_required
def sales_dashboard(request):
    """اللوحة نفسها — لمن يملك صلاحية عرض الطلبات (لا للتجّار)."""
    if not request.user.has_perm("orders.view_order"):
        raise PermissionDenied
    today = timezone.localdate()
    orders = Order.objects.all()
    context = {
        **admin.site.each_context(request),   # سياق اللوحة: الهيدر والقائمة…
        "title": "لوحة المبيعات",
        "cards": _period_cards(orders, today),
        "days": _daily_chart(orders, today),
        "statuses": _status_rows(orders),
        "top_products": _top_products(today),
        "low_stock": Product.objects.filter(
            is_active=True, stock__lte=LOW_STOCK_THRESHOLD).order_by("stock")[:10],
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
    }
    return render(request, "admin/dashboard.html", context)
