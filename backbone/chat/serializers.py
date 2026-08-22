from json import JSONDecodeError
from json import loads as json_loads

from django.contrib.auth.models import User
from rest_framework import serializers

from backbone.users.serializers import (
    UserSummarySerializer,
    UserSummaryWithAvatarSerializer,
)

from . import models


class ConversationMemberSerializer(serializers.ModelSerializer):
    user = UserSummaryWithAvatarSerializer(read_only=True)

    class Meta:
        model = models.ConversationMember
        fields = ("user",)


class ConversationStateSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = models.ConversationState
        fields = (
            "last_read_sequence",
            "user",
        )


class ConversationLastMessageSerializer(serializers.ModelSerializer):
    thread = serializers.SerializerMethodField()
    created_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = models.Message
        fields = (
            "created_at",
            "created_by",
            "system_event",
            "system_event_data",
            "text",
            "thread",
            "type",
        )

    def get_thread(self, obj):
        if obj.conversation.is_thread:
            return {
                "parent_message": {
                    "public_id": str(obj.conversation.parent_message.public_id),
                }
            }
        return None


class ConversationSerializer(serializers.ModelSerializer):
    is_pinned = serializers.BooleanField(default=False, read_only=True)
    last_message = ConversationLastMessageSerializer(read_only=True)
    members = ConversationMemberSerializer(
        many=True, read_only=True, source="active_members"
    )
    states = ConversationStateSerializer(many=True, read_only=True)
    picture = serializers.ImageField(read_only=True)

    class Meta:
        model = models.Conversation
        fields = (
            "created_at",
            "created_by_id",
            "is_pinned",
            "is_thread",
            "kind",
            "last_message",
            "last_sequence",
            "members",
            "picture",
            "public_id",
            "states",
            "title",
            "updated_at",
            "attachment_counts",
        )


class ConversationCommonGroupSerializer(serializers.ModelSerializer):
    picture = serializers.ImageField(read_only=True)

    class Meta:
        model = models.Conversation
        fields = (
            "picture",
            "public_id",
            "title",
        )


class ConversationCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=models.Conversation.Kind.choices)
    title = serializers.CharField(required=False, allow_blank=True)
    users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    parent_message_public_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        kind = attrs["kind"]

        if kind == models.Conversation.Kind.DIRECT:
            if len(attrs["users"]) != 1:
                raise serializers.ValidationError(
                    {"users": ["Exactly one user is required."]}
                )

        elif kind == models.Conversation.Kind.GROUP:
            if not attrs["users"]:
                raise serializers.ValidationError(
                    {"users": ["At least one user is required."]}
                )

        elif kind == models.Conversation.Kind.THREAD:
            if "parent_message_public_id" not in attrs:
                raise serializers.ValidationError(
                    {"parent_message_public_id": ["This field is required."]}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        kind = validated_data["kind"]

        if kind == models.Conversation.Kind.THREAD:
            return models.Conversation.create_thread(
                created_by_id=request.user.id,
                parent_message_public_id=validated_data["parent_message_public_id"],
            )

        user_ids = [u.id for u in validated_data["users"]]

        if kind == models.Conversation.Kind.DIRECT:
            return models.Conversation.create_direct(
                created_by_id=request.user.id,
                user_id=user_ids[0],
            )

        if kind == models.Conversation.Kind.GROUP:
            title = validated_data["title"]

            # set a default title if nothing is present
            if not title:
                users = [
                    (u.get_full_name() or u.username) for u in validated_data["users"]
                ]
                title = ", ".join(users[:2])
                extra = users[2:]
                if extra:
                    title = f"{title}, +{len(extra)}"

            return models.Conversation.create_group(
                title=title,
                created_by_id=request.user.id,
                user_ids=user_ids,
            )

        raise AssertionError("Unhandled conversation kind")


class ConversationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Conversation
        fields = ("title", "picture")


class MessageThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Conversation
        fields = (
            "last_message_at",
            "last_sequence",
            "public_id",
        )


class MessageReactionSummarySerializer(serializers.Serializer):
    emoji = serializers.CharField()
    count = serializers.IntegerField()
    request_user_reacted = serializers.BooleanField()


class MessageImageAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.ImageField(read_only=True)

    class Meta:
        model = models.ImageAttachment
        fields = ("file", "filename", "width", "height", "size", "public_id")


class MessageDocumentAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(read_only=True)

    class Meta:
        model = models.DocumentAttachment
        fields = ("file", "filename", "content_type", "size", "public_id")


class MessageSerializer(serializers.ModelSerializer):
    created_by = UserSummaryWithAvatarSerializer(read_only=True)
    conversation = serializers.SerializerMethodField()
    thread = MessageThreadSerializer()
    reaction_summary = MessageReactionSummarySerializer(
        many=True,
        read_only=True,
        default=[],
    )

    imageattachment_set = MessageImageAttachmentSerializer(many=True)
    documentattachment_set = MessageDocumentAttachmentSerializer(many=True)

    class Meta:
        model = models.Message
        fields = (
            "sequence",
            "conversation",
            "created_at",
            "created_by",
            "text",
            "json",
            "public_id",
            "thread",
            "updated_at",
            "type",
            "system_event",
            "system_event_data",
            "system_event_target_message_public_id",
            "system_event_target_message_preview",
            "system_event_target_message_sequence",
            "is_pinned",
            "imageattachment_set",
            "documentattachment_set",
            "reaction_summary",  # annotated by MessageViewSet
        )

    def get_conversation(self, obj):
        return {
            "public_id": str(obj.conversation.public_id),
            "is_thread": obj.conversation.is_thread,
            "kind": obj.conversation.kind,
        }


class TiptapJSONContentSerializer(serializers.Serializer):
    type = serializers.CharField(required=False)
    attrs = serializers.DictField(required=False)
    content = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
    )
    marks = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    text = serializers.CharField(required=False)

    def validate(self, attrs):
        node_type = attrs.get("type")
        text = attrs.get("text")
        content = attrs.get("content")

        if node_type == "text":
            if text is None:
                raise serializers.ValidationError(
                    {"text": "Text nodes must have text."}
                )

            if content is not None:
                raise serializers.ValidationError(
                    {"content": "Text nodes cannot have content."}
                )

        if text is not None and node_type != "text":
            raise serializers.ValidationError(
                {"text": "Only text nodes can have text."}
            )

        if content is not None:
            for node in content:
                serializer = TiptapJSONContentSerializer(data=node)
                serializer.is_valid(raise_exception=True)

        return attrs


class TiptapDocumentSerializer(serializers.Serializer):
    """
    Validates json is at least structurally a Tiptap document while leaving the
    actual editor schema to Tiptap
    """

    type = serializers.CharField()
    content = TiptapJSONContentSerializer(many=True)

    def validate_type(self, value):
        if value != "doc":
            raise serializers.ValidationError("Root node must be a doc.")
        return value


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, default="")
    json = TiptapDocumentSerializer(required=False, default=dict)

    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
    )
    documents = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
    )

    def validate_json(self, value):
        """Turns multipart form's json string into a dict"""
        try:
            return json_loads(self.initial_data.get("json"))
        except JSONDecodeError as exc:
            raise serializers.ValidationError("Invalid JSON document.") from exc

    def validate(self, attrs):
        text = attrs.get("text")
        json = attrs.get("json")
        images = attrs.get("images")
        documents = attrs.get("documents")

        has_content = bool(text.strip())
        has_json = bool(json)
        has_attachments = bool(images or documents)

        # text and tiptap json must come in pair
        if has_content != has_json:
            raise serializers.ValidationError(
                {
                    "text": "Text and JSON content must be provided together.",
                    "json": "Text and JSON content must be provided together.",
                }
            )

        # a message must contain either content or at least one attachment
        if not has_content and not has_attachments:
            raise serializers.ValidationError(
                {
                    "text": "Message must contain text or at least one attachment.",
                }
            )

        return attrs


class LinkAttachmentSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()

    class Meta:
        model = models.LinkAttachment
        fields = (
            "public_id",
            "created_at",
            "message",
            "url",
            "title",
            "description",
            "image_url",
        )

    def get_message(self, obj):
        return {
            "public_id": obj.message.public_id,
            "sequence": obj.message.sequence,
        }


class ImageAttachmentSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()

    class Meta:
        model = models.ImageAttachment
        fields = (
            "public_id",
            "created_at",
            "message",
            "file",
            "filename",
            "size",
            "width",
            "height",
        )

    def get_message(self, obj):
        return {
            "public_id": obj.message.public_id,
            "sequence": obj.message.sequence,
        }


class DocumentAttachmentSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()

    class Meta:
        model = models.DocumentAttachment
        fields = (
            "public_id",
            "created_at",
            "message",
            "file",
            "filename",
            "size",
            "content_type",
        )

    def get_message(self, obj):
        return {
            "public_id": obj.message.public_id,
            "sequence": obj.message.sequence,
        }
