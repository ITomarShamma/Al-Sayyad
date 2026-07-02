"""لوحة تحكم الطلبات — متابعة الطلبات وتغيير حالتها من الجدول مباشرة."""

from django.contrib import admin

from .models import Order, OrderItem


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
    list_display = ("number", "customer_name", "phone", "city",
                    "total_syp", "payment_method", "status", "created_at")
    list_editable = ("status",)          # غيّر حالة الطلب من الجدول مباشرة
    list_filter = ("status", "payment_method", "city", "created_at")
    search_fields = ("number", "customer_name", "phone")
    list_per_page = 50
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
