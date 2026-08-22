from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from . import models


@admin.register(models.Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "kind",
        "direct_key",
        "title",
        "created_by",
        "created_at",
        "updated_at",
        "parent_message",
        "last_message",
        "last_message_at",
    )


@admin.register(models.ConversationState)
class ConversationStateAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "user",
        "is_pinned",
        "last_read_message",
        "last_read_message_at",
        "last_read_sequence",
        "created_at",
    )


@admin.register(models.ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_filter = ("status", "role")
    search_fields = ("conversation__public_id",)

    list_display = (
        "conversation",
        "user",
        "added_by",
        "role",
        "status",
        "status_changed_by",
        "status_changed_at",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "added_by", "status_changed_by", "conversation")
        )


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    search_fields = ("conversation__public_id", "sequence")
    list_filter = ("is_pinned", "type")
    list_display = (
        "public_id",
        "conversation",
        "created_by",
        "created_at",
        "type",
        "system_event",
        "system_event_target_message_public_id",
        "sequence",
        "is_pinned",
        "text",
    )
    formfield_overrides = {
        JSONField: {"widget": JSONEditorWidget},
    }

    def _has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("conversation", "created_by")
        )


@admin.register(models.LinkAttachment)
class LinkAttachmentAdmin(admin.ModelAdmin):
    search_fields = ("message__conversation__public_id",)
    list_display = (
        "public_id",
        "message",
        "created_at",
        "url",
        "title",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.ImageAttachment)
class ImageAttachmentAdmin(admin.ModelAdmin):
    search_fields = ("message__conversation__public_id",)
    list_display = (
        "public_id",
        "message",
        "created_at",
        "file",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.DocumentAttachment)
class DocumentAttachmentAdmin(admin.ModelAdmin):
    search_fields = ("message__conversation__public_id",)
    list_display = (
        "public_id",
        "message",
        "created_at",
        "file",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
