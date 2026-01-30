# Logistics and Shipment Management

> Full-stack trip optimization and log automation platform for fleets and owner-operators.

## Table of Contents
- [Overview](#overview)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Development Setup (Docker & Dev Containers)](#development-setup-docker--dev-containers)
- [Container Management & Common Tasks](#container-management--common-tasks)
- [Environment Configuration](#environment-configuration)
- [Running Tests & Quality Checks](#running-tests--quality-checks)
- [Background Jobs](#background-jobs)
- [Contributing](#contributing)
- [License](#license)

## Overview
The app helps dispatchers and drivers plan trips by combining optimized routing with automated Hours of Service (HOS) log generation. The backend exposes a GraphQL API that orchestrates route planning, HOS calculations, and structured logging. The React frontend provides an authenticated experience for submitting trip details, monitoring plan progress, and reviewing generated itineraries.

## Core Features
- Integrated OpenRouteService routing with stop classification (start, rest, fuel, pickup, dropoff).
- GraphQL mutation (`planTrip`) producing itineraries, stops, and generated daily logs.
- Background job processing for long-running trip calculations.
- React dashboard with planner form, map visualization, and log summaries.
- Custom authentication (session-based REST endpoints) wired into the frontend state layer.

## Tech Stack
| Layer | Technology |
| --- | --- |
| Backend | Django 4, Graphene-Django, MySQL, python-dotenv |
| Frontend | React 19, Redux Toolkit, Vite, TypeScript, SASS |
| Mapping & Routing | OpenRouteService (REST API) |
| Testing | Django TestCase suite, Jest + React Testing Library (planned), ESLint |
| Tooling | Docker dev container workflow, Background job queue (DB-backed) |

## Repository Layout
```
.
├── backend/              # Django project (GraphQL API, jobs, auth, services)
├── React/                # React + Vite SPA client
└── README.md             # You are here
```

## Prerequisites
- Docker Engine / Docker Desktop with Compose v2
- OpenRouteService API key (free tier works for development)
- VS Code + Dev Containers extension (recommended) or `docker compose` CLI
- Copy of the project `.env` populated with credentials (see [Environment Configuration](#environment-configuration))

## Development Setup (Docker & Dev Containers)
The project is designed to run entirely inside the `.devcontainer` images. Local Python/Node installations are not required for the default workflow.

### Option A: VS Code Dev Container (recommended)
1. Install the **Dev Containers** extension in VS Code.
2. Open the repository in VS Code and run **Dev Containers: Reopen in Container**.
3. VS Code will build the image defined in `.devcontainer/Dockerfile`, start the services from `.devcontainer/docker-compose.yml`, and attach your editor to the running `app` container.
4. Once the container is ready, migrations, static collection, and the Django server are started automatically via the compose command (`gunicorn` on port 8000).

### Option B: CLI-only Docker Compose
1. Ensure the `.env` file is present at the repository root with required credentials.
2. Build and start the stack:
   ```bash
   docker compose -f .devcontainer/docker-compose.yml up --build
   ```
3. The backend is served from `http://localhost:8000`; the MySQL instance is available on `localhost:3306`.

> **Note:** Keep `DEBUG=True` in development so CSRF cookies use `SameSite=Lax`, enabling frontend requests over HTTP.

React assets are baked into the `app` image during build. After frontend updates, rebuild the image to pick up changes:

```bash
docker compose -f .devcontainer/docker-compose.yml build app
docker compose -f .devcontainer/docker-compose.yml up -d app
```

## Container Management & Common Tasks
- View service status:
  ```bash
  docker compose -f .devcontainer/docker-compose.yml ps
  ```
- Run Django management commands:
  ```bash
  docker compose -f .devcontainer/docker-compose.yml exec app python manage.py <command>
  ```
- Access the Django shell:
  ```bash
  docker compose -f .devcontainer/docker-compose.yml exec app python manage.py shell
  ```
- Tail application logs:
  ```bash
  docker compose -f .devcontainer/docker-compose.yml logs -f app
  ```

## Environment Configuration
Backend configuration is documented in [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md). Key values:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django cryptographic secret |
| `DEBUG` | Enables development mode |
| `DB_*` | MySQL credentials and host settings |
| `OPENROUTESERVICE_API_KEY` | External routing API key |

Populate a `.env` file in `backend/` or at the repo root. The backend automatically loads environment variables via `python-dotenv`.

## Running Tests & Quality Checks
All quality commands should be executed inside the Docker environment to ensure parity.

### Backend (Django)
- Run unit tests:
  ```bash
  docker compose -f .devcontainer/docker-compose.yml exec app python manage.py test
  ```
- Optional linting/static checks (add `flake8`, `ruff`, etc. to the image before use):
  ```bash
  docker compose -f .devcontainer/docker-compose.yml exec app flake8
  ```

### Frontend (React)
- ESLint (runs inside a transient Node container):
  ```bash
  docker run --rm \
    -v "$(pwd)/React":/workspace/React \
    -w /workspace/React node:20-alpine \
    sh -c "npm install --frozen-lockfile || npm install && npm run lint"
  ```
- Jest/RTL suites can follow the same pattern once `npm run test` is added to `package.json`.

## Background Jobs
Trip planning can run asynchronously through the DB-backed job queue. Enqueue jobs with the GraphQL `planTrip` mutation (`runAsync: true`), then process them using the management command:

```bash
docker compose run --rm backend python manage.py process_trip_jobs --limit 5
```

If Docker is unavailable, execute the management command directly from an activated backend environment.

## Contributing
See [COLLABORATION.md](docs/COLLABORATION.md) for branching, review process, and coding standards.

## License
Distributed under the terms of the project [license](docs/LICENSE). Update license details before distribution.