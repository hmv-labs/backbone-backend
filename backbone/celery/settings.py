from backbone.settings.caches import REDIS_URL_BROKER


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "django_celery_beat",
    ]

    settings["CELERY_BEAT_SCHEDULER"] = (
        "django_celery_beat.schedulers:DatabaseScheduler"
    )
    settings["CELERY_BROKER_URL"] = REDIS_URL_BROKER
    settings["CELERY_TASK_IGNORE_RESULT"] = True

    # settings["CELERY_WORKER_HIJACK_ROOT_LOGGER"] = False
    # settings["CELERY_WORKER_ENABLE_REMOTE_CONTROL"] = False
    # settings["CELERY_WORKER_SEND_TASK_EVENTS"] = False

    settings["CELERY_TASK_ROUTES"] = {
        "*": "celery",
    }
