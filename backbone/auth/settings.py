from backbone.env import env
from backbone.settings.common import FRONTEND_PUBLIC_URL

SOCIALACCOUNT_GOOGLE_CLIENT_ID = env.str("SOCIALACCOUNT_GOOGLE_CLIENT_ID", "")
SOCIALACCOUNT_GOOGLE_SECRET = env.str("SOCIALACCOUNT_GOOGLE_SECRET", "")


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "allauth",
        "allauth.account",
        "allauth.headless",
        "allauth.socialaccount",
        "allauth.socialaccount.providers.google",
    ]
    settings["MIDDLEWARE"] += [
        "allauth.account.middleware.AccountMiddleware",
    ]

    settings["AUTHENTICATION_BACKENDS"] = (
        "django.contrib.auth.backends.ModelBackend",  # for dango admin
        "allauth.account.auth_backends.AuthenticationBackend",  # login by email
    )

    settings["ACCOUNT_ADAPTER"] = "backbone.auth.adapter.AccountAdapter"

    # do not send emails to unknown accounts (like password reset to non existing emails)
    settings["ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS"] = False

    settings["ACCOUNT_EMAIL_VERIFICATION"] = "mandatory"
    settings["ACCOUNT_LOGIN_METHODS"] = {"email", "username"}
    settings["ACCOUNT_SIGNUP_FIELDS"] = [
        "email*",
        "username*",
        "password1*",
        "password2*",
    ]

    settings["SOCIALACCOUNT_ADAPTER"] = "backbone.auth.adapter.SocialAccountAdapter"
    settings["SOCIALACCOUNT_PROVIDERS"] = {
        "google": {
            "APPS": [
                {
                    "client_id": SOCIALACCOUNT_GOOGLE_CLIENT_ID,
                    "secret": SOCIALACCOUNT_GOOGLE_SECRET,
                    "key": "",
                },
            ],
            "SCOPE": [
                "profile",
                "email",
            ],
            "AUTH_PARAMS": {
                "access_type": "offline",
            },
            "OAUTH_PKCE_ENABLED": True,
        },
    }

    settings["HEADLESS_ADAPTER"] = "backbone.auth.adapter.AccountHeadlessAdapter"
    settings["HEADLESS_CLIENTS"] = ("browser",)
    settings["HEADLESS_ONLY"] = True

    # https://docs.allauth.org/en/dev/headless/configuration.html

    settings["HEADLESS_FRONTEND_URLS"] = {
        "account_confirm_email": FRONTEND_PUBLIC_URL + "/confirm/email/{key}",
        "account_reset_password_from_key": FRONTEND_PUBLIC_URL + "/confirm/password-reset/{key}",

        # Fallback in case the state containing the `next` URL is lost
        # and the handshake with the third-party provider fails.
        "socialaccount_login_error": f"{FRONTEND_PUBLIC_URL}/socialaccount-provider-callback",
    }
