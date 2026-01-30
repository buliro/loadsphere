import uuid

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        first_name = extra_fields.get('first_name', '')
        last_name = extra_fields.get('last_name', '')

        if not first_name or not first_name.strip():
            raise ValueError(_('First name is required.'))
        if not last_name or not last_name.strip():
            raise ValueError(_('Last name is required.'))

        extra_fields.setdefault('username', email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom user model that supports using email instead of username"""
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(_('phone number'), max_length=20, blank=True)
    company = models.CharField(_('company'), max_length=100, blank=True)
    
    # Add any additional fields you want here
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = UserManager()
    
    def __str__(self):
        return self.email

    class Meta:
        app_label = 'planner'

TRIP_STATUS_PLANNED = 'PLANNED'
TRIP_STATUS_IN_PROGRESS = 'IN_PROGRESS'
TRIP_STATUS_COMPLETED = 'COMPLETED'
TRIP_STATUS_CANCELLED = 'CANCELLED'


class Trip(models.Model):
    STATUS_PLANNED = TRIP_STATUS_PLANNED
    STATUS_IN_PROGRESS = TRIP_STATUS_IN_PROGRESS
    STATUS_COMPLETED = TRIP_STATUS_COMPLETED
    STATUS_CANCELLED = TRIP_STATUS_CANCELLED

    STATUS_CHOICES = [
        (TRIP_STATUS_PLANNED, 'Planned'),
        (TRIP_STATUS_IN_PROGRESS, 'In Progress'),
        (TRIP_STATUS_COMPLETED, 'Completed'),
        (TRIP_STATUS_CANCELLED, 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    start_location = models.JSONField()  # {lat: float, lng: float, address: str}
    pickup_location = models.JSONField()  # {lat: float, lng: float, address: str}
    dropoff_location = models.JSONField()  # {lat: float, lng: float, address: str}
    tractor_number = models.CharField(max_length=64, blank=True)
    trailer_numbers = models.JSONField(default=list, blank=True)
    carrier_names = models.JSONField(default=list, blank=True)
    main_office_address = models.CharField(max_length=255, blank=True)
    home_terminal_address = models.CharField(max_length=255, blank=True)
    co_driver_name = models.CharField(max_length=128, blank=True)
    shipper_name = models.CharField(max_length=128, blank=True)
    commodity = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TRIP_STATUS_PLANNED)
    cycle_hours_used = models.FloatField(default=0.0)
    total_miles = models.FloatField(default=0.0)
    total_hours = models.FloatField(default=0.0)
    itinerary_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(status=TRIP_STATUS_IN_PROGRESS),
                name='unique_active_trip_per_user',
            )
        ]

class Route(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='route')
    polyline = models.TextField()  # Encoded polyline string
    total_distance = models.FloatField()  # in miles
    estimated_duration = models.FloatField()  # in hours
    created_at = models.DateTimeField(auto_now_add=True)

class Stop(models.Model):
    STOP_TYPES = [
        ('START', 'Start'),
        ('PICKUP', 'Pickup'),
        ('DROPOFF', 'Dropoff'),
        ('REST', 'Rest Stop'),
        ('FUEL', 'Fuel Stop'),
    ]
    
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    stop_type = models.CharField(max_length=10, choices=STOP_TYPES)
    location = models.JSONField()  # {lat: float, lng: float, address: str}
    duration_minutes = models.IntegerField(default=0)  # Duration of stop in minutes
    sequence = models.IntegerField()  # Order of stops in the route
    distance_from_previous = models.FloatField(default=0.0)  # miles between previous stop and this one
    duration_from_previous = models.FloatField(default=0.0)  # hours between previous stop and this one
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sequence']

class DriverLog(models.Model):
    STATUS_OFF_DUTY = 'OFF_DUTY'
    STATUS_SLEEPER = 'SLEEPER_BERTH'
    STATUS_DRIVING = 'DRIVING'
    STATUS_ON_DUTY = 'ON_DUTY'

    STATUS_CHOICES = [
        (STATUS_OFF_DUTY, 'OFF DUTY'),
        (STATUS_SLEEPER, 'SLEEPER BERTH'),
        (STATUS_DRIVING, 'DRIVING'),
        (STATUS_ON_DUTY, 'ON DUTY (NOT DRIVING)'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='logs')
    day_number = models.PositiveIntegerField()
    log_date = models.DateField()
    total_off_duty_minutes = models.PositiveIntegerField(default=0)
    total_sleeper_minutes = models.PositiveIntegerField(default=0)
    total_driving_minutes = models.PositiveIntegerField(default=0)
    total_on_duty_minutes = models.PositiveIntegerField(default=0)
    total_distance_miles = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['trip', 'day_number']
        unique_together = ('trip', 'day_number')


class DutyStatusSegment(models.Model):
    log = models.ForeignKey(DriverLog, on_delete=models.CASCADE, related_name='segments')
    status = models.CharField(max_length=16, choices=DriverLog.STATUS_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255, blank=True)
    activity = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']


class BackgroundJob(models.Model):
    JOB_TYPE_PLAN_TRIP = 'PLAN_TRIP'

    STATUS_PENDING = 'PENDING'
    STATUS_RUNNING = 'RUNNING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    JOB_TYPE_CHOICES = [
        (JOB_TYPE_PLAN_TRIP, 'Plan Trip'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    job_type = models.CharField(max_length=64, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def mark_running(self):
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_success(self, result: dict):
        self.status = self.STATUS_SUCCESS
        self.result = result
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'result', 'completed_at', 'updated_at'])

    def mark_failed(self, error_message: str):
        self.status = self.STATUS_FAILED
        self.error_message = error_message[:2048]
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
