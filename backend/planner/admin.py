from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import Trip, Route, Stop, DriverLog, BackgroundJob

User = get_user_model()

class StopInline(admin.TabularInline):
    model = Stop
    extra = 0
    readonly_fields = ('created_at', 'updated_at')

class RouteInline(admin.StackedInline):
    model = Route
    extra = 0
    show_change_link = True
    readonly_fields = ('created_at',)
    inlines = [StopInline]

class DriverLogInline(admin.TabularInline):
    model = DriverLog
    extra = 0
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'start_location', 'pickup_location', 'dropoff_location')
    inlines = [RouteInline, DriverLogInline]

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'total_distance', 'estimated_duration')
    inlines = [StopInline]

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('id', 'route', 'stop_type', 'sequence', 'duration_minutes')
    list_filter = ('stop_type',)

@admin.register(DriverLog)
class DriverLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'day_number', 'created_at')
    list_filter = ('day_number',)


@admin.register(BackgroundJob)
class BackgroundJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'job_type', 'status', 'created_at', 'completed_at')
    list_filter = ('job_type', 'status', 'created_at')
    search_fields = ('id', 'user__username', 'job_type', 'status')
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'started_at',
        'completed_at',
        'payload',
        'result',
        'error_message',
    )

# Register the default User model if not already registered
if not admin.site.is_registered(User):
    admin.site.register(User, UserAdmin)
