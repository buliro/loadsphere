from __future__ import annotations

import uuid
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from graphene.test import Client

from planner.models import Trip, BackgroundJob
from planner.schema import schema
from planner.services import trip_planner

User = get_user_model()


class TripPlannerServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="planner",
            email="planner@example.com",
            password="password123",
            first_name="Route",
            last_name="Planner",
        )

    @mock.patch("planner.services.trip_planner.generate_driver_logs")
    @mock.patch("planner.services.trip_planner.plan_route")
    def test_plan_trip_for_user_persists_trip_and_logs(self, mock_plan_route, mock_generate_logs):
        start = {"lat": 34.05, "lng": -118.24, "address": "Los Angeles"}
        pickup = {"lat": 36.17, "lng": -115.14, "address": "Las Vegas"}
        dropoff = {"lat": 40.71, "lng": -74.0, "address": "New York"}

        mock_plan_route.return_value = {
            "polyline": "encoded",
            "total_distance_miles": 100.0,
            "total_duration_hours": 20.0,
            "segments": [
                {"distance_miles": 50.0, "duration_hours": 10.0},
                {"distance_miles": 50.0, "duration_hours": 10.0},
            ],
        }
        mock_generate_logs.return_value = []

        trip = trip_planner.plan_trip_for_user(
            user=self.user,
            start_location=start,
            pickup_location=pickup,
            dropoff_location=dropoff,
            cycle_hours_used=0.0,
        )

        self.assertAlmostEqual(trip.total_miles, 100.0)
        self.assertAlmostEqual(trip.total_hours, 20.0)
        self.assertEqual(trip.logs.count(), 0)
        self.assertEqual(trip.route.stops.count(), 3)
        self.assertEqual(trip.itinerary_summary["total_distance_miles"], 100.0)
        self.assertIn("hos_alerts", trip.itinerary_summary)
        alerts = trip.itinerary_summary["hos_alerts"]
        self.assertEqual(len(alerts), 0)

    def test_enqueue_trip_job_creates_background_job(self):
        job = trip_planner.enqueue_trip_job(
            user=self.user,
            start_location={"lat": 1.0, "lng": 1.0},
            pickup_location={"lat": 2.0, "lng": 2.0},
            dropoff_location={"lat": 3.0, "lng": 3.0},
            cycle_hours_used=10.0,
        )

        self.assertEqual(job.user, self.user)
        self.assertEqual(job.job_type, BackgroundJob.JOB_TYPE_PLAN_TRIP)
        self.assertEqual(job.status, BackgroundJob.STATUS_PENDING)
        self.assertEqual(job.payload["cycle_hours_used"], 10.0)

    @mock.patch("planner.services.trip_planner.plan_trip_for_user")
    def test_process_pending_trip_jobs_handles_success_and_failure(self, mock_plan_trip):
        success_trip = mock.Mock()
        success_trip.id = uuid.uuid4()
        mock_plan_trip.side_effect = [success_trip, trip_planner.TripPlanningError("boom")]

        success_job = BackgroundJob.objects.create(
            user=self.user,
            job_type=BackgroundJob.JOB_TYPE_PLAN_TRIP,
            payload={"cycle_hours_used": 0.0},
        )
        failure_job = BackgroundJob.objects.create(
            user=self.user,
            job_type=BackgroundJob.JOB_TYPE_PLAN_TRIP,
            payload={"cycle_hours_used": 0.0},
        )

        processed = trip_planner.process_pending_trip_jobs(limit=5)

        self.assertEqual(len(processed), 2)

        success_job.refresh_from_db()
        failure_job.refresh_from_db()

        self.assertEqual(success_job.status, BackgroundJob.STATUS_SUCCESS)
        self.assertEqual(success_job.result["trip_id"], str(success_trip.id))
        self.assertEqual(failure_job.status, BackgroundJob.STATUS_FAILED)
        self.assertEqual(failure_job.error_message, "boom")


class PlanTripMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="graphql-user",
            email="graphql@example.com",
            password="password123",
            first_name="GraphQL",
            last_name="Tester",
        )
        self.client = Client(schema)
        self.factory = RequestFactory()

    def _execute(self, mutation, variables):
        request = self.factory.post("/graphql")
        request.user = self.user
        return self.client.execute(
            mutation,
            variable_values=variables,
            context_value=request,
        )

    def test_plan_trip_run_async_returns_job(self):
        mutation = """
            mutation PlanTrip($input: PlanTripInput!) {
                planTrip(input: $input) {
                    success
                    errors
                    job {
                        id
                        status
                        jobType
                        payload
                    }
                    trip {
                        id
                    }
                }
            }
        """

        variables = {
            "input": {
                "startLocation": {"lat": 1.0, "lng": 1.0},
                "pickupLocation": {"lat": 2.0, "lng": 2.0},
                "dropoffLocation": {"lat": 3.0, "lng": 3.0},
                "cycleHoursUsed": 5.0,
                "runAsync": True,
            }
        }

        result = self._execute(mutation, variables)
        if result.get("errors"):
            self.fail(f"Unexpected GraphQL errors: {result['errors']}")
        data = result["data"]["planTrip"]

        self.assertTrue(data["success"])
        self.assertIsNone(data["trip"])
        self.assertIsNotNone(data["job"]["id"])
        self.assertEqual(data["job"]["status"], BackgroundJob.STATUS_PENDING)
        self.assertEqual(data["job"]["jobType"], BackgroundJob.JOB_TYPE_PLAN_TRIP)

    @mock.patch("planner.schema.mutations.plan_trip_for_user")
    def test_plan_trip_sync_returns_trip(self, mock_plan_trip):
        trip = Trip.objects.create(
            user=self.user,
            start_location={"lat": 1.0, "lng": 1.0},
            pickup_location={"lat": 2.0, "lng": 2.0},
            dropoff_location={"lat": 3.0, "lng": 3.0},
            cycle_hours_used=0.0,
        )
        mock_plan_trip.return_value = trip

        mutation = """
            mutation PlanTrip($input: PlanTripInput!) {
                planTrip(input: $input) {
                    success
                    errors
                    job { id }
                    trip {
                        id
                        status
                    }
                }
            }
        """

        variables = {
            "input": {
                "startLocation": {"lat": 1.0, "lng": 1.0},
                "pickupLocation": {"lat": 2.0, "lng": 2.0},
                "dropoffLocation": {"lat": 3.0, "lng": 3.0},
                "cycleHoursUsed": 2.0,
            }
        }

        result = self._execute(mutation, variables)
        if result.get("errors"):
            self.fail(f"Unexpected GraphQL errors: {result['errors']}")
        data = result["data"]["planTrip"]

        self.assertTrue(data["success"])
        self.assertIsNone(data["job"])
        self.assertEqual(data["trip"]["id"], str(trip.id))
        mock_plan_trip.assert_called_once()
