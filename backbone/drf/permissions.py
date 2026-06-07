from rest_framework.permissions import BasePermission


class SuperuserOnlyPermission(BasePermission):
    def has_permission(self, request, view):  # pyright: ignore
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser
