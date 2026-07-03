# هجرة بيانات (data migration): تعبئة search_text للمنتجات الموجودة أصلاً.
# المنتجات الجديدة تتعبّى تلقائياً في Product.save() — هذه للمخزون القديم فقط.

from django.db import migrations

from apps.catalog.search import normalize


def backfill(apps, schema_editor):
    # نستعمل النسخة التاريخية من الموديل (بدون save() المخصص)
    Product = apps.get_model("catalog", "Product")
    for product in Product.objects.all().iterator():
        product.search_text = normalize(f"{product.name} {product.description}")
        product.save(update_fields=["search_text"])


def noop(apps, schema_editor):
    """التراجع لا يحتاج شيئاً — الحقل نفسه يُحذف بهجرة 0002."""


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_product_search_text'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
