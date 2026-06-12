import logging
from typing import List

from django.conf import settings
from django.utils.module_loading import import_string
from django.contrib.postgres.fields import ArrayField
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Context, Template

logger = logging.getLogger(__name__)


class EmailTemplate(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
    subject = models.TextField()
    text = models.TextField()
    html = models.TextField()
    raw = models.TextField(default="")

    no_reply = models.BooleanField(default=True)
    bcc = ArrayField(models.EmailField(), default=list, blank=True)

    _context_provider = None

    class Meta:
        verbose_name = "Backbone email template"
        verbose_name_plural = "Backbone email templates"

    def send(self, to_email: List[str], **context):
        # figure out from_email based on no_reply kwarg
        if self.no_reply:
            from_email = settings.EMAIL_HOST_USER_NOREPLY
            reply_to = None
        else:
            from_email = settings.EMAIL_HOST_USER
            reply_to = [from_email]

        subject, body_text, body_html = self.render(**context)

        # construct the email with text body
        msg = EmailMultiAlternatives(
            subject=subject.strip(),
            body=body_text,
            from_email=from_email,
            to=to_email,
            reply_to=reply_to,
            bcc=self.bcc or None,
        )

        # attach the html alternative
        msg.attach_alternative(body_html, "text/html")

        logger.debug(f'Sending email {self.name} "{subject}" to {to_email}')

        msg.send()

    def get_render_context_provider(self):
        if not self._context_provider:
            provider_class = import_string(
                settings.BACKBONE_EMAILS_EMAILTEMPLATE_CONTEXT_PROVIDER
            )
            self._context_provider = provider_class()
        return self._context_provider

    def get_render_context(self, **extra_context):
        provider = self.get_render_context_provider()
        return provider._get(**extra_context)

    def render(self, **extra_context):
        context = self.get_render_context(**extra_context)
        self.inject_utm_params(context)

        subject = Template(self.subject).render(Context(context))
        text = Template(self.text).render(Context(context))
        html = Template(self.html).render(Context(context))
        return subject, text, html

    def inject_utm_params(self, context):
        """Injects utm params in urls. Assumes all url variables start with `url_`"""
        utm_source = "email"
        utm_medium = self.name.lower()

        for k in context:
            v = context[k]
            if k.startswith("url_") and "utm_source" not in v:
                prefix = "&" if "?" in v else "?"
                v += f"{prefix}utm_source={utm_source}&utm_medium={utm_medium}"
                context[k] = v

        return context
