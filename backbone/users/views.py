from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from . import serializers


class UserSearchViewSet(ModelViewSet):
    serializer_class = serializers.UserSummaryWithAvatarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects.filter(is_active=True)
            .exclude(
                Q(id=self.request.user.id)
                | Q(is_superuser=True)
                | Q(is_staff=True)  # pyright: ignore
            )
            .select_related("avatar")
        )

    def filter_queryset(self, queryset):
        q = self.request.GET.get("q", "")
        if len(q) < 2:
            return queryset.none()

        exclude_ids = self.request.GET.getlist("exclude_ids")
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)

        return queryset.filter(
            Q(first_name__icontains=q)  # pyright: ignore
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email=q)
        )
