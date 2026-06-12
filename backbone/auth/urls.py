from django.urls import include, path
from . import views

urlpatterns = [
    # https://docs.allauth.org/en/dev/headless/installation.html
    path("auth/", include("allauth.headless.urls", "headless")),
    # Even when using headless, the third-party provider endpoints are stil
    # needed for handling e.g. the OAuth handshake. The account views
    # can be disabled using `HEADLESS_ONLY = True`.
    path("auth/social/", include("allauth.urls")),
    path("auth/user/", views.UserViewSet.as_view({"patch": "partial_update"})),
    path("auth/user/password-check/", views.PasswordCheckView.as_view()),
]
