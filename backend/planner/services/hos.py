from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


class HOSComputationError(Exception):
    """Raised when Hours-of-Service computation fails."""


@dataclass
class DailyHosSummary:
    day_number: int
    total_driving_minutes: int
    total_on_duty_minutes: int
    total_off_duty_minutes: int
    total_sleeper_minutes: int
    remaining_cycle_hours: float
    segments: List[Dict[str, Any]]

    def as_payload(self) -> Dict[str, Any]:
        return {
            "day_number": self.day_number,
            "total_driving_minutes": self.total_driving_minutes,
            "total_on_duty_minutes": self.total_on_duty_minutes,
            "total_off_duty_minutes": self.total_off_duty_minutes,
            "total_sleeper_minutes": self.total_sleeper_minutes,
            "remaining_cycle_hours": round(self.remaining_cycle_hours, 2),
            "segments": self.segments,
            "notes": [
                "Automatic HOS plan generated. Review before dispatch.",
                "Adjustments required for real-world constraints (traffic, loading).",
            ],
        }


# FMCSA property-carrying driver limits (Part 395)
DRIVING_LIMIT_PER_DAY = 11.0
ON_DUTY_LIMIT_PER_DAY = 14.0
CYCLE_LIMIT_HOURS = 70.0  # 8-day cycle
MANDATORY_OFF_DUTY_HOURS = 10.0
ON_DUTY_BUFFER_HOURS = 2.0  # Placeholder for loading, inspections, etc.


def generate_driver_logs(total_trip_hours: float, cycle_hours_used: float) -> List[Dict[str, Any]]:
    """Generate placeholder HOS-compliant daily logs for the trip.

    Args:
        total_trip_hours: Total estimated hours to complete the trip.
        cycle_hours_used: Hours already consumed in the driver's 70-hour/8-day cycle.

    Returns:
        List of dictionaries suitable for persisting in DriverLog.log_data.

    Raises:
        HOSComputationError: If there is insufficient cycle time remaining.
    """

    logger.info(
        "hos.generate.start",
        extra={
            "total_trip_hours": round(total_trip_hours, 2),
            "cycle_hours_used": round(cycle_hours_used, 2),
        },
    )

    if total_trip_hours < 0:
        logger.error("hos.invalid_trip_hours", extra={"total_trip_hours": total_trip_hours})
        raise HOSComputationError("Trip duration must be non-negative.")

    cycle_hours_remaining = max(CYCLE_LIMIT_HOURS - cycle_hours_used, 0.0)
    if cycle_hours_remaining <= 0:
        logger.warning("hos.cycle_exhausted", extra={"cycle_hours_used": cycle_hours_used})
        raise HOSComputationError("Driver has exhausted the 70-hour cycle. Trip cannot be scheduled.")

    hours_to_schedule = min(total_trip_hours, cycle_hours_remaining)
    if hours_to_schedule <= 0:
        logger.warning("hos.no_hours_to_schedule", extra={"hours_to_schedule": hours_to_schedule})
        raise HOSComputationError("No remaining hours available to schedule this trip.")

    summaries: List[DailyHosSummary] = []
    day_number = 1
    remaining_hours = hours_to_schedule
    remaining_cycle = cycle_hours_remaining

    while remaining_hours > 0 and remaining_cycle > 0:
        planned_driving = min(DRIVING_LIMIT_PER_DAY, remaining_hours, remaining_cycle)

        planned_on_duty = min(planned_driving + ON_DUTY_BUFFER_HOURS, ON_DUTY_LIMIT_PER_DAY, remaining_cycle)

        driving_minutes = int(round(planned_driving * 60))
        on_duty_minutes = int(round(planned_on_duty * 60))
        off_duty_minutes = int(round(MANDATORY_OFF_DUTY_HOURS * 60))
        sleeper_minutes = 0

        segments = [
            {
                "status": "ON_DUTY",
                "minutes": on_duty_minutes - driving_minutes,
                "remarks": "Pre/post-trip activities",
            },
            {
                "status": "DRIVING",
                "minutes": driving_minutes,
                "remarks": "Planned driving",
            },
            {
                "status": "OFF_DUTY",
                "minutes": off_duty_minutes,
                "remarks": "Rest",
            },
        ]

        remaining_hours -= planned_driving
        remaining_cycle -= planned_on_duty

        summaries.append(
            DailyHosSummary(
                day_number=day_number,
                total_driving_minutes=driving_minutes,
                total_on_duty_minutes=on_duty_minutes,
                total_off_duty_minutes=off_duty_minutes,
                total_sleeper_minutes=sleeper_minutes,
                remaining_cycle_hours=max(remaining_cycle, 0.0),
                segments=segments,
            )
        )

        day_number += 1

    payloads = [summary.as_payload() for summary in summaries]

    logger.info(
        "hos.generate.complete",
        extra={
            "days_generated": len(payloads),
            "remaining_cycle_hours": round(max(remaining_cycle, 0.0), 2),
        },
    )

    return payloads
