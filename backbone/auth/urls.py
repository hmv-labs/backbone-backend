from django.urls import include, path

urlpatterns = [
    # https://docs.allauth.org/en/dev/headless/installation.html
    # Even when using headless, the third-party provider endpoints are stil
    # needed for handling e.g. the OAuth handshake. The account views
    # can be disabled using `HEADLESS_ONLY = True`.
    path("auth-social/", include("allauth.urls")),
    path("auth/", include("allauth.headless.urls", "headless")),
]
