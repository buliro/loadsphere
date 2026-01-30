
DEFAULT_SEARCH_RADIUS_METERS = 5000
import logging
import os
from typing import List, Dict, Any, Sequence

import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class RoutePlannerError(Exception):
    """Raised when the route planning service encounters an error."""


def _get_api_key() -> str:
    """Retrieve the OpenRouteService API key from settings or environment.

    Args:
        None

    Returns:
        str: API key string required to authenticate requests.

    Raises:
        RoutePlannerError: If no API key is configured.
    """
    api_key = getattr(settings, "OPENROUTESERVICE_API_KEY", None) or os.getenv(
        "OPENROUTESERVICE_API_KEY"
    )
    if not api_key:
        raise RoutePlannerError(
            "OpenRouteService API key is not configured. Set OPENROUTESERVICE_API_KEY in the environment."
        )
    return api_key


def _build_coordinates(locations: List[Dict[str, Any]]) -> List[List[float]]:
    """Convert location dictionaries into coordinate pairs.

    Args:
        locations: Sequence of mapping objects containing `lat` and `lng` keys.

    Returns:
        List[List[float]]: Coordinates formatted for OpenRouteService requests.

    Raises:
        RoutePlannerError: If any location is missing or lacks coordinate data.
    """
    coordinates = []
    for location in locations:
        if location is None:
            raise RoutePlannerError("Location data is missing.")
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            raise RoutePlannerError("Each location must include 'lat' and 'lng' values.")
        coordinates.append([float(lng), float(lat)])
    return coordinates


def _normalise_radiuses(radius: float | Sequence[float] | None, count: int) -> List[float]:
    """Ensure radius inputs align with the number of requested coordinates.

    Args:
        radius: Single radius, sequence of radiuses, or None for defaults.
        count: Number of coordinates provided to the routing API.

    Returns:
        List[float]: Sequence of radiuses capped at 10km per coordinate.

    Raises:
        RoutePlannerError: When a sequence length does not match the coordinate count.
    """
    if radius is None:
        return [float(DEFAULT_SEARCH_RADIUS_METERS)] * count

    if isinstance(radius, (int, float)):
        value = min(float(radius), 10000.0)
        return [value] * count

    values = list(radius)
    if len(values) != count:
        raise RoutePlannerError(
            "Radiuses sequence length must match number of coordinates."
        )

    normalised: List[float] = []
    for value in values:
        normalised.append(min(float(value), 10000.0))

    return normalised


def plan_route(
    locations: List[Dict[str, Any]],
    profile: str = "driving-hgv",
    timeout: int = 30,
    *,
    search_radius_meters: float | Sequence[float] | None = None,
) -> Dict[str, Any]:
    """Plan a route using OpenRouteService for the provided locations.

    Args:
        locations: Ordered list of dictionaries with at least `lat` and `lng` keys.
        profile: ORS routing profile to use for routing calculations.
        timeout: Request timeout in seconds for the HTTP request.
        search_radius_meters: Optional radius or radiuses to expand snapping tolerance.

    Returns:
        Dict[str, Any]: Geometry, total distance (miles), total duration (hours), and
            per-segment breakdown.

    Raises:
        RoutePlannerError: If the API key is missing or the request fails.
    """

    api_key = _get_api_key()
    coordinates = _build_coordinates(locations)

    url = f"https://api.openrouteservice.org/v2/directions/{profile}"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "coordinates": coordinates,
        "units": "mi",
        "radiuses": _normalise_radiuses(search_radius_meters, len(coordinates)),
    }

    logger.info(
        "openrouteservice.request",
        extra={
            "profile": profile,
            "coordinates_count": len(coordinates),
            "timeout": timeout,
        },
    )

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.exception("openrouteservice.network_error", extra={"profile": profile})
        raise RoutePlannerError(f"Failed to contact OpenRouteService: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "openrouteservice.error_response",
            extra={
                "status_code": response.status_code,
                "body": response.text,
                "profile": profile,
            },
        )
        raise RoutePlannerError(
            f"OpenRouteService error ({response.status_code}): {response.text}"
        )

    data = response.json()
    routes = data.get("routes") or []
    if not routes:
        raise RoutePlannerError("OpenRouteService returned no routes for the given coordinates.")

    route = routes[0]
    summary = route.get("summary", {})
    segments = route.get("segments", [])

    geometry = route.get("geometry")
    if isinstance(geometry, dict):
        geometry = geometry.get("geometry") or geometry.get("coordinates") or ""

    total_distance_miles = float(summary.get("distance", 0.0))
    total_duration_hours = float(summary.get("duration", 0.0)) / 3600.0

    segment_details = []
    for segment in segments:
        segment_details.append(
            {
                "distance_miles": float(segment.get("distance", 0.0)),
                "duration_minutes": float(segment.get("duration", 0.0)) / 60.0,
                "duration_hours": float(segment.get("duration", 0.0)) / 3600.0,
            }
        )

    payload = {
        "polyline": geometry or "",
        "total_distance_miles": total_distance_miles,
        "total_duration_hours": total_duration_hours,
        "segments": segment_details,
    }

    logger.info(
        "openrouteservice.response",
        extra={
            "profile": profile,
            "total_distance_miles": round(total_distance_miles, 2),
            "total_duration_hours": round(total_duration_hours, 2),
            "segment_count": len(segment_details),
        },
    )

    return payload


def search_locations(
    query: str,
    *,
    limit: int = 5,
    timeout: int = 10,
) -> List[Dict[str, Any]]:
    """Search locations using OpenRouteService geocoding API.

    Args:
        query: Free-form text describing the location.
        limit: Maximum number of results to return (1-10).
        timeout: Request timeout in seconds for the HTTP call.

    Returns:
        List[Dict[str, Any]]: Normalised geocoding results with coordinates and context.

    Raises:
        RoutePlannerError: When the geocoding API fails or returns invalid data.
    """

    query = (query or "").strip()
    if not query:
        return []

    api_key = _get_api_key()
    limit = max(1, min(int(limit), 10))

    url = "https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": api_key,
        "text": query,
        "size": limit,
    }
    headers = {
        "Accept": "application/json",
    }

    logger.info(
        "openrouteservice.geocode.request",
        extra={"query": query, "limit": limit},
    )

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.exception(
            "openrouteservice.geocode.network_error",
            extra={"query": query},
        )
        raise RoutePlannerError(
            f"Failed to contact OpenRouteService geocoder: {exc}"
        ) from exc

    if response.status_code != 200:
        logger.error(
            "openrouteservice.geocode.error_response",
            extra={
                "status_code": response.status_code,
                "body": response.text,
                "query": query,
            },
        )
        raise RoutePlannerError(
            f"OpenRouteService geocoding error ({response.status_code}): {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RoutePlannerError("OpenRouteService geocoding returned invalid JSON") from exc

    features = payload.get("features") or []
    results: List[Dict[str, Any]] = []

    for feature in features:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []

        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
            continue

        properties = feature.get("properties") or {}

        label = (
            properties.get("label")
            or properties.get("name")
            or properties.get("formatted")
            or properties.get("display_name")
            or query
        )

        results.append(
            {
                "id": properties.get("id")
                or properties.get("gid")
                or feature.get("id")
                or label,
                "label": label,
                "address": label,
                "lat": float(coordinates[1]),
                "lng": float(coordinates[0]),
                "context": {
                    "country": properties.get("country"),
                    "region": properties.get("region")
                    or properties.get("state")
                    or properties.get("state_district"),
                    "county": properties.get("county"),
                    "locality": properties.get("locality")
                    or properties.get("city")
                    or properties.get("municipality"),
                },
            }
        )

    return results
