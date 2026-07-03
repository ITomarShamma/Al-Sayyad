"""لوحة تحكم الكاتالوج — من هنا تُدخل التصنيفات والمنتجات والصور."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage

LOW_STOCK_THRESHOLD = 3


class StockLevelFilter(admin.SimpleListFilter):
    """فلتر جانبي: شوف فوراً شو ناقص أو شارف يخلص."""

    title = "مستوى المخزون"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [
            ("out", "نافد (0)"),
            ("low", f"منخفض (≤ {LOW_STOCK_THRESHOLD})"),
            ("ok", "متوفر"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "out":
            return queryset.filter(stock=0)
        if self.value() == "low":
            return queryset.filter(stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD)
        if self.value() == "ok":
            return queryset.filter(stock__gt=LOW_STOCK_THRESHOLD)
        return queryset


class ProductImageInline(admin.TabularInline):
    """صور المنتج تظهر داخل صفحة المنتج نفسها (بدل صفحة منفصلة)."""

    model = ProductImage
    extra = 1                     # صف فارغ واحد جاهز لإضافة صورة
    fields = ("image", "alt_text", "is_main", "sort_order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "products_count", "updated_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    ordering = ("parent__name", "name")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="عدد المنتجات")
    def products_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_display", "stock_display",
                    "stock", "is_active", "updated_at")
    list_filter = (StockLevelFilter, "is_active", "category")
    search_fields = ("name", "description")
    list_editable = ("stock", "is_active")   # تعديل سريع من الجدول مباشرة

    @admin.display(description="حالة المخزون", ordering="stock")
    def stock_display(self, obj):
        """إشارة ملوّنة: أحمر نافد، برتقالي منخفض، أخضر متوفر."""
        if obj.stock == 0:
            return format_html('<b style="color:#D5402B;">● نافد</b>')
        if obj.stock <= LOW_STOCK_THRESHOLD:
            return format_html('<b style="color:#E8A317;">● منخفض ({})</b>', obj.stock)
        return format_html('<span style="color:#2E9E54;">● متوفر</span>')
    list_per_page = 50
    inlines = [ProductImageInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("الأساسيات", {"fields": ("category", "name", "slug", "description")}),
        ("السعر والمخزون", {"fields": ("price", "compare_at_price", "stock", "is_active")}),
        ("المواصفات", {"fields": ("specs",), "description": "مواصفات حرّة تظهر بصفحة المنتج."}),
        ("سجلّ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="السعر", ordering="price")
    def price_display(self, obj):
        return f"{obj.price:,.0f} ل.س"
