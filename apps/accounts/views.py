"""واجهات الحسابات: تسجيل، دخول/خروج، لوحة «حسابي»، الإعدادات."""

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from apps.orders.models import Order

from .forms import MerchantApplyForm, PhoneLoginForm, ProfileEditForm, SignupForm
from .models import Profile

User = get_user_model()


def signup(request):
    """إنشاء حساب زبون: الموبايل = اسم الدخول، ويسجَّل دخوله فوراً."""
    if request.user.is_authenticated:
        return redirect("accounts:account")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data["phone"],
            password=data["password1"],
            first_name=data["full_name"],
        )
        Profile.objects.create(user=user, phone=data["phone"])
        login(request, user)                      # لا نطلب منه الدخول بعد التسجيل
        messages.success(request, "أهلاً فيك بالصَّيَّاد! حسابك جاهز 🎣")
        return redirect("accounts:account")

    return render(request, "accounts/signup.html", {"form": form})


class PhoneLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = PhoneLoginForm
    redirect_authenticated_user = True


@login_required
def account(request):
    """لوحة «حسابي»: البيانات + آخر الطلبات + حالة التاجر إن وُجدت."""
    profile = getattr(request.user, "profile", None)
    merchant = getattr(request.user, "merchant_profile", None)
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")[:10]
    )
    return render(request, "accounts/account.html", {
        "profile": profile,
        "merchant": merchant,
        "orders": orders,
    })


@login_required
def edit(request):
    """إعدادات الحساب: الاسم والمدينة (الرقم = اسم الدخول، لا يُغيَّر ذاتياً)."""
    profile = getattr(request.user, "profile", None)
    initial = {
        "full_name": request.user.first_name,
        "city": profile.city if profile else "",
    }
    form = ProfileEditForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        request.user.first_name = form.cleaned_data["full_name"]
        request.user.save(update_fields=["first_name"])
        if profile:
            profile.city = form.cleaned_data["city"]
            profile.save(update_fields=["city", "updated_at"])
        messages.success(request, "انحفظت بياناتك ✓")
        return redirect("accounts:account")
    return render(request, "accounts/edit.html", {"form": form})


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:account")

    def form_valid(self, form):
        messages.success(self.request, "تغيّرت كلمة السر ✓")
        return super().form_valid(form)


@login_required
def merchant_apply(request):
    """طلب انضمام كتاجر — ينشأ «قيد المراجعة» حتى توافق إدارة المتجر."""
    if hasattr(request.user, "merchant_profile"):
        return redirect("accounts:account")       # قدّم سابقاً — حالته بحسابه

    form = MerchantApplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        merchant = form.save(commit=False)
        merchant.user = request.user
        merchant.save()
        messages.success(
            request, "وصلنا طلبك 🏪 — منراجعه ومنتواصل معك خلال يوم عمل.")
        return redirect("accounts:account")

    return render(request, "accounts/merchant_apply.html", {"form": form})
