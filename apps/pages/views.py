from django.shortcuts import render


def home(request):
    """الصفحة الرئيسية للمتجر — تعرض الواجهة الحقيقية بالهوية البصرية."""
    return render(request, "pages/home.html")


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

