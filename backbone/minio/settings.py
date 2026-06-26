from backbone.bootstrap import env


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "minio_storage",
    ]
    settings["STORAGES"] = {
        "default": {
            "BACKEND": "minio_storage.storage.MinioMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "minio_storage.storage.MinioStaticStorage",
        },
    }

    settings["MINIO_STORAGE_ENDPOINT"] = env("STORAGE_MINIO_ENDPOINT")
    settings["MINIO_STORAGE_ACCESS_KEY"] = env("STORAGE_MINIO_ACCESS_KEY")
    settings["MINIO_STORAGE_SECRET_KEY"] = env("STORAGE_MINIO_SECRET_KEY")

    MEDIA_BUCKET_NAME = "uploads"
    settings["MINIO_STORAGE_MEDIA_BUCKET_NAME"] = MEDIA_BUCKET_NAME
    settings["MINIO_STORAGE_MEDIA_URL"] = "{base_url}/{bucket_name}".format(
        base_url=env("STORAGE_MINIO_MEDIA_BASE_URL"),
        bucket_name=MEDIA_BUCKET_NAME,
    )

    STATIC_BUCKET_NAME = "static"
    settings["MINIO_STORAGE_STATIC_BUCKET_NAME"] = STATIC_BUCKET_NAME
    settings["MINIO_STORAGE_STATIC_URL"] = "{base_url}/{bucket_name}".format(
        base_url=env("STORAGE_MINIO_STATIC_BASE_URL"),
        bucket_name=STATIC_BUCKET_NAME,
    )

    settings["MINIO_STORAGE_USE_HTTPS"] = False
    settings["MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET"] = True
    settings["MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET"] = True
    settings["MINIO_STORAGE_MEDIA_USE_PRESIGNED"] = False
