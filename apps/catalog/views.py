"""واجهات عرض الكاتالوج: التصنيفات وصفحاتها وصفحة المنتج.

قاعدة ثابتة هنا: الزبون لا يرى إلا المفعّل (is_active=True) —
المنتج أو التصنيف غير المفعّل غير موجود من وجهة نظر المتجر (404).
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Category, Product

PRODUCTS_PER_PAGE = 24


def category_list(request):
    """صفحة «التصنيفات»: كل التصنيفات الرئيسية المفعّلة."""
    categories = Category.objects.filter(is_active=True, parent__isnull=True)
    return render(request, "catalog/category_list.html", {"categories": categories})


def category_detail(request, slug):
    """صفحة تصنيف: تصنيفاته الفرعية + منتجاته المفعّلة مع ترقيم صفحات."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    children = category.children.filter(is_active=True)

    products_qs = (
        category.products.filter(is_active=True)
        .prefetch_related("images")      # يمنع استعلاماً لكل بطاقة (N+1)
    )
    paginator = Paginator(products_qs, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))  # رقم خاطئ؟ أول صفحة

    return render(request, "catalog/category_detail.html", {
        "category": category,
        "children": children,
        "page": page,
    })


def product_detail(request, slug):
    """صفحة منتج: الصور والسعر والمواصفات وأزرار الشراء."""
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_active=True,
    )
    return render(request, "catalog/product_detail.html", {"product": product})
