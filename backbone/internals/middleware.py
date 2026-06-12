from django.conf import settings
from django.core import signing
from django.http import HttpResponseForbidden
from django.urls import reverse


class SetRemoteAddrMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request = self.set_remote_addr(request)
        return self.get_response(request)

    def set_remote_addr(self, request):
        """Set proper REMOTE_ADDR address from X_FORWARDED_FOR header
        This is used in deployments where REMOTE_ADDR header is overwritten by
        docker ips and the real public ip gets lost.
        """
        if "HTTP_X_FORWARDED_FOR" in request.META:
            request.META["REMOTE_ADDR"] = (
                request.META["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
            )

        return request


class XChallengeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.BACKBONE_INTERNALS_X_CHALLENGE_ENABLED:
            return self.get_response(request)

        # requests going to these paths are excluded from the token check
        bypass = request.path in map(
            reverse, settings.BACKBONE_INTERNALS_X_CHALLENGE_WHITELIST_PATHS
        )

        if request.path.startswith("/api/") and not bypass:
            token = request.headers.get("x-challenge-token")
            if not token:
                return HttpResponseForbidden("missing-challenge-token")

            try:
                signing.loads(
                    token, max_age=settings.BACKBONE_INTERNALS_X_CHALLENGE_TOKEN_MAX_AGE
                )
            except Exception:
                return HttpResponseForbidden("invalid-challenge-token")

        return self.get_response(request)
