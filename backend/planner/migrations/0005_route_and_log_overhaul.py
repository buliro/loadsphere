from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0004_backgroundjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="tractor_number",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="trip",
            name="trailer_numbers",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="trip",
            name="carrier_names",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="trip",
            name="main_office_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="trip",
            name="home_terminal_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="trip",
            name="co_driver_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="trip",
            name="shipper_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="trip",
            name="commodity",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddConstraint(
            model_name="trip",
            constraint=models.UniqueConstraint(
                fields=("user",),
                condition=Q(status="IN_PROGRESS"),
                name="unique_active_trip_per_user",
            ),
        ),
        migrations.AlterField(
            model_name="driverlog",
            name="day_number",
            field=models.PositiveIntegerField(),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="log_date",
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="driverlog",
            name="total_off_duty_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="total_sleeper_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="total_driving_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="total_on_duty_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="total_distance_miles",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="driverlog",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterUniqueTogether(
            name="driverlog",
            unique_together={("trip", "day_number")},
        ),
        migrations.RemoveField(
            model_name="driverlog",
            name="log_data",
        ),
        migrations.CreateModel(
            name="DutyStatusSegment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "log",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="segments",
                        to="planner.driverlog",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OFF_DUTY", "OFF DUTY"),
                            ("SLEEPER_BERTH", "SLEEPER BERTH"),
                            ("DRIVING", "DRIVING"),
                            ("ON_DUTY", "ON DUTY (NOT DRIVING)"),
                        ],
                        max_length=16,
                    ),
                ),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("location", models.CharField(blank=True, max_length=255)),
                ("activity", models.CharField(blank=True, max_length=255)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["start_time"],
            },
        ),
    ]
