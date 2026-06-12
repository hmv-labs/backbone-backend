from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.template import Context, Template

from backbone.drf.permissions import SuperuserOnlyPermission

from . import models, serializers


class EmailTemplateViewSet(ModelViewSet):
    serializer_class = serializers.EmailTemplateSerializer
    permission_classes = (SuperuserOnlyPermission,)
    lookup_field = "name"

    def get_queryset(self):
        return models.EmailTemplate.objects.all()

    def render_email_template(self, request):
        context = request.data.get("context")
        html = request.data.get("html")
        html = Template(html).render(Context(context))
        return Response({"html": html})
