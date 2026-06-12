from django.urls import path
from . import views

app_name = "backbone.internals"

urlpatterns = [
    path("challenge/", views.ChallengeView.as_view(), name="challenge"),
    path("health-check/", views.HealthCheckView.as_view(), name="health_check"),
]
