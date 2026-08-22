import uuid
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Iterable, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction
from django.db.models import Count, Prefetch, Q
from django.db.models.expressions import Exists, F, OrderBy, OuterRef, Subquery
from django.db.models.functions import JSONObject
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from PIL import Image

from backbone.users.serializers import UserSummarySerializer

from . import websocket_publisher


class ConversationQuerySet(models.QuerySet):
    def for_member(self, user, include_threads=False):
        """
        Returns conversations (direct or group) where the user is an active member.
        """
        filters = Q(
            members__user=user,
            members__status=ConversationMember.Status.ACTIVE,
        )

        if include_threads:
            filters |= Q(
                parent_message__conversation__members__user=user,
                parent_message__conversation__members__status=ConversationMember.Status.ACTIVE,
            )

        return self.filter(filters)

    def with_active_members(self):
        """
        Prefetch active members for use by the Conversation.active_members property.
        The private `_active_members` attribute is intentional: using `active_members`
        as `to_attr` would shadow the model property. The property checks for this
        prefetched attribute first and falls back to querying active members when the
        conversation was not loaded through this queryset.
        """
        return self.prefetch_related(
            Prefetch(
                "members",
                queryset=ConversationMember.objects.active(),
                to_attr="_active_members",
            )
        )

    def with_attachment_counts(self):
        """
        Annotate conversations with the number of link, image, and document
        attachments belonging to their messages.

        The result is stored on the instance as `_attachment_counts` so the
        Conversation.attachment_counts property can use the annotated value
        without issuing another query when the queryset already includes it.
        """
        return self.annotate(
            _attachment_counts=JSONObject(
                links=Count(
                    "messages__linkattachment",
                    distinct=True,
                ),
                images=Count(
                    "messages__imageattachment",
                    distinct=True,
                ),
                documents=Count(
                    "messages__documentattachment",
                    distinct=True,
                ),
            ),
        )

    def order_for(self, user):
        """
        Orders the qs based on the user's conversation state is_pinned flag and
        conversation last_message.
        """
        return self.annotate(
            is_pinned=Subquery(
                ConversationState.objects.filter(
                    user=user, conversation=OuterRef("pk")
                ).values("is_pinned")[:1]
            ),
        ).order_by(
            "-is_pinned",
            OrderBy(F("last_message_at"), descending=True, nulls_last=True),
        )


def conversation_picture_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"chat/{instance.public_id}/picture{suffix}"


class Conversation(models.Model):
    """
    A chat between 2+ users.

    A conversation contains a single timeline of root messages.
    Replies are represented by another Conversation whose parent_message points
    to the message being replied to (Slack-like threads).
    """

    objects = ConversationQuerySet.as_manager()

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"
        THREAD = "thread", "Thread"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    direct_key = models.CharField(max_length=64, default="", blank=True)

    title = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_conversations",
    )

    # only populated when this conversation represents a thread
    parent_message = models.OneToOneField(
        "Message",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="thread",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # denormalized pointer to the most recent message in the conversation
    # avoids aggregating Message rows when listing or previewing conversations
    last_message = models.ForeignKey(
        "Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # cached timestamp of the most recent message
    # enables efficient ordering by recent activity without joining Message
    last_message_at = models.DateTimeField(null=True, blank=True)

    last_sequence = models.PositiveIntegerField(default=0)

    picture = models.ImageField(
        upload_to=conversation_picture_upload_to,
        max_length=64,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.kind}@seq:{self.last_sequence} {self.public_id}"

    @classmethod
    def build_direct_key(cls, user_ids: Iterable[int]) -> str:
        return "-".join(map(str, sorted(set(user_ids))))

    @classmethod
    def create_direct(cls, *, created_by_id: int, user_id: int) -> "Conversation":
        """
        Returns an existing direct conversation if one already exists,
        otherwise creates it.
        """
        user_ids = [created_by_id, user_id]

        direct_key = cls.build_direct_key(user_ids)

        with transaction.atomic():
            conversation, created = cls.objects.get_or_create(
                direct_key=direct_key,
                defaults={
                    "kind": cls.Kind.DIRECT,
                    "created_by_id": created_by_id,
                },
            )

            if created:
                conversation._add_members(user_ids=user_ids, added_by_id=created_by_id)

        return conversation

    @classmethod
    def create_group(
        cls, *, title: str, created_by_id: int, user_ids: Iterable[int]
    ) -> "Conversation":
        """
        Creates a new group conversation.
        """
        if not user_ids:
            raise ValidationError("A group conversation requires at least two members.")

        user_ids = {created_by_id, *user_ids}

        with transaction.atomic():
            conversation = cls.objects.create(
                kind=cls.Kind.GROUP,
                title=title,
                created_by_id=created_by_id,
            )

            conversation._add_members(user_ids=user_ids, added_by_id=created_by_id)

        return conversation

    @classmethod
    def create_thread(
        cls, *, created_by_id: int, parent_message_public_id: str
    ) -> "Conversation":
        """
        Returns the existing thread for a message or creates it.
        """
        parent_message = Message.objects.get(public_id=parent_message_public_id)

        with transaction.atomic():
            conversation, _ = cls.objects.get_or_create(
                parent_message_id=parent_message.id,
                defaults={
                    "kind": cls.Kind.THREAD,
                    "created_by_id": created_by_id,
                },
            )

        return conversation

    @classmethod
    def create_message(
        cls,
        *,
        public_id: str,
        created_by: User | None,
        text: str = "",
        json: dict | None = None,
        images: Iterable[UploadedFile] | None = None,
        documents: Iterable[UploadedFile] | None = None,
        type: str = "user",
        system_event: str = "",
        system_event_data: dict | None = None,
        system_event_target: "Message | None" = None,
    ):
        """
        Creates a message (user or system type) in this conversation.
        """
        json = json or {}
        images = images or []
        documents = documents or []
        system_event_data = system_event_data or {}

        with transaction.atomic():
            conversation = (
                cls.objects.select_for_update(of=("self",))
                .for_member(
                    created_by,
                    include_threads=True,
                )
                .get(public_id=public_id)
            )

            # figure out system event target fields
            if system_event_target:
                system_event_target_message_public_id = system_event_target.public_id
                system_event_target_message_preview = truncatechars(
                    system_event_target.text, 64
                )
                system_event_target_message_sequence = system_event_target.sequence
            else:
                system_event_target_message_public_id = None
                system_event_target_message_preview = ""
                system_event_target_message_sequence = 0

            # create the message and increase its sequence
            message = Message.objects.create(
                conversation=conversation,
                created_by=created_by,
                text=text,
                json=json,
                type=type,
                system_event=system_event,
                system_event_data=system_event_data,
                system_event_target_message_public_id=system_event_target_message_public_id,
                system_event_target_message_preview=system_event_target_message_preview,
                system_event_target_message_sequence=system_event_target_message_sequence,
                sequence=conversation.last_sequence + 1,
            )

            # update conversation
            conversation.last_message = message
            conversation.last_message_at = message.created_at
            conversation.last_sequence = message.sequence
            conversation.save(
                update_fields=(
                    "last_message",
                    "last_message_at",
                    "last_sequence",
                )
            )

            # optimistically advance the sender's read pointer
            # the frontend will also call the mark-read endpoint after rendering
            # so this is only an optimization to avoid the sender briefly seeing
            # their own unread badge
            if created_by is not None:
                conversation.mark_read(user=created_by, message=message)

            # update the last message on the root convo if this is a thread
            # to keep it ordered by latest activity
            if conversation.is_thread:
                conversation.root.last_message = message
                conversation.root.last_message_at = message.created_at
                conversation.root.save(
                    update_fields=(
                        "last_message",
                        "last_message_at",
                    )
                )

            # sync link attachments
            LinkAttachment.sync_from_message(message)

            # create image attachments
            ImageAttachment.objects.bulk_create(
                [
                    ImageAttachment.create_from_upload(
                        message=message,
                        file=image,
                    )
                    for image in images
                ]
            )

            # create document attachments
            DocumentAttachment.objects.bulk_create(
                [
                    DocumentAttachment.create_from_upload(
                        message=message,
                        file=doc,
                    )
                    for doc in documents
                ]
            )

        return message

    @property
    def is_direct(self):
        return self.kind == self.Kind.DIRECT

    @property
    def is_thread(self):
        return self.kind == self.Kind.THREAD and self.parent_message is not None

    @property
    def root(self):
        if self.is_thread:
            return self.parent_message.conversation
        return self

    @property
    def active_members(self) -> list["ConversationMember"]:
        """
        Returns the active members, using prefetched data when available.
        """
        if hasattr(self, "_active_members"):
            return self._active_members
        return list(self.get_members_queryset().active())

    @property
    def attachment_counts(self) -> dict[str, int]:
        """
        Return the number of link, image, and document attachments in this
        conversation.

        When the conversation was fetched using
        ConversationQuerySet.with_attachment_counts(), the counts are already
        available as `_attachment_counts` and no additional query is needed.

        For Conversation instances that were fetched without the annotation,
        the counts are calculated with a single aggregate query and cached on
        the instance so subsequent accesses do not query the database again.
        """
        if hasattr(self, "_attachment_counts"):
            return self._attachment_counts

        self._attachment_counts = self.messages.aggregate(
            links=Count(
                "linkattachment",
                distinct=True,
            ),
            images=Count(
                "imageattachment",
                distinct=True,
            ),
            documents=Count(
                "documentattachment",
                distinct=True,
            ),
        )

        return self._attachment_counts

    @transaction.atomic
    def toggle_pin_for(self, user: User) -> bool:
        state = self.get_state(user)
        state.is_pinned = not state.is_pinned
        state.save(update_fields=["is_pinned"])
        return state.is_pinned

    @transaction.atomic
    def add_members(
        self, *, user_ids: Iterable[int], added_by_id: int
    ) -> tuple[list["ConversationMember"], Optional["Message"]]:
        """
        Adds users to the conversation. Existing inactive members are reactivated.
        Users without an existing membership receive a new active membership.
        """
        user_ids = set(user_ids)

        if not user_ids:
            return [], None

        # lock existing memberships so concurrent add/remove operations don't
        # race with each other
        existing = {
            member.user_id: member
            for member in self.members.select_for_update().filter(
                user_id__in=user_ids,
            )
        }

        # handle existing users - set status to active
        members = []
        now = timezone.now()

        for member in existing.values():
            if member.status == ConversationMember.Status.ACTIVE:
                members.append(member)
                continue

            member.status = ConversationMember.Status.ACTIVE
            member.status_changed_at = now
            member.status_changed_by_id = added_by_id

            member.save(
                update_fields=(
                    "status",
                    "status_changed_at",
                    "status_changed_by",
                )
            )

            members.append(member)

        # create memberships that don't exist yet
        new_user_ids = user_ids - existing.keys()

        members.extend(
            self._add_members(user_ids=new_user_ids, added_by_id=added_by_id)
        )

        # create system message
        system_message = Conversation.create_message(
            public_id=str(self.public_id),
            created_by=members[0].added_by,
            type=Message.Type.SYSTEM,
            system_event=Message.SystemEvent.MEMBER_ADDED,
            system_event_data={
                "users": UserSummarySerializer(
                    [member.user for member in members], many=True
                ).data
            },
        )

        return members, system_message

    def _add_members(
        self, *, user_ids: Iterable[int], added_by_id: int
    ) -> list["ConversationMember"]:
        """
        Creates new conversation memberships. This method assumes that memberships
        for the supplied users do not already exist.
        """
        return ConversationMember.objects.bulk_create(
            [
                ConversationMember(
                    conversation=self,
                    user_id=user_id,
                    added_by_id=added_by_id,
                    role=(
                        ConversationMember.Role.OWNER
                        if user_id == self.created_by_id
                        else ConversationMember.Role.MEMBER
                    ),
                )
                for user_id in user_ids
            ]
        )

    @transaction.atomic
    def remove_member(
        self, *, removed_by_id: int, user_id: int
    ) -> tuple["ConversationMember", "Message"]:
        member = self._set_member_status(
            user_id=user_id,
            status=ConversationMember.Status.REMOVED,
            changed_by_id=removed_by_id,
        )

        system_message = Conversation.create_message(
            public_id=str(self.public_id),
            created_by=member.status_changed_by,
            type=Message.Type.SYSTEM,
            system_event=Message.SystemEvent.MEMBER_REMOVED,
            system_event_data={
                "users": UserSummarySerializer([member.user], many=True).data
            },
        )

        return member, system_message

    @transaction.atomic
    def leave(self, *, user: User) -> tuple["ConversationMember", "Message"]:
        system_message = Conversation.create_message(
            public_id=str(self.public_id),
            created_by=user,
            type=Message.Type.SYSTEM,
            system_event=Message.SystemEvent.MEMBER_LEFT,
            system_event_data={"users": UserSummarySerializer([user], many=True).data},
        )

        member = self._set_member_status(
            user_id=user.id,
            status=ConversationMember.Status.LEFT,
            changed_by_id=user.id,
        )

        return member, system_message

    def _set_member_status(
        self, *, user_id: int, status: "ConversationMember.Status", changed_by_id: int
    ) -> "ConversationMember":
        membership = self.members.select_for_update().get(
            user_id=user_id,
            status=ConversationMember.Status.ACTIVE,
        )

        membership.status = status
        membership.status_changed_at = timezone.now()
        membership.status_changed_by_id = changed_by_id

        membership.save(
            update_fields=(
                "status",
                "status_changed_at",
                "status_changed_by",
            )
        )

        return membership

    def get_members_queryset(self):
        return self.root.members.all()

    def has_member(self, user: User) -> bool:
        """
        Return whether the user is an active member of the conversation.

        Use the prefetched active_members when available to avoid an additional
        database query. Fall back to an EXISTS query for instances that were not
        fetched with active members.
        """
        if hasattr(self, "_active_members"):
            return any(m.user_id == user.id for m in self.active_members)

        return self.get_members_queryset().active().filter(user=user).exists()

    def get_state(self, user: User) -> "ConversationState":
        """
        Returns the per-user state for this conversation.
        The state is created lazily on first access.
        """
        state, _ = self.states.get_or_create(user=user)
        return state

    def mark_read(self, *, user: User, message: "Message") -> None:
        """
        Marks this conversation as read up to the given message for the user.
        """
        state = self.get_state(user)
        if state.last_read_sequence >= message.sequence:
            return

        state.last_read_sequence = message.sequence
        state.last_read_message = message
        state.last_read_message_at = timezone.now()

        state.save(
            update_fields=[
                "last_read_sequence",
                "last_read_message",
                "last_read_message_at",
            ]
        )

    def _websocket_publish(self, func, user_ids=None):
        from .serializers import ConversationSerializer

        data = ConversationSerializer(self).data

        if user_ids is None:
            user_ids = [m.user_id for m in self.active_members]

        for user_id in user_ids:
            func(user_id, data)

    def websocket_publish_create(self, user_ids=None):
        self._websocket_publish(
            websocket_publisher.conversation_create, user_ids=user_ids
        )

    def websocket_publish_update(self, user_ids=None):
        self._websocket_publish(
            websocket_publisher.conversation_update, user_ids=user_ids
        )


class ConversationMemberQuerySet(models.QuerySet):
    def active(self):
        return (
            self.filter(
                status=self.model.Status.ACTIVE,
            )
            .select_related("user", "user__avatar")
            .order_by("joined_at")
        )


class ConversationMember(models.Model):
    """
    Defines a user's membership and permissions within a root conversation.
    """

    objects = ConversationMemberQuerySet.as_manager()

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="members"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    joined_at = models.DateTimeField(auto_now_add=True)

    added_by = models.ForeignKey(
        User, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )

    class Role(models.TextChoices):
        MEMBER = "member"
        OWNER = "owner"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)

    class Status(models.TextChoices):
        ACTIVE = "active"
        LEFT = "left"
        REMOVED = "removed"

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        User, null=True, blank=True, related_name="+", on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "user"),
                name="conversation_member_unique_conversation_user",
            ),
        ]


class ConversationState(models.Model):
    """
    Defines user state for a certain conversation. A missing user state means
    the user has never interacted with this conversation. These rows are created
    lazily when the user opens the conversation (be it direct/group or thread).
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="states"
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversation_states"
    )

    is_pinned = models.BooleanField(default=False)

    last_read_message = models.ForeignKey(
        "Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # when the member has read its last message in the conversation
    last_read_message_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_read_sequence = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("conversation", "user"),
                name="conversation_state_unique_conversation_user",
            ),
        ]


class Message(models.Model):
    """
    A single message inside a conversation.
    Messages themselves don't know about replies.
    A thread is simply another Conversation whose parent_message points here.
    """

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="messages",
        null=True,
        blank=True,
        help_text="Nulls for system messages without an author. "
        "Eg: Messages older than 30 days were archived",
    )

    text = models.TextField(default="")
    json = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    sequence = models.PositiveIntegerField(default=0)

    class Type(models.TextChoices):
        USER = "user"
        SYSTEM = "system"

    type = models.CharField(max_length=16, choices=Type.choices, default=Type.USER)

    class SystemEvent(models.TextChoices):
        PINNED = "pinned"
        UNPINNED = "unpinned"
        MEMBER_ADDED = "member_added"
        MEMBER_REMOVED = "member_removed"
        MEMBER_LEFT = "member_left"

    system_event = models.CharField(
        max_length=16,
        choices=SystemEvent.choices,
        blank=True,
        default="",
    )
    system_event_data = models.JSONField(
        default=dict, blank=True, help_text="Holds related custom data"
    )

    system_event_target_message_public_id = models.UUIDField(null=True, editable=False)
    system_event_target_message_preview = models.CharField(max_length=64, default="")
    system_event_target_message_sequence = models.PositiveIntegerField(default=0)

    is_pinned = models.BooleanField(default=False)

    pinned_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    pinned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def _websocket_publish(self, func, user_ids=None):
        from .serializers import MessageSerializer

        data = MessageSerializer(self).data

        if user_ids is None:
            user_ids = self.conversation.get_members_queryset().values_list(
                "user__id", flat=True
            )

        for user_id in user_ids:
            func(user_id, data)

    def websocket_publish_create(self, user_ids=None):
        self._websocket_publish(websocket_publisher.message_create, user_ids=user_ids)

    def websocket_publish_update(self, user_ids=None):
        self._websocket_publish(websocket_publisher.message_update, user_ids=user_ids)

    @transaction.atomic
    def toggle_pin(self, *, pinned_by: User) -> bool:
        if self.is_pinned:
            self.is_pinned = False
            self.pinned_by = None
            self.pinned_at = None
        else:
            self.is_pinned = True
            self.pinned_by = pinned_by
            self.pinned_at = timezone.now()

        self.save(update_fields=["is_pinned", "pinned_by", "pinned_at"])

        return self.is_pinned

    @transaction.atomic
    def toggle_reaction_for(self, user: User, emoji: str) -> tuple[bool, int]:
        """Toggle a reaction for a user and return its new state and total count.

        The message row is locked while the reaction is changed to serialize
        concurrent reaction updates for this message. The count is calculated
        inside the same transaction so it represents the reaction state produced
        by this operation and can be safely used for the websocket update.
        """
        message = Message.objects.select_for_update().get(pk=self.pk)

        reaction = MessageReaction.objects.filter(
            message=message,
            user=user,
            emoji=emoji,
        ).first()

        if reaction:
            reaction.delete()
            reacted = False
        else:
            MessageReaction.objects.create(
                message=message,
                user=user,
                emoji=emoji,
            )
            reacted = True

        count = MessageReaction.objects.filter(
            message=message,
            emoji=emoji,
        ).count()

        return reacted, count


class MessageReaction(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="message_reactions",
    )

    emoji = models.CharField(max_length=32)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # allows multiple emojis per user
        # if one reaction per user is needed then remove emoji from fields
        # and update the constraint name
        #       fields=("message", "user"),
        #       name="unique_message_user",
        constraints = [
            models.UniqueConstraint(
                fields=("message", "user", "emoji"),
                name="unique_message_user_emoji",
            )
        ]

    @classmethod
    def get_summary(cls, mpids, request_user):
        user_reaction = cls.objects.filter(
            message__public_id=OuterRef("message__public_id"),
            emoji=OuterRef("emoji"),
            user=request_user,
        )

        qs = (
            cls.objects.filter(message__public_id__in=mpids)
            .values("message__public_id", "emoji")
            .annotate(count=Count("id"), request_user_reacted=Exists(user_reaction))
            .order_by("-count")
        )

        summary = defaultdict(list)

        for r in qs:
            mpid = r.pop("message__public_id")
            summary[str(mpid)].append(r)

        return summary


class Attachment(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    message = models.ForeignKey(Message, models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


def attachment_upload_to(instance, filename):
    subfolder = instance.__class__.__name__.lower().replace("attachment", "s")
    return f"chat/{instance.message.conversation.public_id}/{subfolder}/{filename}"


class ImageAttachment(Attachment):
    file = models.ImageField(upload_to=attachment_upload_to)
    filename = models.CharField(max_length=255)
    size = models.BigIntegerField()
    width = models.IntegerField()
    height = models.IntegerField()

    @classmethod
    def create_from_upload(
        cls, *, message: Message, file: UploadedFile
    ) -> "ImageAttachment":
        with Image.open(file) as image:
            width, height = image.size

        file.seek(0)

        return cls(
            message=message,
            file=file,
            filename=Path(file.name).name,
            size=file.size,
            width=width,
            height=height,
        )


class DocumentAttachment(Attachment):
    file = models.FileField(upload_to=attachment_upload_to)
    filename = models.CharField(max_length=255)
    size = models.BigIntegerField()
    content_type = models.CharField(max_length=128)

    @classmethod
    def create_from_upload(
        cls,
        *,
        message: Message,
        file: UploadedFile,
    ) -> "DocumentAttachment":
        return cls(
            message=message,
            file=file,
            filename=Path(file.name).name,
            size=file.size,
            content_type=file.content_type or "",
        )


def _iter_tiptap_links(node: Any) -> Iterator[str]:
    """Recursively walks the entire Tiptap tree to look for links"""
    if not isinstance(node, dict):
        return

    for mark in node.get("marks", []):
        if (
            isinstance(mark, dict)
            and mark.get("type") == "link"
            and isinstance(mark.get("attrs"), dict)
        ):
            href = mark["attrs"].get("href")

            if isinstance(href, str) and href:
                yield href

    for child in node.get("content", []):
        yield from _iter_tiptap_links(child)


class LinkAttachment(Attachment):
    url = models.URLField()
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)

    # TODO celery task to pull metadata (title, descr, url)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("message", "url"),
                name="link_attachment_unique_message_url",
            ),
        ]

    @classmethod
    def sync_from_message(cls, message: Message) -> list["LinkAttachment"]:
        """
        Synchronize link attachments with the links present in the message's
        Tiptap JSON.

        Existing attachments are preserved when their URL is still present,
        allowing asynchronously fetched metadata to survive message edits.
        Attachments for removed URLs are deleted and attachments for newly
        discovered URLs are created.
        """
        urls = list(dict.fromkeys(_iter_tiptap_links(message.json)))
        url_set = set(urls)

        existing = {
            attachment.url: attachment
            for attachment in cls.objects.filter(message=message)
        }

        # remove links that are no longer present in the message
        cls.objects.filter(message=message).exclude(
            url__in=url_set,
        ).delete()

        # create only newly discovered links
        created = [cls(message=message, url=url) for url in urls if url not in existing]

        if created:
            cls.objects.bulk_create(created)

        # return attachments in the same order as the URLs in the message
        attachments = {
            **existing,
            **{attachment.url: attachment for attachment in created},
        }
        return [attachments[url] for url in urls]
