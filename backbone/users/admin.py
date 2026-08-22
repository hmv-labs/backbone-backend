from django.contrib import admin

from . import models


@admin.register(models.UserAvatar)
class UserAvatarAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "image",
        "created_at",
        "updated_at",
    )
