"""Grocery input parser - extracts quantity, unit, and product name."""

import re


# Dutch units
DUTCH_UNITS = {
    "kg": "kg",
    "kilo": "kg",
    "kilogram": "kg",
    "g": "g",
    "gram": "g",
    "gr": "g",
    "ons": "ons",
    "pond": "pond",
    "l": "l",
    "liter": "liter",
    "ml": "ml",
    "milliliter": "ml",
    "dl": "dl",
    "deciliter": "dl",
    "stuks": "stuks",
    "stuk": "stuks",
    "st": "stuks",
    "pak": "pak",
    "pakje": "pak",
    "fles": "fles",
    "flessen": "fles",
    "blik": "blik",
    "blikje": "blik",
    "zak": "zak",
    "zakje": "zak",
    "x": "stuks",
}

# English units
ENGLISH_UNITS = {
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "grams": "g",
    "gram": "g",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "l": "l",
    "liter": "liter",
    "liters": "liter",
    "litre": "liter",
    "litres": "liter",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "pcs": "stuks",
    "pieces": "stuks",
    "piece": "stuks",
    "pack": "pak",
    "packs": "pak",
    "package": "pak",
    "bottle": "fles",
    "bottles": "fles",
    "can": "blik",
    "cans": "blik",
    "bag": "zak",
    "bags": "zak",
}

ALL_UNITS = {**DUTCH_UNITS, **ENGLISH_UNITS}


def parse_grocery_input(raw_input: str) -> tuple[str | None, str | None, str]:
    """
    Parse grocery input like "2 kg tomaten" into (quantity, unit, product_name).

    Examples:
        "2 kg tomaten" -> ("2", "kg", "tomaten")
        "500g kaas" -> ("500", "g", "kaas")
        "tomaten" -> (None, None, "tomaten")
        "3 stuks brood" -> ("3", "stuks", "brood")
        "2-3 appels" -> ("2-3", None, "appels")

    Returns:
        (quantity, unit, product_name)
        - quantity: "2", "500", "2-3", etc. or None
        - unit: normalized unit or None
        - product_name: remaining text (normalized to lowercase)
    """
    text = raw_input.strip()

    # Pattern: optional quantity + optional unit + product name
    # Matches: "2 kg tomaten", "500g kaas", "tomaten", "3 stuks brood"
    pattern = r"^(\d+(?:[.,]\d+)?(?:\s*-\s*\d+)?)\s*([a-zA-Z]+)?\s+(.+)$|^(.+)$"

    match = re.match(pattern, text, re.IGNORECASE)

    if not match:
        return None, None, normalize_product_name(text)

    groups = match.groups()

    # Case 1: quantity + optional unit + product
    if groups[0] and groups[2]:
        quantity = groups[0].replace(",", ".")
        unit_raw = groups[1].lower() if groups[1] else None
        product = groups[2]

        # Normalize unit
        unit = ALL_UNITS.get(unit_raw) if unit_raw else None

        return quantity, unit, normalize_product_name(product)

    # Case 2: just product name
    if groups[3]:
        return None, None, normalize_product_name(groups[3])

    return None, None, normalize_product_name(text)


def normalize_product_name(name: str) -> str:
    """Normalize product name: lowercase for storage and matching."""
    return name.strip().lower()


def display_product_name(name: str) -> str:
    """Display product name: capitalize first letter."""
    return name.capitalize() if name else ""
