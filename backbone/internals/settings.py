from backbone.bootstrap import env
from corsheaders.defaults import default_headers


def configure(settings):
    settings["MIDDLEWARE"] += [
        "backbone.internals.middleware.SetRemoteAddrMiddleware",
    ]

    # x-challenge related settings
    settings["BACKBONE_INTERNALS_X_CHALLENGE_ENABLED"] = env.bool(
        "BACKBONE_INTERNALS_X_CHALLENGE_ENABLED", False
    )

    settings["BACKBONE_INTERNALS_X_CHALLENGE_TOKEN_MAX_AGE"] = env.int(
        "BACKBONE_INTERNALS_X_CHALLENGE_TOKEN_MAX_AGE", 60
    )

    settings["BACKBONE_INTERNALS_X_CHALLENGE_WHITELIST_PATHS"] = []

    if settings["BACKBONE_INTERNALS_X_CHALLENGE_ENABLED"]:
        settings["MIDDLEWARE"] += [
            "backbone.internals.middleware.XChallengeMiddleware",
        ]

        # XXX pay close attention to the whitelist below while adding urls
        # these are resolved inside XChallengeMiddleware

        settings["BACKBONE_INTERNALS_X_CHALLENGE_WHITELIST_PATHS"] = [
            "auth:headless:browser:account:current_session",
            "auth:headless:browser:socialaccount:redirect_to_provider",
            "internals:challenge",
            "internals:health_check",
        ]

        settings["CORS_ALLOW_HEADERS"] = [
            "x-challenge-token",
            "x-request-source",  # nuxt-ssr only, ignored otherwise
            *default_headers,
        ]
    # end x-challenge related settings
