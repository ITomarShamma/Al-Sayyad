"""توليد الصور المصغّرة — صورة الموبايل 5MB تصير بطاقة 30KB.

بطاقات المنتجات صغيرة (~200-300px) لكن الصور المرفوعة من الموبايل ضخمة؛
تحميلها كاملة إهدار قاسٍ على اتصالات سوريا. نولّد نسخة مربّعة 480px
(كافية حتى لشاشات 2x) بصيغة JPEG مضغوطة، مرة واحدة عند الحفظ.
"""

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

THUMB_SIZE = (480, 480)
THUMB_QUALITY = 82


def make_thumbnail(image_field):
    """يرجع (اسم الملف، المحتوى) لمصغّرة مربّعة من حقل صورة، أو None عند الفشل."""
    try:
        # ننسخ البايتات ونرجع المؤشر للبداية — إياك تسكّر ملف الرفع:
        # الحفظ الأصلي بعدنا لسا بدو يقرأه (with ... يسكّره ويكسر الحفظ).
        image_field.open("rb")
        data = image_field.read()
        image_field.seek(0)

        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)      # يحترم دوران كاميرا الموبايل
        img = img.convert("RGB")                 # JPEG لا يدعم الشفافية
        img = ImageOps.fit(img, THUMB_SIZE)      # قصّ مركزي لمربّع
    except Exception:
        return None                              # ملف تالف؟ نتجاهل بلا كسر الحفظ

    buffer = BytesIO()
    img.save(buffer, "JPEG", quality=THUMB_QUALITY, optimize=True)
    name = f"{Path(image_field.name).stem}_thumb.jpg"
    return name, ContentFile(buffer.getvalue())
