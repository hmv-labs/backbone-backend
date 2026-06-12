from rest_framework.viewsets import ModelViewSet, views
from rest_framework.response import Response
from rest_framework import permissions, status

from . import serializers
from . import websocket_publisher


class UserViewSet(ModelViewSet):
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save()
        websocket_publisher.user_update(serializer.data)


class PasswordCheckView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password", "")
        if request.user.check_password(password):
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)
