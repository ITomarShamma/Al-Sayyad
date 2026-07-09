"""اختبارات core: أمر النسخ الاحتياطي (M28)."""

import io
import json
import tempfile
import zipfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.catalog.models import Category, Product


def run_backup(out_dir, **options):
    stdout = io.StringIO()
    call_command("backup", dir=str(out_dir), stdout=stdout, **options)
    return stdout.getvalue()


class BackupCommandTests(TestCase):
    """M28: النسخة تُنشأ، تحوي البيانات والصور، تُسترجع، وتُدوَّر."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "backups"
        self.addCleanup(self.tmp.cleanup)
        cat = Category.objects.create(name="إلكترونيات")
        self.product = Product.objects.create(
            category=cat, name="سماعة لاسلكية", price=Decimal("250000"), stock=5)

    def backup_zip(self):
        return next(self.out.glob("sayyad-backup-*.zip"))

    def test_backup_creates_zip_with_db_json(self):
        output = run_backup(self.out)
        self.assertIn("✓", output)
        with zipfile.ZipFile(self.backup_zip()) as backup:
            data = json.loads(backup.read("db.json"))
        names = {row["fields"].get("name") for row in data
                 if row["model"] == "catalog.product"}
        self.assertIn("سماعة لاسلكية", names)
        # الجداول الآلية مستثناة — تعود مع migrate ولا تُهاجَر بالبيانات
        models = {row["model"] for row in data}
        self.assertFalse({m for m in models if m.startswith("contenttypes")})

    def test_media_files_included(self):
        media = Path(self.tmp.name) / "media"
        (media / "products").mkdir(parents=True)
        (media / "products" / "صورة.jpg").write_bytes(b"fake-image-bytes")
        with override_settings(MEDIA_ROOT=media):
            run_backup(self.out)
        with zipfile.ZipFile(self.backup_zip()) as backup:
            self.assertIn("media/products/صورة.jpg", backup.namelist())

    def test_backup_restores_deleted_data(self):
        """الاختبار الأهم: نسخة ← حذف ← loaddata ← البيانات رجعت."""
        run_backup(self.out)
        with zipfile.ZipFile(self.backup_zip()) as backup:
            db_json = Path(self.tmp.name) / "db.json"
            db_json.write_bytes(backup.read("db.json"))
        product_pk = self.product.pk
        self.product.delete()
        self.assertFalse(Product.objects.filter(pk=product_pk).exists())
        call_command("loaddata", str(db_json), verbosity=0)
        restored = Product.objects.get(pk=product_pk)
        self.assertEqual(restored.name, "سماعة لاسلكية")
        self.assertEqual(restored.price, Decimal("250000"))

    def test_rotation_deletes_oldest_beyond_keep(self):
        self.out.mkdir(parents=True)
        for stamp in ("2026-01-01_000000", "2026-01-02_000000", "2026-01-03_000000"):
            (self.out / f"sayyad-backup-{stamp}.zip").write_bytes(b"old")
        run_backup(self.out, keep=2)
        kept = sorted(p.name for p in self.out.glob("sayyad-backup-*.zip"))
        self.assertEqual(len(kept), 2)                       # الحد محترم
        self.assertNotIn("sayyad-backup-2026-01-01_000000.zip", kept)  # الأقدم راح
        self.assertTrue(kept[-1].startswith("sayyad-backup-2026"))     # الجديدة هنا

    def test_keep_must_be_positive(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            run_backup(self.out, keep=0)
