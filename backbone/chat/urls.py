from django.urls import path

from . import views

app_name = "backbone.chat"

urlpatterns = [
    path(
        "conversations/",
        views.ConversationViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "conversations/unread-count/",
        views.ConversationViewSet.as_view(
            {
                "get": "get_unread_count",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/",
        views.ConversationViewSet.as_view(
            {
                "get": "retrieve",
                "delete": "destroy",
                "patch": "partial_update",
            },
            include_threads=True,
        ),
    ),
    path(
        "conversations/<uuid:public_id>/mark-read/",
        views.ConversationViewSet.as_view(
            {
                "post": "mark_read",
            },
            include_threads=True,
        ),
    ),
    path(
        "conversations/<uuid:public_id>/members/",
        views.ConversationViewSet.as_view(
            {
                "post": "member_add",
                "delete": "member_remove",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/leave/",
        views.ConversationViewSet.as_view(
            {
                "post": "member_leave",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/pin/",
        views.ConversationViewSet.as_view(
            {
                "post": "pin",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/links/",
        views.LinkAttachmentViewSet.as_view(
            {
                "get": "list",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/images/",
        views.ImageAttachmentViewSet.as_view(
            {
                "get": "list",
            }
        ),
    ),
    path(
        "conversations/<uuid:public_id>/documents/",
        views.DocumentAttachmentViewSet.as_view(
            {
                "get": "list",
            }
        ),
    ),
    path(
        "conversations/<uuid:conversation_public_id>/messages-timeline/",
        views.MessageViewSet.as_view(
            {
                "get": "list",
            },
            show_timeline=True,
        ),
    ),
    path(
        "conversations/<uuid:conversation_public_id>/messages/",
        views.MessageViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "messages/<uuid:public_id>/",
        views.MessageViewSet.as_view(
            {
                "get": "retrieve",
            }
        ),
    ),
    path(
        "messages/<uuid:public_id>/pin/",
        views.MessageViewSet.as_view(
            {
                "post": "pin",
            }
        ),
    ),
    path(
        "messages/<uuid:public_id>/react/",
        views.MessageViewSet.as_view(
            {
                "post": "react",
            }
        ),
    ),
    path(
        "common-groups/<int:uid>/",
        views.CommonGroupListView.as_view(),
    ),
]
