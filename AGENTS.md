# AGENTS.md

# Conflux - Flask Application Agent Instructions

## Purpose

This document defines repository-specific guidance for AI coding agents and automated tooling working within the Conflux codebase.

Agents should prioritize:

1. Correctness
2. Consistency with existing patterns
3. Minimal, targeted changes
4. Backwards compatibility
5. Test coverage
6. Maintainability

When uncertain, prefer conservative implementations that preserve existing architecture and behavior.

---

## Project Overview

Conflux is an organisational knowledge platform that models ownership, responsibilities, and dependencies across digital organisations.

Core domain concepts:

- **People** - individuals assigned to teams and roles
- **Teams** - groups responsible for services
- **Roles** - responsibilities individuals perform
- **Services** - digital systems owned by teams
- **Components** - reusable or standalone technical building blocks

The platform focuses on:

- Ownership mapping
- Dependency analysis
- Team composition visibility
- Role-based organisational insights
- Change impact assessment

Conflux is implemented as a Flask-based web application using:

- Flask blueprints organized by domain
- SQLAlchemy ORM
- WTForms for forms and validation
- Alembic for database migrations
- Pytest for testing
- Gunicorn as the WSGI server
- PostgreSQL for persistence
- Valkey for caching and ephemeral state
- Nginx as the reverse proxy and static asset server

The application follows the Flask application factory pattern and runs in a containerized Docker Compose environment.

---

## Source of Truth and Precedence

When repository artifacts disagree, prefer the following order of precedence:

1. Existing runtime behavior and tests
2. Database models and migrations
3. OpenAPI schema
4. AGENTS.md
5. README.md and supporting documentation

If introducing intentional behavioral changes:

- update tests
- update OpenAPI documentation
- update README or CONTRIBUTING documentation where applicable

Do not leave behavior, tests, and API documentation inconsistent.

---

## Development Environment

The primary development workflow uses Docker Compose.

### Local Development

Developers are expected to run the application using:

```shell
docker compose up --watch
```

Agents should:

- prefer container-compatible changes and commands
- avoid assumptions about globally installed host dependencies
- preserve compatibility with Docker Compose live-reload workflows
- avoid unnecessary rebuild or restart behavior

### Configuration

Configuration is environment-variable driven.

Key environment variables include:

- `DATABASE_URL`
- `VALKEY_URL`
- `SECRET_KEY`
- `DOMAIN`
- `GRADES`
- `LOCATIONS`

Do not hardcode configuration values.

### Enumerated Domain Configuration

`GRADES` and `LOCATIONS` define canonical domain values used throughout:

- application validation
- API schemas
- forms
- fixtures and seed data
- filtering behavior

Maintain consistency across all layers when modifying enumerated values.

### Security Configuration

`SECRET_KEY` is security-sensitive and is used for:

- session cookie signing
- CSRF token protection

Never expose, log, or hardcode secret values.

---

## Architecture

### Application Structure

- `app/{domain}/` contains domain-specific blueprints
- `services/` contains business logic and orchestration
- `models/` contains SQLAlchemy models
- `forms/` contains WTForms definitions and validation
- `templates/` contains server-rendered templates
- `tests/` contains pytest-based test suites
- `/web` contains frontend assets and Nginx configuration

### Architectural Principles

- Keep route handlers thin
- Place business logic in service modules
- Preserve existing blueprint boundaries
- Reuse existing utilities before creating new abstractions
- Keep API, frontend, and infrastructure concerns separated
- Prefer composition over duplication
- Match surrounding code style and patterns

### Request Flow

```text
Client -> Nginx -> Flask/Gunicorn -> PostgreSQL/Valkey
```

Respect infrastructure boundaries and separation of concerns when implementing features.

---

## Domain Model Expectations

Maintain consistency with the established domain model:

- People belong to teams
- People perform roles
- Teams own services
- Services depend on components
- Components may be shared across multiple services
- People may have manager relationships with other people

### Relationship Semantics

Current relationship behavior includes:

- `Role -> Person` uses `ON DELETE RESTRICT`
- `Team -> Person` uses `ON DELETE SET NULL`
- `Team -> Service` uses `ON DELETE SET NULL`
- `Person -> Manager` self-reference uses `ON DELETE SET NULL`
- `Service <-> Component` is many-to-many via `service_components`

Preserve existing delete semantics unless explicitly instructed otherwise.

### Archival Semantics

Primary entities use soft archival through:

- `archived_at`
- `updated_at`

Avoid replacing archival behavior with hard deletes unless explicitly required.

### UUID Expectations

All primary entities use PostgreSQL UUID identifiers.

Maintain UUID usage consistently across:

- models
- APIs
- serializers
- tests
- migrations

Avoid introducing integer identifiers or mixed identifier semantics.

### Timestamp Expectations

Timestamps are:

- timezone-aware
- UTC-based
- serialized as ISO-8601 strings with `Z` suffix

Preserve this behavior consistently.

### Ordering Expectations

Relationships commonly specify deterministic ordering using entity names.

Preserve ordering behavior where already defined.

### Serialization Patterns

Models implement explicit `to_dict()` serializers with optional inclusion flags.

Examples:

- `include_people`
- `include_team`
- `include_role`
- `include_components`

Agents should:

- preserve existing serialization patterns
- avoid recursive serialization
- avoid excessively deep nesting
- avoid introducing parallel serialization systems

Unless an existing endpoint already does more, prefer a single level of nested relationship expansion.

---

## API Expectations

The API is currently:

- versioned under `/api/v1/`
- primarily read-only
- JSON-based
- UUID-driven for resource identifiers

### Existing API Resources

Current API resources include:

- Roles
- People
- Teams

Service and component resources exist within the domain model and may be expanded in future APIs.

### API Design Constraints

Preserve:

- existing response structures
- field naming conventions
- filtering behavior
- sorting semantics
- status code behavior
- backwards compatibility where practical

### Filtering and Sorting

Collection endpoints use query-based filtering and sorting.

Preserve semantics for:

- `sort`
- `status`

Preserve existing enum values and defaults.

### Nested vs Detailed Resources

The API intentionally distinguishes between:

- lightweight nested representations
- detailed top-level representations

Avoid unnecessarily expanding nested resources.

### Schema Expectations

API conventions include:

- ISO-8601 timestamps
- explicit enum validation
- nullable fields where documented
- predictable relationship serialization
- consistent object structures

Avoid introducing inconsistent response formats.

### OpenAPI Maintenance

The OpenAPI specification is considered a maintained project artifact.

When modifying API behavior, update:

- endpoint definitions
- request or response schemas
- enum definitions
- examples where appropriate

Do not leave the OpenAPI specification outdated relative to implementation behavior.

---

## Infrastructure

Conflux depends on:

- PostgreSQL for persistence
- Valkey for caching and ephemeral state
- Nginx as the web reverse proxy
- Docker Compose networking for local orchestration

### Web Architecture

- Flask runs behind Nginx
- TLS termination occurs at the web container
- Static assets are served by Nginx

Avoid embedding web-server concerns directly into Flask routes.

### Health Checks

- Preserve `/health` endpoint behavior
- Maintain container healthcheck compatibility
- Avoid blocking startup operations

### Container Constraints

Containers operate with explicit memory limits.

Avoid:

- unnecessary in-memory caching
- loading excessive datasets into memory
- inefficient query patterns
- blocking operations in request handlers

---

## Preferred Implementation Patterns

### Flask

- Use the application factory pattern (`create_app()`)
- Use blueprints for domain separation
- Initialize Flask extensions through application initialization
- Prefer dependency injection where practical

### Database

- Use SQLAlchemy ORM instead of raw SQL where possible
- Prefer typed ORM mappings using `Mapped[...]`
- Prefer model relationships over manual joins
- Use timezone-aware timestamps
- Preserve indexes and uniqueness constraints unless intentionally changing them

### Migrations

- Keep migrations small and focused
- Prefer additive migrations
- Avoid destructive schema changes without explicit instruction
- Ensure migrations remain reversible where practical
- Do not modify historical migrations

Schema changes should generally include corresponding Alembic migrations unless explicitly instructed otherwise.

### Models

- Preserve relationship integrity
- Preserve delete semantics
- Preserve explicit serialization behavior
- Prefer extending existing models over introducing parallel structures

### Forms and Validation

- Use WTForms validation consistently
- Keep validation close to form definitions where practical
- Do not bypass validation layers

Maintain consistency between:

- form validation
- model validation
- API schema validation

### Views and Services

- View functions should coordinate requests and responses only
- Business rules belong in service modules
- Avoid embedding complex logic directly in routes or templates

### Frontend Separation

- Frontend assets and Nginx configuration reside in `/web`
- Avoid coupling Flask internals directly to frontend build logic

---

## Constraints

### Do Not

- introduce new dependencies without clear justification
- perform unrelated refactors
- rewrite working code unnecessarily
- bypass validation or permission checks
- edit generated files unless explicitly required
- change migration history
- introduce global mutable state
- duplicate existing utilities or helpers
- hardcode infrastructure configuration
- expose secrets or sensitive configuration
- introduce breaking API changes without explicit instruction
- introduce recursive serialization behavior

### Prefer

- minimal, localized changes
- existing project conventions
- explicit and readable implementations
- small, reviewable commits
- backwards-compatible behavior

---

## Error Handling and Logging

### Error Handling

- Prefer explicit error handling over silent failures
- Return meaningful HTTP status codes
- Preserve existing exception handling patterns
- Avoid leaking internal details in user-facing errors
- Preserve documented API error semantics where possible

### Logging

- Use structured, concise logging
- Avoid excessive debug logging
- Never log secrets, credentials, tokens, or sensitive user data

---

## Testing Expectations

When writing or modifying tests, follow the conventions and patterns detailed in the official Flask documentation:

- <https://flask.palletsprojects.com/en/stable/testing/>
- <https://flask.palletsprojects.com/en/stable/tutorial/tests/>

### Required Testing Practices

- Use pytest fixtures for setup and teardown
- Ensure proper test isolation
- Use `test_client` for functional HTTP tests
- Mock external dependencies with `monkeypatch`
- Parametrize tests where beneficial
- Prefer factories and fixtures over repetitive inline setup

### SQLite vs PostgreSQL Testing

SQLite may be used for fast unit and integration tests where appropriate.

However, behavior depending on PostgreSQL-specific semantics should be validated against PostgreSQL-compatible execution paths where practical, especially for:

- UUID behavior
- foreign key delete semantics
- relationship behavior
- timestamp handling
- uniqueness constraints

Do not assume SQLite behavior perfectly matches PostgreSQL behavior.

### API Testing Expectations

When modifying API behavior:

- validate response schemas
- validate filtering and sorting behavior
- validate status codes
- validate serialization structure
- validate nullable field handling
- validate enum validation behavior
- validate timestamp serialization behavior

### Model Testing Expectations

When modifying models or relationships:

- validate relationship integrity
- validate delete semantics
- validate serialization output
- validate ordering behavior
- validate archive behavior where applicable

### Test Organization

- Prefer integration tests for routes and blueprint behavior
- Prefer unit tests for service-layer logic
- Avoid excessive mocking in functional tests
- Add or update tests for all behavioral changes

### Test Style

Use clear Given-When-Then structure where practical.

Example:

```python
def test_user_can_view_profile(client):
    """Given an authenticated user
    When the profile page is requested
    Then the response is successful
    """
```

### Existing Examples

Refer to existing tests for established patterns:

- `tests/conftest.py`
- `tests/person/`
- `tests/service/`

---

## Build, Lint, and Test Commands

### Run Application

```bash
docker compose up --watch
```

### Run Tests

```bash
python -m pytest --cov=app --cov-report=term-missing --cov-branch
```

### Run Specific Tests

```bash
pytest tests/person/
```

### Format Code

```bash
black . -l 120
```

### Lint

```bash
flake8 .
```

### Type Check

```bash
mypy .
```

---

## Before Completing Work

Before submitting changes, always:

1. Run formatting
2. Run linting
3. Run type checking
4. Run relevant tests
5. Ensure new behavior includes appropriate test coverage
6. Remove dead code and unused imports
7. Verify imports are correctly organized
8. Ensure changes are scoped only to the requested task

---

## Sensitive Areas

Exercise caution when modifying:

- authentication and authorization flows
- application factory initialization
- database migrations
- session management
- permission enforcement
- shared service-layer utilities
- configuration and environment handling
- API response contracts
- infrastructure and container startup behavior
- serialization schemas and nested resource structures
- relationship delete semantics
- recursive relationship handling

Prefer incremental changes in these areas.

---

## Dependency Management

- Prefer existing project dependencies over adding new libraries
- New dependencies should provide clear maintenance or architectural benefit
- Avoid introducing overlapping frameworks or abstractions

---

## Performance and Reliability

- Avoid unnecessary database queries
- Prefer eager loading where appropriate
- Avoid N+1 query patterns
- Keep request handlers performant
- Avoid blocking operations in request paths
- Preserve application startup performance
- Use caching intentionally and conservatively
- Avoid excessive nested serialization causing large payloads

---

## Security Expectations

- Never trust client input without validation
- Preserve CSRF protections
- Maintain permission and authentication checks
- Use parameterized database operations through SQLAlchemy
- Preserve secure session handling behavior
- Avoid logging sensitive information

---

## Documentation Expectations

When introducing significant behavior changes:

- update relevant docstrings
- update `README.md` if setup or usage changes
- update `CONTRIBUTING.md` if workflow changes
- update OpenAPI documentation where applicable
- keep inline comments concise and meaningful

---

## Agent Workflow Guidance

When implementing changes:

1. Inspect existing patterns before introducing new ones
2. Prefer modifying existing modules over creating new ones
3. Keep changes small and cohesive
4. Validate behavior with tests
5. Avoid speculative refactors

If requirements are ambiguous, prefer the most conservative implementation that preserves existing architecture and behavior.

---

## References

Additional repository guidance can be found in:

- `README.md`
- `CONTRIBUTING.md`
- OpenAPI schema documentation
- `app/models.py`
- existing tests in `tests/`
