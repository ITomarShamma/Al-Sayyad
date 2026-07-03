# الصَّيَّاد · Al-Sayyad

متجر إلكتروني للسوق السوري — عربي أولاً (RTL)، جاهز لإضافة الإنجليزية.
الدفع: **الدفع عند الاستلام** الآن، و**شام كاش** لاحقاً. مبني بـ **Django 5.2 + HTMX**.

> «اطلب… ونحن نصطاد لك»

## الميزات الحالية

- 🗂️ كاتالوج بتصنيفات شجرية، مواصفات مرنة (JSON)، صور بمصغّرات تلقائية
- 🔍 بحث عربي ذكي (سماعه = سماعة) + اقتراحات حية أثناء الكتابة
- 🛒 سلة بالجلسة بلا تسجيل، عدّاد حي وتوست تأكيد (HTMX)
- 💵 إتمام طلب COD بأسعار «لقطة» وخصم مخزون ذرّي — وhook جاهز لشام كاش
- 📦 تتبع الطلب برقمه + الموبايل، مع خط زمن الحالة
- 🏷️ تخفيضات (سعر قديم مشطوب + نسبة الخصم)
- ⚙️ لوحة تحكم معرّبة: تنبيهات المخزون، حالات ملوّنة، تعديل سريع
- 🧭 فرز وفلترة، صفحات ثقة، 404/500 مخصصة، sitemap/robots/OG

## المتطلّبات
- Python 3.12+ (مُختبَر على 3.14) · Git
- (اختياري، لتفعيل الإنجليزية) GNU gettext: `choco install gettext`

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
ثم افتح: http://127.0.0.1:8000/ · لوحة التحكم: `/admin/` · دليل المكوّنات: `/styleguide/`

## الاختبارات
```powershell
python manage.py test apps
```

## بنية المشروع
```
config/        الإعدادات (base/dev/prod) والمسارات
apps/core      أساس مشترك (TimeStampedModel…)
apps/pages     الرئيسية والصفحات الثابتة وrobots
apps/catalog   التصنيفات والمنتجات والبحث وsitemap
apps/cart      السلة (جلسة + HTMX)
apps/orders    إتمام الطلب والتتبع والدفع
templates/     القوالب (components/ = مكتبة المكوّنات)
static/        tokens.css · base.css · components.css · خطوط · js
docs/          architecture.md · database-schema.md (وثائق الشركة)
```

## الوثائق
- **المعمارية والقواعد:** [docs/architecture.md](docs/architecture.md)
- **بنية قاعدة البيانات:** [docs/database-schema.md](docs/database-schema.md)

## الإعدادات (settings)
- **محلياً:** `config.settings.dev` (افتراضي عبر `manage.py`) — SQLite، DEBUG مفعّل.
- **إنتاجاً:** `config.settings.prod` — PostgreSQL وتشديد أمني، عبر
  `DJANGO_SETTINGS_MODULE=config.settings.prod`.
- الأسرار في `.env` (غير مرفوع) — انسخه من `.env.example`.
  بيانات التواصل المعروضة للزبائن: `STORE_PHONE` / `STORE_WHATSAPP` / `STORE_EMAIL`.

## الهوية البصرية
الألوان والخطوط تُعرّف **مرة واحدة** في `static/css/tokens.css`؛ كل قطعة UI
مكوّن قابل لإعادة الاستخدام في `templates/components/` ويظهر بحالاته في
`/styleguide/`. القاعدة: tokens ومكوّنات فقط — لا تكرار.
