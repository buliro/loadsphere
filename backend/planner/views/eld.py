from __future__ import annotations

import csv
from datetime import datetime
from typing import Any, Dict

from django.http import HttpResponse, JsonResponse, HttpRequest
from django.utils import timezone

from ..models import Trip


def _unauthorized() -> JsonResponse:
    """Return a standard 401 JSON response for unauthenticated access."""
    return JsonResponse({"detail": "Authentication required."}, status=401)


def _parse_iso_date(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string into a datetime object or return None when invalid."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _serialize_trip_summary(trip: Trip) -> Dict[str, Any]:
    """Summarise a trip for list responses."""
    return {
        "id": trip.id,
        "status": trip.status,
        "total_miles": trip.total_miles,
        "total_hours": trip.total_hours,
        "cycle_hours_used": trip.cycle_hours_used,
        "created_at": trip.created_at.isoformat(),
        "updated_at": trip.updated_at.isoformat(),
    }


def _serialize_trip_detail(trip: Trip) -> Dict[str, Any]:
    """Expand a trip object with route, stop, and driver log details."""
    route = getattr(trip, "route", None)
    stops = []
    if route:
        stops = [
            {
                "id": stop.id,
                "stop_type": stop.stop_type,
                "location": stop.location,
                "sequence": stop.sequence,
                "distance_from_previous": stop.distance_from_previous,
                "duration_from_previous": stop.duration_from_previous,
                "duration_minutes": stop.duration_minutes,
            }
            for stop in route.stops.all().order_by("sequence")
        ]

    logs = [
        {
            "id": log.id,
            "day_number": log.day_number,
            "log_data": log.log_data,
            "created_at": log.created_at.isoformat(),
            "updated_at": log.updated_at.isoformat(),
        }
        for log in trip.logs.all().order_by("day_number")
    ]

    return {
        **_serialize_trip_summary(trip),
        "start_location": trip.start_location,
        "pickup_location": trip.pickup_location,
        "dropoff_location": trip.dropoff_location,
        "itinerary_summary": trip.itinerary_summary,
        "route": {
            "polyline": route.polyline if route else None,
            "total_distance": route.total_distance if route else None,
            "estimated_duration": route.estimated_duration if route else None,
            "stops": stops,
        }
        if route
        else None,
        "driver_logs": logs,
    }


def eld_trips_view(request: HttpRequest) -> JsonResponse:
    """Return the authenticated user's trips with optional date filtering."""
    if not request.user.is_authenticated:
        return _unauthorized()

    trips = Trip.objects.filter(user=request.user).order_by("-created_at")

    start_param = _parse_iso_date(request.GET.get("start"))
    end_param = _parse_iso_date(request.GET.get("end"))
    if start_param:
        trips = trips.filter(created_at__gte=timezone.make_aware(start_param))
    if end_param:
        trips = trips.filter(created_at__lte=timezone.make_aware(end_param))

    payload = [_serialize_trip_summary(trip) for trip in trips]
    return JsonResponse({"results": payload}, status=200)


def eld_trip_detail_view(request: HttpRequest, trip_id: int) -> HttpResponse:
    """Return a detailed trip payload or CSV export for the specified trip."""
    if not request.user.is_authenticated:
        return _unauthorized()

    try:
        trip = Trip.objects.select_related("route").prefetch_related("logs", "route__stops").get(
            id=trip_id, user=request.user
        )
    except Trip.DoesNotExist:
        return JsonResponse({"detail": "Trip not found."}, status=404)

    if request.GET.get("format") == "csv":
        return _render_trip_csv(trip)

    return JsonResponse(_serialize_trip_detail(trip), status=200)


def _render_trip_csv(trip: Trip) -> HttpResponse:
    """Stream a CSV export of driver log data for a trip."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="trip_{trip.id}_logs.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "trip_id",
            "day_number",
            "total_driving_hours",
            "total_on_duty_hours",
            "remaining_cycle_hours",
            "notes",
        ]
    )

    for log in trip.logs.all().order_by("day_number"):
        data = log.log_data or {}
        notes = "; ".join(data.get("notes", [])) if isinstance(data.get("notes"), list) else ""
        writer.writerow(
            [
                trip.id,
                log.day_number,
                data.get("total_driving_hours", ""),
                data.get("total_on_duty_hours", ""),
                data.get("remaining_cycle_hours", ""),
                notes,
            ]
        )

    return response
