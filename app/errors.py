"""
Centralized error handling for FamiliePlanner.

Provides user-friendly error messages, error codes, and consistent error format.
"""

from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):  # noqa: UP042
    """Error codes for debugging and logging."""

    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    CSRF_ERROR = "CSRF_ERROR"
    RATE_LIMIT = "RATE_LIMIT"

    # Server errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Business logic errors
    FOREIGN_KEY_ERROR = "FOREIGN_KEY_ERROR"
    UNIQUE_CONSTRAINT = "UNIQUE_CONSTRAINT"
    INVALID_REFERENCE = "INVALID_REFERENCE"


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    code: ErrorCode
    message: str
    details: str | None = None
    field: str | None = None  # Voor validatie errors


# Nederlandse error messages (user-facing)
ERROR_MESSAGES = {
    # Validatie errors
    ErrorCode.VALIDATION_ERROR: "De ingevoerde gegevens zijn niet geldig.",
    ErrorCode.FOREIGN_KEY_ERROR: "Dit item verwijst naar een verwijderd of ongeldig item.",
    ErrorCode.UNIQUE_CONSTRAINT: "Deze waarde bestaat al. Kies een andere waarde.",
    ErrorCode.INVALID_REFERENCE: "Het opgegeven item bestaat niet of is verwijderd.",
    # Resource errors
    ErrorCode.NOT_FOUND: "Het gevraagde item kon niet worden gevonden.",
    # Authenticatie/autorisatie
    ErrorCode.UNAUTHORIZED: "Je bent niet ingelogd. Log eerst in om verder te gaan.",
    ErrorCode.FORBIDDEN: "Je hebt geen toegang tot deze actie.",
    ErrorCode.CSRF_ERROR: "Beveiligingsfout: vernieuw de pagina en probeer opnieuw.",
    ErrorCode.RATE_LIMIT: "Te veel verzoeken. Wacht even en probeer opnieuw.",
    # Database errors
    ErrorCode.DATABASE_ERROR: "Er is een fout opgetreden bij het opslaan. Probeer het opnieuw.",
    ErrorCode.INTERNAL_ERROR: "Er is een onverwachte fout opgetreden. Probeer het later opnieuw.",
    # Conflict
    ErrorCode.CONFLICT: "Deze actie kan niet worden uitgevoerd vanwege een conflict.",
}


def get_error_message(code: ErrorCode, details: str | None = None) -> str:
    """Get user-friendly error message for error code."""
    message = ERROR_MESSAGES.get(code, ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR])
    if details:
        return f"{message} Details: {details}"
    return message


# Specifieke error messages voor veelvoorkomende validatie errors
VALIDATION_MESSAGES = {
    "string_too_short": "Te kort. Minimaal {min_length} tekens vereist.",
    "string_too_long": "Te lang. Maximaal {max_length} tekens toegestaan.",
    "value_error.missing": "Dit veld is verplicht.",
    "value_error.email": "Ongeldig e-mailadres.",
    "value_error.url": "Ongeldige URL.",
    "type_error.integer": "Voer een geldig getal in.",
    "type_error.float": "Voer een geldig decimaal getal in.",
    "type_error.boolean": "Ongeldige waarde (true/false verwacht).",
    "value_error.date": "Ongeldige datum. Gebruik formaat: YYYY-MM-DD.",
    "value_error.datetime": "Ongeldige datum/tijd.",
    "value_error.time": "Ongeldige tijd. Gebruik formaat: HH:MM.",
    "greater_than": "Waarde moet groter zijn dan {gt}.",
    "greater_than_equal": "Waarde moet minimaal {ge} zijn.",
    "less_than": "Waarde moet kleiner zijn dan {lt}.",
    "less_than_equal": "Waarde moet maximaal {le} zijn.",
}


def translate_validation_error(error_type: str, ctx: dict | None = None) -> str:
    """
    Translate Pydantic validation error to Dutch user-friendly message.

    Args:
        error_type: Pydantic error type (e.g., 'string_too_short')
        ctx: Error context with params (e.g., {'min_length': 3})

    Returns:
        Dutch error message
    """
    message = VALIDATION_MESSAGES.get(error_type, "Ongeldige waarde.")
    if ctx:
        try:
            return message.format(**ctx)
        except (KeyError, ValueError):
            return message
    return message
