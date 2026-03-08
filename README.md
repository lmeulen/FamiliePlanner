# 🏠 FamiliePlanner

Een responsive gezinsplanner webapp gebouwd met FastAPI + Uvicorn (backend) en vanilla HTML/CSS/JS (frontend). Geen npm of andere package managers nodig.

## Functionaliteiten

| Module | Beschrijving |
|--------|-------------|
| **Overzicht** | Startpagina met fotodiashow, agenda-items van vandaag, maaltijden en taken |
| **Agenda** | Week / maand / lijstweergave, herhaalde afspraken (dagelijks t/m maandelijks), filter op gezinslid |
| **Taken** | Meerdere takenlijsten met instelbare volgorde, herhaalde taken, toewijzen aan gezinslid, vervaldatum, afvinken |
| **Maaltijden** | Weekplanner met ontbijt / lunch / diner / tussendoor, kok en recept-URL |
| **Gezin** | Gezinsleden met naam, kleur en emoji-avatar |
| **Foto's** | Upload gezinsfoto's; diashow op de overzichtspagina |
| **Instellingen** | Thema (licht/donker/systeem), fotogrootte, authenticatie in-/uitschakelen |

## Vereisten

- Python 3.11+
- Linux / Windows / macOS

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
python seed.py

# 6. Start de server
python run.py --host 0.0.0.0 --port 8000
```

Open in de browser: **http://\<server-ip\>:8000**

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

## Projectstructuur

```
FamiliePlanner/
├── app/
│   ├── main.py              # FastAPI app, middleware, routes, exception handlers
│   ├── auth.py              # Authenticatie middleware + login/logout
│   ├── config.py            # Omgevingsvariabelen
│   ├── database.py          # SQLAlchemy async engine
│   ├── enums.py             # MealType en RecurrenceType
│   ├── logging_config.py    # Loguru configuratie
│   ├── models/              # SQLAlchemy ORM modellen
│   ├── schemas/             # Pydantic schema's
│   ├── routers/             # REST API endpoints
│   ├── utils/               # Gedeelde helpers (recurrence, db)
│   ├── static/css/          # themes.css + main.css
│   ├── static/js/           # api.js, app.js, per-pagina JS
│   └── templates/           # Jinja2 HTML templates
├── alembic/versions/        # Databasemigraties
├── tests/                   # Pytest testsuite (~73 tests)
├── logs/                    # Dagelijks roterend logbestand (7 dagen)
├── seed.py                  # Voorbeelddata
├── run.py                   # Uvicorn startscript
└── .env.example             # Sjabloon omgevingsvariabelen
```

## API

Interactieve documentatie: **http://\<server\>:8000/api/docs**

| Endpoint | Beschrijving |
|----------|-------------|
| `GET/POST /api/agenda/` | Afspraken |
| `GET/POST /api/agenda/series` | Herhaalde afspraken |
| `GET/POST /api/tasks/` | Taken |
| `GET/POST /api/tasks/lists` | Takenlijsten |
| `GET/POST /api/meals/` | Maaltijden |
| `GET/POST /api/family/` | Gezinsleden |
| `GET/POST /api/photos/` | Foto's |
| `GET/PUT  /api/settings/` | Instellingen |

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
> Detecteert automatisch maaltijden (18:00-20:00) en gezinsleden in event-titels.

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
