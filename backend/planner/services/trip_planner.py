from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, Sequence, Iterable, List

from django.db import transaction
from django.utils import timezone

from ..models import User, Trip, Route, Stop, DriverLog, DutyStatusSegment, BackgroundJob
from .openroute import plan_route, RoutePlannerError
from .hos import (
    generate_driver_logs,
    HOSComputationError,
    DRIVING_LIMIT_PER_DAY,
    ON_DUTY_LIMIT_PER_DAY,
    CYCLE_LIMIT_HOURS,
)


def _evaluate_hos_alerts(
    log_payloads: Sequence[Dict[str, Any]], cycle_hours_used: float
) -> List[Dict[str, Any]]:
    """Derive Hours-of-Service alerts from generated log payloads.

    Args:
        log_payloads: Sequence of log dictionaries describing planned duty totals.
        cycle_hours_used: Total cycle hours consumed before the planned trip.

    Returns:
        List[Dict[str, Any]]: Alert records detailing rule, severity level, and message.
    """
    alerts: List[Dict[str, Any]] = []

    def _add_alert(level: str, rule: str, message: str, day_number: int | None = None) -> None:
        """Append an alert record to the running list.

        Args:
            level: Severity indicator such as "warning" or "danger".
            rule: Name of the HOS rule being referenced.
            message: Human-readable description of the issue.
            day_number: Optional day number for day-specific alerts.

        Returns:
            None
        """
        alerts.append(
            {
                "level": level,
                "rule": rule,
                "message": message,
                "day_number": day_number,
            }
        )

    for payload in log_payloads:
        day_number = int(payload.get("day_number", 0)) or None

        driving_minutes_raw = payload.get("total_driving_minutes")
        if driving_minutes_raw is None:
            driving_hours_raw = payload.get("total_driving_hours")
            if driving_hours_raw is not None:
                driving_minutes_raw = float(driving_hours_raw) * 60.0
        driving_minutes = float(driving_minutes_raw or 0.0)

        on_duty_minutes_raw = payload.get("total_on_duty_minutes")
        if on_duty_minutes_raw is None:
            on_duty_hours_raw = payload.get("total_on_duty_hours")
            if on_duty_hours_raw is not None:
                on_duty_minutes_raw = float(on_duty_hours_raw) * 60.0
        on_duty_minutes = float(on_duty_minutes_raw or 0.0)

        remaining_cycle = payload.get("remaining_cycle_hours")

        driving = driving_minutes / 60.0
        on_duty = on_duty_minutes / 60.0

        if driving > DRIVING_LIMIT_PER_DAY + 1e-6:
            _add_alert(
                "danger",
                "11-hour driving limit",
                f"Day {day_number}: planned driving of {driving:.1f} hrs exceeds FMCSA 11-hour limit.",
                day_number,
            )
        elif driving >= DRIVING_LIMIT_PER_DAY * 0.95:
            _add_alert(
                "warning",
                "11-hour driving limit",
                f"Day {day_number}: driving scheduled for {driving:.1f} hrs is near the 11-hour limit.",
                day_number,
            )

        if on_duty > ON_DUTY_LIMIT_PER_DAY + 1e-6:
            _add_alert(
                "danger",
                "14-hour on-duty window",
                f"Day {day_number}: on-duty time of {on_duty:.1f} hrs exceeds FMCSA 14-hour limit.",
                day_number,
            )
        elif on_duty >= ON_DUTY_LIMIT_PER_DAY * 0.95:
            _add_alert(
                "warning",
                "14-hour on-duty window",
                f"Day {day_number}: on-duty plan {on_duty:.1f} hrs is near the 14-hour limit.",
                day_number,
            )

        if isinstance(remaining_cycle, (float, int)):
            remaining_cycle = float(remaining_cycle)
            if remaining_cycle < -1e-6:
                _add_alert(
                    "danger",
                    "70-hour/8-day cycle",
                    "Cycle hours exceeded. Schedule requires reset before completion.",
                    day_number,
                )
            elif remaining_cycle <= 8.0:
                _add_alert(
                    "warning",
                    "70-hour/8-day cycle",
                    f"Cycle hours low: {remaining_cycle:.1f} hrs remain after day {day_number}.",
                    day_number,
                )

    projected_cycle_usage = cycle_hours_used + sum(
        (
            (float(entry.get("total_on_duty_minutes")) / 60.0)
            if entry.get("total_on_duty_minutes") is not None
            else float(entry.get("total_on_duty_hours", 0.0))
        )
        for entry in log_payloads
    )
    if projected_cycle_usage >= CYCLE_LIMIT_HOURS:
        _add_alert(
            "danger",
            "70-hour/8-day cycle",
            "Trip plan consumes entire 70-hour cycle. Driver must reset before additional duty.",
            None,
        )
    elif projected_cycle_usage >= CYCLE_LIMIT_HOURS * 0.9:
        _add_alert(
            "warning",
            "70-hour/8-day cycle",
            "Trip plan uses over 90% of the 70-hour cycle. Monitor remaining hours closely.",
            None,
        )

    return alerts


class TripPlanningError(Exception):
    """Raised when synchronous or asynchronous trip planning fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _build_stop_definitions(locations: Sequence[Dict[str, Any]]) -> Sequence[Dict[str, Any]]:
    """Produce canonical stop payloads for start, pickup, and dropoff locations.

    Args:
        locations: Ordered sequence of dictionaries representing trip locations.

    Returns:
        Sequence[Dict[str, Any]]: Stop definitions seeded with placeholder metrics.
    """
    labels = ["START", "PICKUP", "DROPOFF"]
    return [
        {
            "type": label,
            "location": location,
            "distance_from_previous": 0.0,
            "duration_from_previous": 0.0,
        }
        for label, location in zip(labels, locations)
    ]


def plan_trip_for_user(
    *,
    user: User,
    start_location: Dict[str, Any],
    pickup_location: Dict[str, Any],
    dropoff_location: Dict[str, Any],
    cycle_hours_used: float,
    tractor_number: str | None = None,
    trailer_numbers: list[str] | None = None,
    carrier_names: list[str] | None = None,
    main_office_address: str | None = None,
    home_terminal_address: str | None = None,
    co_driver_name: str | None = None,
    shipper_name: str | None = None,
    commodity: str | None = None,
) -> Trip:
    """Plan a trip and persist all related data synchronously.

    Args:
        user: Account requesting the plan; used for ownership checks.
        start_location: JSON-compatible dict describing the trip start.
        pickup_location: Intermediate pickup location metadata.
        dropoff_location: Dropoff location metadata.
        cycle_hours_used: Hours already consumed in the driver's cycle.
        tractor_number: Optional tractor identifier.
        trailer_numbers: Optional trailer identifiers.
        carrier_names: Optional list of carrier names.
        main_office_address: Optional carrier main office address.
        home_terminal_address: Optional home terminal address.
        co_driver_name: Optional co-driver name.
        shipper_name: Optional shipper name.
        commodity: Optional commodity description.

    Returns:
        Trip: Newly created trip with associated route, stops, and itinerary summary persisted.

    Raises:
        TripPlanningError: When routing or data persistence fails.
    """

    if user is None:
        raise TripPlanningError("A valid user is required to plan a trip.")

    with transaction.atomic():
        trip = Trip.objects.create(
            user=user,
            start_location=start_location,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            cycle_hours_used=cycle_hours_used,
            status='PLANNED',
            tractor_number=tractor_number or '',
            trailer_numbers=trailer_numbers or [],
            carrier_names=carrier_names or [],
            main_office_address=main_office_address or '',
            home_terminal_address=home_terminal_address or '',
            co_driver_name=co_driver_name or '',
            shipper_name=shipper_name or '',
            commodity=commodity or '',
        )

        try:
            route_data = plan_route(
                [
                    start_location,
                    pickup_location,
                    dropoff_location,
                ],
                search_radius_meters=5000,
            )
        except RoutePlannerError as exc:
            raise TripPlanningError(str(exc)) from exc

        route = Route.objects.create(
            trip=trip,
            polyline=route_data.get('polyline', ''),
            total_distance=route_data.get('total_distance_miles', 0.0),
            estimated_duration=route_data.get('total_duration_hours', 0.0),
        )

        trip.total_miles = route.total_distance
        trip.total_hours = route.estimated_duration

        stop_definitions = list(
            _build_stop_definitions([
                start_location,
                pickup_location,
                dropoff_location,
            ])
        )

        segments = route_data.get('segments', [])
        legs_payload = []

        for idx in range(1, len(stop_definitions)):
            segment = segments[idx - 1] if idx - 1 < len(segments) else {}
            distance = float(segment.get('distance_miles', 0.0))
            duration_hours = float(segment.get('duration_hours', segment.get('duration_minutes', 0.0) / 60.0))

            stop_definitions[idx]['distance_from_previous'] = distance
            stop_definitions[idx]['duration_from_previous'] = duration_hours

            legs_payload.append(
                {
                    'sequence': idx,
                    'from_stop_type': stop_definitions[idx - 1]['type'],
                    'to_stop_type': stop_definitions[idx]['type'],
                    'from_location': stop_definitions[idx - 1]['location'],
                    'to_location': stop_definitions[idx]['location'],
                    'distance_miles': distance,
                    'duration_hours': duration_hours,
                }
            )

        stop_records = [
            Stop(
                route=route,
                stop_type=definition['type'],
                location=definition['location'],
                duration_minutes=definition.get('duration_minutes', 0),
                sequence=index,
                distance_from_previous=definition.get('distance_from_previous', 0.0),
                duration_from_previous=definition.get('duration_from_previous', 0.0),
            )
            for index, definition in enumerate(stop_definitions, start=1)
        ]
        Stop.objects.bulk_create(stop_records)

        trip.itinerary_summary = {
            'legs': legs_payload,
            'total_distance_miles': route.total_distance,
            'total_duration_hours': route.estimated_duration,
            'hos_alerts': [],
        }
        trip.save(update_fields=['total_miles', 'total_hours', 'itinerary_summary', 'updated_at'])

    return trip


def enqueue_trip_job(
    *,
    user: User,
    start_location: Dict[str, Any],
    pickup_location: Dict[str, Any],
    dropoff_location: Dict[str, Any],
    cycle_hours_used: float,
    tractor_number: str | None = None,
    trailer_numbers: list[str] | None = None,
    carrier_names: list[str] | None = None,
    main_office_address: str | None = None,
    home_terminal_address: str | None = None,
    co_driver_name: str | None = None,
    shipper_name: str | None = None,
    commodity: str | None = None,
) -> BackgroundJob:
    """Create a background job to plan a trip asynchronously.

    Args:
        user: Owner of the job and resulting trip.
        start_location: Trip start location payload.
        pickup_location: Trip pickup location payload.
        dropoff_location: Trip dropoff location payload.
        cycle_hours_used: Hours already consumed in the driver's cycle.
        tractor_number: Optional tractor identifier.
        trailer_numbers: Optional trailer identifiers.
        carrier_names: Optional carrier names.
        main_office_address: Optional business office address.
        home_terminal_address: Optional terminal address.
        co_driver_name: Optional co-driver name.
        shipper_name: Optional shipper name.
        commodity: Optional commodity name.

    Returns:
        BackgroundJob: Persisted job configured to generate the trip.
    """
    payload = {
        'start_location': start_location,
        'pickup_location': pickup_location,
        'dropoff_location': dropoff_location,
        'cycle_hours_used': cycle_hours_used,
    }

    optional_fields: list[tuple[str, Any]] = [
        ('tractor_number', tractor_number),
        ('trailer_numbers', trailer_numbers),
        ('carrier_names', carrier_names),
        ('main_office_address', main_office_address),
        ('home_terminal_address', home_terminal_address),
        ('co_driver_name', co_driver_name),
        ('shipper_name', shipper_name),
        ('commodity', commodity),
    ]

    for key, value in optional_fields:
        if value:
            payload[key] = value

    return BackgroundJob.objects.create(
        user=user,
        job_type=BackgroundJob.JOB_TYPE_PLAN_TRIP,
        payload=payload,
    )


def _run_trip_job(job: BackgroundJob) -> Trip:
    """Execute a trip planning job and persist resulting trip.

    Args:
        job: Background job instance containing planning parameters.

    Returns:
        Trip: Created trip associated with the job's user.

    Raises:
        TripPlanningError: Propagated when planning fails or data is invalid.
    """
    payload = job.payload or {}

    user = job.user
    start_location = payload.get('start_location')
    pickup_location = payload.get('pickup_location')
    dropoff_location = payload.get('dropoff_location')
    cycle_hours_used = float(payload.get('cycle_hours_used', 0.0))
    tractor_number = payload.get('tractor_number')
    trailer_numbers = payload.get('trailer_numbers')
    carrier_names = payload.get('carrier_names')
    main_office_address = payload.get('main_office_address')
    home_terminal_address = payload.get('home_terminal_address')
    co_driver_name = payload.get('co_driver_name')
    shipper_name = payload.get('shipper_name')
    commodity = payload.get('commodity')

    if user is None:
        raise TripPlanningError("Associated user no longer exists for this job.")

    return plan_trip_for_user(
        user=user,
        start_location=start_location,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        cycle_hours_used=cycle_hours_used,
        tractor_number=tractor_number,
        trailer_numbers=trailer_numbers,
        carrier_names=carrier_names,
        main_office_address=main_office_address,
        home_terminal_address=home_terminal_address,
        co_driver_name=co_driver_name,
        shipper_name=shipper_name,
        commodity=commodity,
    )


def process_pending_trip_jobs(limit: int = 10) -> Iterable[BackgroundJob]:
    """Process pending trip planning background jobs in FIFO order.

    Args:
        limit: Maximum number of jobs to fetch and process.

    Returns:
        Iterable[BackgroundJob]: Sequence of jobs that were processed with updated status.
    """
    logger = logging.getLogger(__name__)
    pending_jobs = (
        BackgroundJob.objects
        .select_related('user')
        .filter(job_type=BackgroundJob.JOB_TYPE_PLAN_TRIP, status=BackgroundJob.STATUS_PENDING)
        .order_by('created_at')[:limit]
    )

    processed = []

    for job in pending_jobs:
        job.mark_running()
        try:
            trip = _run_trip_job(job)
            job.mark_success({'trip_id': str(trip.id)})
            logger.info(
                "trip_job.success",
                extra={"job_id": str(job.id), "trip_id": str(trip.id)},
            )
        except TripPlanningError as exc:
            job.mark_failed(exc.message)
            logger.warning(
                "trip_job.failed_known_error",
                extra={"job_id": str(job.id), "error": exc.message},
            )
        except Exception as exc:  # Capture unexpected failures
            job.mark_failed(str(exc))
            logger.exception(
                "trip_job.failed_unexpected",
                extra={"job_id": str(job.id)},
            )
        processed.append(job)

    return processed


def run_job(job_id: str) -> BackgroundJob:
    """Run a specific background job by identifier.

    Args:
        job_id: Primary key of the background job to execute.

    Returns:
        BackgroundJob: Job instance after execution with updated status/result.
    """
    logger = logging.getLogger(__name__)
    job = BackgroundJob.objects.get(id=job_id)
    if job.status not in (BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING):
        return job

    job.mark_running()
    try:
        trip = _run_trip_job(job)
        job.mark_success({'trip_id': str(trip.id)})
        logger.info(
            "trip_job.success",
            extra={"job_id": str(job.id), "trip_id": str(trip.id)},
        )
    except TripPlanningError as exc:
        job.mark_failed(exc.message)
        logger.warning(
            "trip_job.failed_known_error",
            extra={"job_id": str(job.id), "error": exc.message},
        )
    except Exception as exc:
        job.mark_failed(str(exc))
        logger.exception(
            "trip_job.failed_unexpected",
            extra={"job_id": str(job.id)},
        )
    return job
