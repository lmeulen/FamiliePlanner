# One-way sync: FamiliePlanner → Google Calendar

Implementation plan for mirroring FamiliePlanner agenda events into a dedicated Google Calendar.
Outbound only: events created or changed in FamiliePlanner are pushed to Google. Nothing is ever
imported back from Google.

---

## 1. Design principles

| Principle | Decision |
|---|---|
| Direction | Strictly outbound. Google is a read-only mirror. Nothing is ever imported back. |
| Source of truth | FamiliePlanner SQLite DB. On conflict, FamiliePlanner always wins (overwrite the Google event). |
| Identity | Every pushed item carries a FamiliePlanner ID. Stored **twice**: in `extendedProperties.private` (machine-readable, queryable) and as a visible footer line in the description (human-readable, and a recovery path if the mapping table is ever lost). |
| Coupling | Sync must never break the app. All pushes go through an async outbox queue + background worker, exactly like the existing `cozi_scheduler.py` pattern. A failing Google API never fails a user's POST. |
| Idempotency | A content hash per item prevents pointless API calls and makes a full reconciliation pass cheap. |

---

## 2. Authentication

**Recommended: Google Service Account.**

1. Create a GCP project, enable the Google Calendar API, create a service account, download the JSON key.
2. In Google Calendar (personal account), create a dedicated calendar, e.g. *"Familie (FamiliePlanner)"*.
3. Share that calendar with the service account's email address, permission **"Make changes to events"**.
4. Copy the calendar ID (`...@group.calendar.google.com`) into FamiliePlanner settings.

Why not OAuth: no consent screen, no refresh-token expiry (test-mode OAuth refresh tokens expire after
7 days), no browser round-trip on a headless self-hosted box. Downside: events show as created by the
service account — irrelevant for a mirror calendar.

**Secret handling:** the JSON key goes on disk (`data/google_service_account.json`, gitignored, `600`),
path referenced by env var `GOOGLE_SERVICE_ACCOUNT_FILE`. Do **not** put the private key in the
`app_settings` table — that table is dumped verbatim into the nightly `backups/DDMMYYYY.json` files.
The settings UI shows only a redacted "configured / not configured" status.

New settings keys (in `app/routers/settings.py::ALLOWED_KEYS`):

```text
google_sync_enabled          "true" | "false"
google_calendar_id           "abc...@group.calendar.google.com"
google_sync_member_colors    JSON: {"1": 7, "2": 11, ...}  (member_id → Google colorId)
google_sync_title_avatars    "true" | "false"
google_sync_past_window_days "30"    (how far back to mirror on backfill)
```

The existing `timezone` setting (default `UTC`) becomes load-bearing — see §5.

---

## 3. Data model

One new migration adding two tables (`batch_alter_table` for SQLite, per project convention).

```python
class GoogleSyncLink(Base):
    __tablename__ = "google_sync_links"

    id: int                     # PK
    entity_type: str            # "event" | "series" | "instance_override"
    entity_key: str             # see below — stable natural key, not a churning row id
    google_event_id: str        # Google's event id
    google_calendar_id: str     # so a calendar-id change invalidates cleanly
    content_hash: str           # sha256 of the canonical payload
    recurring_event_id: str | None   # parent id, for instance overrides
    original_start: str | None       # RFC3339 / date of the original occurrence
    last_synced_at: datetime
    last_error: str | None
    __table_args__ = (UniqueConstraint("entity_type", "entity_key"),)
```

**`entity_key` is deliberately not the row PK.** Critical gotcha in this codebase: updating a
recurrence series *deletes and recreates* all non-exception occurrences (`CLAUDE.md` gotcha #1), so
`agenda_events.id` churns.

| entity_type | entity_key | Notes |
|---|---|---|
| `event` | `event:{id}` | Standalone events only (`series_id IS NULL`) — these are stable. |
| `series` | `series:{id}` | Maps to one native Google recurring event. |
| `instance_override` | `series:{sid}:{YYYY-MM-DD}` | Keyed by occurrence date, survives regeneration. |

Outbox table:

```python
class GoogleSyncQueue(Base):
    __tablename__ = "google_sync_queue"
    id: int
    entity_type: str
    entity_key: str
    operation: str        # "upsert" | "delete"
    attempts: int
    next_attempt_at: datetime
    last_error: str | None
    created_at: datetime
```

Enqueue is `INSERT OR REPLACE` on `(entity_type, entity_key)` — the queue collapses rapid edits of the
same item into one pending job.

---

## 4. Single events

Straightforward 1:1 mapping.

```json
{
  "summary": "👦🧒 Voetbaltraining",
  "description": "Meenemen: scheenbeschermers\n\n—\nFamiliePlanner · Sam, Noor\nfp-id: event:412",
  "location": "Sportpark De Hoge Bomen",
  "start":  {"dateTime": "2026-08-25T18:30:00", "timeZone": "Europe/Amsterdam"},
  "end":    {"dateTime": "2026-08-25T20:00:00", "timeZone": "Europe/Amsterdam"},
  "colorId": "7",
  "reminders": {"useDefault": false, "overrides": []},
  "transparency": "transparent",
  "guestsCanModify": false,
  "extendedProperties": {
    "private": {
      "fp_id": "event:412",
      "fp_type": "event",
      "fp_members": "1,3",
      "fp_hash": "9c1a…"
    }
  }
}
```

Notes:

- `reminders.overrides: []` — the mirror should never nag you twice. Make it a setting if you want
  notifications from Google instead of the app.
- `transparency: "transparent"` (Free) so the mirror doesn't wreck your work availability. Configurable.
- Create → `events.insert`. Update → `events.patch` (not `update`; patch is tolerant of fields Google
  added). Delete → `events.delete`, treating **404/410 as success**.

---

## 5. Time zones (the part most likely to bite)

FamiliePlanner stores **naive datetimes that are actually local wall-clock time** (`CLAUDE.md`:
"Backend stores UTC-naive datetime — all times treated as local, no TZ conversion").

So: **never** append `Z` and never call `astimezone`. Send the naive value verbatim as the `dateTime`
string, with `timeZone` set to the configured IANA zone:

```python
{"dateTime": dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": settings.timezone}
```

Google then resolves DST correctly, including for recurring events crossing the March/October
transitions — which is exactly why RRULE-based recurrence (§7) is safer than pushing pre-computed UTC
instants.

Consequence: the `timezone` setting must be validated as a real IANA zone (it already is, via
`available_timezones()`) and must not be left at `UTC` if you live in NL. Add a settings-page warning
when `google_sync_enabled=true` and `timezone == "UTC"`.

---

## 6. All-day events

FamiliePlanner all-day events store `00:00:00` → `23:59:59` on the same date with `all_day=True`.
Google uses **date-only fields with an exclusive end**:

```json
"start": {"date": "2026-08-25"},
"end":   {"date": "2026-08-26"}
```

So `end.date = start.date + 1 day`. Getting this wrong is the classic "event shows one day short / one
day long" bug — worth a dedicated unit test.

Multi-day all-day events don't need special handling: this app already converts them into a daily
recurring series on creation (gotcha #10). That means a 3-day holiday arrives in Google as a
3-instance daily recurring all-day event rather than one banner spanning three days.

**Optional refinement (recommended, phase 5):** detect a daily series where every occurrence is all-day
and contiguous, and collapse it back into a single Google event with `start.date = first` /
`end.date = last + 1`. Google renders that as one continuous banner across the week — much nicer for
holidays. Guard it behind a setting; skip the collapse if the series has exceptions.

---

## 7. Recurring events

**Push the series as a native Google recurring event with an RRULE — do not push occurrences
individually.**

Rationale: infinite series generate occurrences up to `today + 365 days` and the scheduler keeps
extending that rolling window. Pushing per-occurrence would mean ~365 events per daily series, and a
full re-push every time the window rolls or the series is edited. A native recurring event is a
*single* API object.

### 7.1 Mapping

`app/utils/recurrence.py` already builds `dateutil.rrule` objects from `RecurrenceType` + `interval` +
`monthly_pattern`, and `RecurrenceSeries.rrule` can hold a raw RFC 5545 string. Add a sibling function
`build_rrule_string(series) -> str` that emits the RRULE text instead of the rule object. Same switch,
different output:

| RecurrenceType | RRULE |
|---|---|
| `daily` | `RRULE:FREQ=DAILY;INTERVAL={interval}` |
| `every_other_day` | `RRULE:FREQ=DAILY;INTERVAL=2` |
| `weekly` | `RRULE:FREQ=WEEKLY;INTERVAL={interval}` |
| `biweekly` | `RRULE:FREQ=WEEKLY;INTERVAL=2` |
| `weekdays` | `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` |
| `monthly` | `RRULE:FREQ=MONTHLY;INTERVAL={interval}` (+ `BYDAY=2TU` from `monthly_pattern`) |
| `yearly` | `RRULE:FREQ=YEARLY;INTERVAL={interval}` |

End condition:

- `series_end` set → `;UNTIL=YYYYMMDDT235959Z` (UNTIL must be UTC when DTSTART has a timeZone —
  convert the local end-of-day to UTC here, this is the one place you *do* convert).
- `count` set → `;COUNT=n`.
- Infinite (`series_end=None, count=None`) → **omit both**. Google happily stores a truly infinite
  recurrence. This is a genuine win: the rolling-window regeneration becomes a purely local concern and
  never touches Google again.

Event body uses `start`/`end` derived from `series_start` + `start_time_of_day` / `end_time_of_day`,
plus `"recurrence": ["RRULE:..."]`.

### 7.2 Exceptions

When a local occurrence has `is_exception=True`, patch that single Google instance:

1. `events.instances(calendarId, eventId=<parent google id>, timeMin=…, timeMax=…)` around the
   occurrence date, or list once and cache.
2. Find the instance whose `originalStartTime` matches the occurrence's original date.
3. `events.patch` that instance id with the modified fields.
4. Record it as an `instance_override` link keyed `series:{sid}:{date}`.

Deleted occurrences (local row missing where the RRULE says one should exist) → `events.delete` on the
instance, which Google records as a cancelled instance (`EXDATE`), leaving the rest intact.

### 7.3 Series edits

When a series is updated, patch the parent event's `recurrence`, `summary`, `start`/`end`. Google keeps
existing instance overrides where it can. Because local regeneration wipes and recreates non-exception
rows, do **not** try to diff instances by id — reconcile by date, using the `instance_override` links.

### 7.4 Safety valve

If RRULE construction fails, or the series has more exceptions than a threshold (say >25% of
occurrences), fall back to **expanded mode**: delete the parent recurring event and push occurrences as
individual events keyed `series:{sid}:{date}`, capped at the `today ± window` range. Log a warning.
This keeps weird series correct at the cost of more API calls.

---

## 8. Colours = who the event is for

Google Calendar allows only **11 fixed per-event colours**. FamiliePlanner members have free-form hex
colours, so a mapping is required.

| colorId | Name | Hex |
|---|---|---|
| 1 | Lavender | `#7986cb` |
| 2 | Sage | `#33b679` |
| 3 | Grape | `#8e24aa` |
| 4 | Flamingo | `#e67c73` |
| 5 | Banana | `#f6bf26` |
| 6 | Tangerine | `#f4511e` |
| 7 | Peacock | `#039be5` |
| 8 | Graphite | `#616161` |
| 9 | Blueberry | `#3f51b5` |
| 10 | Basil | `#0b8043` |
| 11 | Tomato | `#d50000` |

**Assignment:** on first sync, auto-assign each member the nearest Google colour by CIE76 ΔE in Lab
space (better perceptual match than raw RGB distance), greedily, ensuring no two members get the same
colorId while members ≤ 11. Persist the result in `google_sync_member_colors` so the mapping is
**stable** and user-overridable — add a small colour-picker grid on the settings page showing
member → Google swatch.

**Multi-member events** (the m2m case) are the interesting bit. Since Google supports exactly one
colour per event:

- `colorId` = the colour of the **primary member** = lowest `family_members.id` among assigned members
  (deterministic, stable).
- Full membership is conveyed by prefixing the title with the members' **emoji avatars** — `avatar`
  already exists on `FamilyMember`. `"👦🧒 Voetbaltraining"`. This is what actually makes the calendar
  readable at a glance, because Google's month view shows the title but the colour is only a small dot.
- Events with **no members** → `colorId` from a configurable "family/everyone" default
  (suggest `8` Graphite).
- Events for **all members** → optionally a dedicated "family" colour instead of the primary member's,
  so household-wide events stand out.
- Full member names go in the description footer.

Both the avatar prefix and colouring are toggleable (`google_sync_title_avatars`), because emoji in
titles is a taste thing.

> **Alternative worth knowing:** one Google sub-calendar per family member gives true multi-colour and
> per-person show/hide toggles in the Google UI. It costs N API writes per multi-member event and N
> mapping rows. Starting single-calendar is recommended; the `GoogleSyncLink` schema already carries
> `google_calendar_id`, so a later move to multi-calendar is additive, not a rewrite.

---

## 9. What it looks like when you open Google Calendar

**Month view** — each day cell lists events in time order. All-day items (holidays, "Vrij", multi-day
trips) sit as solid colour bars at the top of the day cell; timed items appear beneath as a coloured dot
+ time + title. Because titles are prefixed with avatars you get rows like:

```text
ma 24        di 25                 wo 26
             ▌ 👨‍👩‍👧‍👦 Vakantie ─────────────────────▶
● 08:15 🧒 Zwemles     ● 18:30 👦🧒 Voetbaltraining
● 19:00 👩 Yoga        ● 20:00 👨 Werkoverleg
```

Colour tells you *whose* it primarily is (Noor = Peacock blue, Sam = Tomato red, Mama = Basil green,
Papa = Blueberry); the avatar prefix tells you *everyone* involved.

**Week / day view** — timed events render as coloured blocks in the member's colour. All-day events sit
in the strip above the grid. Because `transparency` is `transparent`, these blocks won't mark you Busy
in free/busy lookups, so a work calendar overlay stays clean.

**Recurring events** carry Google's ↻ loop glyph in the event detail pane, and Google shows "Weekly on
Tuesday" / "Every 2 weeks" natively — because we push real RRULEs, not 52 copies. Editing one instance
in Google shows the usual "This event / All events" prompt (you shouldn't edit there, but nothing
breaks — the next reconciliation pass restores FamiliePlanner's version).

**Clicking an event** shows:

```text
👦🧒 Voetbaltraining
Tuesday, 25 August ⋅ 18:30 – 20:00
Sportpark De Hoge Bomen        ← tappable, opens Maps
Weekly on Tuesday

Meenemen: scheenbeschermers

—
FamiliePlanner · Sam, Noor
https://familieplanner.local/agenda?event=412
fp-id: event:412
```

The URL is a deep link back into the agenda (add a `?event=` query param handler in `agenda.js` to open
the event form). This makes the mirror actionable from your phone: see it in Google, tap through to edit
in FamiliePlanner.

**On mobile** the calendar appears as a normal toggleable calendar in the Google Calendar app sidebar,
syncs to the iOS/Android system calendar, feeds Google Assistant ("what's on tomorrow"), and appears on
Wear OS / smart displays. That's really the payoff of mirroring into Google rather than exposing an ICS
feed.

---

## 10. Sync engine

```text
Router (create/update/delete)
      └─► enqueue(entity_type, entity_key, op)      ← cheap INSERT, same transaction
                    │
      background worker (google_calendar_scheduler.py)
                    │
      ┌─────────────┴─────────────┐
      │ claim due jobs (batch 50) │
      │ build payload             │
      │ compare content_hash      │──► unchanged → mark done, 0 API calls
      │ insert / patch / delete   │
      │ update GoogleSyncLink     │
      │ on failure → backoff      │
      └───────────────────────────┘
```

**Enqueue points** — in `app/routers/agenda.py`: `create_event`, `update_event`, `delete_event`,
`create_series`, `update_series`, `delete_series`. Also `app/services/cozi_sync.py` (so Cozi-imported
events propagate) and `app/recurrence_scheduler.py` (rolling-window regeneration — though with infinite
RRULEs this mostly becomes a no-op, which is the point).

Rather than sprinkling calls, use a thin helper
`app/services/google_sync.py::enqueue_event(db, event)` / `enqueue_series(db, series)`, called
explicitly. Avoid SQLAlchemy `after_flush` event hooks here — they'd fire during the series
delete-and-recreate churn and generate huge queue noise.

**Worker cadence:** every 60 s (near-real-time enough, tiny cost), plus a **nightly full reconciliation**
at ~01:00 (after the existing midnight backup) that walks all events/series in the window, recomputes
hashes, pushes drift, and deletes orphaned Google events whose `fp_id` no longer resolves locally.
Orphan detection uses `events.list(privateExtendedProperty="fp_type=event")` — that's exactly why the ID
lives in extended properties as well as the description.

**Retries:** exponential backoff `2^attempts` minutes, capped at 6 h, max 10 attempts then park with
`last_error` surfaced in the settings UI. Respect `403 rateLimitExceeded` / `429` with `Retry-After`.
Use `batch` requests when >5 operations are pending to stay well inside quota (default 1M queries/day —
you will never come close).

**Library:** `google-api-python-client` + `google-auth` are sync-only. Two clean options — (a) run calls
in `asyncio.to_thread`, or (b) skip the SDK and call the REST API with `httpx.AsyncClient`, minting the
service-account JWT with `google-auth` (`google.oauth2.service_account.Credentials` + manual refresh).
Pick **(a)** for phase 1: less code, well-trodden, and the worker is off the request path anyway so
blocking a thread is harmless.

**Kill switch:** `google_sync_enabled=false` stops the worker and leaves existing Google events
untouched. A separate explicit "Remove all synced events from Google" button in settings performs the
destructive teardown, with a confirm dialog.

---

## 11. Files

```text
app/models/google_sync.py                    GoogleSyncLink, GoogleSyncQueue
app/services/google_calendar.py              thin API client (auth, insert/patch/delete/list/instances)
app/services/google_sync.py                  payload building, hashing, enqueue, process_queue, reconcile
app/utils/google_colors.py                   hex → colorId nearest-match (Lab ΔE), stable assignment
app/google_calendar_scheduler.py             background worker (mirrors cozi_scheduler.py)
app/routers/google_sync.py                   POST /api/google/test, /backfill, /reconcile; GET /status
alembic/versions/xxxx_add_google_sync.py     batch_alter_table migration
tools/google_calendar_sync.py                --backfill / --reconcile / --purge / --dry-run
tests/test_google_sync_payload.py            pure payload/hash/colour tests, no network
tests/test_google_sync_queue.py              enqueue/dedupe/backoff with a fake client
```

Plus edits to:

- `app/main.py` — register the worker in the lifespan context manager
- `app/routers/settings.py` — new keys + validation
- `app/templates/settings.html` + `app/static/js/settings.js` — config panel, member-colour grid,
  status / last-error display
- `app/routers/agenda.py` — enqueue calls
- `app/static/js/agenda.js` — `?event=` deep-link handler
- `requirements.txt` — `google-api-python-client`, `google-auth`

---

## 12. Testing

The payload builder must be a **pure function** of `(event|series, members, settings)` → dict. That
makes the valuable tests network-free:

- All-day end-date is exclusive (`+1 day`) — single day and multi-day.
- Naive local datetime is emitted verbatim with the configured `timeZone`, never UTC-shifted.
- RRULE string for each of the 7 `RecurrenceType` values, × each end condition (until / count /
  infinite).
- `UNTIL` is UTC-normalised while `DTSTART` stays local.
- Colour: deterministic member→colorId assignment; multi-member picks lowest member id; no-member
  fallback.
- Hash stability: same input → same hash; any field change → different hash.
- Queue: repeated enqueues of one key collapse to one row; backoff schedule; 404 on delete counted as
  success.

Integration tests use a fake `GoogleCalendarClient` recording calls. One optional
`@pytest.mark.integration` test hits a real throwaway calendar, skipped unless credentials are present.

---

## 13. Phasing

| Phase | Scope | Outcome |
|---|---|---|
| 1 | Auth, settings, models/migration, client, payload builder, single non-recurring timed + all-day events, queue + worker, backfill tool | Standalone events mirrored correctly |
| 2 | Colours + avatar prefixes + description footer + deep link | Calendar becomes readable at a glance |
| 3 | Recurring series via RRULE, instance overrides, cancelled instances, expanded-mode fallback | Full coverage |
| 4 | Nightly reconciliation, orphan cleanup, settings status panel with last-error + "sync now", purge button | Self-healing |
| 5 | Optional: contiguous all-day series collapsed into single banners; optional per-member sub-calendars | Polish |

---

## 14. Risks

1. **Time zone drift** — the biggest one. The `timezone` setting currently defaults to `UTC` and is
   barely used; sync makes it critical. Mitigation: settings warning + explicit tests.
2. **Series regeneration churn** — mitigated by keying on `(series_id, date)` rather than row ids, and
   by infinite RRULEs removing the rolling-window pressure entirely.
3. **Manual edits in Google** — silently overwritten by reconciliation. Document it; the calendar is a
   mirror, not a workspace. Consider `guestsCanModify: false` and a note in the description footer.
4. **Colour exhaustion** — >11 family members means duplicates. Detect and warn in the settings UI;
   avatar prefixes still disambiguate.
5. **Secret exposure via backups** — solved by keeping the key file out of `app_settings`; verify the
   nightly backup export doesn't pick up the new tables' error strings verbatim either.
6. **Deleting the wrong events** — orphan cleanup must only ever touch events carrying a matching
   `fp_id` extended property *and* the configured calendar id. Never a blind "delete everything in
   range". Ship it behind `--dry-run` first.
