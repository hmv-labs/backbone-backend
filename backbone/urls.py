from django.conf import settings
from importlib import import_module
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
]

for app in settings.BACKBONE_APPS:
    try:
        app_urls = import_module(f"{app}.urls")

        urlpatterns += [
            path("", include(app_urls))
        ]
    except ModuleNotFoundError:
        continue
