import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ContextProvider:
    """Simple class that can be used to customize EmailTemplates common context.
    Overwrite get_common_context method then point your class in settings:
    BACKBONE_EMAILS_EMAILTEMPLATE_CONTEXT_PROVIDER = 'example.context.MyContextProvider'
    """

    def _get(self, **extra_context):
        context = self.get_common_context()
        context.update(extra_context)
        return context

    def get_common_context(self):
        """Returns common context that is used in all emails"""
        context = {}

        # add EmailBase context and inject utm params into urls
        path_logo = settings.BACKBONE_EMAILS_EMAILTEMPLATE_PATH_LOGO
        path_settings_notifications = (
            settings.BACKBONE_EMAILS_EMAILTEMPLATE_PATH_SETTINGS_NOTIFICATIONS
        )

        context.update(
            {
                "url_index": settings.FRONTEND_PUBLIC_URL,
                "url_logo": f"{settings.FRONTEND_PUBLIC_URL}{path_logo}",
                "url_settings_notifications": f"{settings.FRONTEND_PUBLIC_URL}{path_settings_notifications}",
            }
        )
        return context
