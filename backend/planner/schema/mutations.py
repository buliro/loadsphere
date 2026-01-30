from collections.abc import Mapping
from datetime import datetime

import graphene
from graphql_jwt.decorators import login_required

from ..models import Trip, BackgroundJob
from ..services.trip_planner import (
    plan_trip_for_user,
    enqueue_trip_job,
    TripPlanningError,
)
from ..services.logs import upsert_driver_log, delete_driver_log
from ..models import DriverLog
from .types import LocationInput, DriverLogType


class DutySegmentInput(graphene.InputObjectType):
    """GraphQL input object describing an hours-of-service duty segment."""
    status = graphene.String(required=True)
    start_time = graphene.String(required=True)
    end_time = graphene.String(required=True)
    location = graphene.String()
    activity = graphene.String()
    remarks = graphene.String()


def _serialise_segments(segments: list[dict]) -> list[dict]:
    """Normalise incoming duty segment payloads for the logs service.

    Args:
        segments: List of dictionaries from GraphQL input containing segment data.

    Returns:
        list[dict]: Sanitised segment payloads keyed with backend expectations.
    """
    serialised: list[dict] = []

    for segment in segments:
        serialised.append(
            {
                "status": segment.get("status"),
                "startTime": segment.get("start_time") or segment.get("startTime"),
                "endTime": segment.get("end_time") or segment.get("endTime"),
                "location": segment.get("location"),
                "activity": segment.get("activity"),
                "remarks": segment.get("remarks"),
            }
        )

    return serialised


class DriverLogBaseMutation(graphene.Mutation):
    """Base mutation carrying shared driver log success/error fields."""
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)
    log = graphene.Field(DriverLogType)

    class Meta:
        abstract = True

    @staticmethod
    def _parse_log_date(log_date: str | None):
        """Convert a YYYY-MM-DD string into a date object.

        Args:
            log_date: Optional date string supplied by the client.

        Returns:
            date | None: Parsed date object or None when input is empty.

        Raises:
            ValidationError: If the date string does not match the expected format.
        """
        if not log_date:
            return None
        try:
            return datetime.strptime(log_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError("logDate must be in YYYY-MM-DD format") from exc


class CreateDriverLog(DriverLogBaseMutation):
    """Mutation for creating a driver log and associated duty segments."""
    class Arguments:
        trip_id = graphene.ID(required=True)
        day_number = graphene.Int(required=True)
        log_date = graphene.String()
        notes = graphene.String()
        total_distance_miles = graphene.Float()
        segments = graphene.List(DutySegmentInput, required=True)

    @login_required
    def mutate(
        self,
        info,
        trip_id,
        day_number,
        segments,
        log_date=None,
        notes=None,
        total_distance_miles=None,
    ):
        """Persist a new driver log for the authenticated user's trip.

        Args:
            info: GraphQL execution info containing context/user.
            trip_id: Trip identifier the log belongs to.
            day_number: Sequential day number for the log.
            segments: Duty segment inputs describing the day's activities.
            log_date: Optional log date string.
            notes: Optional text notes to attach to the log.
            total_distance_miles: Optional distance driven on the day.

        Returns:
            CreateDriverLog: Mutation payload with success flag, errors, and resulting log.
        """
        user = info.context.user

        segment_payloads = _serialise_segments(segments or [])

        try:
            log = upsert_driver_log(
                user=user,
                trip_id=trip_id,
                day_number=day_number,
                log_date=DriverLogBaseMutation._parse_log_date(log_date),
                notes=notes or "",
                total_distance_miles=total_distance_miles,
                segments=segment_payloads,
            )
        except (ValidationError, PermissionDenied) as exc:
            return CreateDriverLog(success=False, errors=[str(exc)], log=None)

        return CreateDriverLog(success=True, errors=[], log=log)


class UpdateDriverLog(DriverLogBaseMutation):
    """Mutation for updating an existing driver log and its segments."""
    class Arguments:
        log_id = graphene.ID(required=True)
        log_date = graphene.String()
        notes = graphene.String()
        total_distance_miles = graphene.Float()
        segments = graphene.List(DutySegmentInput, required=True)

    @login_required
    def mutate(
        self,
        info,
        log_id,
        segments,
        log_date=None,
        notes=None,
        total_distance_miles=None,
    ):
        """Update an existing driver log owned by the authenticated user.

        Args:
            info: GraphQL execution info containing context/user.
            log_id: Identifier of the log to update.
            segments: Replacement duty segments for the log.
            log_date: Optional new log date string.
            notes: Optional replacement log notes.
            total_distance_miles: Optional new mileage value.

        Returns:
            UpdateDriverLog: Mutation payload reflecting success, errors, and log data.
        """
        user = info.context.user

        try:
            existing = DriverLog.objects.select_related("trip").get(id=log_id)
        except DriverLog.DoesNotExist:
            return UpdateDriverLog(success=False, errors=["Driver log not found"], log=None)

        if existing.trip.user != user:
            return UpdateDriverLog(success=False, errors=["Not permitted"], log=None)

        segment_payloads = _serialise_segments(segments or [])

        try:
            log = upsert_driver_log(
                user=user,
                trip_id=str(existing.trip_id),
                day_number=existing.day_number,
                log_date=DriverLogBaseMutation._parse_log_date(log_date) or existing.log_date,
                notes=notes if notes is not None else existing.notes,
                total_distance_miles=total_distance_miles if total_distance_miles is not None else existing.total_distance_miles,
                segments=segment_payloads,
            )
        except (ValidationError, PermissionDenied) as exc:
            return UpdateDriverLog(success=False, errors=[str(exc)], log=None)

        return UpdateDriverLog(success=True, errors=[], log=log)


class DeleteDriverLog(graphene.Mutation):
    """Mutation removing a driver log if the user has permission."""
    class Arguments:
        log_id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, log_id):
        """Delete a driver log for the authenticated user.

        Args:
            info: GraphQL execution info containing context/user.
            log_id: Identifier of the log to delete.

        Returns:
            DeleteDriverLog: Payload indicating success and any error messages.
        """
        user = info.context.user

        try:
            deleted = delete_driver_log(user=user, log_id=log_id)
        except PermissionDenied as exc:
            return DeleteDriverLog(success=False, errors=[str(exc)])

        if not deleted:
            return DeleteDriverLog(success=False, errors=["Driver log not found"])

        return DeleteDriverLog(success=True, errors=[])

class PlanTripInput(graphene.InputObjectType):
    """GraphQL input object describing trip planning parameters."""
    start_location = LocationInput(required=True)
    pickup_location = LocationInput(required=True)
    dropoff_location = LocationInput(required=True)
    cycle_hours_used = graphene.Float(required=True)
    tractor_number = graphene.String()
    trailer_numbers = graphene.List(graphene.String)
    carrier_names = graphene.List(graphene.String)
    main_office_address = graphene.String()
    home_terminal_address = graphene.String()
    co_driver_name = graphene.String()
    shipper_name = graphene.String()
    commodity = graphene.String()
    run_async = graphene.Boolean(default_value=False)

class PlanTrip(graphene.Mutation):
    """Mutation planning a trip synchronously or enqueuing a background job."""
    class Arguments:
        input = PlanTripInput(required=True)
    
    success = graphene.Boolean()
    trip = graphene.Field('planner.schema.types.TripType')
    job = graphene.Field('planner.schema.types.BackgroundJobType')
    errors = graphene.List(graphene.String)
    
    @staticmethod
    def _location_to_dict(location):
        """Convert GraphQL location input into a plain dict for storage.

        Args:
            location: GraphQL input object or mapping with location data.

        Returns:
            dict | None: Dictionary containing non-null location fields.
        """
        if location is None:
            return None
        if isinstance(location, Mapping):
            return {k: v for k, v in dict(location).items() if v is not None}

        result = {}
        for field in ('lat', 'lng', 'address'):
            value = getattr(location, field, None)
            if value is not None:
                result[field] = value
        return result

    @login_required
    def mutate(root, info, input):
        """Create a route plan immediately or enqueue a background job.

        Args:
            root: GraphQL root object (unused).
            info: GraphQL execution info containing context/user.
            input: PlanTripInput payload with trip details.

        Returns:
            PlanTrip: Mutation payload containing success state, trip/job, and errors.
        """
        user = info.context.user
        start_location = PlanTrip._location_to_dict(input.start_location)
        pickup_location = PlanTrip._location_to_dict(input.pickup_location)
        dropoff_location = PlanTrip._location_to_dict(input.dropoff_location)
        cycle_hours_used = float(input.cycle_hours_used)
        tractor_number = getattr(input, 'tractor_number', None)
        trailer_numbers = getattr(input, 'trailer_numbers', None)
        carrier_names = getattr(input, 'carrier_names', None)
        main_office_address = getattr(input, 'main_office_address', None)
        home_terminal_address = getattr(input, 'home_terminal_address', None)
        co_driver_name = getattr(input, 'co_driver_name', None)
        shipper_name = getattr(input, 'shipper_name', None)
        commodity = getattr(input, 'commodity', None)
        run_async = getattr(input, 'run_async', False)

        if run_async:
            job_kwargs = dict(
                user=user,
                start_location=start_location,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                cycle_hours_used=cycle_hours_used,
            )

            optional_kwargs = {
                "tractor_number": tractor_number,
                "trailer_numbers": trailer_numbers,
                "carrier_names": carrier_names,
                "main_office_address": main_office_address,
                "home_terminal_address": home_terminal_address,
                "co_driver_name": co_driver_name,
                "shipper_name": shipper_name,
                "commodity": commodity,
            }

            for key, value in optional_kwargs.items():
                if value:
                    job_kwargs[key] = value

            job = enqueue_trip_job(**job_kwargs)
            return PlanTrip(success=True, trip=None, job=job, errors=[])

        try:
            trip = plan_trip_for_user(
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
            return PlanTrip(success=True, trip=trip, job=None, errors=[])
        except TripPlanningError as exc:
            return PlanTrip(success=False, trip=None, job=None, errors=[exc.message])
        except Exception as exc:  # Fallback to ensure errors are surfaced cleanly
            return PlanTrip(success=False, trip=None, job=None, errors=[str(exc)])

class DeleteTrip(graphene.Mutation):
    """Mutation removing a planned trip from the authenticated user's account."""
    class Arguments:
        trip_id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, trip_id):
        """Delete a planned trip when allowed by business rules.

        Args:
            info: GraphQL execution info containing context/user.
            trip_id: Identifier of the trip to delete.

        Returns:
            DeleteTrip: Payload indicating success or errors.
        """
        user = info.context.user

        try:
            trip = Trip.objects.get(id=trip_id, user=user)
        except Trip.DoesNotExist:
            return DeleteTrip(success=False, errors=["Trip not found"])

        if trip.status != Trip.STATUS_PLANNED:
            return DeleteTrip(success=False, errors=["Only planned routes can be deleted."])

        trip.delete()

        return DeleteTrip(success=True, errors=[])

class UpdateTripStatus(graphene.Mutation):
    """Mutation updating the status of a user's trip with validation rules."""
    class Arguments:
        trip_id = graphene.ID(required=True)
        status = graphene.String(required=True)
    
    success = graphene.Boolean()
    trip = graphene.Field('planner.schema.types.TripType')
    errors = graphene.List(graphene.String)
    
    @login_required
    def mutate(self, info, trip_id, status):
        """Update trip status after validating transitions and ownership.

        Args:
            info: GraphQL execution info containing context/user.
            trip_id: Identifier of the trip to update.
            status: New status value requested by the client.

        Returns:
            UpdateTripStatus: Payload with success flag, trip data, and errors if any.
        """
        user = info.context.user

        try:
            trip = Trip.objects.get(id=trip_id, user=user)
        except Trip.DoesNotExist:
            return UpdateTripStatus(success=False, trip=None, errors=["Trip not found"])

        normalised_status = (status or "").strip().upper()
        valid_statuses = {
            Trip.STATUS_PLANNED,
            Trip.STATUS_IN_PROGRESS,
            Trip.STATUS_COMPLETED,
            Trip.STATUS_CANCELLED,
        }

        if normalised_status not in valid_statuses:
            return UpdateTripStatus(
                success=False,
                trip=None,
                errors=["Invalid status value"],
            )

        if normalised_status == Trip.STATUS_IN_PROGRESS:
            existing_active = Trip.objects.filter(
                user=user,
                status=Trip.STATUS_IN_PROGRESS,
            ).exclude(pk=trip.pk)

            if existing_active.exists():
                return UpdateTripStatus(
                    success=False,
                    trip=None,
                    errors=["Another trip is already in progress"],
                )

        if (
            trip.status == Trip.STATUS_IN_PROGRESS
            and normalised_status not in {Trip.STATUS_IN_PROGRESS, Trip.STATUS_COMPLETED}
        ):
            return UpdateTripStatus(
                success=False,
                trip=None,
                errors=["Routes already in progress can only be marked as completed."],
            )

        if trip.status != Trip.STATUS_PLANNED and normalised_status == Trip.STATUS_PLANNED:
            return UpdateTripStatus(
                success=False,
                trip=None,
                errors=["Only routes still in planning can be marked as planned."],
            )

        trip.status = normalised_status
        trip.save(update_fields=["status", "updated_at"])

        return UpdateTripStatus(success=True, trip=trip, errors=[])

class Mutation(graphene.ObjectType):
    """Root GraphQL mutation entry point for trip and driver log operations."""
    plan_trip = PlanTrip.Field()
    update_trip_status = UpdateTripStatus.Field()
    delete_trip = DeleteTrip.Field()
    create_driver_log = CreateDriverLog.Field()
    update_driver_log = UpdateDriverLog.Field()
    delete_driver_log = DeleteDriverLog.Field()
