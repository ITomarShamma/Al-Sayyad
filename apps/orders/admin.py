"""لوحة تحكم الطلبات — متابعة الطلبات وتغيير حالتها من الجدول مباشرة."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem

# لون كل حالة — نفس ألوان الهوية الدلالية
STATUS_COLORS = {
    Order.Status.PENDING: "#E8A317",     # بانتظار التأكيد — تنبيه
    Order.Status.CONFIRMED: "#2D6FB3",   # مؤكّد — معلومة
    Order.Status.SHIPPED: "#0E6B5E",     # قيد التوصيل — أساسي
    Order.Status.DELIVERED: "#2E9E54",   # مُسلَّم — نجاح
    Order.Status.CANCELLED: "#D5402B",   # ملغى — خطأ
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
    list_display = ("number", "status_display", "customer_name", "phone", "city",
                    "total_syp", "payment_method", "status", "created_at")
    list_editable = ("status",)          # غيّر حالة الطلب من الجدول مباشرة
    list_filter = ("status", "payment_method", "city", "created_at")
    search_fields = ("number", "customer_name", "phone")
    date_hierarchy = "created_at"        # تنقّل سنة ← شهر ← يوم فوق الجدول
    list_per_page = 50

    @admin.display(description="الحالة", ordering="status")
    def status_display(self, obj):
        color = STATUS_COLORS.get(obj.status, "#5B6B64")
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
