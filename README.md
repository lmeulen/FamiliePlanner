# 🏠 FamiliePlanner

Een responsive gezinsplanner webapp gebouwd met FastAPI + Uvicorn (backend) en vanilla HTML/CSS/JS (frontend). Geen npm of andere package managers nodig.

## Functionaliteiten

| Module | Beschrijving |
|--------|-------------|
| **Overzicht** | Startpagina met fotodiashow, agenda-items van vandaag, maaltijden en taken |
| **Agenda** | Week / maand / lijstweergave, herhaalde afspraken (dagelijks t/m maandelijks), filter op gezinslid |
| **Taken** | Meerdere takenlijsten met instelbare volgorde, herhaalde taken, toewijzen aan gezinslid, vervaldatum, afvinken |
| **Maaltijden** | Weekplanner met ontbijt / lunch / diner / tussendoor, kok en recept-URL |
| **Gezin** | Gezinsleden met naam, kleur en emoji-avatar – volledig aanpasbaar |
| **Foto's** | Upload gezinsfoto's; diashow op de overzichtspagina met instelbare grootte |
| **Instellingen** | Licht/donker/systeem thema, fotogrootte, inloggen in-/uitschakelen |
| **Beveiliging** | Optionele sessie-authenticatie met gebruikersnaam en wachtwoord |

## Vereisten

- Python 3.11+
- Linux / Windows / macOS homeserver

## Installatie & starten

```bash
# 1. Kloon of download het project
cd /path/to/FamiliePlanner

# 2. Maak een virtual environment aan (eenmalig)
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.\.venv\Scripts\activate           # Windows

# 3. Installeer afhankelijkheden (eenmalig)
pip install -r requirements.txt

# 4. Kopieer en pas de omgevingsvariabelen aan
cp .env.example .env
# Bewerk .env: stel SECRET_KEY, APP_USERNAME en APP_PASSWORD in

# 5. Seed de database met voorbeelddata (optioneel)
python seed.py

# 6. Start de server
python run.py --host 0.0.0.0 --port 8000
```

Open daarna in de browser: **http://\<server-ip\>:8000**

### Ontwikkelmodus (auto-reload)
```bash
python run.py --host 0.0.0.0 --port 8000 --reload
```

### Productie (systemd service)
Maak `/etc/systemd/system/familieplanner.service`:
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

## Omgevingsvariabelen (`.env`)

Kopieer `.env.example` naar `.env` en pas de waarden aan:

| Variabele | Standaard | Beschrijving |
|-----------|-----------|-------------|
| `SECRET_KEY` | _(willekeurig)_ | Geheime sleutel voor het ondertekenen van sessiecookies |
| `APP_USERNAME` | `admin` | Inlognaam |
| `APP_PASSWORD` | `familieplanner` | Wachtwoord |
| `AUTH_REQUIRED` | `true` | Stel in op `false` om authenticatie uit te schakelen |

> ⚠️ Commit `.env` nooit naar git. Het bestand staat standaard in `.gitignore`.

## Projectstructuur

```
FamiliePlanner/
├── app/
│   ├── main.py              # FastAPI app, middleware, pagina routes, exception handlers
│   ├── auth.py              # Sessie-authenticatie middleware + login/logout
│   ├── config.py            # Omgevingsvariabelen en applicatie-instellingen
│   ├── database.py          # SQLAlchemy async engine + get_db dependency
│   ├── enums.py             # MealType en RecurrenceType enums
│   ├── logging_config.py    # Loguru: dagelijks roterend logbestand in logs/
│   ├── models/              # SQLAlchemy ORM modellen
│   │   ├── family.py        # FamilyMember
│   │   ├── agenda.py        # AgendaEvent, RecurrenceSeries, M2M-tabellen
│   │   ├── tasks.py         # Task, TaskList, TaskRecurrenceSeries, M2M-tabellen
│   │   ├── meals.py         # Meal
│   │   ├── photos.py        # Photo (bestandsmetadata)
│   │   └── settings.py      # AppSetting (sleutel-waarde opslag)
│   ├── schemas/             # Pydantic request/response schema's
│   ├── routers/             # FastAPI routers (REST API)
│   │   ├── family.py        # /api/family
│   │   ├── agenda.py        # /api/agenda + /api/agenda/series
│   │   ├── tasks.py         # /api/tasks + /api/tasks/lists
│   │   ├── meals.py         # /api/meals
│   │   ├── photos.py        # /api/photos (upload/lijst/verwijder)
│   │   └── settings.py      # /api/settings
│   ├── utils/
│   │   ├── recurrence.py    # Gedeelde herhalingspatroon-generator
│   │   └── db.py            # Gedeelde M2M junction helper
│   ├── static/
│   │   ├── css/
│   │   │   ├── themes.css   # CSS custom properties licht/donker
│   │   │   └── main.css     # Layout, componenten, animaties, responsive
│   │   └── js/
│   │       ├── api.js       # Centrale fetch wrapper (401 → login redirect)
│   │       ├── app.js       # Globale FP namespace: helpers, gezinsleden cache
│   │       ├── theme.js     # Thema: toggle + localStorage + cross-tab sync
│   │       ├── modal.js     # Modal/bottom-sheet controller
│   │       ├── toast.js     # Toast-notificaties
│   │       ├── dashboard.js # Overzichtspagina + FAB speed-dial + fotodiashow
│   │       ├── agenda.js    # Kalenderweergaven + herhaling
│   │       ├── tasks.js     # Takenlijsten + lijstbeheer modal
│   │       ├── meals.js     # Weekplanner maaltijden
│   │       ├── family.js    # Gezinsleden beheer
│   │       ├── photos.js    # Foto upload/galerij
│   │       └── settings.js  # Instellingenpagina
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Hoofd-layout, navigatie, modal, scripts
│       ├── login.html       # Inlogpagina (standalone)
│       ├── dashboard.html
│       ├── agenda.html
│       ├── tasks.html
│       ├── meals.html
│       ├── family.html
│       ├── photos.html
│       └── settings.html
├── alembic/                 # Databasemigraties (Alembic)
│   └── versions/            # Migratiebestanden
├── tests/                   # Pytest testsuite (~73 tests)
├── logs/                    # Logbestanden (dagelijks roterend, 7 dagen bewaard)
├── seed.py                  # Voorbeelddata voor ontwikkeling
├── run.py                   # Uvicorn startscript
├── requirements.txt
└── .env.example             # Sjabloon voor omgevingsvariabelen
```

## REST API

Interactieve documentatie beschikbaar op **http://\<server\>:8000/api/docs**

| Endpoint | Beschrijving |
|----------|-------------|
| `GET /api/agenda/today` | Agenda-items van vandaag |
| `GET /api/agenda/week` | Agenda-items komende 7 dagen |
| `GET /api/agenda/series` | Herhaalde afspraken beheren |
| `GET /api/tasks/` | Alle taken (filters: `done`, `due_date`, `list_id`) |
| `GET /api/tasks/today` | Taken met vervaldatum = vandaag |
| `GET /api/tasks/overdue` | Verlopen taken |
| `GET /api/tasks/lists` | Takenlijsten (gesorteerd op volgorde) |
| `GET /api/meals/today` | Maaltijden van vandaag |
| `GET /api/meals/week` | Maaltijden komende 7 dagen |
| `GET /api/family/` | Alle gezinsleden |
| `GET /api/photos/` | Alle foto's |
| `POST /api/photos/` | Foto uploaden (multipart/form-data) |
| `GET /api/settings/` | Huidige instellingen ophalen |
| `PUT /api/settings/` | Instellingen bijwerken |

## Tests uitvoeren

```bash
pytest tests/ -v
```

## Logging

Logbestanden worden per dag aangemaakt in de map `logs/` en automatisch verwijderd na 7 dagen. Het logniveau is standaard `INFO`; aan te passen via de `LOG_LEVEL` omgevingsvariabele.


## Vereisten

- Python 3.11+
- Linux / Windows / macOS homeserver

## Installatie & starten

```bash
# 1. Kloon of download het project
cd /path/to/FamiliePlanner

# 2. Maak een virtual environment aan (eenmalig)
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
.\.venv\Scripts\activate           # Windows

# 3. Installeer afhankelijkheden (eenmalig)
pip install -r requirements.txt

# 4. Seed de database met voorbeelddata (eenmalig)
python seed.py

# 5. Start de server
python run.py --host 0.0.0.0 --port 8000
```

Open daarna in de browser: **http://<server-ip>:8000**

### Ontwikkelmodus (auto-reload)
```bash
python run.py --host 0.0.0.0 --port 8000 --reload
```

### Productie (systemd service)
Maak `/etc/systemd/system/familieplanner.service`:
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

## Projectstructuur

```
FamiliePlanner/
├── app/
│   ├── main.py            # FastAPI app + pagina routes
│   ├── config.py          # Configuratie (gezinsleden standaard, DB URL)
│   ├── database.py        # SQLAlchemy async + init_db()
│   ├── models/            # ORM modellen (SQLAlchemy)
│   │   ├── family.py
│   │   ├── agenda.py
│   │   ├── tasks.py
│   │   └── meals.py
│   ├── schemas/           # Pydantic request/response schema's
│   ├── routers/           # FastAPI routers (REST API)
│   │   ├── family.py      # GET/POST/PUT/DELETE /api/family
│   │   ├── agenda.py      # GET/POST/PUT/DELETE /api/agenda
│   │   ├── tasks.py       # GET/POST/PUT/DELETE /api/tasks + /api/tasks/lists
│   │   └── meals.py       # GET/POST/PUT/DELETE /api/meals
│   ├── static/
│   │   ├── css/
│   │   │   ├── themes.css # CSS custom properties licht/donker
│   │   │   └── main.css   # Layout, componenten, animaties
│   │   └── js/
│   │       ├── api.js     # Centrale fetch wrapper
│   │       ├── app.js     # Gedeelde helpers & gezinsleden cache
│   │       ├── theme.js   # Thema: toggle + localStorage
│   │       ├── modal.js   # Bottom-sheet / modal controller
│   │       ├── toast.js   # Toast-notificaties
│   │       ├── dashboard.js
│   │       ├── agenda.js
│   │       ├── tasks.js
│   │       ├── meals.js
│   │       └── family.js
│   └── templates/         # Jinja2 HTML templates
│       ├── base.html      # Hoofd-layout, navigatie, modal
│       ├── dashboard.html
│       ├── agenda.html
│       ├── tasks.html
│       ├── meals.html
│       └── family.html
├── seed.py                # Eenmalige seed met voorbeelddata
├── run.py                 # Uvicorn startscript
├── requirements.txt
└── familieplanner.db      # SQLite database (aangemaakt bij eerste start)
```

## REST API

Interactieve documentatie beschikbaar op **http://\<server\>:8000/api/docs**

| Endpoint | Beschrijving |
|----------|-------------|
| `GET /api/agenda/today` | Agenda-items van vandaag |
| `GET /api/agenda/week` | Agenda-items komende 7 dagen |
| `GET /api/tasks/today` | Taken met vervaldatum=vandaag |
| `GET /api/meals/today` | Maaltijden van vandaag |
| `GET /api/meals/week` | Maaltijden komende 7 dagen |
| `GET /api/family/` | Alle gezinsleden |
