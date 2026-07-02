# بنية قاعدة البيانات — متجر الصَّيَّاد

> وثيقة مرجعية للشركة. تُحدَّث مع كل موديول جديد.
> آخر تحديث: 2026-07-02 — بعد الموديول M3 (الكاتالوج).

## نظرة عامة

- **محرّك قاعدة البيانات:** SQLite أثناء التطوير → **PostgreSQL** في الإنتاج
  (نفس البنية تماماً؛ Django ORM يتكفّل بالفرق).
- **تسمية الجداول:** `<app>_<model>` تلقائياً (مثل `catalog_product`).
- **كل الجداول** ترث حقلَي التوثيق الزمني:
  `created_at` (تاريخ الإنشاء) و`updated_at` (آخر تعديل).
- **المفاتيح الأساسية:** `id` رقم صحيح كبير (BigAutoField) تلقائي بكل جدول.

## مخطط العلاقات (ERD)

```mermaid
erDiagram
    CATEGORY ||--o{ CATEGORY : "أب/أبناء (شجرة)"
    CATEGORY ||--o{ PRODUCT  : "تحتوي (PROTECT)"
    PRODUCT  ||--o{ PRODUCT_IMAGE : "لها صور (CASCADE)"

    CATEGORY {
        bigint id PK
        varchar name "الاسم (100)"
        varchar slug UK "معرّف بالرابط، يدعم العربية"
        bigint parent_id FK "NULL = تصنيف رئيسي"
        bool is_active "مفعّل"
        datetime created_at
        datetime updated_at
    }
    PRODUCT {
        bigint id PK
        bigint category_id FK "التصنيف (PROTECT)"
        varchar name "الاسم (200)"
        varchar slug UK "معرّف بالرابط، يدعم العربية"
        text description "الوصف"
        decimal price "السعر ل.س (12,0) بلا كسور"
        int stock "الكمية بالمخزون"
        bool is_active "غير المفعّل لا يظهر بالمتجر"
        json specs "مواصفات مرنة"
        datetime created_at
        datetime updated_at
    }
    PRODUCT_IMAGE {
        bigint id PK
        bigint product_id FK "المنتج (CASCADE)"
        varchar image "مسار الملف products/YYYY/MM/"
        varchar alt_text "نص بديل (200)"
        bool is_main "الصورة الرئيسية"
        smallint sort_order "الترتيب"
        datetime created_at
        datetime updated_at
    }
```

## الجداول بالتفصيل

### 1) `catalog_category` — التصنيفات (شجرية)

| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | BigAuto | مفتاح أساسي |
| `name` | VarChar(100) | اسم التصنيف |
| `slug` | Slug(120) | **فريد**، يُولّد تلقائياً من الاسم (يدعم العربية) |
| `parent_id` | FK → نفس الجدول | `NULL` = تصنيف رئيسي؛ غير ذلك = فرعي. حذف الأب يحذف الأبناء (CASCADE) |
| `is_active` | Boolean | إخفاء/إظهار التصنيف |
| `created_at` / `updated_at` | DateTime | تلقائي |

**قيود:** لا يتكرر نفس الاسم تحت نفس الأب (`uniq_category_name_per_parent`).
**الشجرة:** مستوى واحد أو أكثر (إلكترونيات ← سماعات ← …) بعمق حر.

### 2) `catalog_product` — المنتجات

| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | BigAuto | مفتاح أساسي |
| `category_id` | FK → category | **PROTECT**: لا يمكن حذف تصنيف فيه منتجات |
| `name` | VarChar(200) | اسم المنتج |
| `slug` | Slug(220) | **فريد**، تلقائي من الاسم، يدعم العربية |
| `description` | Text | وصف حر (اختياري) |
| `price` | Decimal(12,0) | السعر بالليرة السورية **بلا كسور** |
| `stock` | PositiveInt | الكمية المتوفرة |
| `is_active` | Boolean | غير المفعّل لا يظهر بالمتجر إطلاقاً |
| `specs` | JSON | مواصفات مرنة تختلف بين المنتجات: `{"اللون": "أسود"}` |
| `created_at` / `updated_at` | DateTime | تلقائي |

**فهارس:** `(is_active, category)` لصفحات التصنيف، و`-created_at` للأحدث أولاً.
**خصائص محسوبة (ليست أعمدة):** `in_stock` = مفعّل + كمية > 0، `main_image` = أول صورة.

### 3) `catalog_productimage` — صور المنتجات

| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | BigAuto | مفتاح أساسي |
| `product_id` | FK → product | **CASCADE**: حذف المنتج يحذف صوره |
| `image` | Image | يُخزَّن الملف في `media/products/سنة/شهر/` |
| `alt_text` | VarChar(200) | وصف للصورة (وصولية + SEO) |
| `is_main` | Boolean | الصورة الرئيسية للمنتج |
| `sort_order` | SmallInt | ترتيب العرض |
| `created_at` / `updated_at` | DateTime | تلقائي |

**الترتيب الافتراضي:** الرئيسية أولاً، ثم حسب `sort_order`.

## قرارات تصميم مهمّة (ولماذا)

1. **السعر Decimal وليس Float:** أخطاء التقريب بالـFloat ممنوعة بالمال.
   بلا كسور لأن الليرة السورية عملياً لا تُستخدم بكسور.
2. **PROTECT على تصنيف المنتج:** يمنع حذف تصنيف بالغلط وضياع منتجاته —
   يجب نقل المنتجات أولاً ثم الحذف.
3. **CASCADE على صور المنتج:** الصور بلا معنى بعد حذف منتجها.
4. **`specs` JSON بدل أعمدة لكل مواصفة:** المتجر متنوّع (مثل أمازون) —
   مواصفات الغسالة غير مواصفات السماعة؛ عمود لكل مواصفة = جنون.
   JSON يبقيها مرنة، وبالمستقبل يمكن ترقيتها لجدول Attributes منفصل عند الحاجة.
5. **Slug فريد يدعم العربية:** روابط مقروءة `‎/منتج/سماعة-لاسلكية/` أفضل
   للمستخدم ولمحركات البحث من `/product/17/`.
6. **جداول Django الجاهزة** (مستخدمون، صلاحيات، جلسات) تُدار تلقائياً:
   `auth_user`, `auth_group`, `django_session`, …

## القادم (مخطَّط له، غير منفّذ بعد)

| موديول | جداول متوقعة |
|---|---|
| M5 السلة | بلا جداول — السلة بالجلسة (session) حتى إتمام الطلب |
| M6 الطلبات | `orders_order` (بيانات الزبون، العنوان، طريقة الدفع COD/شام كاش، الحالة، الإجمالي) + `orders_orderitem` (سطر لكل منتج: الكمية × سعر لحظة الشراء) |
