"""واجهات عرض الكاتالوج: التصنيفات وصفحاتها وصفحة المنتج.

قاعدة ثابتة هنا: الزبون لا يرى إلا المفعّل (is_active=True) —
المنتج أو التصنيف غير المفعّل غير موجود من وجهة نظر المتجر (404).
"""

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Category, Product
from .search import normalize

PRODUCTS_PER_PAGE = 24
SUGGESTIONS_LIMIT = 5

# خيارات الترتيب المسموحة — أي قيمة غريبة من الرابط ترجع للافتراضي
SORTS = {
    "new": "-created_at",
    "price_asc": "price",
    "price_desc": "-price",
}


def apply_browse_controls(request, qs):
    """يطبّق الفرز والفلترة من باراميترات الرابط على أي قائمة منتجات.

    يرجع (queryset, sort, available) — القيمتان تعودان للقالب
    ليعرض أدوات التحكم بحالتها الحالية.
    """
    sort = request.GET.get("sort", "new")
    if sort not in SORTS:
        sort = "new"
    available = request.GET.get("available") == "1"
    if available:
        qs = qs.filter(stock__gt=0)
    return qs.order_by(SORTS[sort]), sort, available


def _search_queryset(q):
    """منتجات مفعّلة تطابق كل كلمات البحث (بعد التطبيع).

    كل كلمة تضيّق النتائج (AND): «شاحن سريع» يرجع ما يحوي الكلمتين معاً.
    """
    nq = normalize(q)
    if not nq:
        return Product.objects.none()
    qs = Product.objects.filter(is_active=True)
    for word in nq.split():
        qs = qs.filter(search_text__contains=word)
    return qs


def search(request):
    """صفحة نتائج البحث — ?q=كلمات البحث، مع نفس أدوات الفرز والفلترة."""
    q = request.GET.get("q", "").strip()
    results = _search_queryset(q).prefetch_related("images")
    results, sort, available = apply_browse_controls(request, results)
    paginator = Paginator(results, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "catalog/search_results.html", {
        "q": q,
        "page": page,
        "total": paginator.count if q else 0,
        "sort": sort,
        "available": available,
    })


def search_suggest(request):
    """اقتراحات حية تحت شريط البحث (HTMX) — أول 5 نتائج مطابقة."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:                       # حرف واحد؟ لسا بكير عالاقتراح
        return render(request, "catalog/partials/search_suggest.html",
                      {"q": q, "products": []})
    products = _search_queryset(q)[:SUGGESTIONS_LIMIT]
    return render(request, "catalog/partials/search_suggest.html",
                  {"q": q, "products": products})


def category_list(request):
    """صفحة «التصنيفات»: كل التصنيفات الرئيسية المفعّلة."""
    categories = Category.objects.filter(is_active=True, parent__isnull=True)
    return render(request, "catalog/category_list.html", {"categories": categories})


def category_detail(request, slug):
    """صفحة تصنيف: منتجات الشجرة كاملة (هو + كل فروعه) + فرز وفلترة."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    children = category.children.filter(is_active=True)

    products_qs = (
        Product.objects.filter(
            is_active=True,
            category_id__in=category.descendant_ids(),  # الشجرة كلها، مو المباشر فقط
        )
        .prefetch_related("images")      # يمنع استعلاماً لكل بطاقة (N+1)
    )
    products_qs, sort, available = apply_browse_controls(request, products_qs)
    paginator = Paginator(products_qs, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))  # رقم خاطئ؟ أول صفحة

    return render(request, "catalog/category_detail.html", {
        "category": category,
        "children": children,
        "page": page,
        "sort": sort,
        "available": available,
    })


def product_detail(request, slug):
    """صفحة منتج: الصور والسعر والمواصفات وأزرار الشراء."""
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_active=True,
    )
    return render(request, "catalog/product_detail.html", {"product": product})
