from django.urls import re_path

from backbone.channels import consumers

websocket_urlpatterns = [
    re_path(r"ws/$", consumers.WebsocketConsumer.as_asgi()),
]
