"""سلة التسوّق — مخزّنة بجلسة المتصفح (session)، بلا تسجيل دخول وبلا جداول.

لماذا الجلسة؟ الزبون السوري أول مرة يتسوّق أونلاين — ما منطلب منه حساب
ليعبّي سلته. السلة تعيش بجلسته، وعند إتمام الطلب (M6) تتحوّل لسجل Order دائم.

شكل التخزين داخل الجلسة:  {"12": 3}  أي: المنتج رقم 12 × 3 قطع.
"""

from decimal import Decimal

from apps.catalog.models import Product

CART_SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.session = request.session
        # نسخة محلية — لا نكتب بالجلسة إلا عند تعديل فعلي (انظر _save)
        self.data = dict(self.session.get(CART_SESSION_KEY, {}))
        self._items_cache = None

    def _save(self):
        """يكتب السلة بالجلسة ويعلّمها معدّلة ليحفظها Django."""
        self.session[CART_SESSION_KEY] = self.data
        self.session.modified = True
        self._items_cache = None

    # --- تعديل المحتوى -----------------------------------------------------
    def add(self, product, quantity=1):
        """يزيد الكمية الحالية (زر «أضف للسلة» يضيف فوق الموجود)."""
        current = self.data.get(str(product.id), 0)
        self.set(product, current + quantity)

    def set(self, product, quantity):
        """يثبّت الكمية بقيمة محددة — مقصوصة على المخزون، والصفر يحذف."""
        quantity = max(0, min(int(quantity), product.stock))
        if quantity == 0:
            self.data.pop(str(product.id), None)
        else:
            self.data[str(product.id)] = quantity
        self._save()

    def remove(self, product):
        self.data.pop(str(product.id), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    # --- القراءة والعرض ------------------------------------------------------
    def items(self):
        """أسطر السلة: منتج + كمية + إجمالي السطر (استعلام واحد للكل)."""
        if self._items_cache is None:
            products = (
                Product.objects.filter(id__in=self.data.keys(), is_active=True)
                .prefetch_related("images")
            )
            self._items_cache = [
                {
                    "product": p,
                    "quantity": self.data[str(p.id)],
                    "line_total": p.price * self.data[str(p.id)],
                    "line_total_display": f"{p.price * self.data[str(p.id)]:,.0f}",
                }
                for p in products
            ]
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
