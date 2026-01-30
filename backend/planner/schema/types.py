import graphene
from graphene_django import DjangoObjectType
from ..models import Trip, Route, Stop, DriverLog, DutyStatusSegment, BackgroundJob

class LocationInput(graphene.InputObjectType):
    """GraphQL input object capturing latitude, longitude, and address details."""
    lat = graphene.Float()
    lng = graphene.Float()
    address = graphene.String()


class StopType(DjangoObjectType):
    """Expose planner Stop instances to the GraphQL API."""

    class Meta:
        model = Stop
        fields = (
            'id',
            'stop_type',
            'location',
            'duration_minutes',
            'sequence',
            'distance_from_previous',
            'duration_from_previous',
        )


class RouteType(DjangoObjectType):
    """GraphQL type describing a planned Route and its ordered stops."""
    stops = graphene.List(StopType)
    
    class Meta:
        model = Route
        fields = ('id', 'polyline', 'total_distance', 'estimated_duration', 'stops')
    
    def resolve_stops(self, info):
        """Return the route stops ordered by sequence."""
        return self.stops.all().order_by('sequence')


class DutyStatusSegmentType(DjangoObjectType):
    """Expose duty status segment data recorded for a driver log."""

    class Meta:
        model = DutyStatusSegment
        fields = (
            'id',
            'status',
            'start_time',
            'end_time',
            'location',
            'activity',
            'remarks',
            'created_at',
            'updated_at',
        )


class DriverLogType(DjangoObjectType):
    """GraphQL type representing a DriverLog with its duty segments."""
    segments = graphene.List(DutyStatusSegmentType)

    class Meta:
        model = DriverLog
        fields = (
            'id',
            'day_number',
            'log_date',
            'total_off_duty_minutes',
            'total_sleeper_minutes',
            'total_driving_minutes',
            'total_on_duty_minutes',
            'total_distance_miles',
            'notes',
            'created_at',
            'updated_at',
            'segments',
        )

    def resolve_segments(self, info):
        """Return duty segments sorted by their start time."""
        return self.segments.all().order_by('start_time')


class BackgroundJobType(DjangoObjectType):
    """Expose background job metadata for monitoring asynchronous planning."""

    class Meta:
        model = BackgroundJob
        fields = (
            'id',
            'job_type',
            'status',
            'payload',
            'result',
            'error_message',
            'created_at',
            'updated_at',
            'started_at',
            'completed_at',
        )


class TripType(DjangoObjectType):
    """GraphQL type describing a Trip and its related resources."""
    route = graphene.Field(RouteType)
    logs = graphene.List(DriverLogType)
    
    class Meta:
        model = Trip
        fields = (
            'id',
            'start_location',
            'pickup_location',
            'dropoff_location',
            'tractor_number',
            'trailer_numbers',
            'carrier_names',
            'main_office_address',
            'home_terminal_address',
            'co_driver_name',
            'shipper_name',
            'commodity',
            'status',
            'cycle_hours_used',
            'total_miles',
            'total_hours',
            'itinerary_summary',
            'created_at',
            'updated_at',
            'route',
            'logs',
        )
    
    def resolve_route(self, info):
        """Return the associated route if it has been planned."""
        return getattr(self, 'route', None)
    
    def resolve_logs(self, info):
        """Return driver logs in chronological order."""
        return self.logs.all().order_by('day_number')
