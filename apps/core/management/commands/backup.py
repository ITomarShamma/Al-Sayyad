# -*- coding: utf-8 -*-
"""نسخة احتياطية كاملة للمتجر: قاعدة البيانات + صور المنتجات في zip واحد.

    python manage.py backup               # إلى مجلد backups/ (خارج git)
    python manage.py backup --keep 30     # احتفظ بآخر 30 نسخة بدل 14
    python manage.py backup --dir D:\\نسخ  # وجهة أخرى (قرص خارجي مثلاً)

داخل الملف sayyad-backup-<تاريخ>.zip:
    db.json  — كل البيانات عبر dumpdata (يعمل على SQLite وPostgreSQL سواء)
    media/   — صور المنتجات كما هي

الاسترجاع على قاعدة جديدة فارغة:
    python manage.py migrate
    python manage.py loaddata db.json     (بعد فك الضغط)
    ثم انسخ مجلد media/ من النسخة إلى جذر المشروع

الجدولة (هي «الأتمتة» — الأمر نفسه لا يجدول نفسه):
    Windows:  schtasks /Create /SC DAILY /ST 03:30 /TN "AlSayyad Backup"
              /TR "C:\\Al-Sayyad\\.venv\\Scripts\\python.exe C:\\Al-Sayyad\\manage.py backup"
    Linux:    30 3 * * *  /srv/alsayyad/.venv/bin/python /srv/alsayyad/manage.py backup
"""

import zipfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# جداول لا معنى لنسخها: تُعاد تلقائياً مع migrate أو هي مؤقتة بطبيعتها
EXCLUDED = ["contenttypes", "auth.permission", "sessions", "admin.logentry"]


class Command(BaseCommand):
    help = "نسخة احتياطية (قاعدة البيانات + الصور) في zip واحد مع تدوير القديم."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=None,
                            help="مجلد الحفظ (الافتراضي: backups/ بجذر المشروع)")
        parser.add_argument("--keep", type=int, default=14,
                            help="عدد النسخ المحفوظة — الأقدم يُحذف تلقائياً (الافتراضي 14)")

    def handle(self, *args, **options):
        if options["keep"] < 1:
            raise CommandError("--keep يجب أن يكون 1 على الأقل.")
        out_dir = Path(options["dir"] or settings.BACKUP_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        stamp = timezone.localtime().strftime("%Y-%m-%d_%H%M%S")
        zip_path = out_dir / f"sayyad-backup-{stamp}.zip"

        # 1) قاعدة البيانات كلها نصاً واحداً (JSON) في الذاكرة
        data = StringIO()
        call_command("dumpdata", exclude=EXCLUDED, stdout=data)

        # 2) الضغط: db.json + كل ملف تحت media/
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as backup:
            backup.writestr("db.json", data.getvalue())
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                for file in sorted(media_root.rglob("*")):
                    if file.is_file():
                        backup.write(file, Path("media") / file.relative_to(media_root))

        # 3) التدوير: فوق الحد؟ الأقدم يذهب (الأسماء بالتاريخ = ترتيبها زمني)
        existing = sorted(out_dir.glob("sayyad-backup-*.zip"))
        for old in existing[:-options["keep"]]:
            old.unlink()
            self.stdout.write(f"حُذفت نسخة قديمة: {old.name}")

        size_kb = zip_path.stat().st_size / 1024
        kept = min(len(existing), options["keep"])
        self.stdout.write(self.style.SUCCESS(
            f"✓ {zip_path.name} ({size_kb:,.0f} KB) — النسخ المحفوظة الآن: {kept}"))
