"""Map FamiliePlanner member colours onto Google Calendar's 11 fixed event colours."""

from __future__ import annotations

# Google Calendar event colorIds and their rendered hex values.
GOOGLE_EVENT_COLORS: dict[str, str] = {
    "1": "#7986cb",  # Lavender
    "2": "#33b679",  # Sage
    "3": "#8e24aa",  # Grape
    "4": "#e67c73",  # Flamingo
    "5": "#f6bf26",  # Banana
    "6": "#f4511e",  # Tangerine
    "7": "#039be5",  # Peacock
    "8": "#616161",  # Graphite
    "9": "#3f51b5",  # Blueberry
    "10": "#0b8043",  # Basil
    "11": "#d50000",  # Tomato
}

GOOGLE_COLOR_NAMES: dict[str, str] = {
    "1": "Lavender",
    "2": "Sage",
    "3": "Grape",
    "4": "Flamingo",
    "5": "Banana",
    "6": "Tangerine",
    "7": "Peacock",
    "8": "Graphite",
    "9": "Blueberry",
    "10": "Basil",
    "11": "Tomato",
}

DEFAULT_COLOR_ID = "8"  # Graphite, used for events without members


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        raise ValueError(f"Ongeldige hex kleur: {value}")
    return tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _srgb_to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return float(((channel + 0.055) / 1.055) ** 2.4)


def _hex_to_lab(value: str) -> tuple[float, float, float]:
    """Convert sRGB hex to CIE Lab (D65) for perceptual distance comparison."""
    r, g, b = (_srgb_to_linear(c) for c in _hex_to_rgb(value))

    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return float(t ** (1 / 3)) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def color_distance(hex_a: str, hex_b: str) -> float:
    """CIE76 delta-E between two hex colours."""
    la, aa, ba = _hex_to_lab(hex_a)
    lb, ab, bb = _hex_to_lab(hex_b)
    return float(((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2) ** 0.5)


def nearest_color_id(hex_color: str, exclude: set[str] | None = None) -> str:
    """Return the perceptually closest Google colorId, optionally skipping taken ones."""
    excluded = exclude or set()
    candidates = {cid: chex for cid, chex in GOOGLE_EVENT_COLORS.items() if cid not in excluded}
    if not candidates:
        candidates = GOOGLE_EVENT_COLORS

    try:
        return min(candidates, key=lambda cid: color_distance(hex_color, candidates[cid]))
    except ValueError:
        return DEFAULT_COLOR_ID


def assign_member_colors(members: list[tuple[int, str]]) -> dict[str, str]:
    """Assign each member a distinct Google colorId, best match first.

    Args:
        members: ``(member_id, hex_color)`` pairs.

    Returns:
        ``{str(member_id): colorId}``. Duplicates only occur beyond 11 members.
    """
    # Assign the least ambiguous members first so they get their best match.
    ordered = sorted(
        members,
        key=lambda m: min(color_distance(m[1], c) for c in GOOGLE_EVENT_COLORS.values()),
    )

    taken: set[str] = set()
    mapping: dict[str, str] = {}
    for member_id, hex_color in ordered:
        color_id = nearest_color_id(hex_color, exclude=taken)
        mapping[str(member_id)] = color_id
        if len(taken) < len(GOOGLE_EVENT_COLORS):
            taken.add(color_id)

    return mapping
