from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Iterable, Mapping

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import DriverLog, DutyStatusSegment, Trip

FIFTEEN_MINUTES = 15
MINUTES_PER_DAY = 24 * 60
VALID_STATUSES = {
    DriverLog.STATUS_OFF_DUTY,
    DriverLog.STATUS_SLEEPER,
    DriverLog.STATUS_DRIVING,
    DriverLog.STATUS_ON_DUTY,
}


@dataclass
class SegmentInput:
    status: str
    start_time: time
    end_time: time
    location: str
    activity: str
    remarks: str

    @property
    def duration_minutes(self) -> int:
        """Compute the segment duration in minutes.

        Returns:
            int: Total minutes between `start_time` and `end_time`.
        """
        start_dt = datetime.combine(datetime.today().date(), self.start_time)
        end_dt = datetime.combine(datetime.today().date(), self.end_time)
        delta = end_dt - start_dt
        minutes = int(delta.total_seconds() // 60)
        return minutes

    def validate(self) -> None:
        """Ensure the segment abides by status, ordering, and duration rules.

        Raises:
            ValidationError: When status is invalid, times are out of order, or duration is off.
        """
        if self.status not in VALID_STATUSES:
            raise ValidationError(f"Unsupported duty status '{self.status}'")
        if self.end_time <= self.start_time:
            raise ValidationError("Segment end_time must be after start_time")
        minutes = self.duration_minutes
        if minutes % FIFTEEN_MINUTES != 0:
            raise ValidationError("Duty segments must be in 15-minute increments")


def _parse_time(label: str, value: str | None) -> time:
    """Parse HH:MM-formatted strings into a `time` object.

    Args:
        label: Field name for error messages.
        value: Raw string input to parse.

    Returns:
        time: Parsed time value.

    Raises:
        ValidationError: If the value is missing or incorrectly formatted.
    """
    if not value:
        raise ValidationError(f"Missing {label}")
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValidationError(f"Invalid {label} format; expected HH:MM") from exc


def _normalise_segments(raw_segments: Iterable[Mapping[str, Any]]) -> list[SegmentInput]:
    """Convert raw payload dictionaries into validated `SegmentInput` objects.

    Args:
        raw_segments: Iterable of incoming segment payloads.

    Returns:
        list[SegmentInput]: Validated segment objects preserving input order.

    Raises:
        ValidationError: When any segment fails validation.
    """
    segments: list[SegmentInput] = []
    for raw in raw_segments:
        status = raw.get("status", DriverLog.STATUS_OFF_DUTY)
        start_time = _parse_time("startTime", raw.get("startTime"))
        end_time = _parse_time("endTime", raw.get("endTime"))
        segment = SegmentInput(
            status=status,
            start_time=start_time,
            end_time=end_time,
            location=(raw.get("location") or "")[:255],
            activity=(raw.get("activity") or "")[:255],
            remarks=raw.get("remarks") or "",
        )
        segment.validate()
        segments.append(segment)
    return segments


@transaction.atomic
def upsert_driver_log(
    *,
    user,
    trip_id: str,
    day_number: int,
    log_date,
    notes: str,
    segments: Iterable[Mapping[str, Any]],
    total_distance_miles: float | None = None,
) -> DriverLog:
    """Create or update a driver log and its duty status segments.

    Args:
        user: Authenticated user requesting the change; must own the trip.
        trip_id: Identifier of the trip being updated.
        day_number: Sequential day index for the log (1-based).
        log_date: Calendar date for the log entry.
        notes: Free-form notes to persist with the log.
        segments: Iterable payload describing duty status segments.
        total_distance_miles: Optional total distance driven that day.

    Returns:
        DriverLog: Persisted log instance reflecting the latest data.

    Raises:
        ValidationError: When payload values are invalid.
        PermissionDenied: When the trip does not belong to the requesting user.
    """
    if day_number <= 0:
        raise ValidationError("dayNumber must be 1 or greater")

    try:
        trip = Trip.objects.get(id=trip_id, user=user)
    except Trip.DoesNotExist as exc:
        raise PermissionDenied("Trip not found") from exc

    parsed_segments = _normalise_segments(segments)
    if not parsed_segments:
        raise ValidationError("At least one duty segment is required")

    totals = {
        DriverLog.STATUS_OFF_DUTY: 0,
        DriverLog.STATUS_SLEEPER: 0,
        DriverLog.STATUS_DRIVING: 0,
        DriverLog.STATUS_ON_DUTY: 0,
    }

    minutes_cursor = 0
    last_segment_end: time | None = None
    for segment in parsed_segments:
        minutes = segment.duration_minutes
        totals[segment.status] += minutes
        minutes_cursor += minutes
        if last_segment_end and segment.start_time < last_segment_end:
            raise ValidationError("Duty segments may not overlap")
        last_segment_end = segment.end_time

    if minutes_cursor > MINUTES_PER_DAY:
        raise ValidationError("Daily duty segments exceed 24 hours")

    log_date = log_date or timezone.now().date()

    driver_log, _ = DriverLog.objects.get_or_create(
        trip=trip,
        day_number=day_number,
        defaults={"log_date": log_date},
    )

    driver_log.log_date = log_date
    driver_log.notes = notes or ""
    driver_log.total_off_duty_minutes = totals[DriverLog.STATUS_OFF_DUTY]
    driver_log.total_sleeper_minutes = totals[DriverLog.STATUS_SLEEPER]
    driver_log.total_driving_minutes = totals[DriverLog.STATUS_DRIVING]
    driver_log.total_on_duty_minutes = totals[DriverLog.STATUS_ON_DUTY]
    if total_distance_miles is not None:
        driver_log.total_distance_miles = float(total_distance_miles)
    driver_log.save()

    driver_log.segments.all().delete()

    duty_segments = [
        DutyStatusSegment(
            log=driver_log,
            status=segment.status,
            start_time=segment.start_time,
            end_time=segment.end_time,
            location=segment.location,
            activity=segment.activity,
            remarks=segment.remarks,
        )
        for segment in parsed_segments
    ]
    DutyStatusSegment.objects.bulk_create(duty_segments)

    return driver_log


@transaction.atomic
def delete_driver_log(*, user, log_id: str) -> bool:
    """Delete a driver log belonging to the authenticated user.

    Args:
        user: Authenticated user requesting deletion.
        log_id: Primary key of the log to remove.

    Returns:
        bool: True when the log existed and was deleted, False if not found.

    Raises:
        PermissionDenied: If the log exists but belongs to a different user.
    """
    try:
        log = DriverLog.objects.select_related("trip").get(id=log_id)
    except DriverLog.DoesNotExist:
        return False

    if log.trip.user != user:
        raise PermissionDenied("Not allowed to modify this log")

    log.delete()
    return True
