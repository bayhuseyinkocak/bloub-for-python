"""Shapes and colours offered by the customiser.

Unlike the animation silhouettes (profiles.py), these are NOT measured off the
video: they are built analytically from the original customiser grid.
"""

import math

from .math import js_round
from .profiles import PROFILE_SAMPLES
from .shape import (
    hull_of_circles,
    profile_from_polygon,
    regular_polygon_profile,
    superellipse_profile,
    union_of_circles_profile,
)


def _normalize(radii, max_=1.0):
    peak = max(radii)
    if peak <= 0:
        return radii
    k = max_ / peak
    return [r * k for r in radii]


_ANGLES = [(i / PROFILE_SAMPLES) * math.pi * 2 for i in range(PROFILE_SAMPLES)]

# Pebble: circle deformed by two low harmonics.
_pebble = _normalize(
    [1 + 0.075 * math.cos(2 * a + 0.5) + 0.035 * math.cos(3 * a + 2.1) for a in _ANGLES], 1.02
)

# Cloud: union of bumps, wide at the bottom, two lobes on top.
_cloud = _normalize(
    union_of_circles_profile([
        {"x": -0.44, "y": 0.2, "r": 0.54},
        {"x": 0.46, "y": 0.2, "r": 0.5},
        {"x": 0.02, "y": 0.3, "r": 0.6},
        {"x": -0.24, "y": -0.3, "r": 0.48},
        {"x": 0.3, "y": -0.24, "r": 0.44},
    ]),
    1.02,
)

# Droplet: big disk at the bottom, tapered point on top.
_droplet = _normalize(
    profile_from_polygon(hull_of_circles(0, 0.28, 0.66, 0, -0.96, 0.05), 0, 0), 1.04
)

# Lying capsule: hull of two side-by-side disks.
_capsule = profile_from_polygon(hull_of_circles(-0.42, 0, 0.62, 0.42, 0, 0.62), 0, 0)

# Egg: squashed superellipse (n = 2.2). The profile is a LITTLE narrower at the
# top than at the bottom, so the pointier end reads upwards - the state "egg"
# is a rounder egg, this one is the classic tapered one.
_egg = _normalize(
    [
        superellipse_profile(2.2)[i] * (1 + 0.055 * math.sin(a) - 0.02 * math.cos(2 * a))
        for i, a in enumerate(_ANGLES)
    ],
    1.0,
)

# Speech bubble: a round body with a tail tapering off the upper left.
# Two circles and their convex hull: the hull is exact and star-shaped around
# the centre, so the tail keeps a straight taper and a sharp tip, and the body
# stays a clean circle where the eyes sit.
_bulle = _normalize(
    profile_from_polygon(hull_of_circles(0.0, 0.0, 0.62, -0.78, 0.52, 0.06, 96), 0.0, 0.0),
    1.0,
)

# Chubby: the circle flattened vertically (x 1.12, y 0.84) - a wide, squat body.
_rond = _normalize(superellipse_profile(2.4, 1.12, 0.84), 1.08)

SHAPES = [
    {"id": "cercle", "radii": [1.0] * PROFILE_SAMPLES},
    {"id": "galet", "radii": _pebble},
    {"id": "squircle", "radii": _normalize(superellipse_profile(4.2), 1.15)},
    {"id": "capsule", "radii": _capsule},
    {"id": "triangle", "radii": regular_polygon_profile(3, 1.12, 0.34, -90)},
    {"id": "hexagone", "radii": regular_polygon_profile(6, 1.04, 0.26, 0)},
    {"id": "nuage", "radii": _cloud},
    {"id": "goutte", "radii": _droplet},
    {"id": "oeuf", "radii": _egg},
    {"id": "bulle", "radii": _bulle},
    {"id": "rond", "radii": _rond},
]

SHAPE_BY_ID = {s["id"]: s for s in SHAPES}
DEFAULT_SHAPE = "cercle"

COLORS = [
    {"id": "encre", "hex": "#0a0a0c"},
    {"id": "brun", "hex": "#8b5e3c"},
    {"id": "rouge", "hex": "#e8483f"},
    {"id": "orange", "hex": "#f08a24"},
    {"id": "ambre", "hex": "#f0b429"},
    {"id": "vert", "hex": "#3ecf8e"},
    {"id": "turquoise", "hex": "#2fbfa0"},
    {"id": "bleu", "hex": "#3b93f0"},
    {"id": "violet", "hex": "#8b5cf6"},
    {"id": "rose", "hex": "#e152b0"},
    {"id": "gris", "hex": "#a3a3a3"},
    {"id": "creme", "hex": "#f1efe9"},
]

COLOR_BY_ID = {c["id"]: c for c in COLORS}
DEFAULT_COLOR = "encre"


def mix_hex(from_, to, t):
    """Blend two hex colours. Used for the depth haze of the particles."""

    def parse(h):
        v = int(h[1:], 16)
        return [(v >> 16) & 255, (v >> 8) & 255, v & 255]

    a = parse(from_)
    b = parse(to)
    c = [js_round(x + (y - x) * t) for x, y in zip(a, b)]
    return "#" + "".join("{:02x}".format(x) for x in c)
