from pathlib import Path

from django.contrib.auth.models import User
from django.db import models


def avatar_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"avatars/{instance.id}/avatar{suffix}"


class UserAvatar(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="avatar")
    image = models.ImageField(upload_to=avatar_upload_to, max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
