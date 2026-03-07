# Error Handling

FamiliePlanner implementeert verbeterde error handling met gebruiksvriendelijke Nederlandse foutmeldingen.

## Architectuur

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (API.js)                                            │
│ - Detecteert error types (network, HTTP status, API error) │
│ - Formatteert user-friendly messages                        │
│ - Toont details waar beschikbaar                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend Exception Handlers (main.py)                        │
│ - RequestValidationError → 422 (Pydantic validatie)         │
│ - IntegrityError → 422 (Foreign key, unique constraint)     │
│ - SQLAlchemyError → 500 (Database errors)                   │
│ - HTTPException → Status code met Dutch message             │
│ - Exception → 500 (Catch-all met error page)                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Error Response Format (errors.py)                           │
│ {                                                            │
│   "code": "ERROR_CODE",                                      │
│   "message": "Nederlandse gebruikersmelding",                │
│   "details": "Extra details (optioneel)",                    │
│   "field": "veldnaam (voor validatie errors)"                │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Codes

Gedefinieerd in `app/errors.py`:

### Client Errors (4xx)

| Code | Status | Betekenis |
|------|--------|-----------|
| `VALIDATION_ERROR` | 422 | Ongeldige invoer (Pydantic validatie) |
| `NOT_FOUND` | 404 | Resource niet gevonden |
| `UNAUTHORIZED` | 401 | Niet ingelogd |
| `FORBIDDEN` | 403 | Geen toegang |
| `CONFLICT` | 409 | Conflict (bijv. concurrency) |
| `CSRF_ERROR` | 403 | CSRF token mismatch |
| `RATE_LIMIT` | 429 | Te veel requests |

### Server Errors (5xx)

| Code | Status | Betekenis |
|------|--------|-----------|
| `DATABASE_ERROR` | 500 | Database fout |
| `INTERNAL_ERROR` | 500 | Onverwachte server error |

### Business Logic Errors

| Code | Status | Betekenis |
|------|--------|-----------|
| `FOREIGN_KEY_ERROR` | 422 | Verwijzing naar non-existent item |
| `UNIQUE_CONSTRAINT` | 422 | Waarde bestaat al (duplication) |
| `INVALID_REFERENCE` | 422 | Ongeldige referentie |

---

## Error Response Format

**Standaard formaat:**

```json
{
  "code": "VALIDATION_ERROR",
  "message": "De ingevoerde gegevens zijn niet geldig.",
  "details": "Te kort. Minimaal 3 tekens vereist.",
  "field": "name"
}
```

**Velden:**
- `code` (**required**): Error code voor logging/debugging
- `message` (**required**): User-friendly Nederlandse melding
- `details` (*optional*): Extra informatie over de fout
- `field` (*optional*): Veldnaam bij validatie errors

---

## Frontend Error Handling

### API.js Enhanced Error Detection

```javascript
try {
  const data = await API.post('/api/family/', payload);
} catch (error) {
  // error.message: Nederlandse gebruikersmelding
  // error.status: HTTP status code
  // error.code: Error code (bijv. "VALIDATION_ERROR")
  // error.details: Extra details
  // error.field: Veldnaam (bij validatie)

  Toast.show(error.message, 'error');
}
```

### Error Message Formatting

API.js formatteert automatisch:

1. **Nieuwe error format** (code/message/details):
   ```
   "De ingevoerde gegevens zijn niet geldig. (Te kort. Minimaal 3 tekens vereist.) Veld: name"
   ```

2. **Legacy format** (alleen detail):
   ```
   "Referenced resource does not exist (invalid id)."
   ```

3. **Network errors**:
   ```
   "Geen internetverbinding. Controleer je verbinding en probeer opnieuw."
   ```

4. **HTTP status fallbacks**:
   ```
   404 → "Het item kon niet worden gevonden."
   500 → "Er is een serverfout opgetreden. Probeer het later opnieuw."
   429 → "Te veel verzoeken. Wacht even en probeer opnieuw."
   ```

---

## Backend Exception Handlers

### 1. Pydantic Validation Errors

**Handler:** `validation_exception_handler`

```python
{
  "code": "VALIDATION_ERROR",
  "message": "De ingevoerde gegevens zijn niet geldig.",
  "details": "Te kort. Minimaal 3 tekens vereist.",
  "field": "body.name"
}
```

**Vertaalde validatie errors:**
- `string_too_short` → "Te kort. Minimaal {min_length} tekens vereist."
- `value_error.missing` → "Dit veld is verplicht."
- `value_error.email` → "Ongeldig e-mailadres."
- `type_error.integer` → "Voer een geldig getal in."

Zie `app/errors.py::VALIDATION_MESSAGES` voor alle vertalingen.

### 2. Database Integrity Errors

**Handler:** `integrity_error_handler`

**Foreign Key:**
```python
{
  "code": "FOREIGN_KEY_ERROR",
  "message": "Dit item verwijst naar een verwijderd of ongeldig item."
}
```

**Unique Constraint:**
```python
{
  "code": "UNIQUE_CONSTRAINT",
  "message": "Deze waarde bestaat al. Kies een andere waarde."
}
```

### 3. HTTP Exceptions (404, 403, etc.)

**Handler:** `http_exception_handler`

**JSON Response (API):**
```python
{
  "code": "NOT_FOUND",
  "message": "Het gevraagde item kon niet worden gevonden.",
  "details": "Family member not found"  # Original detail
}
```

**HTML Response (Browser):**
Redirect naar `/error.html` met:
- Error code (404, 500)
- Nederlandse titel
- Gebruiksvriendelijke boodschap
- Suggestie voor actie

### 4. Generic Exceptions (500)

**Handler:** `generic_exception_handler`

- Logged met volledige stack trace (server-side)
- User krijgt algemene melding **zonder** stack trace
- HTML error page voor browser requests
- JSON response voor API requests

---

## HTML Error Pages

### 404 Page

**Voorbeeld:**

```
404

Pagina niet gevonden

De pagina die je zoekt bestaat niet of is verplaatst.

💡 Ga terug naar het overzicht of gebruik het menu.

[← Ga terug]  [🏠 Naar overzicht]
```

### 500 Page

```
500

Er is iets misgegaan

Er is een onverwachte fout opgetreden.

💡 Probeer de pagina te vernieuwen. Als het probleem blijft, neem contact op.

[← Ga terug]  [🏠 Naar overzicht]
```

Gedefinieerd in `app/templates/error.html`.

---

## Custom Error Messages

### Toevoegen van nieuwe error codes:

**1. Definieer code in `app/errors.py`:**

```python
class ErrorCode(str, Enum):
    # ...
    CUSTOM_ERROR = "CUSTOM_ERROR"

ERROR_MESSAGES = {
    # ...
    ErrorCode.CUSTOM_ERROR: "Jouw Nederlandse foutmelding hier.",
}
```

**2. Gebruik in routers:**

```python
from app.errors import ErrorCode, ErrorResponse

@router.post("/endpoint")
async def endpoint():
    if some_condition:
        error = ErrorResponse(
            code=ErrorCode.CUSTOM_ERROR,
            message=get_error_message(ErrorCode.CUSTOM_ERROR),
            details="Extra context hier"
        )
        return JSONResponse(
            status_code=400,
            content=error.model_dump(exclude_none=True)
        )
```

---

## Testing Error Handling

**File:** `tests/test_error_handling.py`

### Test Coverage

- ✅ 404 errors (JSON en HTML)
- ✅ Validation errors (Pydantic)
- ✅ Integrity errors (Foreign key, unique)
- ✅ Database errors
- ✅ Stack traces niet zichtbaar voor users
- ✅ Consistent error format
- ✅ Nederlandse messages

**Run tests:**

```bash
pytest tests/test_error_handling.py -v
```

---

## Best Practices

### 1. **Gebruik specifieke error codes**

✅ **Good:**
```python
raise HTTPException(404, "Taak niet gevonden")
# → Automatisch vertaald naar NOT_FOUND error
```

❌ **Bad:**
```python
raise HTTPException(500, "Error")
# → Generieke melding, niet actionable
```

### 2. **Geef context in details**

```python
error = ErrorResponse(
    code=ErrorCode.VALIDATION_ERROR,
    message=get_error_message(ErrorCode.VALIDATION_ERROR),
    details=f"Datum {date} ligt in het verleden"  # Context!
)
```

### 3. **Log errors met context**

```python
logger.error("Failed to create task: {}", exc, task_id=task_id, user=user)
# → Server logs hebben context voor debugging
# → User krijgt vriendelijke melding
```

### 4. **Test error scenarios**

```python
def test_create_with_invalid_data():
    response = client.post("/api/tasks/", json={"invalid": "data"})
    assert response.status_code == 422
    assert "code" in response.json()
    assert "VALIDATION_ERROR" in response.json()["code"]
```

---

## Production Checklist

- ✅ Alle errors hebben Nederlandse messages
- ✅ Error codes gedefinieerd voor alle scenarios
- ✅ Stack traces niet zichtbaar in responses
- ✅ Error logging met context
- ✅ HTML error pages voor 404/500
- ✅ Consistent error response format
- ✅ Tests voor alle error types
- ✅ Network error handling in frontend
- ✅ User-friendly error messages (actionable)

---

## Related Files

- `app/errors.py` - Error codes, messages, translations
- `app/main.py` - Exception handlers
- `app/static/js/api.js` - Frontend error handling
- `app/templates/error.html` - HTML error pages
- `tests/test_error_handling.py` - Error handling tests
