"""Shared enums used by both models and schemas."""
import enum


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class RecurrenceType(str, enum.Enum):
    daily           = "daily"
    every_other_day = "every_other_day"
    weekly          = "weekly"
    biweekly        = "biweekly"
    weekdays        = "weekdays"
    monthly         = "monthly"
