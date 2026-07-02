"""لوحة تحكم الكاتالوج — من هنا تُدخل التصنيفات والمنتجات والصور."""

from django.contrib import admin

from .models import Category, Product, ProductImage


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
    list_display = ("name", "category", "price_display", "stock", "is_active", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name", "description")
    list_editable = ("stock", "is_active")   # تعديل سريع من الجدول مباشرة
    list_per_page = 50
    inlines = [ProductImageInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("الأساسيات", {"fields": ("category", "name", "slug", "description")}),
        ("السعر والمخزون", {"fields": ("price", "stock", "is_active")}),
        ("المواصفات", {"fields": ("specs",), "description": "مواصفات حرّة تظهر بصفحة المنتج."}),
        ("سجلّ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="السعر", ordering="price")
    def price_display(self, obj):
        return f"{obj.price:,.0f} ل.س"
