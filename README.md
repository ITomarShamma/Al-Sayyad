# الصَّيَّاد · Al-Sayyad

متجر إلكتروني للسوق السوري — عربي أولاً (RTL)، قابل لإضافة الإنجليزية لاحقاً.
الدفع: الدفع عند الاستلام (COD) الآن، وشام كاش لاحقاً. مبني بـ **Django + HTMX**.

> «اطلب… ونحن نصطاد لك»

## المتطلّبات
- Python 3.12+ (مُختبَر على 3.14)
- Git

## التشغيل محلياً (Windows / PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
ثم افتح: http://127.0.0.1:8000/  · لوحة التحكم: http://127.0.0.1:8000/admin/

## بنية المشروع
```
config/        إعدادات المشروع (settings مقسّمة: base/dev/prod) والمسارات
apps/core      أدوات مشتركة (base models, helpers)
apps/pages     الصفحات (الرئيسية…)
apps/catalog   التصنيفات والمنتجات
apps/cart      السلة
apps/orders    الطلبات والدفع
templates/     قوالب HTML
static/        CSS / JS / خطوط / صور
locale/        ملفات الترجمة (ar / en)
```

## الإعدادات (settings)
- **محلياً:** `config.settings.dev` (افتراضي عبر `manage.py`) — SQLite، DEBUG مفعّل.
- **إنتاجاً:** `config.settings.prod` — PostgreSQL وتشديد أمني، عبر
  `DJANGO_SETTINGS_MODULE=config.settings.prod`.
- الأسرار في ملف `.env` (غير مرفوع على git) — انسخه من `.env.example`.

## الهوية البصرية
الألوان والخطوط تُعرّف **مرة واحدة** كـ design tokens في `static/css/tokens.css`
(تجي بالموديول M1). القاعدة: tokens ومكوّنات قابلة لإعادة الاستخدام فقط — لا تكرار.
