from django.urls import include, path

app_name = "backbone.auth"

urlpatterns = [
    path("auth/", include("allauth.headless.urls", "headless")),
]
