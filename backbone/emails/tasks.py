from celery import shared_task
from typing import List
from .models import EmailTemplate


@shared_task
def send_email(*, template_name: str, tos: List[str], **context):
    template = EmailTemplate.objects.get(name=template_name)
    template.send(tos, **context)
