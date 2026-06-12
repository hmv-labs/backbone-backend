from django.urls import path
from . import views

app_name = "backbone.emails"

urlpatterns = [
    path(
        "email-templates/",
        views.EmailTemplateViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "email-template-render/",
        views.EmailTemplateViewSet.as_view(
            {
                "post": "render_email_template",
            }
        ),
    ),
    path(
        "email-template/<str:name>/",
        views.EmailTemplateViewSet.as_view(
            {
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
]
