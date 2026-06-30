from django.shortcuts import render


def home(request):
    """الصفحة الرئيسية للمتجر — تعرض الواجهة الحقيقية بالهوية البصرية."""
    return render(request, "pages/home.html")

