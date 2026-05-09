# Conflux - Copilot Instructions

## Purpose

This document defines repository-specific guidance for AI coding agents and automated tooling working within the Conflux codebase. Conflux is an organisational knowledge platform that models ownership, responsibilities, and dependencies across digital organisations.

Agents should prioritise:

1. Correctness
2. Consistency with existing patterns
3. Minimal, targeted changes
4. Backwards compatibility
5. Test coverage
6. Maintainability

When uncertain, prefer conservative implementations that preserve existing architecture and behaviour.

## Source of Truth and Precedence

When repository artifacts disagree, prefer the following order of precedence:

1. Existing runtime behaviour and tests
2. Database models (`app/models.py`) and migrations (`migrations/versions/`)
3. OpenAPI schema (`openapi.json`)
4. `.github/copilot-instructions.md`
5. `README.md` and supporting documentation

If introducing intentional behavioural changes, update tests, API documentation, and the README. Do not leave behaviour, tests, and API documentation inconsistent.

## Before Completing Work

Before submitting changes, you must execute the following commands in this exact sequence to ensure code quality and formatting. Do not use standard Python execution commands; use the provided containerised CLI where applicable.

1. **Sort Imports:** `isort .`
2. **Format Code (Baseline):** `black .` (Forces standard 90-character breaks for shorter lines)
3. **Format Code (Extended & Target):** `black . -t py314 -l 120` (Allows necessary longer lines up to 120 chars and targets Python 3.14 style)
4. **Lint:** `flake8 .` (Must pass with `flake8-bugbear` and `pep8-naming` rules)
5. **Type Check:** `mypy .`
6. **Run Tests:** `python -m pytest --cov=app --cov-report=term-missing --cov-branch`

If a test fails after your changes, do not modify the test to force it to pass. You must fix the underlying implementation, unless the prompt explicitly dictates a change to the expected behaviour.

## Configuration & Security

- Configuration is environment-variable driven (`DATABASE_URL`, `VALKEY_URL`, `SECRET_KEY`, `DOMAIN`, `GRADES`, `LOCATIONS`). Do not hardcode configuration values.
- Maintain consistency across all layers when modifying enumerated domain values (`GRADES` and `LOCATIONS`).
- Never expose, log, or hardcode the `SECRET_KEY`.
- Always use the `SECRET_KEY` for session cookie signing and CSRF token protection.

## Architecture & Structural Boundaries

- **Core Pattern:** Strictly follow the application structure and conventions from Miguel Grinberg's "Flask Mega-Tutorial" (Part XV).
- Use the **Application Factory Pattern**. Extensions must be instantiated globally in `app/__init__.py` but initialized strictly inside `create_app()`.
- `app/models.py` contains ALL SQLAlchemy models. Do not create separate model files to avoid circular import loops.
- `app/{domain}/` contains domain-specific Flask Blueprints. Respect the strict MVC-style internal split:
  - `api.py` & `ui.py` (Controllers): Handle request parsing, form validation, and response formatting ONLY. **Strict Rule: These files MUST NEVER import the database session or execute SQLAlchemy queries.**
  - `service.py` (Service Layer): Contains ALL business logic, orchestration, and database interactions. This is the ONLY layer permitted to execute SQLAlchemy queries. Controllers must delegate to these service functions.
  - `forms.py`: WTForms definitions and validation.
- `tests/` is strictly split into `unit/` and `integration/`.
- `web/` contains Node.js/Webpack frontend assets (including GOV.UK Frontend) and Nginx configuration. Do not leak these concerns into the Flask backend.
- **No HTTP Leakage**. The service layer must NEVER return HTTP status codes, `jsonify` payloads, or Werkzeug response objects. It must return native Python objects (dicts, lists, models) or raise custom domain exceptions. The view layer is strictly responsible for catching these exceptions and translating them into HTTP 400/404/500 responses.

## Logging Expectations

- **Format:** All logging must be structured and output in **JSON format**. Do not use plain text strings for log messages.
- **Separation of Concerns:** Strictly avoid duplicating log messages between the view and service layers.
- **View Layer (`api.py` & `ui.py`):** Logging in controllers must focus ONLY on the HTTP request/response cycle (e.g., incoming request paths, WTForms validation failures, and final HTTP status codes).
- **Service Layer (`service.py`):** The service layer is strictly responsible for logging the outcomes of business logic, database transactions, and model persistency (both successes and failures).
- **Data Sanitisation:** Never log sensitive organisational data, credentials, or Personally Identifiable Information (PII) such as email addresses in the JSON log payloads. Log identifiers (UUIDs) and state changes instead.

## Code Style & Type Hinting

- **Native Typing:** Strictly use Python built-in types for annotations wherever possible (e.g., use `list`, `dict`, `set`, `tuple` instead of importing `List`, `Dict`, `Set`, `Tuple` from the `typing` module).
- Avoid unnecessary imports from `typing` unless using specific constructs that don't have built-in equivalents (like `Any`, `Callable`, or `Literal`).
- **Return Types:** Every function and method must have an explicit return type annotation, even if it is `-> None`.
- **String Formatting:** Strictly use Python f-strings for all string interpolation and formatting. Do not use older methods such as `.format()` or `%` formatting.

## Documentation & Commenting Expectations

- **Docstrings:** Provide concise, PEP-compliant docstrings for all public modules, classes, and methods. Focus on the "what" and "why" to support editor autocomplete and static analysis.
- **Style:** Do not use overly dense or decorative comment blocks (e.g., massive ASCII art headers or redundant file headers).
- **In-line Comments:** Use in-line comments sparingly. They must only be used to explain complex logic, non-obvious intent, or specific domain context. Do not use them to explain what the code is doing line-by-line.
- **Language:** All documentation, docstrings, and comments must use **UK English** (e.g., _behaviour_, _initialise_, _authorised_).
- **Type Information:** Since the codebase targets Python 3.14 and uses strict type hinting, avoid duplicating type information within docstrings. Let the type annotations serve as the source of truth.

## Database & ORM Expectations (SQLAlchemy)

- Strictly use **SQLAlchemy 2.0 style** model class and attribute definitions (e.g., `Mapped[str]`, `mapped_column()`) via Flask-SQLAlchemy v3.x. Do not use legacy 1.x declarative styles.
- All database models must be strictly normalised to **3rd Normal Form (3NF)**.
- **Many-to-Many Relationships:** Always resolve M2M relationships using explicit link (association) tables or models. Never use PostgreSQL arrays or JSON fields to fake relations.
- **Domain Rules:** People belong to teams; People perform roles; Teams own services; Services depend on components.
- **Delete Semantics:** Preserve existing behaviours:
  - `Role -> Person` uses `ON DELETE RESTRICT`
  - `Team -> Person` and `Team -> Service` use `ON DELETE SET NULL`
  - `Service <-> Component` is many-to-many via explicit link table `service_components`
- **Primary Keys:** Use PostgreSQL UUID identifiers for all primary entities. Avoid introducing integer identifiers.
- **Timestamps:** Timestamps must always be timezone-aware and in UTC. When in string format, they must always be in strict ISO 8601 format, explicitly substituting `+00:00` for `Z` (Zulu time). Use existing utilities like `app.utils.govuk_datetime` where appropriate.
- **Archival:** Primary entities use soft archival through `archived_at` and `updated_at`. Avoid hard deletes.
- **Performance / N+1 Prevention:** When querying lists of records that require relationship expansion, you must use explicit SQLAlchemy 2.0 eager loading (e.g., `options(selectinload(...))`) in the service layer. Do not rely on lazy loading inside loops.

### Serialization Patterns

Models must implement explicit `to_dict()` serializers to prevent recursive serialization.
Example structure:

```python
def to_dict(self, include_relations: bool = False) -> dict:
    data = {
        "id": str(self.id),
        "name": self.name,
        # Ensure UTC datetime objects are strictly formatted with Z instead of +00:00
        "created_at": self.created_at.isoformat().replace("+00:00", "Z") if self.created_at else None
    }
    # Add relationship expansion logic here if requested, avoiding deep nesting
    return data
```

## Database Migrations

- Keep migrations small, focused, and additive.
- Do not modify historical migrations in migrations/versions/.
- Strict Rule: Do not manually write Alembic migration scripts. Always generate them using the containerised CLI, e.g., docker compose exec web flask db migrate -m "description", and then manually review the output in migrations/versions/.

## API Expectations

- The API is versioned under `/api/v1/`, primarily read-only, JSON-based, and UUID-driven.
- Timestamp Formats: All API timestamp responses must be UTC, timezone-aware, and strictly formatted as ISO 8601 strings ending in `Z` (not `+00:00`).
- Preserve existing response structures, field naming conventions, filtering behaviour, and sorting semantics.
- Always update `openapi.json` at the repository root when modifying API behaviour.

## Testing Expectations

### Framework and Style

- Strictly use `pytest`. Do not use Python's built-in `unittest.TestCase` classes.
- Name all test files, test classes, and test functions with the `test_` prefix.
- **Docstrings:** All tests must include BDD-style docstrings using the exact format:
  ```python
  """
  GIVEN [initial state or context]
  WHEN [action or event occurs]
  THEN [expected outcome or state]
  """
  ```
- Use @pytest.mark.parametrize to test multiple sets of inputs and expected outputs.

### Test Categorisation (Unit vs Integration)

Strictly stick to Unit and Integration tests. Do not write functional, end-to-end, or acceptance tests. Place tests in their respective directories:

- Unit Tests (tests/unit/): Test the functionality of an individual unit of code isolated from its dependencies. These act as the first line of defence, testing from the inside out (from the programmer's point of view). heavily use monkeypatch to mock external dependencies.
- Integration Tests (tests/integration/): Test multiple components working together properly, focusing on functionality the user will utilize. These test from the outside in (from the end user's point of view). Use the client fixture (app.test_client()) here to issue HTTP requests.

### Fixtures and Setup (tests/conftest.py)

- Place all shared test setup logic and factory data in `tests/conftest.py` using `@pytest.fixture`.
- Always rely on an app fixture configured with `TESTING=True` and an isolated test database.
- Build domain-specific fixtures (e.g., authenticated_client, mock_person, mock_team) to encapsulate complex state setup.

### Context Management

- Strict Rule: Always execute database queries, model assertions, or service layer calls inside an explicit application context using with `app.app_context():` within your tests.
- Do not attempt to query the database using the test client response object directly.
