"""لوحة تحكم الطلبات — متابعة الطلبات وتغيير حالتها من الجدول مباشرة."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Coupon, DeliveryZone, Order, OrderItem
from .notifications import customer_whatsapp_url


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """الكوبونات — أنشئ كوداً وحدّد نوعه وقيوده."""

    list_display = ("code", "kind", "value", "state", "used_count",
                    "usage_limit", "min_order_total", "expires_at", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code",)
    readonly_fields = ("used_count", "created_at", "updated_at")

    @admin.display(description="الحالة")
    def state(self, obj):
        from django.utils import timezone
        if not obj.is_active:
            return format_html('<b style="color:#51637A;">● موقوف</b>')
        if obj.expires_at and obj.expires_at < timezone.now():
            return format_html('<b style="color:#D93526;">● منتهي</b>')
        if obj.usage_limit is not None and obj.used_count >= obj.usage_limit:
            return format_html('<b style="color:#B45309;">● استُنفد</b>')
        return format_html('<b style="color:#15803D;">● فعّال</b>')


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    """رسوم التوصيل حسب المحافظة — عدّلها من الجدول مباشرة."""

    list_display = ("name", "fee_state", "fee", "is_active", "sort_order")
    list_editable = ("fee", "is_active", "sort_order")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="الحالة")
    def fee_state(self, obj):
        if obj.fee is None:
            return format_html('<b style="color:#B45309;">● يُتفق هاتفياً</b>')
        if obj.fee == 0:
            return format_html('<b style="color:#15803D;">● توصيل مجاني</b>')
        return format_html('<span style="color:#0F62B0;">● {} ل.س</span>', obj.fee_display)

# لون كل حالة — نفس ألوان الهوية الدلالية
STATUS_COLORS = {
    Order.Status.PENDING: "#B45309",     # بانتظار التأكيد — تنبيه
    Order.Status.CONFIRMED: "#1D6FC2",   # مؤكّد — معلومة
    Order.Status.SHIPPED: "#0F62B0",     # قيد التوصيل — أساسي
    Order.Status.DELIVERED: "#15803D",   # مُسلَّم — نجاح
    Order.Status.CANCELLED: "#D93526",   # ملغى — خطأ
}


class OrderItemInline(admin.TabularInline):
    """أسطر الطلب تظهر داخل صفحته — للقراءة فقط، الفاتورة لا تُعدَّل."""

    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total_display")

    @admin.display(description="إجمالي السطر")
    def line_total_display(self, obj):
        return f"{obj.line_total:,.0f} ل.س"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "status_display", "customer_name", "phone",
                    "whatsapp_link", "city", "total_syp", "payment_method",
                    "status", "created_at")
    list_editable = ("status",)          # غيّر حالة الطلب من الجدول مباشرة
    list_filter = ("status", "payment_method", "city", "created_at")
    search_fields = ("number", "customer_name", "phone")
    date_hierarchy = "created_at"        # تنقّل سنة ← شهر ← يوم فوق الجدول
    list_per_page = 50

    @admin.display(description="الحالة", ordering="status")
    def status_display(self, obj):
        color = STATUS_COLORS.get(obj.status, "#51637A")
        return format_html('<b style="color:{};">● {}</b>', color, obj.get_status_display())
    inlines = [OrderItemInline]
    readonly_fields = ("number", "total", "created_at", "updated_at")
    fieldsets = (
        ("الطلب", {"fields": ("number", "status", "payment_method", "total")}),
        ("الزبون", {"fields": ("customer_name", "phone", "city", "address", "notes")}),
        ("سجلّ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="الإجمالي", ordering="total")
    def total_syp(self, obj):
        return f"{obj.total:,.0f} ل.س"

    @admin.display(description="واتساب")
    def whatsapp_link(self, obj):
        """زر مراسلة الزبون برسالة معبّأة برقم طلبه — سير عملك الهاتفي اليومي."""
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">💬 راسل الزبون</a>',
            customer_whatsapp_url(obj),
        )
