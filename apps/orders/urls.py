from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/summary/", views.checkout_summary, name="checkout_summary"),
    path("order/<str:number>/", views.confirmation, name="confirmation"),
    path("track/", views.track, name="track"),
]
