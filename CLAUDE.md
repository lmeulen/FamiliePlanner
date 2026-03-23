# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FamiliePlanner is a family organization webapp with FastAPI backend and vanilla HTML/CSS/JS frontend. No build tools required for frontend. Uses SQLite with SQLAlchemy async ORM, session-based authentication, and comprehensive recurring event/task system.

**Tech Stack:**
- Backend: FastAPI 0.115+, SQLAlchemy 2.0 (async), Uvicorn, Pydantic, Loguru
- Frontend: Vanilla JS (no frameworks), Jinja2 templates
- Database: SQLite with async (aiosqlite)
- Testing: pytest + pytest-asyncio (~73 tests)
- CI: GitHub Actions (ruff, black, mypy, pytest, commitlint)

## Development Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # Edit SECRET_KEY, APP_USERNAME, APP_PASSWORD
```

### Running
```bash
python run.py --host 0.0.0.0 --port 8000 --reload  # Development
python -m tools.seed                                # Populate test data
```

### Testing & Linting
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agenda.py -v

# Run single test
pytest tests/test_agenda.py::test_create_event -v

# CI checks (must all pass)
ruff check .                      # Linting
ruff format .                     # Auto-format
black .                           # Code formatting
mypy app/ --ignore-missing-imports  # Type checking
pytest tests/ -v                  # Tests
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Docker

FamiliePlanner supports Docker deployment:

```bash
cp .env.example .env
docker-compose up -d
```

See full guide: [docs/README.docker.md](docs/README.docker.md)

### Utility Tools

The `tools/` directory contains standalone scripts for maintenance and data operations:

```bash
# Database operations
python -m tools.clean_database          # Remove all events, tasks, and meals
python -m tools.clean_database --dry-run  # Preview what would be deleted
python -m tools.seed                    # Populate with test data
python -m tools.breakup_multiday_appointments  # Convert multi-day events to daily series
python -m tools.breakup_multiday_appointments --dry-run  # Preview conversion

# Backup and restore
python -m tools.run_nightly_backup_once  # Manually trigger backup (creates backups/DDMMYYYY.json)

# Photo management
python -m tools.generate_missing_thumbnails  # Regenerate missing thumbnails in uploads/

# Cozi integration (import from Cozi ICS feed)
python -m tools.cozi_import_advisor     # Analyze Cozi feed and suggest mappings
python -m tools.cozi_importer --dry-run  # Preview import without changes
python -m tools.cozi_importer           # Import events from Cozi (auto-converts multi-day to daily series)
python -m tools.cozi_importer --today   # Import only today's events

# Security
python -m tools.hash_password           # Generate bcrypt hash for passwords

# Grocery debugging
python -m tools.check_grocery_db        # Verify grocery database state and learning data

# Mealie recipe integration
python -m tools.list_mealie_recipes                       # List all recipe names from Mealie
python -m tools.list_mealie_recipes --detailed            # Show detailed info (categories, tags, rating)
python -m tools.list_mealie_recipes --ingredients         # Show ingredients (slower, fetches full details)
python -m tools.list_mealie_recipes --detailed --ingredients  # Show everything
python -m tools.list_mealie_recipes --page 2              # Show specific page only
python -m tools.list_mealie_recipes --configure           # Configure Mealie settings interactively
```

**Nightly backup system:** The app automatically creates JSON backups at midnight via `app/backup_scheduler.py`. Backups are stored in `backups/DDMMYYYY.json` with full database export (events, tasks, meals, family members, photos metadata). The backup scheduler runs as a background task launched during app startup (lifespan context manager) and is gracefully stopped on shutdown.

## Architecture

### Backend Structure

**Request Flow:**
```
Request → SessionMiddleware → CSRFMiddleware → AuthMiddleware →
SlowAPIMiddleware (rate limiting) → PrometheusMiddleware (metrics) →
FastAPI router → Pydantic validation → SQLAlchemy ORM → SQLite
```

**Module Organization:**
- `app/main.py` - FastAPI app, middleware stack, page routes, exception handlers
- `app/routers/*.py` - REST API endpoints (agenda, tasks, meals, family, photos, grocery, settings, search, stats)
- `app/models/*.py` - SQLAlchemy ORM models (Base from database.py)
- `app/schemas/*.py` - Pydantic request/response schemas with validation
- `app/utils/*.py` - Shared utilities (recurrence logic, DB helpers)
- `app/auth.py` - Session-based auth middleware + login/logout handlers
- `app/csrf.py` - CSRF token validation middleware
- `app/errors.py` - Error codes, error response models, translation utilities
- `app/database.py` - Async engine, session factory, `get_db()` dependency
- `app/backup_scheduler.py` - Nightly backup job (runs at 00:00)
- `app/metrics.py` - Prometheus metrics configuration
- `app/config.py` - Environment variable loading and app configuration
- `app/logging_config.py` - Loguru setup with file rotation
- `app/enums.py` - MealType and RecurrenceType enums
- `tools/*.py` - Standalone maintenance scripts (see Utility Tools section)
- `backups/` - JSON backup files (DDMMYYYY.json format)

### Frontend Architecture

**No build step.** Vanilla JavaScript with manual module organization:
- `app/static/js/app.js` - Global utilities (`FP` object) for date/time formatting, member utilities, UI helpers
- `app/static/js/api.js` - Fetch wrapper with CSRF token handling
- `app/static/js/toast.js` - Toast notification system
- `app/static/js/modal.js` - Reusable modal controller
- `app/static/js/theme.js` - Theme switcher (light/dark/system)
- `app/static/js/cache.js` - Client-side caching utilities
- `app/static/js/pwa-install.js` - PWA install prompt handler
- `app/static/js/grocery-db.js` - IndexedDB wrapper for offline grocery list
- `app/static/js/form-controllers/` - **Shared form controllers** for DRY principle
  - `recurrence-ui.js` - Recurrence field management (used by both events and tasks)
  - `event-form.js` - Event CRUD controller (agenda + dashboard)
  - `task-form.js` - Task CRUD controller (tasks + dashboard)
- `app/static/js/{page}.js` - Page-specific logic (agenda.js, tasks.js, meals.js, grocery.js, photos.js, dashboard.js, family.js, settings.js, search.js, stats.js)
- `app/templates/*.html` - Jinja2 templates extending `base.html`

**PWA Features:**
- Installable as native app (Android, iOS, Windows, macOS)
- Service Worker with offline-first caching strategy (`app/static/sw.js`)
- App shortcuts for quick access (Agenda, Taken, Maaltijden)
- Manifest file (`app/static/manifest.json`) with icons and theme colors
- Update notifications when new versions are available

**Global Objects:**
- `window.FP` - Date/time formatting, member utilities, UI helpers
- `window.API` - GET/POST/PUT/DELETE wrappers with error handling
- `window.Toast` - Notification system
- `window.Modal` - Modal dialog controller
- `window.Theme` - Theme management (light/dark/system)

### Recurring Series Pattern

**Critical Pattern:** Both agenda events and tasks support recurring series with individual exception handling.

**Two-entity model:**
1. **Series table** (`recurrence_series`, `task_recurrence_series`) - Stores recurrence rule
2. **Instance table** (`agenda_events`, `tasks`) - Individual occurrences with `series_id` FK

**Workflow:**
- Creating series → generates all occurrences (max 365) via `utils/recurrence.py`
- Updating single instance → sets `is_exception=True`, detaches from series updates
- Updating series → regenerates all non-exception occurrences
- Deleting series → cascades to all instances

**Recurrence types** (`app/enums.py`):
- `daily`, `every_other_day`, `weekly`, `biweekly`, `weekdays`, `monthly`, `yearly`

### Database Patterns

**Async Session Management:**
```python
# Router dependency injection
async def endpoint(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model).where(...))
    item = result.scalar_one_or_none()
```

**Many-to-many relationships:**
- Use junction tables: `agenda_event_members`, `task_members`, etc.
- Helper: `app/utils/db.py::set_junction_members()` for atomic updates
- Always use `selectin` loading strategy: `.options(selectinload(Model.members))`

**Important:** Foreign keys have `ON DELETE CASCADE` or `SET NULL` - check models before deleting!

## Configuration

**pyproject.toml** centralizes tool configurations:
- **Ruff**: Line length 120, Python 3.11+, excludes `.venv`, `alembic/versions`
- **Black**: Line length 120, Python 3.11 target
- **Mypy**: Ignores `tools/` and `alembic/`, requires imports to be silent, ignores test errors
- **Pytest**: Auto async mode, testpaths `tests/`, strict markers, supports `slow` and `integration` markers

## Key Conventions

### Type Safety (mypy)

- **Union return types in FastAPI routes need `response_model=None`**
  ```python
  @app.get("/route", response_model=None)  # Required for Union[HTMLResponse, RedirectResponse]
  async def handler() -> HTMLResponse | RedirectResponse:
  ```

- Use `# type: ignore[specific-code]` for unavoidable issues (PIL Image types, slowapi handlers)
- Prefer explicit dict typing: `dict[str, Any]` over `dict`

### Testing

- Tests use in-memory SQLite (`:memory:`)
- Authentication disabled via `os.environ["AUTH_DISABLED"] = "1"` in `conftest.py`
- Each test gets fresh DB (function scope)
- Use `AsyncClient` from httpx, not TestClient

### Pydantic Schemas

- `Create` - POST request body, excludes id/timestamps
- `Update` - PUT request body, may have optional fields
- `Out` - Response model, includes id/timestamps, uses `model_config = ConfigDict(from_attributes=True)`
- Schemas separate from models to avoid circular imports

### Frontend Data Flow

1. Page loads → fetch data via `API.get()`
2. Render to DOM (no virtual DOM/reactivity)
3. User action → form submit/button click
4. POST/PUT/DELETE via `API.*()`
5. Success → re-fetch and re-render OR update local state
6. Show Toast notification

### Frontend Patterns

**Form Controllers (DRY Principle):**
- Shared form controllers in `app/static/js/form-controllers/` to avoid code duplication
- `event-form.js` handles event CRUD across both agenda page and dashboard quick-add
- `task-form.js` handles task CRUD across tasks page and dashboard quick-add
- `recurrence-ui.js` manages recurrence UI fields for both events and tasks
- When modifying event/task forms, update the controller, not individual page scripts

### CSRF Protection

- Enabled via `CSRFMiddleware` in main.py
- Token auto-injected in base.html: `<meta name="csrf-token" content="{{ request.state.csrf_token }}">`
- `api.js` reads token and adds to all non-GET requests via `X-CSRF-Token` header
- `/login` endpoint is exempt from CSRF checks (no session exists at first login)

### Error Handling

- Centralized error handling via `app/errors.py` with `ErrorCode` enum and `ErrorResponse` model
- Custom exception handlers in `main.py` for:
  - `SQLAlchemyError` → 400 with translated error message
  - `IntegrityError` → 400 with user-friendly constraint violation messages
  - `RequestValidationError` → 422 with translated Pydantic validation errors
  - `StarletteHTTPException` → Preserved status code with error details
- All API errors return JSON with `{"detail": "error message"}` format

### Commit Messages

Follow conventional commits (enforced by commitlint in CI):
```
feat: Add calendar export functionality
fix: Resolve timezone issue in event display
docs: Update API documentation
refactor: Simplify recurring task generation
test: Add tests for series deletion cascade
```

## Important Gotchas

1. **Recurring series regeneration is expensive** - deletes and recreates all occurrences. Consider performance for large series.

2. **member_ids handling** - Many-to-many relationships require separate junction table operations. Use `set_junction_members()` utility, not direct ORM assignment.

3. **Datetime handling** - Frontend uses local datetime-local inputs. Backend stores UTC-naive datetime. All-day events store start-of-day datetime with `all_day=True` flag.

4. **Photo uploads** - Original files stored in `app/static/uploads/`, thumbnails (200px) in `app/static/uploads/thumbnails/`. Both JPEG and PNG supported with RGBA→RGB conversion.

5. **Authentication bypass** - Set `AUTH_REQUIRED=false` in .env OR `os.environ["AUTH_DISABLED"]="1"` for tests. Middleware checks both.

6. **Static file versioning & caching** - `base.html` appends `?v={{ static_v }}` to CSS/JS to bust cache. `static_v` is unix timestamp from app startup. The app uses `CachedStaticFiles` with custom Cache-Control headers: thumbnails cached 1 year (immutable), photos 1 day, CSS/JS 1 hour, images/fonts 1 week.

7. **Alembic in async context** - `init_db()` runs Alembic upgrade in thread executor to avoid blocking event loop.

8. **Cozi importer meal detection** - The Cozi importer only imports events as meals if they occur between 18:00-20:00 (dinner time). This prevents false positives from all-day events or morning appointments being classified as meals.

9. **Tools run as modules** - All scripts in `tools/` must be run as modules (`python -m tools.script_name`) not as direct scripts, to ensure proper import paths and database access.

10. **Multi-day all-day events** - When creating an all-day event that spans multiple days, the frontend and Cozi importer automatically convert it to a daily recurring series so the event appears on all days. Use `tools/breakup_multiday_appointments.py` to convert existing multi-day events that were created before this feature.

11. **SQLite migrations** - Always use `batch_alter_table` context manager in Alembic migrations for SQLite compatibility. SQLite has limited ALTER TABLE support, and batch mode creates a temporary table, copies data, and swaps tables atomically.

12. **Grocery parser** - The grocery parser (`app/utils/grocery_parser.py`) intelligently parses freeform input like "2 kg tomaten" or "500g cheese" to extract quantity, unit, and product name. Supports Dutch and English units with auto-translation. Use `parse_grocery_input()` for parsing and `display_product_name()` for user-friendly capitalization.

13. **Grocery learning algorithm** - The grocery system learns product-category associations in `grocery_product_learning` table. When a user adds a product, it remembers the category. Next time the same product is added, it auto-suggests the most frequently used category. Learning data updates on both manual category changes and initial selections.

14. **Offline grocery support** - The grocery list uses IndexedDB (`grocery-db.js`) for offline-first functionality. When offline, items are stored locally with temporary negative IDs and queued for sync. When online, a background sync process uploads pending changes and resolves ID conflicts. The UI shows an offline indicator and sync status banner.

## Grocery List Feature

**Smart grocery list** with offline PWA support, category learning, and intelligent parsing.

**Key Features:**
- **Smart parser** - Parses "2 kg tomaten" → quantity: 2, unit: "kg", product: "tomaten"
- **Category learning** - Remembers product-category associations, auto-suggests on next use
- **Offline-first** - IndexedDB storage, works without internet, auto-syncs when online
- **11 default categories** - Groente & fruit, Zuivel, Vlees & vis, Brood & bakkerij, etc.
- **Category reordering** - Custom sort order via drag-and-drop modal
- **Bilingual parsing** - Dutch and English units (lb → kg, pieces → stuks)

**Architecture:**
- **Three-table model** - `grocery_categories`, `grocery_items`, `grocery_product_learning`
- **Smart parsing** - Regex-based parser extracts quantity/unit/product from freeform text
- **Learning table** - Tracks product→category mappings with usage count for confidence
- **IndexedDB sync** - Offline queue with background sync, temporary negative IDs for conflicts
- **Optimistic updates** - UI updates immediately, syncs in background

## API Documentation

Interactive docs available at: `http://localhost:8000/api/docs` (Swagger UI)

All API routes return JSON. Common responses:
- `200` - Success
- `201` - Created
- `204` - Deleted (no content)
- `404` - Not found
- `422` - Validation error (Pydantic)
- `400` - SQLAlchemy error

### Monitoring

**Prometheus metrics** available at: `http://localhost:8000/metrics`

Tracked metrics include:
- `http_requests_total` - Total HTTP requests by method/endpoint/status
- `http_request_duration_seconds` - Request latency histogram
- `db_query_duration_seconds` - Database query duration
- `db_connections_active` - Active database connections
- Business metrics: `events_created_total`, `tasks_created_total`, `tasks_completed_total`, `meals_created_total`, `photos_uploaded_total`

Metrics configured in `app/metrics.py`, middleware in `PrometheusMiddleware`

### Grocery API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/grocery/categories` | GET | List all categories (ordered by sort_order) |
| `/api/grocery/categories/reorder` | PUT | Update category sort order |
| `/api/grocery/items` | GET | List all items (unchecked first, then by category) |
| `/api/grocery/items` | POST | Create item with smart parsing and learning |
| `/api/grocery/items/{id}` | PATCH | Update item (check/uncheck, change category) |
| `/api/grocery/items/{id}` | DELETE | Delete single item |
| `/api/grocery/items/done` | DELETE | Clear all checked items |
| `/api/grocery/suggest/{product}` | GET | Get category suggestion based on learning |

## Useful Queries

**Find all recurring series:**
```sql
SELECT * FROM recurrence_series;
SELECT * FROM task_recurrence_series;
```

**Find exceptions in a series:**
```sql
SELECT * FROM agenda_events WHERE series_id = ? AND is_exception = 1;
```

**Today's events:**
```sql
SELECT * FROM agenda_events
WHERE date(start_time) = date('now');
```
