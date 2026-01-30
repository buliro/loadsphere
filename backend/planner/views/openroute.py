from __future__ import annotations

import json

from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_GET, require_POST

from ..services.openroute import search_locations, plan_route, RoutePlannerError


@require_GET
def search_locations_view(request: HttpRequest) -> JsonResponse:
    """Proxy OpenRouteService location search for authenticated users.

    Args:
        request: HTTP request containing query parameters `q` and optional `limit`.

    Returns:
        JsonResponse: Payload of location suggestions or an error message with HTTP
        status 401/502 if authentication fails or the external service errors.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse({"results": []}, status=200)

    limit_param = request.GET.get("limit") or ""
    try:
        limit = int(limit_param) if limit_param else 5
    except ValueError:
        limit = 5

    try:
        results = search_locations(query, limit=limit)
    except RoutePlannerError as exc:
        return JsonResponse({"detail": str(exc)}, status=502)

    return JsonResponse({"results": results}, status=200)


@require_POST
def route_distance_view(request: HttpRequest) -> JsonResponse:
    """Compute the routed road distance for an ordered collection of coordinates.

    Args:
        request: HTTP request whose JSON body must include a ``locations`` array with
            at least two objects containing ``lat`` and ``lng`` numeric values. An
            optional ``profile`` string may be supplied to choose the OpenRouteService
            routing profile.

    Returns:
        JsonResponse: Payload containing the total distance (miles), duration (hours),
        decoded segments metadata, and the encoded polyline describing the routed
        geometry. HTTP 401 is returned when the caller is unauthenticated, 400 for
        invalid payloads, and 502 when the upstream routing service fails.
    """

    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    locations = payload.get("locations")
    if not isinstance(locations, list) or len(locations) < 2:
        return JsonResponse({"detail": "Provide at least two locations with lat/lng."}, status=400)

    parsed_locations = []
    for index, raw_location in enumerate(locations):
        if not isinstance(raw_location, dict):
            return JsonResponse({"detail": f"Location at index {index} must be an object."}, status=400)

        lat = raw_location.get("lat")
        lng = raw_location.get("lng")

        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return JsonResponse(
                {"detail": f"Location at index {index} requires numeric lat and lng."},
                status=400,
            )

        parsed_locations.append({"lat": float(lat), "lng": float(lng)})

    profile = payload.get("profile") or "driving-hgv"

    try:
        route_data = plan_route(parsed_locations, profile=profile)
    except RoutePlannerError as exc:
        return JsonResponse({"detail": str(exc)}, status=502)

    return JsonResponse(
        {
            "total_distance_miles": route_data.get("total_distance_miles", 0.0),
            "total_duration_hours": route_data.get("total_duration_hours", 0.0),
            "polyline": route_data.get("polyline"),
            "segments": route_data.get("segments", []),
        },
        status=200,
    )
