import logging

from django.db.models import Sum
from django.db.models.expressions import F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.forms import ValidationError
from rest_framework import permissions, response, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from . import models, serializers, websocket_publisher

logger = logging.getLogger(__file__)


class ConversationViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"
    include_threads = False

    def get_queryset(self):
        return (
            models.Conversation.objects.for_member(
                self.request.user, include_threads=self.include_threads
            )
            .select_related(
                "last_message__conversation__parent_message",
                "last_message__created_by",
            )
            .prefetch_related(
                "states__user",
            )
            .with_active_members()
            .with_attachment_counts()
            .order_for(self.request.user)
        )

    def get_serializer_class(self):  # pyright: ignore
        if self.request.method == "PATCH":
            return serializers.ConversationUpdateSerializer
        if self.request.method == "POST":
            return serializers.ConversationCreateSerializer
        return serializers.ConversationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        # we only publish create ws events for direct and group conversations
        if not obj.is_thread:
            user_ids = [request.user.id] + request.data["users"]
            obj.websocket_publish_create(user_ids=user_ids)

        return response.Response({"id": obj.public_id}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # groups can be currently updated by creators only
        if instance.kind == instance.Kind.GROUP:
            if instance.created_by_id != request.user.id:
                return Response(status=status.HTTP_403_FORBIDDEN)

        # direct / threads can be updated by any member
        if not instance.root.has_member(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        obj = serializer.save()
        obj.websocket_publish_update()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # groups can be currently deleted by creators only
        if instance.kind == instance.Kind.GROUP:
            if instance.created_by_id != request.user.id:
                return Response(status=status.HTTP_403_FORBIDDEN)

        # direct / threads can be deleted by any member
        if not instance.root.has_member(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # gather data first for ws updates - then publish after deletion
        uids = [m.user_id for m in instance.active_members]
        public_id = str(instance.public_id)

        instance.delete()

        for uid in uids:
            websocket_publisher.conversation_delete(uid, public_id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_unread_count(self, request):
        """
        Total unread messages across all conversations and threads.
        Conversations without a ConversationState are treated as completely unread.
        """
        total = (
            models.Conversation.objects.for_member(
                request.user,
                include_threads=True,
            )
            .annotate(
                last_read_sequence=Coalesce(
                    Subquery(
                        models.ConversationState.objects.filter(
                            conversation=OuterRef("pk"),
                            user=request.user,
                        ).values("last_read_sequence")[:1]
                    ),
                    Value(0),
                ),
            )
            .aggregate(
                unread=Coalesce(
                    Sum(
                        F("last_sequence") - F("last_read_sequence"),
                    ),
                    Value(0),
                ),
            )["unread"]
        )

        return Response({"count": total})

    def mark_read(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            message = models.Message.objects.get(
                public_id=request.data.get("message_public_id", "")
            )
        except (models.Message.DoesNotExist, ValidationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        obj.mark_read(user=request.user, message=message)

        # need to re-pull the object to have it properly serialized
        obj = self.get_object()

        # publish websocket update to all users to have all conversation states updated
        obj.websocket_publish_update()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def member_add(self, request, *args, **kwargs):
        instance = self.get_object()

        # adding members make sense for groups only
        if instance.kind != instance.Kind.GROUP:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # and only the group creator can add members
        if instance.created_by_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        user_ids = request.data.get("user_ids")
        if not user_ids:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        members, system_message = instance.add_members(
            user_ids=user_ids, added_by_id=request.user.id
        )

        instance = self.get_object()
        instance.websocket_publish_update()

        system_message.websocket_publish_create()

        return Response(status=status.HTTP_200_OK)

    def member_remove(self, request, *args, **kwargs):
        instance = self.get_object()

        # removing members make sense for groups only
        if instance.kind != instance.Kind.GROUP:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # and only the group creator can remove members
        if instance.created_by_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # owner cannot remove himself
        if instance.created_by_id == user_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        member, system_message = instance.remove_member(
            removed_by_id=request.user.id, user_id=user_id
        )

        instance = self.get_object()
        instance.websocket_publish_update()

        # publish delete to the removed member
        websocket_publisher.conversation_delete(user_id, str(instance.public_id))

        system_message.websocket_publish_create()

        return Response(status=status.HTTP_200_OK)

    def member_leave(self, request, *args, **kwargs):
        instance = self.get_object()

        # leaving make sense in groups only
        if instance.kind != instance.Kind.GROUP:
            return Response(status=status.HTTP_403_FORBIDDEN)

        member, system_message = instance.leave(user=request.user)

        # XXX do use self.get_object again since it will result in 404
        # ie: request user is no longer ACTIVE in the conversation
        # pull the conversation again instead - without involving request.user
        instance = (
            models.Conversation.objects.filter(
                id=instance.id,
            )
            .select_related(
                "last_message__conversation__parent_message",
                "last_message__created_by",
            )
            .prefetch_related(
                "states__user",
            )
            .with_active_members()
            .first()
        )
        instance.websocket_publish_update()

        # publish delete to the member who left
        websocket_publisher.conversation_delete(
            request.user.id, str(instance.public_id)
        )

        system_message.websocket_publish_create()

        return Response(status=status.HTTP_200_OK)

    def pin(self, request, *args, **kwargs):
        obj = self.get_object()
        is_pinned = obj.toggle_pin_for(request.user)

        # need to re-pull the object to have it properly serialized
        obj = self.get_object()

        # publish websocket update for the request user only
        obj.websocket_publish_update(user_ids=[request.user.id])

        return Response({"is_pinned": is_pinned})


class MessageViewSet(ModelViewSet):
    serializer_class = serializers.MessageSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    show_timeline = False
    timeline_page_size = 20
    timeline_jump_context = 15

    def get_queryset(self):
        qs = (
            models.Message.objects.select_related(
                "conversation",
                "created_by__avatar",
                "thread",
            )
            .prefetch_related(
                "documentattachment_set",
                "imageattachment_set",
                "thread__messages",
            )
            .order_by("-sequence")
        )

        if "conversation_public_id" in self.kwargs:
            qs = qs.filter(
                conversation__public_id=self.kwargs["conversation_public_id"]
            )

        return qs

    def filter_queryset(self, queryset):
        wants_pinned = self.request.GET.get("pinned") == "true"
        if wants_pinned:
            queryset = queryset.filter(is_pinned=True)

        q = self.request.GET.get("q")
        if q and len(q) >= 2:
            queryset = queryset.filter(text__icontains=q)

        return queryset

    def get_sequence_param(self, name: str):
        try:
            param = int(self.request.GET.get(name))
        except (TypeError, ValueError):
            param = None
        return param

    def list(self, request, *args, **kwargs):
        if self.show_timeline:
            response = self.timeline(request, *args, **kwargs)
        else:
            response = super().list(request, *args, **kwargs)

        # annotate reaction_summary for this page only
        mpids = [m["public_id"] for m in response.data["results"]]
        reaction_summary = models.MessageReaction.get_summary(mpids, request.user)

        for result in response.data["results"]:
            summary = reaction_summary.get(result["public_id"])
            if summary:
                result["reaction_summary"] = summary

        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)

        # annotate reaction_summary
        mpids = [response.data["public_id"]]
        reaction_summary = models.MessageReaction.get_summary(mpids, request.user)
        response.data["reaction_summary"] = reaction_summary[response.data["public_id"]]

        return response

    def timeline(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        around = self.get_sequence_param("around")
        before = self.get_sequence_param("before")
        after = self.get_sequence_param("after")

        # initial load
        if around is None and before is None and after is None:
            results = list(qs[: self.timeline_page_size])
            results.reverse()

        # jump to a message
        elif around is not None:
            sequence = around

            try:
                anchor = qs.get(sequence=sequence)
            except models.Message.DoesNotExist:
                # no anchor found - failback to initial load
                results = list(qs[: self.timeline_page_size])
                results.reverse()
            else:
                # anchor found - get before and after anchor context
                before_results = list(
                    qs.filter(sequence__lt=sequence)[: self.timeline_jump_context]
                )

                before_results.reverse()

                after_results = list(
                    qs.filter(
                        sequence__gt=sequence,
                    ).order_by(
                        "sequence"
                    )[: self.timeline_jump_context]
                )

                results = before_results + [anchor] + after_results

        # load older messages
        elif before is not None:
            sequence = before

            results = list(qs.filter(sequence__lt=sequence)[: self.timeline_page_size])

            results.reverse()

        # load newer messages
        else:
            sequence = after

            results = list(
                qs.filter(sequence__gt=sequence).order_by("sequence")[
                    : self.timeline_page_size
                ]
            )

        serializer = self.get_serializer(results, many=True)

        first_sequence = results[0].sequence if results else None
        last_sequence = results[-1].sequence if results else None

        has_previous = (
            first_sequence is not None
            and qs.filter(sequence__lt=first_sequence).exists()
        )

        has_next = (
            last_sequence is not None and qs.filter(sequence__gt=last_sequence).exists()
        )

        return Response(
            {
                "request": {
                    "params": {
                        "around": around,
                        "before": before,
                        "after": after,
                    }
                },
                "first_sequence": first_sequence,
                "last_sequence": last_sequence,
                "has_previous": has_previous,
                "has_next": has_next,
                "results": serializer.data,
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = serializers.MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = models.Conversation.create_message(
                public_id=self.kwargs["conversation_public_id"],
                created_by=request.user,
                text=serializer.validated_data["text"],
                json=serializer.validated_data["json"],
                images=serializer.validated_data.get("images"),
                documents=serializer.validated_data.get("documents"),
            )
        except models.Conversation.DoesNotExist:
            return Response(
                {"conversation": ["invalid"]}, status=status.HTTP_400_BAD_REQUEST
            )

        # update the root conversation to have the last bits
        # and state set (for request user)
        message.conversation.root.websocket_publish_update()

        if message.conversation.is_thread:
            # if the created message belongs to a conversation thread
            # then we update the parent message in the main thread
            # so it nicely shows the messages count and possibly others thread related
            message.conversation.parent_message.websocket_publish_update()

            # also update the thread conversation to have the last bits
            # and states set (for request user)
            message.conversation.websocket_publish_update()

        # make sure the message create is published last
        # because this could be the very first message in the conversation thread
        # in which case the parent message needs to be updated first
        # otherwise frontend tries to add the message to an undefined list
        message.websocket_publish_create()

        return Response({"id": message.public_id}, status=status.HTTP_201_CREATED)

    def pin(self, request, *args, **kwargs):
        obj = self.get_object()

        if not obj.conversation.has_member(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # pinned messages inside threads are currently not allowed
        if obj.conversation.is_thread:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        is_pinned = obj.toggle_pin(pinned_by=request.user)

        # update the message
        obj.websocket_publish_update()

        # create system message
        system_message = models.Conversation.create_message(
            public_id=obj.conversation.public_id,
            created_by=request.user,
            type=models.Message.Type.SYSTEM,
            system_event=(
                models.Message.SystemEvent.PINNED
                if is_pinned
                else models.Message.SystemEvent.UNPINNED
            ),
            system_event_target=obj,
        )

        # update the conversation
        system_message.conversation.websocket_publish_update()

        # send the message create event
        system_message.websocket_publish_create()

        return Response({"is_pinned": is_pinned})

    def react(self, request, *args, **kwargs):
        obj = self.get_object()

        if not obj.conversation.has_member(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

        emoji = request.data.get("emoji")

        if not emoji:
            return Response(
                {"detail": "emoji is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reacted, count = obj.toggle_reaction_for(request.user, emoji)

        members = obj.conversation.get_members_queryset()
        for member in members:
            websocket_publisher.message_reaction(
                member.user_id,
                actor_id=request.user.id,
                actor_reacted=reacted,
                count=count,
                cpid=str(obj.conversation.public_id),
                emoji=emoji,
                mpid=str(obj.public_id),
            )

        return Response({"emoji": emoji, "reacted": reacted}, status=status.HTTP_200_OK)


class AttachmentViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    model_class = None

    def get_queryset(self):
        if self.model_class is None:
            raise Exception(
                "must provide LinkAttachment, ImageAttachment or DocumentAttachment"
            )

        return (
            self.model_class.objects.select_related("message")
            .filter(message__conversation__public_id=self.kwargs["public_id"])
            .order_by("-created_at")
        )


class LinkAttachmentViewSet(AttachmentViewSet):
    model_class = models.LinkAttachment
    serializer_class = serializers.LinkAttachmentSerializer


class ImageAttachmentViewSet(AttachmentViewSet):
    model_class = models.ImageAttachment
    serializer_class = serializers.ImageAttachmentSerializer


class DocumentAttachmentViewSet(AttachmentViewSet):
    model_class = models.DocumentAttachment
    serializer_class = serializers.DocumentAttachmentSerializer


class CommonGroupListView(ListAPIView):
    """Returns common groups for request user and uid in url."""

    serializer_class = serializers.ConversationCommonGroupSerializer

    def get_queryset(self):
        return (
            models.Conversation.objects.filter(
                kind=models.Conversation.Kind.GROUP,
                members__user=self.request.user,
                members__status=models.ConversationMember.Status.ACTIVE,
            )
            .filter(
                members__user_id=self.kwargs["uid"],
                members__status=models.ConversationMember.Status.ACTIVE,
            )
            .distinct()
            .order_by("-updated_at")
        )
