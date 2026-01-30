# Collaboration Guide

This document captures the expectations for contributing to the ELD Route & Log Planner project. Adhering to these guidelines ensures consistency, high code quality, and efficient collaboration.

## Table of Contents
1. [Communication](#communication)
2. [Branching Strategy](#branching-strategy)
3. [Issue Management](#issue-management)
4. [Development Workflow](#development-workflow)
5. [Code Style & Quality](#code-style--quality)
6. [Testing Expectations](#testing-expectations)
7. [Pull Request Checklist](#pull-request-checklist)
8. [Release Process](#release-process)
9. [Onboarding New Contributors](#onboarding-new-contributors)

---

## Communication
- Use the team’s designated Slack channel (or agreed communication tool) for day-to-day coordination.
- Schedule standups or async check-ins at the start of each sprint.
- Document major decisions in `/docs` to keep the knowledge base current.

## Branching Strategy
- **Default branch:** `main` holds production-ready code.
- **Development branches:** prefix feature work with `feature/`, bug fixes with `fix/`, and chores with `chore/`.
- Keep branches focused; avoid bundling unrelated changes.

```
main
└── feature/<summary>
    └── fix/<ticket-id>
```

## Issue Management
- Track work in the issue tracker (GitHub Issues, Linear, Jira, etc.).
- Link commits and pull requests to their corresponding issues.
- Write clear acceptance criteria and definition of done for each issue.

## Development Workflow
1. Create a topic branch from `main`.
2. Implement changes with small, logical commits.
3. Run relevant tests and linters locally.
4. Open a draft PR early to share context.
5. Request review once feedback is addressed and checks pass.

## Code Style & Quality
- Follow existing code patterns; prefer incremental fixes over large rewrites.
- Backend: adhere to Django best practices, type hints where practical, and ensure docstrings include Args/Returns.
- Frontend: stick to TypeScript strictness, Redux Toolkit patterns, and accessible UI components.
- Keep documentation/update logs in `/docs` synchronized with code changes.

## Testing Expectations
- Backend: add or update Django tests around models, services, and GraphQL mutations affected by a change.
- Frontend: prefer Jest + React Testing Library for components, Redux slices, and hooks.
- Snapshot tests should be applied sparingly and only for stable UI.

## Pull Request Checklist
- [ ] Issue linked and description explains motivation.
- [ ] Tests added or updated; all test suites pass.
- [ ] Linting passes (ESLint, etc.).
- [ ] Documentation updated where relevant (README, docs/).
- [ ] Screenshots or GIFs attached for UI changes.
- [ ] Reviewers requested once checks pass.

## Release Process
- Merge only via pull requests after at least one approval.
- Tag releases following semantic versioning when a deployable build is ready.
- Rebuild the backend Docker image after merging backend changes to keep parity with production deployments.

## Onboarding New Contributors
- Share this document and the [README](README.md) as the starting point.
- Ensure newcomers have access to environment variables and API keys (stored securely via `.env` or secrets manager).
- Pair a newcomer with a project buddy for the first sprint to speed up knowledge transfer.
