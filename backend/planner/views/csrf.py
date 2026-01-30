from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf_token_view(_request):
    """Set a CSRF cookie and confirm success.

    Args:
        _request: Incoming HTTP request; unused but required by Django view signature.

    Returns:
        JsonResponse: Payload confirming that a CSRF cookie is present.
    """
    return JsonResponse({"success": True})
