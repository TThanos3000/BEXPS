from django.conf import settings
from django.http import HttpResponse


class DevCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        is_allowed_origin = origin in getattr(settings, "INWORS_CORS_ALLOWED_ORIGINS", [])

        if (
            is_allowed_origin
            and request.method == "OPTIONS"
            and request.headers.get("Access-Control-Request-Method")
        ):
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if is_allowed_origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = (
                "Content-Type, X-XSRF-TOKEN, X-CSRFToken, X-Requested-With"
            )
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Max-Age"] = "86400"
            response["Vary"] = "Origin"

        return response
