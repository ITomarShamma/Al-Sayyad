"""حماية تسجيل الدخول من تخمين كلمات السر (rate limiting).

الفكرة: نعدّ محاولات الدخول الفاشلة لكل «رقم موبايل» ولكل «عنوان IP»
على حدة. من يتجاوز الحد المسموح (افتراضياً 5 محاولات) خلال النافذة
(افتراضياً ربع ساعة تبدأ من أول محاولة فاشلة) يُقفَل دخوله حتى نهاية
النافذة — حتى لو أدخل كلمة السر الصحيحة. الدخول الناجح قبل القفل
يصفّر العدّادات.

لماذا عدّادان؟ عدّاد الرقم يحمي حساباً بعينه من التخمين، وعدّاد الـIP
يمنع مهاجماً واحداً من تجربة أرقام كثيرة (رقم واحد × محاولتين لكل رقم
يفلت من عدّاد الرقم لكن يصطاده عدّاد الـIP).

لماذا الكاش وليس جدولاً بقاعدة البيانات؟ العدّادات بيانات مؤقتة لا يضرّ
فقدانها (إعادة تشغيل السيرفر = بداية نظيفة) — والكاش أسرع وينظّف نفسه
بانتهاء المهلة. ملاحظة إنتاج: الكاش الافتراضي (LocMem) منفصل لكل process؛
مع عدة Gunicorn workers يُنصح بكاش مشترك (Redis أو DatabaseCache) ليكون
الحد دقيقاً — بدونه تبقى الحماية قائمة لكن الحد الفعلي يتضاعف بعددهم.
"""

import time

from django.conf import settings
from django.core.cache import cache


def _max_attempts():
    return settings.LOGIN_MAX_ATTEMPTS


def _window_seconds():
    return settings.LOGIN_LOCKOUT_SECONDS


def _keys(username, request=None):
    """مفتاحا الكاش لهذه المحاولة: واحد للرقم وواحد لعنوان الـIP.

    ملاحظة: خلف Nginx يجب تمرير عنوان الزائر الحقيقي (real_ip) وإلا
    صار كل الزوار بعنوان واحد — فيُقفلون جميعاً معاً.
    """
    keys = []
    if username:
        keys.append(f"login:fail:user:{username}")
    ip = request.META.get("REMOTE_ADDR") if request is not None else None
    if ip:
        keys.append(f"login:fail:ip:{ip}")
    return keys


def seconds_locked(username, request=None):
    """كم ثانية باقية على فكّ القفل؟ صفر = غير مقفول، جرّب عادي."""
    now = time.time()
    remaining = 0
    for key in _keys(username, request):
        entry = cache.get(key)
        if entry and entry["count"] >= _max_attempts():
            unlock_at = entry["first"] + _window_seconds()
            remaining = max(remaining, int(unlock_at - now))
    return max(remaining, 0)


def register_failure(username, request=None):
    """محاولة فاشلة: +1 على العدّادين. النافذة تُحسب من أول فشل —
    لذلك مهلة الكاش تتناقص مع كل تسجيل بدل أن تتجدد."""
    now = time.time()
    for key in _keys(username, request):
        entry = cache.get(key) or {"count": 0, "first": now}
        entry["count"] += 1
        ttl = entry["first"] + _window_seconds() - now
        if ttl > 0:
            cache.set(key, entry, ttl)


def reset(username, request=None):
    """دخول ناجح = المحاولات الفاشلة القديمة تُنسى فوراً."""
    cache.delete_many(_keys(username, request))
