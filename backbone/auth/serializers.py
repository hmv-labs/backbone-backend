from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "display",
            "email",
            "first_name",
            "has_usable_password",
            "is_superuser",
            "last_name",
            "username",
        )

    def get_display(self, obj):
        return obj.get_full_name() or obj.username
