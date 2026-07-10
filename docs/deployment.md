# خطة نشر متجر الصَّيَّاد

> قرار الاستضافة + خطوات التنفيذ كاملة. ترافق `architecture.md`.
> آخر تحديث: 2026-07-10.

## أولاً: القرار — أين نستضيف؟

### لماذا صار الخيار أسهل في 2026

العائق التاريخي كان العقوبات: مزوّدون كثر كانوا يحجبون الزوار السوريين أو
يرفضون خدمة مواقع تستهدف سوريا. هذا تغيّر جذرياً:

- الولايات المتحدة أنهت برنامج عقوبات سوريا بالأمر التنفيذي 14312 (حزيران 2025)،
  وأُلغي «قانون قيصر» ضمن قانون الدفاع الوطني (كانون الأول 2025).
- الاتحاد الأوروبي رفع العقوبات الاقتصادية (مع إبقاء عقوبات تستهدف أشخاصاً بعينهم).
- عملياً: منصات كبرى (LinkedIn، Apple…) أزالت الحجب الشامل عن سوريا خلال 2025–2026،
  ومصرف سوريا المركزي أعلن اتفاقاً مع Visa (كانون الأول 2025).

النتيجة: **اختيار المزوّد اليوم مسألة سعر وكمون (latency) وطريقة دفع** —
لا مسألة حجب. تبقى التوصية باختبار الوصول من داخل سوريا أول أسبوع تشغيل.

### التوصية: Hetzner Cloud — خطة CX22 (ألمانيا)

| المعيار | **Hetzner CX22 (التوصية)** | DigitalOcean | Hostinger KVM2 | Contabo |
|---|---|---|---|---|
| السعر التقريبي | **€4.6/شهر** | $12/شهر (المكافئ) | ~$7/شهر | ~$6/شهر |
| المواصفات | 2 vCPU · 4GB RAM · 40GB NVMe | 2 vCPU · 2GB | 2 vCPU · 8GB | 4 vCPU · 8GB |
| الموقع الأقرب | نورمبرغ/فالكنشتاين (ألمانيا) | فرانكفورت | ليتوانيا/ألمانيا | ألمانيا |
| الكمون لدمشق | ~70–110ms (ممتاز لموقع متجر) | مشابه | مشابه | مشابه |
| الدفع | بطاقة / PayPal | بطاقة / PayPal | بطاقة / PayPal / **عملات رقمية** | بطاقة / PayPal |
| الملاحظة | أفضل سعر/أداء وسمعة تشغيلية ممتازة | أغلى لنفس المواصفات | خيار احتياطي إن تعذّر الدفع | رخيص لكن دعمه أضعف |

**قاعدة القرار:** Hetzner CX22 ما دام الدفع ببطاقة/PayPal متاحاً لعمر.
إن تعذّر الدفع → Hostinger (يقبل طرق دفع أوسع بينها العملات الرقمية).
الخطة CX22 تكفي المتجر سنوات؛ الترقية لاحقاً بضغطة زر بلا إعادة تثبيت.

### الدومين

- عملي وسريع: `.com` أو `.store` من Namecheap/Porkbun (~$10/سنة).
- `.sy` لاحقاً للهيبة المحلية (يتطلب تسجيلاً عبر الجهات السورية — لا يعطّل الإطلاق).
- DNS: سجلّا `A` للدومين و`www` نحو IP السيرفر. (Cloudflare اختياري لاحقاً —
  يبدأ «رمادياً» DNS-only حتى لا يتعقّد ضبط الـHTTPS أول مرة.)

## ثانياً: جاهز في الكود منذ الآن (لا عمل إضافياً)

| الجاهزية | أين |
|---|---|
| إعدادات إنتاج منفصلة تقرأ الأسرار من `.env` | `config/settings/prod.py` |
| PostgreSQL بلا تغيير كود | نفس الملف (`DB_*` من البيئة) |
| تقوية HTTPS (SSL redirect، HSTS، كوكيز آمنة، proxy header) | نفس الملف |
| كاش مشترك لعدّادات حماية الدخول (M25) | `CACHES` DatabaseCache — أُضيف بهذه الخطة |
| متطلبات السيرفر | `requirements-prod.txt` (psycopg + gunicorn) |
| نسخ احتياطي بأمر واحد + تدوير | `manage.py backup` (M28) |
| ترجمات مجمَّعة `.mo` مرفوعة بالمستودع | `locale/en/…` |

## ثالثاً: خطوات التنفيذ (جلسة واحدة ~ساعتان)

> المستخدم `deploy`، المسار `/srv/alsayyad`، الدومين `alsayyad.com` — بدّل ما يلزم.

### 1) سيرفر جديد + تأمين أساسي

Ubuntu 24.04 LTS. أول دخول بـroot:

```bash
adduser deploy && usermod -aG sudo deploy
rsync -a ~/.ssh /home/deploy/ && chown -R deploy:deploy /home/deploy/.ssh
# من ثم الدخول دائماً بـdeploy، وتعطيل دخول root وكلمات السر:
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo apt update && sudo apt -y upgrade
sudo apt -y install ufw fail2ban unattended-upgrades
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
```

### 2) تثبيت البرمجيات

```bash
sudo apt -y install python3.12-venv python3-dev build-essential \
                    nginx postgresql libpq-dev git
```

### 3) قاعدة البيانات

```bash
sudo -u postgres psql -c "CREATE USER alsayyad WITH PASSWORD '<كلمة-سر-قوية>';"
sudo -u postgres psql -c "CREATE DATABASE alsayyad OWNER alsayyad;"
```

### 4) الكود والبيئة

```bash
sudo mkdir -p /srv/alsayyad && sudo chown deploy:deploy /srv/alsayyad
git clone https://github.com/ITomarShamma/Al-Sayyad.git /srv/alsayyad
cd /srv/alsayyad
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-prod.txt
cp .env.example .env   # ثم عبّئ قيم الإنتاج:
```

قيم `.env` على السيرفر (الفروق المهمة عن التطوير):

```ini
DJANGO_SECRET_KEY=<مولَّد جديد طويل — python -c "import secrets;print(secrets.token_urlsafe(64))">
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=alsayyad.com,www.alsayyad.com
DB_PASSWORD=<نفس كلمة سر الخطوة 3>
EMAIL_HOST=smtp.gmail.com          # مع App Password لإشعارات الطلبات
EMAIL_HOST_USER=tahashamma222@gmail.com
EMAIL_HOST_PASSWORD=<App Password>
BACKUP_DIR=/srv/backups/alsayyad
```

### 5) تجهيز Django

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py migrate
python manage.py createcachetable          # جدول الكاش المشترك (حماية الدخول)
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check --deploy            # يجب أن يمرّ بلا تحذيرات حمراء
```

### 6) نقل بيانات التطوير (اختياري — والمخرَج هو نفسه نسخة M28)

على جهاز التطوير: `python manage.py backup` ثم ارفع الـzip للسيرفر:

```bash
unzip sayyad-backup-*.zip -d restore/
python manage.py loaddata restore/db.json
cp -r restore/media/ /srv/alsayyad/media/
```

### 7) Gunicorn كخدمة نظام

`/etc/systemd/system/alsayyad.service`:

```ini
[Unit]
Description=Al-Sayyad (Gunicorn)
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/srv/alsayyad
Environment=DJANGO_SETTINGS_MODULE=config.settings.prod
ExecStart=/srv/alsayyad/.venv/bin/gunicorn config.wsgi:application \
          --workers 3 --bind unix:/run/alsayyad.sock \
          --access-logfile - --error-logfile -
RuntimeDirectory=alsayyad
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now alsayyad
```

### 8) Nginx أمامه

`/etc/nginx/sites-available/alsayyad`:

```nginx
server {
    listen 80;
    server_name alsayyad.com www.alsayyad.com;

    client_max_body_size 10M;          # صور المنتجات من لوحة التحكم

    location /static/ { alias /srv/alsayyad/staticfiles/; expires 30d; }
    location /media/  { alias /srv/alsayyad/media/;       expires 30d; }

    location / {
        proxy_pass http://unix:/run/alsayyad.sock;
        proxy_set_header Host $host;
        # ضروريان: الأول ليعرف Django أن الاتصال آمن (SECURE_PROXY_SSL_HEADER)،
        # والثاني ليصل عنوان الزائر الحقيقي لعدّادات حماية الدخول (M25)
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/alsayyad /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

> ملاحظة M25: مرّر عنوان الزائر الحقيقي إلى Django. الأبسط اعتماد وحدة
> `ngx_http_realip_module` أو ضبط middleware يقرأ `X-Real-IP` — وإلا صار كل
> الزوار بعنوان واحد (127.0.0.1) فيتشاركون قفل محاولات الدخول. تُختبر بـ:
> محاولتا دخول خاطئتان من جهازين مختلفين يجب ألا تجمعا على عدّاد واحد.

### 9) HTTPS

```bash
sudo apt -y install certbot python3-certbot-nginx
sudo certbot --nginx -d alsayyad.com -d www.alsayyad.com
```

(التجديد تلقائي عبر systemd timer — تحقق: `sudo certbot renew --dry-run`.)

### 10) النسخ الاحتياطي المجدول

```bash
sudo mkdir -p /srv/backups/alsayyad && sudo chown deploy /srv/backups/alsayyad
crontab -e   # للمستخدم deploy:
# 30 3 * * * cd /srv/alsayyad && DJANGO_SETTINGS_MODULE=config.settings.prod .venv/bin/python manage.py backup
```

لاحقاً (مستحسن): نسخ خارج السيرفر — `rclone` نحو أي تخزين سحابي، أو تنزيل
أسبوعي يدوي للـzip. النسخة على نفس السيرفر لا تحمي من ضياع السيرفر نفسه.

## رابعاً: فحوص يوم الإطلاق

- [ ] `python manage.py check --deploy` نظيف
- [ ] رسوم التوصيل الحقيقية للمحافظات الـ14 (لوحة التحكم ← مناطق التوصيل)
- [ ] طلب تجريبي كامل من موبايل حقيقي داخل سوريا: تصفح ← سلة ← إتمام ← تتبع
- [ ] وصل بريد «طلب جديد» + زر واتساب يفتح محادثة الزبون
- [ ] اللغتان تعملان والتبديل يثبت بالجلسة
- [ ] تنصيب الـPWA من كروم أندرويد + ظهور صفحة «ما في اتصال» بوضع الطيران
- [ ] لوحة المبيعات `/admin/dashboard/` للمدير فقط (تاجر تجريبي لا يراها)
- [ ] قفل الدخول: 5 محاولات خاطئة تقفل فعلاً (من جهازين لا تتشارك القفل)
- [ ] وُجدت نسخة احتياطية الليلة الأولى في `/srv/backups/alsayyad`

## خامساً: بعد الإطلاق

- **مراقبة:** UptimeRobot (مجاني) على `/` + تنبيه بريد عند السقوط.
- **أخطاء:** سجلّ Gunicorn عبر `journalctl -u alsayyad`؛ لاحقاً Sentry (خطة مجانية).
- **تحديث نسخة:** `git pull && pip install -r requirements-prod.txt && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart alsayyad`.
- **عند النمو:** Redis بدل DatabaseCache، وبحث PostgreSQL النصّي الكامل فوق
  `search_text` (مخطَّط له في `database-schema.md`)، وCloudflare أمام الموقع.
- **شام كاش:** عند وصول الـAPI — التطوير محلياً كالعادة، والتفعيل بالإنتاج
  متغيّرات `.env` فقط (النقطة جاهزة في `apps/orders/payments.py`).
