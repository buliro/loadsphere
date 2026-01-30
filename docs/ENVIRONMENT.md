# Backend Environment & API Configuration

This project relies on environment variables to configure the Django backend, database connectivity, and third-party REST integrations. The recommended approach is to place all secrets and overrides in a `.env` file (loaded by `python-dotenv`) that Docker Compose or local tooling will pick up automatically.

## Required Environment Variables

| Variable | Description | Default (if unset) |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key used for cryptographic signing. Generate a unique value for production. | `django-insecure-very-secret-key-change-in-production` |
| `DEBUG` | Enables Django debug mode. Use `False` in non-development environments. | `True` |
| `DB_NAME` | MySQL database name. Used by the backend container. | `route_planner` |
| `DB_USER` | Database user for the application. | `user` |
| `DB_PASSWORD` | Password for `DB_USER`. | `password` |
| `DB_HOST` | Hostname/IP of the MySQL instance. In Docker, this should remain `db`. | `db` |
| `DB_PORT` | MySQL port. | `3306` |
| `DB_TEST_NAME` | Optional MySQL database name used by Django tests. | `route_planner_test` |
| `OPENROUTESERVICE_API_KEY` | **Required.** API key issued by OpenRouteService for route planning. Stored securely in `.env`. | _(no default)_ |

### Optional Variables
- `DATABASE_URL`: If provided (e.g., via external orchestration), overrides the individual `DB_*` settings. Use the format `mysql://user:password@host:port/database`.
- `LOG_LEVEL`: Set to `INFO`, `DEBUG`, etc., to control Django’s logging verbosity once logging configuration is added.

## Example `.env`
```env
# Django
SECRET_KEY=replace-me
DEBUG=True

# Database (kept in sync with docker-compose.yml defaults)
DB_NAME=route_planner
DB_USER=user
DB_PASSWORD=password
DB_HOST=db
DB_PORT=3306

# Third-party REST integration
OPENROUTESERVICE_API_KEY=your-ors-api-key
```

## Third-Party REST API Usage
- **Provider:** [OpenRouteService](https://openrouteservice.org/) (REST API)
- **Endpoint:** `https://api.openrouteservice.org/v2/directions/driving-hgv`
- **Authentication:** API key supplied through the `Authorization` header (managed internally by the backend service).
- **Data Flow:**
  1. `planner.services.openroute.plan_route` constructs the REST request using trip waypoints.
  2. Response segments are persisted into `Stop` records and an itinerary summary on the `Trip`.
  3. Structured logging captures request/response metadata for observability and debugging.

## Background Processing (Database Queue)
- Trip planning jobs can be enqueued by setting the GraphQL `planTrip` mutation `runAsync` flag to `true`.
- Jobs are stored in the `planner_backgroundjob` table—no external queues or brokers required.
- To service queued work, run the management command (via Docker or locally):

  ```bash
  docker compose run --rm backend python manage.py process_trip_jobs --limit 5
  ```

- The command processes pending jobs synchronously and updates job status (`PENDING → RUNNING → SUCCESS/FAILED`).

Ensure the `OPENROUTESERVICE_API_KEY` has sufficient quota for the expected workload. Avoid committing real keys to version control—use `.env` and deployment-specific secret management instead.
