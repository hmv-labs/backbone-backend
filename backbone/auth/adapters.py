import json
import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponse
from django.db.models import signals
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.headless.internal.restkit.response import APIResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.usersessions.adapter import DefaultUserSessionsAdapter
from allauth.usersessions.models import UserSession
from backbone.emails.tasks import send_email
from backbone.internals.honeypot import is_honeypot_valid
from django.contrib.auth.models import User, AbstractBaseUser
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from rest_framework import status
from typing import Any

from .serializers import UserSerializer
from . import websocket_publisher

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    def authentication_failed(self, request: HttpRequest, **credentials: Any) -> None:
        email = credentials.get("email")
        if not email:
            return

        user = User.objects.filter(email=email).first()
        if user and not user.has_usable_password():
            # raise ValidationError("no-usable-password", code="no-usable-password")
            raise ImmediateHttpResponse(
                APIResponse(
                    request,
                    errors=[{"code": "no-usable-password"}],
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

    def clean_email(self, email: str) -> str:
        email = super().clean_email(email)

        if EmailAddress.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "This email address is already taken.",
                code="email_taken",
            )

        return email

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        logger.debug(f"[send_mail] {template_prefix} -> {email} -> {context}")

        if template_prefix in [
            # user tries to log in, but its email is not yet verified
            "account/email/email_confirmation",
            # user just signed up
            "account/email/email_confirmation_signup",
        ]:
            send_email.apply_async(  # pyright: ignore
                kwargs={
                    "template_name": "AccountEmailConfirm",
                    "tos": [email],
                    "context": {
                        "url_confirm": context["activate_url"],
                    },
                },
            )
            return

        if template_prefix == "account/email/password_reset_key":
            # user requested a password reset
            send_email.apply_async(  # pyright: ignore
                kwargs={
                    "template_name": "PasswordReset",
                    "tos": [email],
                    "context": {
                        "url_confirm": context["password_reset_url"],
                    },
                },
            )
            return

        return super().send_mail(template_prefix, email, context)

    def pre_login(self, request: HttpRequest, *a, **kw) -> HttpResponse | None:
        """Overwritten to check honeypot fields are valid"""
        validate_honeypot(request, min_submit_ms=500)
        return super().pre_login(request, *a, **kw)

    def save_user(self, request: HttpRequest, *a, **kw):
        """Overwritten to check honeypot fields are valid.
        Method triggered by BaseSignupForm.save method.
        """
        validate_honeypot(request)
        return super().save_user(request, *a, **kw)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    pass


class AccountHeadlessAdapter(DefaultHeadlessAdapter):
    def serialize_user(self, user: AbstractBaseUser) -> dict[str, Any]:
        return UserSerializer(user).data  # pyright: ignore


class UserSessionsAdapter(DefaultUserSessionsAdapter):
    pass


def validate_honeypot(request, min_submit_ms=None):
    if not is_honeypot_valid(json.loads(request.body), min_submit_ms=min_submit_ms):
        raise ImmediateHttpResponse(
            APIResponse(
                request,
                errors=[
                    {
                        "message": "Session invalid. Please try again.",
                        "code": "hp-invalid",
                    }
                ],
                status=status.HTTP_400_BAD_REQUEST,
            )
        )


@receiver(signals.post_save, sender=UserSession)
def ws_usersession_init(sender, instance, created, **kws):
    if created:
        websocket_publisher.usersession_init(instance.user_id, instance.id)


@receiver(signals.post_delete, sender=UserSession)
def ws_usersession_end(sender, instance, **kws):
    websocket_publisher.usersession_end(instance.user_id, instance.id)


@receiver(user_logged_out)
def ws_user_logout(sender, request, user, **kws):
    websocket_publisher.user_logout(user.id)
