# هجرة بيانات: المحافظات السورية الـ14 كمناطق توصيل.
# الرسم يبدأ فارغاً (NULL = «يُتفق هاتفياً») — عمر يعبّي الأرقام الحقيقية
# من لوحة التحكم: الطلبات ← مناطق التوصيل.

from django.db import migrations

GOVERNORATES = [
    "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس",
    "إدلب", "دير الزور", "الرقة", "الحسكة", "درعا", "السويداء", "القنيطرة",
]


def seed(apps, schema_editor):
    DeliveryZone = apps.get_model("orders", "DeliveryZone")
    for i, name in enumerate(GOVERNORATES):
        DeliveryZone.objects.get_or_create(name=name, defaults={"sort_order": i})


def unseed(apps, schema_editor):
    DeliveryZone = apps.get_model("orders", "DeliveryZone")
    DeliveryZone.objects.filter(name__in=GOVERNORATES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_deliveryzone_order_delivery_fee'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
