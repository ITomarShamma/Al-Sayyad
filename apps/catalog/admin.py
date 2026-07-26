"""لوحة تحكم الكاتالوج — من هنا تُدخل الماركات والتصنيفات والمنتجات وخياراتها وصورها."""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import (Brand, Category, Product, ProductImage, ProductOption,
                     ProductOptionValue, ProductVariant, Review)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """التقييمات — أخفِ المسيء بإزالة «منشور» بدل الحذف."""

    list_display = ("product", "user", "rating", "comment_short",
                    "is_approved", "created_at")
    list_editable = ("is_approved",)
    list_filter = ("rating", "is_approved")
    search_fields = ("product__name", "user__username", "comment")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="التعليق")
    def comment_short(self, obj):
        return (obj.comment[:60] + "…") if len(obj.comment) > 60 else obj.comment

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


class VariantStockFilter(admin.SimpleListFilter):
    """نفس فلتر المخزون لكن على مستوى التركيبة — «أي مقاس خلص؟»."""

    title = "مستوى المخزون"
    parameter_name = "variant_stock"

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


# ==========================================================================
#  الخيارات والمتغيّرات (المقاسات والألوان)
# ==========================================================================

VALUE_SEPARATORS = ",،\n"


class ProductOptionForm(forms.ModelForm):
    """خيار المنتج مع قيمه بسطر واحد — «S, M, L, XL» بدل صفحة لكل قيمة.

    إدخال البيانات يقوم به موظّف مبيعات لا مبرمج: كتابة المقاسات مفصولة
    بفواصل أسرع بكثير من فتح صفحة مستقلة لكل مقاس.
    """

    values_text = forms.CharField(
        label="القيم", required=False,
        widget=forms.TextInput(attrs={"size": 45, "placeholder": "S, M, L, XL"}),
        help_text="افصل بفاصلة. الترتيب هنا هو ترتيب ظهورها للزبون.",
    )

    class Meta:
        model = ProductOption
        fields = ("name", "values_text", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["values_text"].initial = "، ".join(
                v.value for v in self.instance.values.all())

    @staticmethod
    def _parse(text):
        """يفكّ النص لقائمة قيم مرتّبة بلا تكرار ولا فراغات."""
        for sep in VALUE_SEPARATORS[1:]:
            text = text.replace(sep, VALUE_SEPARATORS[0])
        seen, out = set(), []
        for raw in text.split(VALUE_SEPARATORS[0]):
            value = raw.strip()
            if value and value not in seen:
                seen.add(value)
                out.append(value)
        return out

    def _sync_values(self, option):
        """يوائم قيم الخيار مع النص: يضيف الجديد، يرتّب، ويحذف المحذوف بأمان."""
        wanted = self._parse(self.cleaned_data.get("values_text", ""))
        existing = {v.value: v for v in option.values.all()}

        for order, value in enumerate(wanted):
            obj = existing.get(value)
            if obj is None:
                ProductOptionValue.objects.create(
                    option=option, value=value, sort_order=order)
            elif obj.sort_order != order:
                obj.sort_order = order
                obj.save(update_fields=["sort_order", "updated_at"])

        # قيمة أُزيلت من النص: نحذفها فقط إذا ما في متغيّر يستعملها —
        # وإلا كنّا نكسر مخزوناً وطلبات مرتبطة بها (PROTECT).
        for value, obj in existing.items():
            if value in wanted:
                continue
            in_use = (obj.variants_as_first.exists()
                      or obj.variants_as_second.exists())
            if not in_use:
                obj.delete()

    def save(self, commit=True):
        option = super().save(commit=commit)
        if commit:
            self._sync_values(option)
        return option


class ProductOptionInline(admin.TabularInline):
    """محاور الاختيار للمنتج: «المقاس» و«اللون» (اثنان كحدّ أقصى)."""

    model = ProductOption
    form = ProductOptionForm
    extra = 1
    max_num = ProductOption.MAX_PER_PRODUCT
    verbose_name = "خيار (مقاس/لون)"
    verbose_name_plural = (
        "الخيارات — اكتب المحور وقيمه، ثم احفظ واستعمل إجراء "
        "«توليد كل التركيبات» من قائمة المنتجات"
    )


class ProductVariantInline(admin.TabularInline):
    """التركيبات القابلة للشراء — هنا يُدار **المخزون الحقيقي** لكل مقاس/لون."""

    model = ProductVariant
    extra = 0
    fields = ("value_1", "value_2", "sku", "price", "stock", "is_active")
    verbose_name = "متغيّر (تركيبة)"
    verbose_name_plural = "المتغيّرات — مخزون كل مقاس/لون على حدة"

    def get_formset(self, request, obj=None, **kwargs):
        # نمرّر المنتج الحالي لتصفية القوائم المنسدلة على قيمه هو فقط
        request._variant_parent = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ("value_1", "value_2"):
            parent = getattr(request, "_variant_parent", None)
            kwargs["queryset"] = (
                ProductOptionValue.objects.filter(option__product=parent)
                .select_related("option")
                if parent is not None else ProductOptionValue.objects.none()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "products_count", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="عدد المنتجات")
    def products_count(self, obj):
        return obj.products.count()


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


def merchant_of(request):
    """ملف التاجر المفعَّل لمستخدم اللوحة — None لموظفي المتجر والمدراء."""
    if request.user.is_superuser:
        return None
    mp = getattr(request.user, "merchant_profile", None)
    return mp if (mp and mp.is_approved) else None


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "brand", "category", "price_display",
                    "stock_display", "stock", "is_active", "updated_at")
    list_filter = (StockLevelFilter, "is_active", "category", "brand", "merchant")
    search_fields = ("name", "description", "sku")
    list_editable = ("stock", "is_active")   # تعديل سريع من الجدول مباشرة
    autocomplete_fields = ("brand",)
    actions = ["generate_variants"]

    @admin.display(description="البائع", ordering="merchant")
    def seller(self, obj):
        return obj.merchant.store_name if obj.merchant else "الصَّيَّاد"

    # --- توليد التركيبات: أهم زر لمن يُدخل ملابس بمقاسات وألوان -------------
    @admin.action(description="توليد كل تركيبات الخيارات (المقاسات × الألوان)")
    def generate_variants(self, request, queryset):
        """ينشئ متغيّراً لكل تركيبة ناقصة — الموجود لا يُلمس مخزونه."""
        created = skipped = 0
        for product in queryset.prefetch_related("options__values"):
            options = list(product.options.all())
            if not options:
                skipped += 1
                continue
            first = list(options[0].values.all())
            if len(options) == 1:
                combos = [(v, None) for v in first]
            else:
                combos = [(a, b) for a in first for b in options[1].values.all()]
            for value_1, value_2 in combos:
                _, made = ProductVariant.objects.get_or_create(
                    product=product, value_1=value_1, value_2=value_2,
                    defaults={"stock": 0},
                )
                created += made
            product.sync_stock()

        if created:
            self.message_user(
                request,
                f"تم توليد {created} تركيبة جديدة — املأ مخزون كل واحدة من صفحة المنتج.",
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} منتج بلا خيارات — أضف «المقاس» أو «اللون» أولاً ثم أعد الإجراء.",
                level="warning",
            )

    # --- عزل التجّار: كلٌّ يرى ويدير منتجاته فقط -----------------------------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        mp = merchant_of(request)
        return qs.filter(merchant=mp) if mp else qs

    def save_model(self, request, obj, form, change):
        mp = merchant_of(request)
        if mp:
            obj.merchant = mp        # منتجات التاجر تُنسب له إجبارياً
        super().save_model(request, obj, form, change)
        # المنتج ذو المتغيّرات: مخزونه محسوب لا مُدخَل — نصحّح أي تعديل يدوي
        # (من الجدول السريع مثلاً) فوراً حتى لا يفترق الرقم عن الحقيقة.
        obj.sync_stock()

    def save_related(self, request, form, formsets, change):
        # بعد حفظ المتغيّرات المضمّنة نعيد الجمع — الحفظ الفردي لكل متغيّر
        # يزامن أصلاً، وهذه ضمانة أخيرة بعد الحذف أو التعطيل داخل نفس الحفظ.
        super().save_related(request, form, formsets, change)
        form.instance.sync_stock()

    def get_exclude(self, request, obj=None):
        # التاجر لا يرى حقل «البائع» أصلاً — يُعبّأ عنه تلقائياً
        return ("merchant",) if merchant_of(request) else None

    def get_fieldsets(self, request, obj=None):
        # مع exclude لازم نشيل الحقل من fieldsets أيضاً وإلا انكسر الفورم
        fieldsets = super().get_fieldsets(request, obj)
        if not merchant_of(request):
            return fieldsets
        return [
            (title, {**opts, "fields": tuple(f for f in opts["fields"] if f != "merchant")})
            for title, opts in fieldsets
        ]

    def get_list_filter(self, request):
        if merchant_of(request):
            return (StockLevelFilter, "is_active", "category")
        return self.list_filter

    @admin.display(description="حالة المخزون", ordering="stock")
    def stock_display(self, obj):
        """إشارة ملوّنة: أحمر نافد، برتقالي منخفض، أخضر متوفر.

        للمنتج ذي المقاسات/الألوان نوضّح أن الرقم مجموع تركيباته — حتى لا
        يظنّه أحد رقماً يُحرَّر يدوياً.
        """
        if obj.stock == 0:
            badge = format_html('<b style="color:#D93526;">● نافد</b>')
        elif obj.stock <= LOW_STOCK_THRESHOLD:
            badge = format_html('<b style="color:#B45309;">● منخفض ({})</b>', obj.stock)
        else:
            badge = format_html('<span style="color:#15803D;">● متوفر</span>')

        count = obj.variants.filter(is_active=True).count()
        if count:
            return format_html(
                '{} <span style="color:#5A6472;">— مجموع {} تركيبة</span>', badge, count)
        return badge

    list_per_page = 50
    inlines = [ProductOptionInline, ProductVariantInline, ProductImageInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("الأساسيات", {"fields": ("merchant", "category", "brand", "name", "slug",
                                  "sku", "description")}),
        ("السعر والمخزون", {
            "fields": ("price", "compare_at_price", "stock", "is_active"),
            "description": "منتج بمقاسات أو ألوان؟ اترك «الكمية بالمخزون» — "
                           "تُحسب تلقائياً من مخزون التركيبات تحت.",
        }),
        ("المواصفات", {"fields": ("specs",),
                       "description": "مواصفات ثابتة للعرض فقط (المنشأ، الكفالة). "
                                      "المقاسات والألوان تُدار من «الخيارات» تحت."}),
        ("سجلّ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        """مخزون المنتج ذي المتغيّرات محسوب — نقفله بدل ترك رقم كاذب يُحرَّر."""
        fields = super().get_readonly_fields(request, obj)
        if obj is not None and obj.options.exists():
            return tuple(fields) + ("stock",)
        return fields

    @admin.display(description="السعر", ordering="price")
    def price_display(self, obj):
        return f"{obj.price:,.0f} ل.س"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """جرد المقاسات والألوان عبر كل المنتجات — لتعبئة المخزون بسرعة.

    شاشة «شو ناقص؟»: فلترة على النافد، وتعديل الكميات من الجدول مباشرة.
    """

    list_display = ("product", "combination", "sku", "unit_price",
                    "stock", "is_active")
    list_editable = ("stock", "is_active")
    list_filter = (VariantStockFilter, "is_active", "product__category",
                   "product__brand")
    search_fields = ("product__name", "sku", "value_1__value", "value_2__value")
    list_select_related = ("product", "value_1", "value_2")
    list_per_page = 60

    @admin.display(description="التركيبة")
    def combination(self, obj):
        return obj.short_label

    @admin.display(description="السعر")
    def unit_price(self, obj):
        # نميّز السعر الموروث من المنتج عن السعر الخاص بهذه التركيبة
        if obj.price is None:
            return format_html('<span style="color:#5A6472;">{} (من المنتج)</span>',
                               f"{obj.effective_price:,.0f}")
        return f"{obj.effective_price:,.0f}"

    # عزل التجّار: كلٌّ يرى مخزون منتجاته فقط
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        mp = merchant_of(request)
        return qs.filter(product__merchant=mp) if mp else qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        mp = merchant_of(request)
        if mp and db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(merchant=mp)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
