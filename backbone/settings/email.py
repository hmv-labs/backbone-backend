from backbone.env import env

EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
EMAIL_SUBJECT_PREFIX = ""

# Custom use - no reply email host user
EMAIL_HOST_USER_NOREPLY = env("EMAIL_HOST_USER_NOREPLY")

# The email address that error messages come from
# such as those sent to ADMINS and MANAGERS
SERVER_EMAIL = EMAIL_HOST_USER_NOREPLY
