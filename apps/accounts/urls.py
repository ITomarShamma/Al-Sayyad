from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.account, name="account"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.PhoneLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("edit/", views.edit, name="edit"),
    path("password/", views.ChangePasswordView.as_view(), name="password_change"),
    path("merchant/apply/", views.merchant_apply, name="merchant_apply"),
]
