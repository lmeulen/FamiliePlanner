# Database Schema

FamiliePlanner gebruikt SQLite met SQLAlchemy ORM. Foreign key constraints zijn ingeschakeld.

## Kernentiteiten

### `family_members`
```sql
id              INTEGER PRIMARY KEY
name            VARCHAR(50) NOT NULL
color           VARCHAR(7) DEFAULT '#4ECDC4'
avatar          VARCHAR(10) DEFAULT '👤'
```

### `app_settings`
```sql
key             VARCHAR(100) PRIMARY KEY
value           TEXT NOT NULL DEFAULT ''
```

## Agenda / Kalender

### `agenda_events`
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

### `recurrence_series`
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

### `agenda_event_members` (many-to-many)
```sql
event_id        INTEGER → agenda_events.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (event_id, member_id)
```

### `recurrence_series_members` (many-to-many)
```sql
series_id       INTEGER → recurrence_series.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (series_id, member_id)
```

## Taken

### `task_lists`
```sql
id              INTEGER PRIMARY KEY
name            VARCHAR(100) NOT NULL
color           VARCHAR(7) DEFAULT '#4ECDC4'
sort_order      INTEGER NOT NULL DEFAULT 0
created_at      DATETIME DEFAULT NOW()
```

### `tasks`
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

### `task_recurrence_series`
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

### `task_members` (many-to-many)
```sql
task_id         INTEGER → tasks.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (task_id, member_id)
```

### `task_recurrence_series_members` (many-to-many)
```sql
series_id       INTEGER → task_recurrence_series.id (ON DELETE CASCADE)
member_id       INTEGER → family_members.id (ON DELETE CASCADE)
PRIMARY KEY (series_id, member_id)
```

## Maaltijden

### `meals`
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

## Foto's

### `photos`
```sql
id              INTEGER PRIMARY KEY
filename        VARCHAR(255) UNIQUE NOT NULL
display_name    VARCHAR(200) NULL
uploaded_at     DATETIME DEFAULT NOW()
```

## Relaties Overzicht

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

## Indexes

- `agenda_events.start_time`
- `agenda_events.series_id`
- `tasks.done`
- `tasks.due_date`
- `tasks.list_id`
- `tasks.series_id`
- `task_recurrence_series.list_id`
- `meals.date`
- `meals.cook_member_id`
