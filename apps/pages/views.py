from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from apps.catalog.models import Category, Product


def home(request):
    """الرئيسية: التصنيفات الرئيسية + أحدث المنتجات (من قاعدة البيانات)."""
    categories = Category.objects.filter(is_active=True, parent__isnull=True)[:8]
    latest_products = (
        Product.objects.filter(is_active=True)
        .prefetch_related("images")
        [:8]                      # الترتيب الافتراضي: الأحدث أولاً (Meta.ordering)
    )
    return render(request, "pages/home.html", {
        "categories": categories,
        "latest_products": latest_products,
    })


def about(request):
    """عن الصَّيَّاد — من نحن ولماذا يثق فينا الزبون."""
    return render(request, "pages/about.html")


def contact(request):
    """تواصل معنا — القيم من الإعدادات (STORE_*) لتُعدَّل بمكان واحد."""
    return render(request, "pages/contact.html", {
        "phone": settings.STORE_PHONE,
        "whatsapp": settings.STORE_WHATSAPP,
        "email": settings.STORE_EMAIL,
    })


def robots_txt(request):
    """ملف robots.txt — يوجّه محركات البحث ويشير لخريطة الموقع."""
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /track/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def styleguide(request):
    """دليل المكوّنات — يعرض كل مكوّنات الواجهة وحالاتها (صفحة تطوير)."""
    # قائمة الألوان نمرّرها للقالب ليبني عيّنات (swatches) منها.
    colors = [
        ("Tide — أساسي", "--color-tide", "#0E6B5E"),
        ("Deep Sea", "--color-deep-sea", "#0B4A41"),
        ("Catch Gold — تمييز", "--color-gold", "#D99A2B"),
        ("Sea Foam", "--color-sea-foam", "#E4F1ED"),
        ("Ink — نص", "--color-ink", "#16261F"),
        ("Slate — نص ثانوي", "--color-slate", "#5B6B64"),
        ("Line — حدود", "--color-line", "#E6E1D3"),
        ("Paper — خلفية", "--color-paper", "#FAF8F2"),
        ("Success", "--color-success", "#2E9E54"),
        ("Error", "--color-error", "#D5402B"),
        ("Warning", "--color-warning", "#E8A317"),
        ("Info", "--color-info", "#2D6FB3"),
        ("ShamCash", "--color-shamcash", "#1FA37A"),
        ("COD", "--color-cod", "#7A5B2A"),
    ]
    return render(request, "pages/styleguide.html", {"colors": colors})

