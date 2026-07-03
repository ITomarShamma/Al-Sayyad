# هجرة بيانات: توليد المصغّرات للصور المرفوعة قبل هذه الميزة.
# الصور الجديدة تتولّد مصغّراتها تلقائياً في ProductImage.save().

from django.db import migrations

from apps.catalog.images import make_thumbnail


def backfill(apps, schema_editor):
    ProductImage = apps.get_model("catalog", "ProductImage")
    for pi in ProductImage.objects.filter(thumb="").exclude(image="").iterator():
        result = make_thumbnail(pi.image)
        if result:
            name, content = result
            pi.thumb.save(name, content, save=True)


def noop(apps, schema_editor):
    """التراجع: الحقل نفسه يُحذف بهجرة 0005 — الملفات تبقى بلا ضرر."""


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_productimage_thumb'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
