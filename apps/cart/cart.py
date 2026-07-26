"""سلة التسوّق — مخزّنة بجلسة المتصفح (session)، بلا تسجيل دخول وبلا جداول.

لماذا الجلسة؟ الزبون السوري أول مرة يتسوّق أونلاين — ما منطلب منه حساب
ليعبّي سلته. السلة تعيش بجلسته، وعند إتمام الطلب تتحوّل لسجل Order دائم.

شكل التخزين داخل الجلسة:  {"12:0": 3, "17:5": 1}
    المفتاح = «رقم المنتج : رقم المتغيّر»، و0 تعني منتجاً بلا مقاسات/ألوان.
    سطر لكل تركيبة: «قميص L أبيض» و«قميص M أسود» سطران مستقلّان بمخزونين
    مستقلّين — وهذا سبب وجود المتغيّر بالمفتاح أصلاً.

الصيغة القديمة ("12") تُقرأ كما هي وتُرقّى إلى "12:0" — سلال الزبائن
المفتوحة وقت التحديث لا تنكسر.
"""

from decimal import Decimal

from apps.catalog.models import Product, ProductVariant

CART_SESSION_KEY = "cart"
NO_VARIANT = 0


class Cart:
    def __init__(self, request):
        self.session = request.session
        # نسخة محلية — لا نكتب بالجلسة إلا عند تعديل فعلي (انظر _save)
        self.data = self._normalized(self.session.get(CART_SESSION_KEY, {}))
        self._items_cache = None

    # --- مفاتيح السلة ---------------------------------------------------------
    @staticmethod
    def _normalized(raw):
        """يرقّي أي مفتاح بالصيغة القديمة («12») إلى الجديدة («12:0»)."""
        data = {}
        for key, quantity in (raw or {}).items():
            key = str(key)
            data[key if ":" in key else f"{key}:{NO_VARIANT}"] = quantity
        return data

    @staticmethod
    def key_for(product, variant=None):
        return f"{product.id}:{variant.id if variant is not None else NO_VARIANT}"

    @staticmethod
    def _split(key):
        """«12:5» ← (12, 5). المفتاح المشوّه يُهمَل بدل أن يُسقط الصفحة."""
        product_id, _, variant_id = str(key).partition(":")
        try:
            return int(product_id), int(variant_id or NO_VARIANT)
        except ValueError:
            return None, None

    def _save(self):
        """يكتب السلة بالجلسة ويعلّمها معدّلة ليحفظها Django."""
        self.session[CART_SESSION_KEY] = self.data
        self.session.modified = True
        self._items_cache = None

    # --- تعديل المحتوى -----------------------------------------------------
    def add(self, product, quantity=1, variant=None):
        """يزيد الكمية الحالية (زر «أضف للسلة» يضيف فوق الموجود)."""
        current = self.data.get(self.key_for(product, variant), 0)
        self.set(product, current + quantity, variant=variant)

    def set(self, product, quantity, variant=None):
        """يثبّت الكمية — مقصوصة على مخزون التركيبة المختارة، والصفر يحذف."""
        limit = variant.stock if variant is not None else product.stock
        quantity = max(0, min(int(quantity), limit))
        key = self.key_for(product, variant)
        if quantity == 0:
            self.data.pop(key, None)
        else:
            self.data[key] = quantity
        self._save()

    def remove(self, product, variant=None):
        self.data.pop(self.key_for(product, variant), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    # --- القراءة والعرض ------------------------------------------------------
    def items(self):
        """أسطر السلة: منتج (+متغيّر) وكمية وإجمالي السطر — باستعلامين لا أكثر."""
        if self._items_cache is None:
            pairs = {key: self._split(key) for key in self.data}
            product_ids = {p for p, _ in pairs.values() if p}
            variant_ids = {v for _, v in pairs.values() if v}

            products = {
                p.id: p for p in
                Product.objects.filter(id__in=product_ids, is_active=True)
                .prefetch_related("images")
            }
            variants = {}
            if variant_ids:
                variants = {
                    v.id: v for v in
                    ProductVariant.objects.filter(id__in=variant_ids, is_active=True)
                    .select_related("product", "value_1__option", "value_2__option")
                }

            lines = []
            for key, quantity in self.data.items():
                product_id, variant_id = pairs[key]
                product = products.get(product_id)
                if product is None:
                    continue                     # منتج تعطّل أو انحذف
                variant = variants.get(variant_id) if variant_id else None
                if variant_id and variant is None:
                    continue                     # تركيبة تعطّلت — تختفي بهدوء
                unit_price = variant.effective_price if variant else product.price
                line_total = unit_price * quantity
                lines.append({
                    "key": key,
                    "product": product,
                    "variant": variant,
                    # حدّ الكمية لهذا السطر — زر «+» يتوقف عنده
                    "stock_limit": variant.stock if variant else product.stock,
                    "unit_price": unit_price,
                    "unit_price_display": f"{unit_price:,.0f}",
                    "quantity": quantity,
                    "line_total": line_total,
                    "line_total_display": f"{line_total:,.0f}",
                })
            self._items_cache = lines
        return self._items_cache

    @property
    def total_quantity(self):
        return sum(self.data.values())

    @property
    def total_price(self):
        return sum((i["line_total"] for i in self.items()), Decimal("0"))

    @property
    def total_price_display(self):
        return f"{self.total_price:,.0f}"

    def __len__(self):
        return self.total_quantity
