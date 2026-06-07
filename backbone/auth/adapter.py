import logging

from django.contrib.auth.models import User
from allauth.core.exceptions import ImmediateHttpResponse
from rest_framework import status
from allauth.headless.internal.restkit.response import APIResponse
from django.http import HttpRequest
from typing import Any
from allauth.account.adapter import DefaultAccountAdapter
from allauth.headless.adapter import DefaultHeadlessAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

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

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        # TODO figure out why logger does not output anything
        print(f"### [send_mail] {template_prefix} -> {email} -> {context}")

        logger.debug(f"[send_mail] {template_prefix} -> {email} -> {context}")

        if template_prefix == "account/email/email_confirmation":
            # TODO publish celery task
            # TODO frontend page as indicated in settings["HEADLESS_FRONTEND_URLS"]
            return

        if template_prefix == "account/email/password_reset_key":
            # TODO publish celery task
            # TODO frontend page as indicated in settings["HEADLESS_FRONTEND_URLS"]
            return

        return super().send_mail(template_prefix, email, context)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    pass


class AccountHeadlessAdapter(DefaultHeadlessAdapter):
    def serialize_user(self, user: User) -> dict[str, Any]:  # pyright: ignore
        data = super().serialize_user(user)
        return {
            **data,
            "display": user.get_full_name() or user.get_username(),
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
