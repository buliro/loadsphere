import json
from typing import Any, Dict, List

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()


def _serialize_user(user: User) -> Dict[str, Any]:
    """Return a JSON-serialisable dictionary with the public user attributes.

    Args:
        user: Django user instance to normalise.

    Returns:
        Dict[str, Any]: Public fields that can be sent to the frontend.
    """
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def _error_response(errors: List[str], status: int = 400) -> JsonResponse:
    """Build a JsonResponse describing validation errors.

    Args:
        errors: List of validation error messages.
        status: HTTP status code to send back with the response.

    Returns:
        JsonResponse: Structured payload with `success` flag and errors list.
    """
    return JsonResponse({"success": False, "errors": errors}, status=status)


def _parse_json_body(request: HttpRequest) -> Dict[str, Any] | None:
    """Decode and parse request.body as JSON, returning None when invalid.

    Args:
        request: Incoming HTTP request carrying a JSON body.

    Returns:
        Dict[str, Any] | None: Parsed JSON payload, empty dict for no body, or None if parsing fails.
    """
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


@csrf_exempt
def register_view(request: HttpRequest) -> JsonResponse:
    """Handle user registration, creating an account and immediately logging in.

    Args:
        request: HTTP request containing registration fields in JSON format.

    Returns:
        JsonResponse: Success payload with user data or errors with proper status code.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    payload = _parse_json_body(request)
    if payload is None:
        return _error_response(["Invalid JSON payload."])

    email = payload.get("email", "").strip().lower()
    password1 = payload.get("password1", "")
    password2 = payload.get("password2", "")
    first_name = payload.get("first_name", "").strip()
    last_name = payload.get("last_name", "").strip()

    errors: List[str] = []

    if not email:
        errors.append("Email address is required.")
    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")
    if len(password1) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password1 != password2:
        errors.append("Passwords do not match.")

    if User.objects.filter(email=email).exists():
        errors.append("A user with this email already exists.")

    if errors:
        return _error_response(errors)

    try:
        user = User.objects.create_user(
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )
    except ValueError as exc:
        return _error_response([str(exc)])

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({"success": True, "user": _serialize_user(user)}, status=201)


@csrf_exempt
def login_view(request: HttpRequest) -> JsonResponse:
    """Authenticate a user by email and password, returning the session payload.

    Args:
        request: HTTP request containing login credentials in JSON format.

    Returns:
        JsonResponse: Success payload with user data or error details on failure.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    payload = _parse_json_body(request)
    if payload is None:
        return _error_response(["Invalid JSON payload."])

    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        return _error_response(["Email and password are required."])

    user = authenticate(request, username=email, password=password)
    if user is None:
        return _error_response(["Invalid credentials."], status=401)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({"success": True, "user": _serialize_user(user)})


@csrf_exempt
def logout_view(request: HttpRequest) -> JsonResponse:
    """Terminate the current authenticated session.

    Args:
        request: HTTP request initiating the logout.

    Returns:
        JsonResponse: Payload confirming the user has been logged out.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    logout(request)
    return JsonResponse({"success": True})


def session_view(request: HttpRequest) -> JsonResponse:
    """Return the current session status and user details if authenticated.

    Args:
        request: HTTP request used to resolve the authenticated user.

    Returns:
        JsonResponse: Session state with optional serialised user data.
    """
    if request.user.is_authenticated:
        return JsonResponse({"authenticated": True, "user": _serialize_user(request.user)})

    return JsonResponse({"authenticated": False, "user": None})
