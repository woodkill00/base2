from django.urls import path
from . import views

urlpatterns = [
    path("items", views.items_list),
    path("items/", views.items_list),
    path("items/<int:item_id>", views.item_detail),
    path("items/<int:item_id>/", views.item_detail),
    path("items/create", views.item_create),
    path("items/create/", views.item_create),
]
