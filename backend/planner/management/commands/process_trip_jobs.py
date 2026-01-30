from django.core.management.base import BaseCommand

from ...services.trip_planner import process_pending_trip_jobs


class Command(BaseCommand):
    """Django management command for processing queued trip planning jobs."""
    help = "Process pending trip planning jobs synchronously using the database queue."

    def add_arguments(self, parser):
        """Register CLI arguments for limiting the number of jobs processed.

        Args:
            parser: ArgumentParser-like object used by Django's management framework.

        Returns:
            None
        """
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of pending jobs to process in this run (default: 10).",
        )

    def handle(self, *args, **options):
        """Execute the command, processing pending trip jobs up to the provided limit.

        Args:
            *args: Positional arguments passed by Django (unused).
            **options: Parsed command-line options containing `limit`.

        Returns:
            None
        """
        limit = options["limit"]
        processed_jobs = process_pending_trip_jobs(limit=limit)
        count = len(processed_jobs)
        if count == 0:
            self.stdout.write(self.style.WARNING("No pending trip jobs found."))
            return

        for job in processed_jobs:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed job {job.id} with status {job.status}."
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Completed processing {count} job(s)."))
