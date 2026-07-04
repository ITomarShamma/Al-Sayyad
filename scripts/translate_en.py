# -*- coding: utf-8 -*-
"""يعبّي ترجمات الإنجليزية في locale/en/LC_MESSAGES/django.po.

يُشغَّل بعد makemessages: يملأ msgstr من القاموس أدناه ويطبع أي نص
بلا ترجمة حتى لا يفوتنا شيء. آمن للإعادة (idempotent).
    python scripts/translate_en.py
"""

import re
import sys
from pathlib import Path

PO_PATH = Path(__file__).resolve().parents[1] / "locale/en/LC_MESSAGES/django.po"

TRANSLATIONS = {
    # --- الحسابات ---
    "في حساب مسجَّل بهالرقم أصلاً — جرّب تسجيل الدخول.": "An account with this number already exists — try logging in.",
    "كلمتا السر غير متطابقتين.": "The two passwords don't match.",
    "رقم الموبايل": "Mobile number",
    "كلمة السر": "Password",
    "الرقم أو كلمة السر غير صحيحة — تأكد وجرّب مرة ثانية.": "Wrong number or password — check and try again.",
    "زبون": "Customer",
    "تاجر": "Merchant",
    "أهلاً فيك بالصَّيَّاد! حسابك جاهز 🎣": "Welcome to Al-Sayyad! Your account is ready 🎣",
    "انحفظت بياناتك ✓": "Your details were saved ✓",
    "تغيّرت كلمة السر ✓": "Password changed ✓",
    "وصلنا طلبك 🏪 — منراجعه ومنتواصل معك خلال يوم عمل.": "We received your application 🏪 — we'll review it and contact you within one business day.",
    "أدخل رقم موبايل سوري صحيح: 09 يتبعها 8 أرقام.": "Enter a valid Syrian mobile number: 09 followed by 8 digits.",
    "أهلاً": "Hello",
    "بياناتي": "My details",
    "الاسم": "Name",
    "الموبايل": "Mobile",
    "المدينة": "City",
    "الدور": "Role",
    "تعديل البيانات": "Edit details",
    "تغيير كلمة السر": "Change password",
    "طلباتي": "My orders",
    "ما في طلبات بعد — طلباتك الجاية رح تظهر هون.": "No orders yet — your future orders will show up here.",
    "للتجّار": "For merchants",
    "متجرك": "Your store",
    "إدارة منتجاتي": "Manage my products",
    "طلبك لمتجر": "Your application for",
    "منتواصل معك بعد مراجعة الطلب.": "We'll contact you once it's reviewed.",
    "عندك بضاعة وبدك تبيع عالصَّيَّاد؟ قدّم طلب انضمام كتاجر.": "Got goods to sell on Al-Sayyad? Apply to join as a merchant.",
    "انضم كتاجر": "Join as a merchant",
    "تسجيل الخروج": "Log out",
    "تعديل بياناتي": "Edit my details",
    "الاسم الكامل": "Full name",
    "المحافظة / المدينة": "Governorate / city",
    "تتعبّى تلقائياً بصفحة إتمام الطلب.": "Filled in automatically at checkout.",
    "رقم الموبايل هو اسم دخولك — لتغييره تواصل معنا.": "Your mobile number is your login — contact us to change it.",
    "حفظ": "Save",
    "رجوع": "Back",
    "تسجيل الدخول": "Log in",
    "دخول": "Log in",
    "ما عندك حساب؟": "No account yet?",
    "سجّل جديد": "Sign up",
    "طلبت كزائر؟ تقدر تتبع طلبك بلا حساب من": "Ordered as a guest? Track your order without an account from the",
    "صفحة التتبع": "tracking page",
    "بيع بضاعتك عالصَّيَّاد: أنت تضيف منتجاتك، ونحن منتكفّل بالواجهة والطلبات والتوصيل.": "Sell your goods on Al-Sayyad: you add your products, we handle the storefront, orders and delivery.",
    "اسم المتجر": "Store name",
    "موبايل التواصل": "Contact mobile",
    "عن المتجر (اختياري)": "About the store (optional)",
    "شو بتبيعوا؟ من متى وأنتم شغالين؟": "What do you sell? How long have you been in business?",
    "قدّم الطلب": "Submit application",
    "كلمة السر الحالية": "Current password",
    "كلمة السر الجديدة": "New password",
    "تأكيد كلمة السر الجديدة": "Confirm new password",
    "تغيير": "Change",
    "حساب جديد": "New account",
    "بحساب واحد: طلباتك محفوظة، وبياناتك تتعبّى وحدها عند الطلب.": "With one account your orders are saved and your details fill in automatically at checkout.",
    "هو نفسه اسم دخولك — منتواصل معك عليه.": "It's also your login — we'll contact you on it.",
    "تأكيد كلمة السر": "Confirm password",
    "أنشئ حسابي": "Create my account",
    "عندك حساب؟": "Already have an account?",
    "سجّل دخول": "Log in",

    # --- الطلبات ---
    "بانتظار التأكيد": "Awaiting confirmation",
    "مؤكّد": "Confirmed",
    "قيد التوصيل": "Out for delivery",
    "مُسلَّم": "Delivered",
    "ملغى": "Cancelled",
    "الدفع عند الاستلام": "Cash on delivery",
    "شام كاش": "ShamCash",
    "الكمية المتوفرة تغيّرت لهالمنتجات: %(names)s — حدّث سلتك وجرّب مرة ثانية.": "Available stock changed for: %(names)s — update your cart and try again.",
    "رجوع للسلة": "Back to cart",
    "منتواصل معك عليه لتأكيد الطلب والتوصيل.": "We'll call you on it to confirm your order and arrange delivery.",
    "العنوان بالتفصيل": "Detailed address",
    "الحي، الشارع، رقم البناء، طابق…": "Neighborhood, street, building number, floor…",
    "ملاحظات (اختياري)": "Notes (optional)",
    "طريقة الدفع": "Payment method",
    "شام كاش — قريباً": "ShamCash — coming soon",
    "أكّد الطلب": "Confirm order",
    "ملخص طلبك": "Your order summary",
    "الإجمالي": "Total",
    "تم استلام طلبك": "Order received",
    "تم استلام طلبك!": "Order received!",
    "رقم طلبك": "Your order number is",
    "احتفظ فيه لأي استفسار.": "keep it for any inquiries.",
    "منتواصل معك على %(phone)s خلال ساعات لتأكيد الطلب وترتيب التوصيل.": "We'll contact you on %(phone)s within hours to confirm your order and arrange delivery.",
    "ملخص الطلب": "Order summary",
    "رجوع للرئيسية": "Back to home",
    "وين طلبي؟": "Where's my order?",
    "اكتب رقم الطلب (من صفحة التأكيد) ورقم الموبايل يلي طلبت فيه.": "Enter your order number (from the confirmation page) and the mobile number you ordered with.",
    "رقم الطلب": "Order number",
    "دوّر عالطلب": "Find my order",
    "طلب": "Order",
    "هذا الطلب ملغى. إذا في خطأ، تواصل معنا.": "This order is cancelled. If that's a mistake, contact us.",
    "ما لقينا طلباً بهالرقمين — تأكد من رقم الطلب ورقم الموبايل وجرّب مرة ثانية.": "No matching order — double-check the order number and mobile number, then try again.",
    "التوصيل يُتفق عليه عند تأكيد الطلب هاتفياً.": "Delivery is arranged when we confirm your order by phone.",
    "إتمام الطلب": "Checkout",

    # --- السلة ---
    "سلة التسوّق": "Shopping cart",
    "أُضيف للسلة": "Added to cart",
    "اعرض السلة": "View cart",
    "قطعة": "item",
    "أنقص الكمية": "Decrease quantity",
    "زد الكمية": "Increase quantity",
    "وصلت أقصى كمية متوفرة": "Maximum available quantity reached",
    "حذف": "Remove",
    "متابعة التسوّق": "Continue shopping",
    "سلتك فاضية بعد.": "Your cart is still empty.",

    # --- الكاتالوج والبحث ---
    "مسار التنقّل": "Breadcrumb",
    "ما في منتجات مطابقة بهالتصنيف.": "No matching products in this category.",
    "ما في تصنيفات بعد.": "No categories yet.",
    "ترتيب": "Sort",
    "الأحدث": "Newest",
    "السعر: من الأرخص": "Price: low to high",
    "السعر: من الأغلى": "Price: high to low",
    "المتوفر فقط": "In stock only",
    "طبّق": "Apply",
    "صفحات": "Pages",
    "السابق": "Previous",
    "صفحة %(current)s من %(total)s": "Page %(current)s of %(total)s",
    "التالي": "Next",
    "كل النتائج عن «%(q)s»": "All results for “%(q)s”",
    "خصم %(discount)s٪": "%(discount)s%% off",
    "البائع:": "Seller:",
    "متوفر": "In stock",
    "نفدت الكمية": "Out of stock",
    "دفع عند الاستلام": "Cash on delivery",
    "أضف للسلة": "Add to cart",
    "شارك المنتج عالواتساب": "Share on WhatsApp",
    "الوصف": "Description",
    "المواصفات": "Specifications",
    "منتجات مشابهة": "Similar products",
    "بحث: %(q)s": "Search: %(q)s",
    "نتائج البحث عن «%(q)s»": "Search results for “%(q)s”",
    "ما لقينا شي عن «%(q)s» — جرّب كلمة أبسط أو أقصر.": "We couldn't find anything for “%(q)s” — try a simpler or shorter word.",
    "تصفّح التصنيفات": "Browse categories",
    "البحث": "Search",
    "اكتب بشريط البحث فوق شو عم تدوّر عليه — ونحن نصطاده لك.": "Type what you're looking for in the search bar above — and we'll catch it for you.",

    # --- الهيكل العام ---
    "الصَّيَّاد": "Al-Sayyad",
    "دوّر عن أي شي…": "Search for anything…",
    "بحث": "Search",
    "القائمة الرئيسية": "Main menu",
    "الرئيسية": "Home",
    "التصنيفات": "Categories",
    "السلة": "Cart",
    "حسابي": "My account",
    "روابط الموقع": "Site links",
    "عن الصَّيَّاد": "About Al-Sayyad",
    "تواصل معنا": "Contact us",
    "تتبع طلبك": "Track your order",
    "سوقك السوري الموثوق": "Your trusted Syrian marketplace",
    "التنقّل الأساسي": "Primary navigation",
    "ل.س": "SYP",
    "ابدأ التسوّق": "Start shopping",

    # --- 404 ---
    "الصفحة غير موجودة": "Page not found",
    "ما في شي هون!": "Nothing here!",
    "الصفحة يلي بتدوّر عليها غير موجودة أو انتقلت — جرّب البحث أو ارجع للرئيسية.": "The page you're looking for doesn't exist or has moved — try searching or go back home.",

    # --- الرئيسية وعن الصياد وتواصل ---
    "اطلب… ونحن نصطاد لك": "Ask — and we'll catch it for you",
    "الصَّيَّاد سوق سوري إلكتروني: قُل ما تبحث عنه — ونُحضِر لك الصيد. سوقٌ موثوق وواسع، صُمِّم ليكون سهلاً على كل بيت سوري، حتى لو كانت هذه أول مرة تتسوق فيها أونلاين.": "Al-Sayyad is a Syrian online marketplace: name what you seek — we bring you the catch. A trusted, abundant marketplace built to feel effortless for every Syrian household, even on your very first online order.",
    "موثوق": "Trusted",
    "ادفع عند الاستلام — ما تدفع شي قبل ما توصلك أغراضك وتشوفها بعينك.": "Cash on delivery — pay nothing until your goods arrive and you see them yourself.",
    "وافر": "Abundant",
    "كل احتياجات بيتك بمكان واحد، من الإلكترونيات للمطبخ.": "Everything your home needs in one place, from electronics to the kitchen.",
    "بسيط": "Effortless",
    "شاشات واضحة وخطوات قليلة — بلا تسجيل حسابات ولا تعقيد.": "Clear screens and few steps — no forced sign-ups, no complexity.",
    "قريب": "Local",
    "سوري بالكامل: باللغة، وبالليرة، وبطرق الدفع، وبالناس.": "Fully Syrian: the language, the lira, the payment, the people.",
    "سؤال عن طلب؟ منتج؟ اقتراح؟ نحن موجودون.": "A question about an order? A product? A suggestion? We're here.",
    "اتصال": "Call",
    "واتساب": "WhatsApp",
    "إيميل": "Email",
    "ولتتبع طلبك بأي وقت:": "And to track your order any time:",
    "صفحة طلباتي": "My orders page",
    "سوقك السوري": "Your Syrian marketplace",
    "كل شي لبيتك، بمكان واحد.": "Everything for your home, in one place.",
    "اطلب… ونحن نصطاد لك.": "Ask… and we'll catch it for you.",
    "تسوّق حسب التصنيف": "Shop by category",
    "وصل حديثاً": "New arrivals",
    "الشباك فاضية بعد — المنتجات عالطريق!": "The nets are still empty — products are on the way!",
    "ليش الصَّيَّاد؟": "Why Al-Sayyad?",
    "دفعك وتوصيلك بأمان.": "Safe payment and delivery.",
    "كل شي للبيت بمكان واحد.": "Everything for the home in one place.",
    "سهل حتى لأول طلب أونلاين.": "Easy even for your first online order.",
    "سوري بالكامل: لغة ودفع وناس.": "Fully Syrian: language, payment, people.",

    # --- دليل المكوّنات (صفحة تطوير) ---
    "دليل المكوّنات": "Component guide",
    "كل قطع الواجهة وحالاتها بمكان واحد. أي مكوّن منبنيه مرّة ومنستعمله بكل الصفحات.": "Every UI piece and its states in one place. Build a component once, use it on every page.",
    "الألوان (Tokens)": "Colors (tokens)",
    "كل لون معرّف مرّة وحدة كمتغيّر في tokens.css.": "Every color is defined once as a variable in tokens.css.",
    "الطباعة": "Typography",
    "عنوان رئيسي للصفحة": "Page heading",
    "عنوان قسم": "Section heading",
    "عنوان فرعي": "Subheading",
    "نص أساسي مريح للقراءة على الموبايل والشاشات الكبيرة.": "Body text that reads comfortably on mobile and large screens.",
    "نص صغير للملاحظات والتفاصيل.": "Small text for notes and details.",
    "الأزرار": "Buttons",
    "أنواع وحالات (عادي / معطّل / تحميل).": "Variants and states (normal / disabled / loading).",
    "الشارات": "Badges",
    "شارات الحالة وشارات الدفع.": "Status and payment badges.",
    "الحقول": "Fields",
    "حقل عادي / مع مساعدة / إلزامي / مع خطأ.": "Normal / with help / required / with error.",
    "البطاقة العامة": "Card",
    "حاوية لأي محتوى.": "A container for any content.",
    "عنوان البطاقة": "Card title",
    "نص توضيحي قصير داخل البطاقة.": "Short descriptive text inside the card.",
    "بطاقات المنتجات": "Product cards",
    "بيانات تجريبية الآن؛ بالموديول M4 منمرّر منتجات حقيقية من قاعدة البيانات.": "Demo data for now; module M4 feeds real products from the database.",
}

# صيغ الجمع: (المفرد بالعربية) -> (مفرد إنجليزي، جمع إنجليزي)
PLURALS = {
    "قطعة واحدة": ("One item", "%(n)s items"),
    "منتج واحد": ("One product", "%(n)s products"),
    "نتيجة واحدة": ("One result", "%(n)s results"),
}

HEADER_FIXES = {
    '"Project-Id-Version: PACKAGE VERSION\\n"': '"Project-Id-Version: Al-Sayyad\\n"',
    '"Language: \\n"': '"Language: en\\n"',
    '"Language-Team: LANGUAGE <LL@li.org>\\n"': '"Language-Team: en\\n"',
}


def read_string(block):
    """يعيد بناء نص po متعدد الأسطر: msgid "" "a" "b" -> ab

    كل جزء مقتبس يُلتقط لوحده — إياك و(.*) الجشعة مع DOTALL:
    كانت تبتلع علامات الاقتباس بين الأجزاء وتفسد المفتاح.
    """
    return "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', block))


def main():
    text = PO_PATH.read_text(encoding="utf-8")
    for old, new in HEADER_FIXES.items():
        text = text.replace(old, new)
    text = text.replace("#, fuzzy\n", "")          # الترويسة لم تعد مسودة

    entries = text.split("\n\n")
    missing, done = [], 0

    for i, entry in enumerate(entries):
        if "msgid " not in entry or 'msgid ""\nmsgstr' in entry:
            continue                                # الترويسة أو ليست مدخلة

        msgid_m = re.search(r'msgid ((?:"[^\n]*"\n?)+?)(?=msgid_plural|msgstr)', entry)
        if not msgid_m:
            continue
        msgid = read_string(msgid_m.group(1))

        if "msgid_plural" in entry:
            if msgid not in PLURALS:
                missing.append(msgid)
                continue
            one, many = PLURALS[msgid]
            entry = re.sub(r'msgstr\[0\] ""', f'msgstr[0] "{one}"', entry)
            entry = re.sub(r'msgstr\[1\] ""', f'msgstr[1] "{many}"', entry)
        else:
            if msgid not in TRANSLATIONS:
                missing.append(msgid)
                continue
            translation = TRANSLATIONS[msgid].replace('"', '\\"')
            entry, n = re.subn(r'msgstr ""(?!\n")', f'msgstr "{translation}"', entry)
            if n == 0:                              # مترجمة سابقاً — حدّثها
                entry = re.sub(r'msgstr "(?:[^"\\]|\\.)*"',
                               f'msgstr "{translation}"', entry)
        entries[i] = entry
        done += 1

    PO_PATH.write_text("\n\n".join(entries), encoding="utf-8", newline="\n")
    print(f"translated: {done}")
    if missing:
        print(f"MISSING ({len(missing)}):")
        for m in missing:
            print(" -", m)
        sys.exit(1)


if __name__ == "__main__":
    main()
