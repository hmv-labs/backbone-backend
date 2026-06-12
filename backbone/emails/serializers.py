from rest_framework import serializers
from . import models


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmailTemplate
        fields = (
            "subject",
            "name",
            "text",
            "html",
            "raw",
        )
