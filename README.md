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

## Database Schema

FamiliePlanner gebruikt SQLite met SQLAlchemy ORM. Foreign key constraints zijn ingeschakeld.

### Kernentiteiten

#### `family_members`
```sql
id              INTEGER PRIMARY KEY
name            VARCHAR(50) NOT NULL
color           VARCHAR(7) DEFAULT '#4ECDC4'
avatar          VARCHAR(10) DEFAULT '👤'
```

#### `app_settings`
```sql
key             VARCHAR(100) PRIMARY KEY
value           TEXT NOT NULL DEFAULT ''
```

### Agenda / Kalender

#### `agenda_events`
```sql
id              INTEGER PRIMARY KEY
title           VARCHAR(200) NOT NULL
description     TEXT DEFAULT ''
location        VARCHAR(200) DEFAULT ''
start_time      DATETIME NOT NULL [indexed]
end_time        DATETIME NOT NULL
all_day         BOOLEAN DEFAULT FALSE
color           VARCHAR(7) DEFAULT '#4ECDC4'
series_id       INTEGER NULL [indexed] → recurrence_series.id (ON DELETE CASCADE)
is_exception    BOOLEAN DEFAULT FALSE
created_at      DATETIME DEFAULT NOW()
```

#### `recurrence_series`
```sql
id                  INTEGER PRIMARY KEY
title               VARCHAR(200) NOT NULL
description         TEXT DEFAULT ''
location            VARCHAR(200) DEFAULT ''
all_day             BOOLEAN DEFAULT FALSE
color               VARCHAR(7) DEFAULT '#4ECDC4'
recurrence_type     ENUM NOT NULL (daily, every_other_day, weekly, biweekly, weekdays, monthly)
series_start        DATE NOT NULL
series_end          DATE NOT NULL
start_time_of_day   TIME NOT NULL
end_time_of_day     TIME NOT NULL
created_at          DATETIME DEFAULT NOW()
```

#### `agenda_event_members` (many-to-many)
```sql
event_id        INTEGER → agenda_events.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (event_id, member_id)
```

#### `recurrence_series_members` (many-to-many)
```sql
series_id       INTEGER → recurrence_series.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (series_id, member_id)
```

### Taken

#### `task_lists`
```sql
id              INTEGER PRIMARY KEY
name            VARCHAR(100) NOT NULL
color           VARCHAR(7) DEFAULT '#4ECDC4'
sort_order      INTEGER NOT NULL DEFAULT 0
created_at      DATETIME DEFAULT NOW()
```

#### `tasks`
```sql
id              INTEGER PRIMARY KEY
title           VARCHAR(200) NOT NULL
description     TEXT DEFAULT ''
done            BOOLEAN DEFAULT FALSE [indexed]
due_date        DATE NULL [indexed]
list_id         INTEGER NULL [indexed] → task_lists.id (ON DELETE SET NULL)
series_id       INTEGER NULL [indexed] → task_recurrence_series.id (ON DELETE CASCADE)
is_exception    BOOLEAN DEFAULT FALSE
created_at      DATETIME DEFAULT NOW()
```

#### `task_recurrence_series`
```sql
id                  INTEGER PRIMARY KEY
title               VARCHAR(200) NOT NULL
description         TEXT DEFAULT ''
list_id             INTEGER NULL [indexed] → task_lists.id (ON DELETE SET NULL)
recurrence_type     ENUM NOT NULL (daily, every_other_day, weekly, biweekly, weekdays, monthly)
series_start        DATE NOT NULL
series_end          DATE NOT NULL
created_at          DATETIME DEFAULT NOW()
```

#### `task_members` (many-to-many)
```sql
task_id         INTEGER → tasks.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (task_id, member_id)
```

#### `task_recurrence_series_members` (many-to-many)
```sql
series_id       INTEGER → task_recurrence_series.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (series_id, member_id)
```

### Maaltijden

#### `meals`
```sql
id              INTEGER PRIMARY KEY
date            DATE NOT NULL [indexed]
meal_type       ENUM DEFAULT 'dinner' (breakfast, lunch, dinner, snack)
name            VARCHAR(200) NOT NULL
description     TEXT DEFAULT ''
recipe_url      VARCHAR(500) DEFAULT ''
cook_member_id  INTEGER NULL [indexed] → family_members.id (ON DELETE SET NULL)
created_at      DATETIME DEFAULT NOW()
```

### Foto's

#### `photos`
```sql
id              INTEGER PRIMARY KEY
filename        VARCHAR(255) UNIQUE NOT NULL
display_name    VARCHAR(200) NULL
uploaded_at     DATETIME DEFAULT NOW()
```

### Relaties Overzicht

```
family_members
    ├─→ agenda_event_members ←─ agenda_events
    │                               └─→ recurrence_series
    ├─→ recurrence_series_members ←─┘
    │
    ├─→ task_members ←─ tasks
    │                      ├─→ task_lists
    │                      └─→ task_recurrence_series
    ├─→ task_recurrence_series_members ←─┘
    │
    └─→ meals (cook_member_id)
```

### Indexes

- `agenda_events.start_time`
- `agenda_events.series_id`
- `tasks.done`
- `tasks.due_date`
- `tasks.list_id`
- `tasks.series_id`
- `task_recurrence_series.list_id`
- `meals.date`
- `meals.cook_member_id`
