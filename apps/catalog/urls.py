from django.urls import path

from . import views

app_name = "catalog"

# ملاحظة مهمة: نستعمل <str:slug> وليس <slug:slug> —
# محوّل slug الجاهز في Django يقبل أحرفاً لاتينية فقط،
# ومعرّفاتنا عربية (سماعة-لاسلكية) فلا تطابقه.
urlpatterns = [
    path("categories/", views.category_list, name="category_list"),
    path("search/", views.search, name="search"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("c/<str:slug>/", views.category_detail, name="category"),
    path("p/<str:slug>/", views.product_detail, name="product"),
    path("p/<int:product_id>/review/", views.submit_review, name="submit_review"),
]
