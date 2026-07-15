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
        "Disallow: /offline/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def webmanifest(request):
    """بيان الـPWA — عبر view (لا ملف static) لضمان نوع المحتوى الصحيح
    ولاستعمال {% static %} بمسارات الأيقونات."""
    return render(request, "pages/manifest.webmanifest",
                  content_type="application/manifest+json")


def service_worker(request):
    """عامل الخدمة — يُقدَّم من الجذر (/sw.js) ليشمل نطاقُه الموقعَ كله؛
    لو قُدِّم من /static/js/ لاقتصر نطاقه على /static/js/."""
    return render(request, "pages/sw.js",
                  content_type="application/javascript")


def offline(request):
    """صفحة «ما في اتصال» — يخزّنها عامل الخدمة ويعرضها عند انقطاع النت."""
    return render(request, "pages/offline.html")


def styleguide(request):
    """دليل المكوّنات — يعرض كل مكوّنات الواجهة وحالاتها (صفحة تطوير)."""
    # قائمة الألوان نمرّرها للقالب ليبني عيّنات (swatches) منها.
    # أدوار تشير للثيم النشط — العيّنات تُرسم حيّة، فتتبدّل مع الوضع الليلي.
    # الـhex المطبوع للثيم الفاتح (مرجعي).
    colors = [
        ("Primary — فيروزي البحر", "--primary", "#0E7C90"),
        ("Primary strong", "--primary-strong", "#0A5F70"),
        ("Accent — مرجاني", "--accent", "#CC3D1C"),
        ("Violet — بنفسجي السماء", "--color-violet", "#6D4AFF"),
        ("Surface", "--surface", "#FFFFFF"),
        ("Surface-2 — سطح غائر", "--surface-2", "#EEF2F8"),
        ("Ink — نص", "--text", "#131722"),
        ("Slate — نص ثانوي", "--text-muted", "#5A6472"),
        ("Line — حدود", "--border", "#E2E7F0"),
        ("BG — خلفية", "--bg", "#F5F7FB"),
        ("Success", "--color-success", "#15803D"),
        ("Error", "--color-error", "#D93526"),
        ("Warning", "--color-warning", "#B45309"),
        ("Info", "--color-info", "#1D6FC2"),
        ("ShamCash", "--color-shamcash", "#0A7A55"),
        ("COD", "--color-cod", "#7A5B2A"),
    ]
    return render(request, "pages/styleguide.html", {"colors": colors})

