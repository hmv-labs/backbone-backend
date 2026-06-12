from django.contrib import admin

from . import models


@admin.register(models.EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "subject",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
