"""تخصيص عام للوحة التحكم (يُحمَّل تلقائياً مع admin autodiscover)."""

from django.contrib import admin

admin.site.site_header = "لوحة تحكم الصَّيَّاد"
admin.site.site_title = "الصَّيَّاد"
admin.site.index_title = "إدارة المتجر"
