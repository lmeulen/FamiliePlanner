"""Shared enums used by both models and schemas."""

import enum


class MealType(enum.StrEnum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class RecurrenceType(enum.StrEnum):
    daily = "daily"
    every_other_day = "every_other_day"
    weekly = "weekly"
    biweekly = "biweekly"
    weekdays = "weekdays"
    monthly = "monthly"
    yearly = "yearly"
