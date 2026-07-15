"""لوحة تحكم الحسابات — مراجعة التجّار والموافقة عليهم بضغطة."""

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .forms import RateLimitedAdminLoginForm
from .models import MerchantProfile, Profile

MERCHANT_GROUP_NAME = "تاجر"

# دخول لوحة التحكم بنفس حماية التخمين (M25) — انظر accounts/ratelimit.py
admin.site.login_form = RateLimitedAdminLoginForm


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__first_name", "user__username", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "phone", "city",
                    "approval_display", "created_at")
    list_filter = ("is_approved", "city")
    search_fields = ("store_name", "user__username", "phone")
    readonly_fields = ("created_at", "updated_at")
    actions = ["approve_merchants"]

    @admin.display(description="الحالة", ordering="is_approved")
    def approval_display(self, obj):
        if obj.is_approved:
            return format_html('<b style="color:#15803D;">● مفعّل</b>')
        return format_html('<b style="color:#B45309;">● قيد المراجعة</b>')

    @admin.action(description="✓ الموافقة على التجّار المحدّدين")
    def approve_merchants(self, request, queryset):
        """الموافقة = تفعيل + دخول محدود للوحة التحكم (منتجاته فقط).

        ثلاث خطوات لكل تاجر:
        1. is_approved=True — متجره يصير فعّالاً.
        2. عضوية مجموعة «تاجر» + is_staff — يفتح لوحة التحكم بصلاحيات
           المجموعة فقط (المجموعة وصلاحياتها تُنشأ بهجرة بيانات).
        3. دوره بالملف الشخصي يصير «تاجر».
        """
        group, _ = Group.objects.get_or_create(name=MERCHANT_GROUP_NAME)
        approved = 0
        for merchant in queryset.filter(is_approved=False):
            merchant.is_approved = True
            merchant.save(update_fields=["is_approved", "updated_at"])
            user = merchant.user
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            user.groups.add(group)
            profile = getattr(user, "profile", None)
            if profile:
                profile.role = Profile.Role.MERCHANT
                profile.save(update_fields=["role", "updated_at"])
            approved += 1
        self.message_user(
            request, f"تمت الموافقة على {approved} تاجر/تجّار ✓", messages.SUCCESS)
