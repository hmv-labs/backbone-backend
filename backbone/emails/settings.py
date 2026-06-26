from backbone.bootstrap import env


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "backbone.emails",
    ]

    # below are paths relative to FRONTEND_PUBLIC_URL
    # they are used in models.EmailTemplate.send when building the context
    settings["BACKBONE_EMAILS_EMAILTEMPLATE_PATH_LOGO"] = env.str(
        "BACKBONE_EMAILS_EMAILTEMPLATE_PATH_LOGO", "/logos/logo_email.png"
    )
    settings["BACKBONE_EMAILS_EMAILTEMPLATE_PATH_SETTINGS_NOTIFICATIONS"] = env.str(
        "BACKBONE_EMAILS_EMAILTEMPLATE_PATH_SETTINGS_NOTIFICATIONS",
        "/settings/notifications",
    )
    settings["BACKBONE_EMAILS_EMAILTEMPLATE_CONTEXT_PROVIDER"] = (
        "backbone.emails.context.ContextProvider"
    )
