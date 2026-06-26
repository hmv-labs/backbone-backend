from django.conf import settings
from django.conf.urls.static import static
from importlib import import_module
from django.urls import path, include

urlpatterns = []

for app in settings.BACKBONE_APPS:
    try:
        app_urls = import_module(f"{app}.urls")
        namespace = app.replace("backbone.", "")
        urlpatterns += [path(f"{namespace}/", include(app_urls, namespace))]
    except ModuleNotFoundError:
        continue


if settings.DEBUG:
    urlpatterns += (
        [
            path("__debug__/", include("debug_toolbar.urls", "djdt")),
        ]
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    )
