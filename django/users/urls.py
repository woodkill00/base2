from django.urls import path
from . import views

urlpatterns = [
    path("", views.users_list),
    path("me", views.me),
]
