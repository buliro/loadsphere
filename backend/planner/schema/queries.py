import graphene

from django.core.exceptions import PermissionDenied

from ..models import Trip, BackgroundJob, DriverLog
from .types import TripType, BackgroundJobType, DriverLogType

class Query(graphene.ObjectType):
    """GraphQL root query for accessing trips, driver logs, and jobs."""
    trip = graphene.Field(TripType, id=graphene.ID(required=True))
    my_trips = graphene.List(TripType, status=graphene.String())
    driver_log = graphene.Field(DriverLogType, id=graphene.ID(required=True))
    my_driver_logs = graphene.List(DriverLogType, trip_id=graphene.ID(required=True))
    job = graphene.Field(BackgroundJobType, id=graphene.ID(required=True))
    my_jobs = graphene.List(BackgroundJobType, job_type=graphene.String())
    
    def resolve_trip(self, info, id):
        """Fetch a single trip owned by the authenticated user.

        Args:
            info: GraphQL execution info containing context/user.
            id: Trip identifier to retrieve.

        Returns:
            Trip | None: Trip instance when found, otherwise None.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        try:
            return Trip.objects.get(id=id, user=user)
        except Trip.DoesNotExist:
            return None
    
    def resolve_my_trips(self, info, status=None):
        """Return trips for the authenticated user filtered by status.

        Args:
            info: GraphQL execution info containing context/user.
            status: Optional status string to filter results.

        Returns:
            QuerySet[Trip]: Ordered queryset of trips.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        queryset = Trip.objects.filter(user=user)
        if status:
            queryset = queryset.filter(status=status.upper())
        return queryset.order_by('-created_at')

    def resolve_driver_log(self, info, id):
        """Fetch a driver log ensuring the requesting user owns the parent trip.

        Args:
            info: GraphQL execution info containing context/user.
            id: Driver log identifier to retrieve.

        Returns:
            DriverLog | None: Log instance when accessible, otherwise None.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")

        try:
            log = DriverLog.objects.select_related('trip').get(id=id)
        except DriverLog.DoesNotExist:
            return None

        if log.trip.user_id != user.id:
            raise PermissionDenied("Driver log not found")

        return log

    def resolve_my_driver_logs(self, info, trip_id):
        """List driver logs for a trip owned by the authenticated user.

        Args:
            info: GraphQL execution info containing context/user.
            trip_id: Trip identifier whose logs should be returned.

        Returns:
            QuerySet[DriverLog]: Logs ordered by day number.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")

        try:
            trip = Trip.objects.get(id=trip_id, user=user)
        except Trip.DoesNotExist:
            raise PermissionDenied("Trip not found")

        return (
            DriverLog.objects.filter(trip=trip)
            .prefetch_related('segments')
            .order_by('day_number')
        )

    def resolve_job(self, info, id):
        """Fetch a background job belonging to the authenticated user.

        Args:
            info: GraphQL execution info containing context/user.
            id: Background job identifier to retrieve.

        Returns:
            BackgroundJob | None: Job instance or None if not found.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        try:
            return BackgroundJob.objects.get(id=id, user=user)
        except BackgroundJob.DoesNotExist:
            return None

    def resolve_my_jobs(self, info, job_type=None):
        """List background jobs for the authenticated user with optional filtering.

        Args:
            info: GraphQL execution info containing context/user.
            job_type: Optional job type string to filter results.

        Returns:
            QuerySet[BackgroundJob]: Jobs ordered by creation time.
        """
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")

        queryset = BackgroundJob.objects.filter(user=user)
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        return queryset.order_by('-created_at')
