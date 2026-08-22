from django.urls import path

from . import views

app_name = "backbone.users"

urlpatterns = [
    path("", views.UserSearchViewSet.as_view({"get": "list"})),
]
