import time
from django.core import signing
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle


class ChallengeBurstThrottle(AnonRateThrottle):
    scope = "challenge_burst"


class ChallengeSustainedThrottle(AnonRateThrottle):
    scope = "challenge_sustained"


class ChallengeView(generics.views.APIView):
    throttle_classes = [ChallengeBurstThrottle, ChallengeSustainedThrottle]
    permission_classes = [permissions.AllowAny]

    def get_throttles(self):
        is_ssr = self.request.META.get("HTTP_X_REQUEST_SOURCE") == "nuxt-ssr"
        if is_ssr:
            # do not throttle ssr requests as we might block GoogleBot
            return []
        return super().get_throttles()

    def get(self, request):
        # TODO add user-agent sha in the returned token
        # then check in middleware:
        # if token.user_agent_sha != sha256(request.headers["User-Agent"])): raise 403
        token = signing.dumps({"ts": time.time()})
        return Response({"token": token})


class HealthCheckView(generics.views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_200_OK)
