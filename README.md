# 🏠 FamiliePlanner

Een moderne Progressive Web App voor gezinsorganisatie, gebouwd met FastAPI + Uvicorn (backend) en vanilla HTML/CSS/JS (frontend). Installeerbaar als native app op mobiel en desktop, werkt offline!

## 🚀 Highlights

- ⚡ **Snelle PWA** - Installeer als native app, werkt offline, instant loading
- 🔄 **Herhaalde Series** - Slimme recurrence voor events en taken (dagelijks tot jaarlijks)
- 👥 **Multi-user** - Kleur-gecodeerde gezinsleden met avatar en filtering
- 🌓 **Dark Mode** - Light/dark/system thema met smooth transitions
- 📱 **Mobile First** - Responsive design, touch-optimized, safe-area support
- 🔍 **Global Search** - Zoek door alle modules (events, tasks, meals)
- 📊 **Statistieken** - Inzicht in gebruikspatronen en activiteit
- 💾 **Auto Backup** - Dagelijkse JSON backups om 00:00
- 🔒 **Veilig** - CSRF protection, rate limiting, session-based auth
- 📈 **Monitorbaar** - Prometheus metrics voor monitoring

## ✨ Functionaliteiten

| Module | Beschrijving |
|--------|-------------|
| **📱 Progressive Web App** | Installeerbaar als native app, werkt offline, app shortcuts, snelle laadtijden |
| **🏠 Overzicht** | Dashboard met fotodiashow, agenda van vandaag, maaltijden en taken met snelle toevoeg-opties |
| **📅 Agenda** | Dag / week / maand / lijstweergave, herhaalde afspraken, multi-day support, filter op gezinslid, iCal export |
| **✅ Taken** | Meerdere takenlijsten met custom volgorde, herhaalde taken, toewijzen aan gezinsleden, vervaldatum, verlopen-taken groepering |
| **🍽️ Maaltijden** | Weekplanner met ontbijt/lunch/diner/snack, kok-toewijzing, recept-URL's, meal-type filtering |
| **👨‍👩‍👧‍👦 Gezin** | Gezinsleden beheren met naam, kleur en emoji-avatar |
| **🖼️ Foto's** | Upload foto's (JPEG/PNG), automatische thumbnails, diashow op dashboard, fullscreen viewer |
| **🔍 Zoeken** | Globaal zoeken door agenda, taken en maaltijden met deep-linking |
| **📊 Statistieken** | Inzicht in gebruikspatronen, meest actieve leden, populaire maaltijden |
| **⚙️ Instellingen** | Thema (licht/donker/systeem), fotogrootte dashboard, authenticatie toggle, export/import |

## 🎯 Kernfuncties

### Progressive Web App (PWA)
- ✅ **Installeerbaar als native app** - Android, iOS, Windows, macOS
- ✅ **Offline support** - Werkt zonder internetverbinding (cached data)
- ✅ **App shortcuts** - Snelle toegang tot Agenda, Taken, Maaltijden
- ✅ **Custom install prompt** - Gebruiksvriendelijke installatie-banner
- ✅ **Update notificaties** - Automatische meldingen bij nieuwe versies
- ✅ **Standalone mode** - Geen browser chrome, volledige app-ervaring

### Herhaalde Series
- **Agenda events** - Dagelijks, wekelijks, tweewekelijks, maandelijks, jaarlijks
- **Taken** - Terugkerende taken met flexibele planning
- **Exception handling** - Bewerk individuele voorkomsten zonder serie te breken
- **Bulk updates** - Pas hele serie aan met één actie

### Geavanceerde Filters
- **Gezinslid filtering** - Zie alleen relevante items per persoon
- **Type filtering** - Filter op maaltijdtype, takenlijst, etc.
- **Datum ranges** - Flexibele datumbereiken voor overzichten

## 📋 Vereisten

- Python 3.11+
- Linux / Windows / macOS
- Moderne browser (Chrome, Edge, Safari, Firefox)

## Installatie & starten

```bash
# 1. Kloon of download het project
cd /path/to/FamiliePlanner

# 2. Maak een virtual environment aan
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.\.venv\Scripts\activate         # Windows

# 3. Installeer afhankelijkheden
pip install -r requirements.txt

# 4. Configureer omgevingsvariabelen
cp .env.example .env
# Bewerk .env en stel SECRET_KEY, APP_USERNAME en APP_PASSWORD in

# 5. Seed de database met voorbeelddata (optioneel)
python -m tools.seed

# 6. Start de server
python run.py --host 0.0.0.0 --port 8000
```

Open in de browser: **http://\<server-ip\>:8000**

## 📱 PWA Installatie

### Mobiel (Android/iOS)

**Android (Chrome/Edge):**
1. Open de app in Chrome of Edge
2. Zie install banner onderaan → tap "Installeren"
3. Of: Menu (⋮) → "App installeren" / "Add to Home Screen"
4. App verschijnt op home screen met 🏠 icoon

**iOS (Safari):**
1. Open de app in Safari
2. Tap Share-knop (vierkant met pijl omhoog)
3. Scroll en tap "Add to Home Screen"
4. Tap "Add"

### Desktop (Chrome/Edge)

1. Open de app in Chrome of Edge
2. Klik install icoon (⊕) in adresbalk
3. Bevestig installatie
4. App opent in eigen venster (zoals desktop app)

**App shortcuts:** Long-press app icoon → Zie shortcuts voor Agenda, Taken, Maaltijden

📖 Volledige PWA test guide: [PWA_TESTING.md](PWA_TESTING.md)

### Ontwikkelmodus
```bash
python run.py --host 0.0.0.0 --port 8000 --reload
```

### Productie (systemd)
```ini
[Unit]
Description=FamiliePlanner
After=network.target

[Service]
User=<jouw-user>
WorkingDirectory=/path/to/FamiliePlanner
ExecStart=/path/to/FamiliePlanner/.venv/bin/python run.py --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now familieplanner
```

## Omgevingsvariabelen

Kopieer `.env.example` naar `.env`:

| Variabele | Standaard | Beschrijving |
|-----------|-----------|-------------|
| `SECRET_KEY` | _(willekeurig)_ | Sleutel voor sessiecookies |
| `APP_USERNAME` | `admin` | Inlognaam |
| `APP_PASSWORD` | `familieplanner` | Wachtwoord |
| `AUTH_REQUIRED` | `true` | `false` om authenticatie uit te schakelen |
| `COZI_ICS_URL` | _(leeg)_ | Cozi ICS feed URL voor import tools (optioneel) |

> ⚠️ Commit `.env` nooit naar git.

## 📁 Projectstructuur

```
FamiliePlanner/
├── app/
│   ├── main.py                      # FastAPI app, middleware, routes, exception handlers
│   ├── auth.py                      # Authenticatie middleware + login/logout
│   ├── csrf.py                      # CSRF token validatie middleware
│   ├── config.py                    # Omgevingsvariabelen
│   ├── database.py                  # SQLAlchemy async engine + session factory
│   ├── enums.py                     # MealType en RecurrenceType enums
│   ├── errors.py                    # Error codes, response models, translations
│   ├── logging_config.py            # Loguru configuratie (file rotation)
│   ├── metrics.py                   # Prometheus metrics configuratie
│   ├── backup_scheduler.py          # Nightly backup scheduler (00:00)
│   ├── models/                      # SQLAlchemy ORM modellen
│   │   ├── agenda.py                # AgendaEvent, RecurrenceSeries
│   │   ├── tasks.py                 # Task, TaskList, TaskRecurrenceSeries
│   │   ├── meals.py                 # Meal
│   │   ├── family.py                # FamilyMember
│   │   ├── photos.py                # Photo
│   │   └── settings.py              # Settings
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── routers/                     # REST API endpoints
│   │   ├── agenda.py                # Events, recurring series, iCal export
│   │   ├── tasks.py                 # Tasks, lists, series, overdue position
│   │   ├── meals.py                 # Meals (today, week, filters)
│   │   ├── family.py                # Family members CRUD
│   │   ├── photos.py                # Photo upload, thumbnails
│   │   ├── settings.py              # App settings
│   │   ├── search.py                # Global search across all modules
│   │   └── stats.py                 # Usage statistics, insights
│   ├── utils/                       # Gedeelde helpers
│   │   ├── recurrence.py            # Recurrence rule generator (max 365 occurrences)
│   │   └── db.py                    # Junction table helpers
│   ├── static/
│   │   ├── css/
│   │   │   ├── themes.css           # Light/dark/system theme variables
│   │   │   └── main.css             # Layout, components, PWA styles
│   │   ├── js/
│   │   │   ├── form-controllers/    # Shared form controllers (DRY)
│   │   │   │   ├── recurrence-ui.js # Recurrence field management
│   │   │   │   ├── event-form.js    # Event CRUD (agenda + dashboard)
│   │   │   │   └── task-form.js     # Task CRUD (tasks + dashboard)
│   │   │   ├── api.js               # Fetch wrapper with CSRF
│   │   │   ├── app.js               # Global utilities (FP object)
│   │   │   ├── cache.js             # Client-side caching
│   │   │   ├── modal.js             # Modal controller
│   │   │   ├── toast.js             # Toast notifications
│   │   │   ├── theme.js             # Theme switcher
│   │   │   ├── pwa-install.js       # PWA install prompt
│   │   │   ├── dashboard.js         # Dashboard page logic
│   │   │   ├── agenda.js            # Agenda views (day/week/month/list)
│   │   │   ├── tasks.js             # Task lists and management
│   │   │   ├── meals.js             # Weekly meal planner
│   │   │   ├── photos.js            # Photo upload and gallery
│   │   │   ├── family.js            # Family member management
│   │   │   ├── search.js            # Global search UI
│   │   │   ├── stats.js             # Statistics dashboard
│   │   │   └── settings.js          # Settings page
│   │   ├── manifest.json            # PWA manifest (icons, shortcuts)
│   │   ├── sw.js                    # Service worker (offline support)
│   │   └── uploads/                 # User-uploaded photos + thumbnails/
│   └── templates/                   # Jinja2 HTML templates
│       ├── base.html                # Base layout (nav, modal, PWA setup)
│       ├── dashboard.html           # Dashboard with photo slideshow
│       ├── agenda.html              # Calendar views + event form
│       ├── tasks.html               # Task lists + task form
│       ├── meals.html               # Weekly meal grid + meal form
│       ├── photos.html              # Photo gallery + upload
│       ├── family.html              # Family member cards
│       ├── search.html              # Search results page
│       ├── stats.html               # Statistics page
│       ├── settings.html            # Settings form
│       ├── login.html               # Login page
│       └── error.html               # Error page
├── alembic/versions/                # Database migrations (Alembic)
├── tests/                           # Pytest testsuite (~106 tests)
├── tools/                           # Maintenance scripts (run as modules)
│   ├── clean_database.py            # Clear all data (with dry-run)
│   ├── seed.py                      # Generate test data
│   ├── breakup_multiday_appointments.py  # Convert multi-day to series
│   ├── run_nightly_backup_once.py   # Manual backup trigger
│   ├── generate_missing_thumbnails.py    # Regenerate thumbnails
│   ├── cozi_import_advisor.py       # Analyze Cozi ICS feed
│   ├── cozi_importer.py             # Import from Cozi
│   └── hash_password.py             # Generate bcrypt hash
├── backups/                         # Nightly JSON backups (DDMMYYYY.json)
├── logs/                            # Daily rotating logs (7 day retention)
├── docs/                            # Documentation
│   ├── README.docker.md             # Docker setup guide
│   └── database.md                  # Database schema and relations
├── run.py                           # Uvicorn startup script
├── .env.example                     # Environment variable template
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Pytest configuration
├── pyproject.toml                   # Tool configs (ruff, black, mypy)
├── PWA_TESTING.md                   # PWA installation and testing guide
└── README.md                        # This file
```

## 🔧 Tech Stack

### Backend
- **FastAPI 0.115+** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM met type hints
- **Uvicorn** - ASGI server met hot reload
- **Pydantic** - Data validation en serialization
- **Loguru** - Structured logging met file rotation
- **Alembic** - Database migrations
- **SQLite** - Async database (aiosqlite)
- **Prometheus Client** - Metrics export

### Frontend
- **Vanilla JavaScript** - No build tools, no frameworks
- **Jinja2** - Server-side templating
- **CSS Custom Properties** - Theming (light/dark/system)
- **Service Worker** - PWA offline support
- **Cache API** - Client-side caching

### Development
- **Pytest** - Testing framework (~106 tests)
- **Ruff** - Fast Python linter
- **Black** - Code formatter
- **Mypy** - Static type checker
- **GitHub Actions** - CI/CD pipeline

## 📡 API

Interactieve documentatie: **http://\<server\>:8000/api/docs** (Swagger UI)

### Endpoints

| Endpoint | Beschrijving |
|----------|-------------|
| **Agenda** ||
| `GET/POST /api/agenda/` | Lijst/creëer events (met date filtering) |
| `PUT/DELETE /api/agenda/{id}` | Update/verwijder event |
| `GET/POST /api/agenda/series` | Lijst/creëer recurring series |
| `PUT/DELETE /api/agenda/series/{id}` | Update/verwijder series (regenereert voorkomsten) |
| `GET /api/agenda/{id}/export` | Export event als iCal (.ics) |
| **Taken** ||
| `GET/POST /api/tasks/` | Lijst/creëer taken (filters: list_id, member_id, done) |
| `PUT/DELETE /api/tasks/{id}` | Update/verwijder taak |
| `PATCH /api/tasks/{id}/toggle` | Toggle done status |
| `GET/POST /api/tasks/lists` | Lijst/creëer takenlijsten |
| `PUT /api/tasks/lists/reorder` | Herorder takenlijsten |
| `GET/POST /api/tasks/series` | Lijst/creëer recurring task series |
| `GET /api/tasks/overdue-position` | Ophalen positie "Verlopen taken" groep |
| **Maaltijden** ||
| `GET/POST /api/meals/` | Lijst/creëer maaltijden (filters: start, end, meal_type) |
| `GET /api/meals/today` | Maaltijden van vandaag |
| `GET /api/meals/week` | Maaltijden komende 7 dagen |
| **Familie** ||
| `GET/POST /api/family/` | Lijst/creëer gezinsleden |
| `PUT/DELETE /api/family/{id}` | Update/verwijder gezinslid |
| **Foto's** ||
| `GET/POST /api/photos/` | Lijst/upload foto's (multipart/form-data) |
| `DELETE /api/photos/{id}` | Verwijder foto (inclusief thumbnail) |
| **Zoeken** ||
| `GET /api/search/?q={query}` | Zoek in agenda, taken, maaltijden (min 3 chars) |
| **Statistieken** ||
| `GET /api/stats/overview` | Usage statistics (events, tasks, meals per member) |
| `GET /api/stats/meals/popular` | Meest geplande maaltijden |
| **Instellingen** ||
| `GET /api/settings/` | Ophalen app settings |
| `PUT /api/settings/` | Update settings |

### Response Formats

**Success:**
```json
{
  "id": 1,
  "title": "Voetbaltraining",
  "start_time": "2026-03-15T14:00:00",
  "member_ids": [1, 2]
}
```

**Error:**
```json
{
  "detail": "Event not found"
}
```

## 📊 Monitoring

**Prometheus metrics** beschikbaar op: `http://\<server\>:8000/metrics`

**Getrackte metrics:**
- `http_requests_total` - HTTP requests per method/endpoint/status
- `http_request_duration_seconds` - Request latency (histogram)
- `db_query_duration_seconds` - Database query duration
- `db_connections_active` - Active DB connections
- `events_created_total` - Aantal aangemaakte events
- `tasks_created_total` - Aantal aangemaakte taken
- `tasks_completed_total` - Aantal afgevinkte taken
- `meals_created_total` - Aantal geplande maaltijden
- `photos_uploaded_total` - Aantal geüploade foto's

**Grafana dashboard:** Importeer metrics voor visualisatie

## Tests

```bash
pytest tests/ -v
```

## Hulpprogramma's (tools/)

De `tools/` directory bevat standalone scripts voor onderhoud en data-operaties. Alle scripts moeten worden uitgevoerd als module met `python -m tools.script_name`.

### Database

**clean_database.py** - Verwijder alle agenda-items, taken en maaltijden
```bash
python -m tools.clean_database          # Voer cleanup uit
python -m tools.clean_database --dry-run  # Preview zonder wijzigingen
```

**seed.py** - Vul database met voorbeelddata
```bash
python -m tools.seed                    # Maakt testdata aan (wist eerst alles!)
```

**breakup_multiday_appointments.py** - Converteer meerdaagse afspraken naar dagelijkse reeksen
```bash
python -m tools.breakup_multiday_appointments  # Voer conversie uit
python -m tools.breakup_multiday_appointments --dry-run  # Preview conversie
```

### Backup

**run_nightly_backup_once.py** - Maak handmatig een backup
```bash
python -m tools.run_nightly_backup_once  # Creëert backups/DDMMYYYY.json
```
> De app maakt automatisch elke nacht om 00:00 een backup via `app/backup_scheduler.py`.

### Foto's

**generate_missing_thumbnails.py** - Genereer ontbrekende thumbnails
```bash
python -m tools.generate_missing_thumbnails  # Maakt thumbnails (200px) voor bestaande foto's
```

### Cozi integratie

> **Configuratie**: Stel `COZI_ICS_URL` in `.env` in met je private Cozi ICS feed URL, of gebruik `--url` argument.

**cozi_import_advisor.py** - Analyseer Cozi ICS feed zonder te importeren
```bash
python -m tools.cozi_import_advisor           # Gebruik COZI_ICS_URL uit .env
python -m tools.cozi_import_advisor --url "https://..."  # Gebruik aangepaste ICS URL
python -m tools.cozi_import_advisor --today   # Filter alleen vandaag
```

**cozi_importer.py** - Importeer events vanuit Cozi ICS feed
```bash
python -m tools.cozi_importer                 # Gebruik COZI_ICS_URL uit .env
python -m tools.cozi_importer --dry-run       # Preview zonder wijzigingen
python -m tools.cozi_importer --today         # Importeer alleen vandaag
```
> Detecteert automatisch maaltijden (18:00-20:00) en gezinsleden in event-titels. Meerdaagse all-day events worden automatisch omgezet naar dagelijkse series.

### Beveiliging

**hash_password.py** - Genereer bcrypt hash voor wachtwoord
```bash
python -m tools.hash_password                 # Interactief (vraagt wachtwoord)
python -m tools.hash_password mijnwachtwoord  # Direct als argument
```
> Gebruik de output in `APP_PASSWORD` in `.env`.

## Docker

FamiliePlanner draait ook via Docker en Docker Compose.

Snelle start:
```bash
cp .env.example .env
docker-compose up -d
```

Standaard URL: **http://localhost:8002**

Zie volledige handleiding: [docs/README.docker.md](docs/README.docker.md)

## Database

Het databaseschema en relaties staan in: [docs/database.md](docs/database.md)

## 🆕 Recent Updates

### v1.4.0 - PWA Implementation (March 2026)
- ✅ Progressive Web App met offline support
- ✅ Installeerbaar als native app (Android, iOS, Desktop)
- ✅ Service Worker met intelligente caching
- ✅ App shortcuts voor snelle toegang
- ✅ Custom install prompt met smart dismissal
- ✅ Safe-area support voor notched devices

### v1.3.0 - Form Controller Refactoring (March 2026)
- ✅ Gedeelde form controllers voor events en taken
- ✅ Recurrence UI controller voor herhalings-logica
- ✅ ~700 regels code duplicatie geëlimineerd (95% reductie)
- ✅ Consistent gedrag over alle formulieren
- ✅ Simplified mode voor dashboard quick-add

### v1.2.0 - UI Improvements (March 2026)
- ✅ Maandweergave met gelijkmatige kolom-breedtes
- ✅ Foto modal met correcte aspect ratio
- ✅ Maximale weergave-grootte voor foto's

## 🧪 Kwaliteit & Testing

**Pre-commit checks:**
```bash
ruff check . --fix && black . && mypy app/ --ignore-missing-imports && pytest tests/ -v
```

**Test coverage:**
- ~106 tests (pytest + pytest-asyncio)
- Backend API tests (agenda, tasks, meals, family, photos, search, stats)
- Error handling tests
- Recurrence logic tests
- Settings tests

**CI/CD Pipeline (GitHub Actions):**
- ✅ Ruff linting
- ✅ Black formatting check
- ✅ Mypy type checking
- ✅ Pytest test suite
- ✅ Commitlint (conventional commits)

**Code quality tools:**
- **Ruff** - Fast Python linter (line length 120)
- **Black** - Code formatter
- **Mypy** - Static type checker (strict imports)
- **Pytest** - Testing framework met async support
## 🏗️ Architectuur

### Request Flow
```
Request → SessionMiddleware → CSRFMiddleware → AuthMiddleware →
SlowAPIMiddleware (rate limiting) → PrometheusMiddleware (metrics) →
FastAPI router → Pydantic validation → SQLAlchemy ORM → SQLite
```

### Database Schema
- **One-to-Many**: FamilyMember → Events/Tasks/Meals
- **Many-to-Many**: Events ↔ Members, Tasks ↔ Members (junction tables)
- **Recurring Series**: Separate tables for rules (RecurrenceSeries, TaskRecurrenceSeries)
- **Exception Handling**: `is_exception` flag voor individuele series-wijzigingen

Volledige schema documentatie: [docs/database.md](docs/database.md)

### Frontend Architecture
- **No build tools** - Pure HTML/CSS/JS met Jinja2 templates
- **Module pattern** - IIFE's per page (agenda.js, tasks.js, etc.)
- **Shared controllers** - Form controllers in `form-controllers/` directory
- **Global utilities** - `window.FP` object met helpers (date/time, members, UI)
- **Service Worker** - Offline-first caching strategy

## 🗺️ Roadmap

### Planned Features (by Priority)

#### High Priority
- [ ] **Task Priorities & Dependencies** - Priority levels (low/med/high/urgent), task dependencies
- [ ] **Grocery List from Meals** - Auto-generate shopping list from weekly meal plan
- [ ] **Notification System** - Email/push notifications for reminders and daily digest

#### Medium Priority
- [ ] **Advanced Search Filters** - Date range, member, type, status filters with pagination
- [ ] **Background Sync** - Queue offline changes, auto-sync when online
- [ ] **Share Functionality** - Share photos/events from other apps to FamiliePlanner

#### Low Priority
- [ ] **Push Notifications** - Browser push for upcoming events/tasks
- [ ] **Periodic Background Sync** - Auto-refresh data while app closed
- [ ] **Multi-language Support** - i18n framework for translations

### Recently Completed ✅
- PWA implementation with offline support (v1.4.0)
- Form controller refactoring (v1.3.0)
- Global search across modules (v1.2.0)
- Statistics dashboard (v1.2.0)
- Recurring series for events & tasks (v1.0.0)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code style (ruff, black, mypy)
4. Write tests for new features
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`, etc.)
6. Open a Pull Request

**Before submitting:**
```bash
# Run all quality checks
ruff check . --fix
black .
mypy app/ --ignore-missing-imports
pytest tests/ -v
```

## 📄 License

Dit is een privéproject voor persoonlijk gebruik. Geen specifieke licentie.

## 🙏 Acknowledgments

- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - Excellent ORM with async support
- **Loguru** - Best-in-class Python logging
- **Ruff** - Blazingly fast linter
- **Claude Sonnet 4.5** - AI pair programming assistant

---

**Gemaakt met ❤️ voor efficiënte gezinsorganisatie**
