"""واجهات عرض الكاتالوج: التصنيفات وصفحاتها وصفحة المنتج.

قاعدة ثابتة هنا: الزبون لا يرى إلا المفعّل (is_active=True) —
المنتج أو التصنيف غير المفعّل غير موجود من وجهة نظر المتجر (404).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import Category, Product, Review
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


RELATED_LIMIT = 4


def product_detail(request, slug):
    """صفحة منتج: الصور والسعر والمواصفات والشراء + مشابهة + مشاركة."""
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_active=True,
    )

    # منتجات مشابهة: نفس التصنيف، المتوفر أولاً ثم الأحدث
    related = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)
        .prefetch_related("images")
        .order_by("-stock", "-created_at")[:RELATED_LIMIT]
    )

    # نص المشاركة عالواتساب — رابط مطلق (بالدومين) وليس نسبياً
    share_text = (
        f"{product.name} — {product.price_display} ل.س عالصَّيَّاد\n"
        f"{request.build_absolute_uri(product.get_absolute_url())}"
    )

    # التقييمات: المنشورة فقط + متوسطها، وهل الزائر الحالي مشترٍ موثَّق؟
    reviews = product.reviews.filter(is_approved=True).select_related("user")
    stats = reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    can_review = Review.can_review(request.user, product)
    my_review = None
    if can_review:
        my_review = product.reviews.filter(user=request.user).first()

    return render(request, "catalog/product_detail.html", {
        "product": product,
        "related": related,
        "share_text": share_text,
        "reviews": reviews,
        # نصاً لا رقماً: الرقم العائم يتلوقل (٤٫٠) حسب اللغة — بدنا 4.0 ثابتة
        "rating_avg": f"{stats['avg']:.1f}" if stats["avg"] else None,
        "rating_count": stats["count"],
        "rating_stars": round(stats["avg"]) if stats["avg"] else 0,
        "can_review": can_review,
        "my_review": my_review,
    })


@login_required
@require_POST
def submit_review(request, product_id):
    """حفظ تقييم مشترٍ موثَّق — إعادة الإرسال تحدّث تقييمه السابق (PRG)."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    if not Review.can_review(request.user, product):
        messages.error(request, _("التقييم متاح لمن اشترى المنتج من الصَّيَّاد."))
        return redirect(product.get_absolute_url())

    try:
        rating = int(request.POST.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    if not 1 <= rating <= 5:
        messages.error(request, _("اختر تقييماً من 1 إلى 5 نجوم."))
        return redirect(product.get_absolute_url())

    Review.objects.update_or_create(
        product=product, user=request.user,
        defaults={"rating": rating,
                  "comment": request.POST.get("comment", "").strip()},
    )
    messages.success(request, _("شكراً لتقييمك ✓"))
    return redirect(product.get_absolute_url())
