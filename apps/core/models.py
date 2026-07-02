from django.db import models


class TimeStampedModel(models.Model):
    """أساس مشترك: يضيف تاريخ الإنشاء وآخر تعديل لأي جدول يرث منه.

    abstract = True يعني: هذا ليس جدولاً بحد ذاته — مجرّد حقول جاهزة
    تُنسخ لكل موديل يرث منه (Category, Product, …).
    """

    created_at = models.DateTimeField("أُنشئ في", auto_now_add=True)
    updated_at = models.DateTimeField("آخر تعديل", auto_now=True)

    class Meta:
        abstract = True
