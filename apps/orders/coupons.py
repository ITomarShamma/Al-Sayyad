"""إدارة الكوبون داخل الجلسة — يرافق السلة حتى يتحوّل لقطةً على الطلب.

كالسلة تماماً: الكوبون «مسودة» بجلسة الزائر، ولا يصير حقيقةً محاسبية
إلا لحظة إنشاء الطلب (services) حيث يُعاد التحقق ويُحجز الاستخدام بقفل.
"""

from django.utils.translation import gettext as _

from apps.core.validators import normalize_digits

from .models import Coupon, CouponError

SESSION_KEY = "coupon_code"


def normalize_code(raw):
    """المستخدم يكتب الكود بأي شكل — فراغات/أحرف صغيرة/أرقام هندية."""
    return normalize_digits(raw).upper()


def apply_coupon(session, raw_code, items_subtotal):
    """يتحقق ويخزّن الكود بالجلسة — يرمي CouponError برسالة مفهومة."""
    code = normalize_code(raw_code)
    coupon = Coupon.objects.filter(code=code).first()
    if coupon is None:
        raise CouponError(_("الكود غير صحيح — تأكد منه وجرّب مرة ثانية."))
    coupon.ensure_valid(items_subtotal)
    session[SESSION_KEY] = coupon.code
    session.modified = True
    return coupon


def clear_coupon(session):
    session.pop(SESSION_KEY, None)
    session.modified = True


def get_valid_coupon(session, items_subtotal):
    """الكوبون المخزَّن إن كان ما يزال صالحاً — وإلا يُحذف بصمت ويرجع None.

    (السلة تتغيّر بعد التطبيق: ممكن ينزل المجموع تحت الحد الأدنى،
    أو تنتهي الصلاحية بين زيارتين — نتحقق عند كل استعمال.)
    """
    code = session.get(SESSION_KEY)
    if not code:
        return None
    coupon = Coupon.objects.filter(code=code).first()
    if coupon is None:
        clear_coupon(session)
        return None
    try:
        coupon.ensure_valid(items_subtotal)
    except CouponError:
        clear_coupon(session)
        return None
    return coupon
