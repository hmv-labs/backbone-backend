from django.contrib.auth.models import User
from rest_framework import serializers


class UserSummarySerializer(serializers.ModelSerializer):
    display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "display",
            "id",
            "username",
        )

    def get_display(self, obj):
        return obj.get_full_name() or obj.username


class UserSummaryWithAvatarSerializer(UserSummarySerializer):
    avatar = serializers.ImageField(
        source="avatar.image",
        read_only=True,
    )

    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + ("avatar",)
