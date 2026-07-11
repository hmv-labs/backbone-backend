from backbone.bootstrap import env
from backbone.settings.common import FRONTEND_PUBLIC_URL


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "allauth",
        "allauth.account",
        "allauth.usersessions",
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
    # https://docs.allauth.org/en/dev/account/configuration.html#email-addresses
    # use just one email address
    settings["ACCOUNT_CHANGE_EMAIL"] = True

    # ############### social accounts ################################################
    settings["SOCIALACCOUNT_GOOGLE_CLIENT_ID"] = env.str(
        "SOCIALACCOUNT_GOOGLE_CLIENT_ID", ""
    )
    settings["SOCIALACCOUNT_GOOGLE_SECRET"] = env.str("SOCIALACCOUNT_GOOGLE_SECRET", "")
    settings["SOCIALACCOUNT_FACEBOOK_CLIENT_ID"] = env.str(
        "SOCIALACCOUNT_FACEBOOK_CLIENT_ID", ""
    )
    settings["SOCIALACCOUNT_FACEBOOK_SECRET"] = env.str(
        "SOCIALACCOUNT_FACEBOOK_SECRET", ""
    )

    settings["SOCIALACCOUNT_PROVIDERS"] = {
        "google": {
            "APPS": [
                {
                    "client_id": settings["SOCIALACCOUNT_GOOGLE_CLIENT_ID"],
                    "secret": settings["SOCIALACCOUNT_GOOGLE_SECRET"],
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
        # TODO
        # "facebook": {
        #     "APPS": [
        #         {
        #             "client_id": settings["SOCIALACCOUNT_FACEBOOK_CLIENT_ID"],
        #             "secret": settings["SOCIALACCOUNT_FACEBOOK_SECRET"],
        #             "key": "",
        #         },
        #     ],
        #     "SCOPE": [
        #         "profile",
        #         "email",
        #     ],
        #     "AUTH_PARAMS": {
        #         "access_type": "offline",
        #     },
        #     "OAUTH_PKCE_ENABLED": True,
        # },
    }
    # ############### social accounts ################################################

    settings["HEADLESS_CLIENTS"] = ("browser",)
    settings["HEADLESS_ONLY"] = True

    # https://docs.allauth.org/en/dev/headless/configuration.html

    settings["HEADLESS_FRONTEND_URLS"] = {
        "account_confirm_email": FRONTEND_PUBLIC_URL + "/confirm/email/{key}",
        "account_reset_password_from_key": FRONTEND_PUBLIC_URL
        + "/confirm/password-reset/{key}",
        "account_signup": FRONTEND_PUBLIC_URL + "/signup",
        # Fallback in case the state containing the `next` URL is lost
        # and the handshake with the third-party provider fails.
        "socialaccount_login_error": f"{FRONTEND_PUBLIC_URL}/callback/social-account-provider",
    }

    # adapters
    settings["ACCOUNT_ADAPTER"] = "backbone.auth.adapters.AccountAdapter"
    settings["HEADLESS_ADAPTER"] = "backbone.auth.adapters.AccountHeadlessAdapter"
    settings["SOCIALACCOUNT_ADAPTER"] = "backbone.auth.adapters.SocialAccountAdapter"
    settings["USERSESSIONS_ADAPTER"] = "backbone.auth.adapters.UserSessionsAdapter"
