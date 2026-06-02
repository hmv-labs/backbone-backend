from backbone.env import env


def configure(settings):
    SENTRY_DSN = env.str("SENTRY_DSN")

    if SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        settings["SENTRY_DSN"] = SENTRY_DSN

        try:
            SENTRY_TRACE_SAMPLE_RATE = float(
                env.int("SENTRY_TRACE_SAMPLE_RATE", default=0)
            )
        except Exception as e:
            print(f"Unable to get SENTRY_TRACE_SAMPLE_RATE from the environment: {e}")
            SENTRY_TRACE_SAMPLE_RATE = 0.0

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # We recommend adjusting this value in production,
            traces_sample_rate=SENTRY_TRACE_SAMPLE_RATE,
            # If you wish to associate users to errors (assuming you are using
            # django.contrib.auth) you may enable sending PII data.
            send_default_pii=True,
        )
