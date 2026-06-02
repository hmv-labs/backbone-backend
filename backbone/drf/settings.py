def configure(settings):
    settings["INSTALLED_APPS"] += [
        "rest_framework",
    ]

    settings["REST_FRAMEWORK"] = {
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication",
        ],
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
        ],
        "DEFAULT_PAGINATION_CLASS": "backbone.drf.pagination.Pagination",
        "DEFAULT_THROTTLE_RATES": {
            "challenge_burst": "5/min",
            "challenge_sustained": "100/day",
        },
        "PAGE_SIZE": 20,
    }
