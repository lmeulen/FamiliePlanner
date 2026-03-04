# 🏠 FamiliePlanner

Een responsive gezinsplanner webapp gebouwd met FastAPI + Uvicorn (backend) en vanilla HTML/CSS/JS (frontend). Geen npm of andere package managers nodig.

## Functionaliteiten

| Module | Beschrijving |
|--------|-------------|
| **Overzicht** | Startpagina met agenda-items van vandaag, maaltijden en taken |
| **Agenda** | Week / maand / lijstweergave, CRUD afspraken, filter op gezinslid |
| **Taken** | Meerdere takenlijsten, toewijzen aan gezinslid, vervaldatum, afvinken |
| **Maaltijden** | Weekplanner met ontbijt / lunch / diner / tussendoor, recept-URL |
| **Gezin** | 5 gezinsleden met naam, kleur en emoji-avatar – volledig aanpasbaar |
| **Thema** | Licht en donker thema (automatisch op basis van systeemvoorkeur + handmatig) |

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

## Uitbreidingstips

- **Authenticatie** – voeg FastAPI `HTTPBasicCredentials` of JWT toe in `app/main.py`
- **Push-notificaties** – integreer Web Push API via `pywebpush`
- **Google Calendar sync** – gebruik `google-auth` + Calendar API in een nieuwe router
- **Boodschappenlijst** – voeg `models/shopping.py` + `routers/shopping.py` toe (zelfde patroon als taken)
- **Herhaalde afspraken** – voeg `recurrence_rule` veld toe aan `AgendaEvent`
- **Meerdere huishoudens** – voeg `household_id` toe aan alle modellen + authenticatie
