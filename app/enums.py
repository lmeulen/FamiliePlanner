"""Shared enums used by both models and schemas."""

import enum


class MealType(str, enum.Enum):
    """Meal type enum - compatible with Python 3.10+."""

    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class RecurrenceType(str, enum.Enum):
    """Recurrence type enum - compatible with Python 3.10+."""

    daily = "daily"
    every_other_day = "every_other_day"
    weekly = "weekly"
    biweekly = "biweekly"
    weekdays = "weekdays"
    monthly = "monthly"
    yearly = "yearly"
