# هجرة بيانات: مجموعات الأدوار الأربع بصلاحياتها.
#
# «الأدوار المختلفة بأسماء مختلفة» للوحة التحكم:
#   مدير المتجر    — كل شيء بالمتجر (بلا إدارة مستخدمي النظام)
#   موظف الطلبات   — يشاهد ويغيّر حالة الطلبات فقط
#   مدخل بيانات    — يضيف/يعدّل الكاتالوج، لا يحذف
#   تاجر           — منتجاته فقط (العزل في ProductAdmin.get_queryset)
#
# عمر ينشئ الموظفين من لوحة التحكم (مستخدم + is_staff) ويضمّهم للمجموعة
# المناسبة — الصلاحيات تلحق العضوية تلقائياً.

from django.apps import apps as django_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUPS = {
    "مدير المتجر": {
        "catalog": ["add", "change", "delete", "view"],   # كل نماذج الكاتالوج
        "orders": ["add", "change", "delete", "view"],
        "accounts": ["change", "view"],                    # مراجعة التجّار والملفات
    },
    "موظف الطلبات": {
        "orders": ["view", "change"],
    },
    "مدخل بيانات": {
        "catalog": ["add", "change", "view"],              # بلا حذف — عطّل بدل ما تحذف
    },
    "تاجر": {
        # يظهر له من الكاتالوج ما تسمح به الصلاحيات، والعزل لمنتجاته
        # يفرضه ProductAdmin (get_queryset/save_model)
        "catalog": ["add", "change", "view"],
    },
}


def create_groups(apps, schema_editor):
    # الصلاحيات تُنشأ عادة بعد اكتمال كل الهجرات (post_migrate) —
    # ننشئها يدوياً الآن حتى تجدها هذه الهجرة على قاعدة جديدة (كالاختبارات).
    for app_config in django_apps.get_app_configs():
        create_permissions(app_config, apps=apps, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, spec in GROUPS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        perms = []
        for app_label, actions in spec.items():
            for model in django_apps.get_app_config(app_label).get_models():
                model_name = model._meta.model_name
                perms += list(Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename__in=[f"{a}_{model_name}" for a in actions],
                ))
        group.permissions.set(perms)               # idempotent — يضبطها كما هي


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUPS.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        # الصلاحيات المطلوبة تخص نماذج هذه التطبيقات — لازم جداولها موجودة
        ('catalog', '0007_product_merchant'),
        ('orders', '0002_order_user'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
