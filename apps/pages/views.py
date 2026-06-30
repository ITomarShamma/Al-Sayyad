from django.http import HttpResponse


def home(request):
    """Temporary landing page.

    Confirms the project runs end-to-end. The real, styled homepage arrives
    in module M1 (design system + templates).
    """
    html = (
        "<!doctype html><html lang='ar' dir='rtl'>"
        "<meta charset='utf-8'>"
        "<body style='font-family:sans-serif;text-align:center;margin-top:15vh'>"
        "<h1>الصَّيَّاد ✅</h1>"
        "<p>المشروع يعمل. هذه صفحة مؤقتة — الواجهة الحقيقية تجي بالموديول M1.</p>"
        "<p><a href='/admin/'>لوحة التحكم /admin</a></p>"
        "</body></html>"
    )
    return HttpResponse(html)

