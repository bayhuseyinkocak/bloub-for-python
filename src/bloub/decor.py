"""Rings, comet ribbons, dots, particles and the notification pastille."""

import math

from .math import TAU, clamp, create_rng, js_round, js_str, r2


def wheel(hue, s=0.55, l=0.62):
    """HSL wheel with a hue gradient along each trace (measured S 45-62%, L 50-67%)."""
    h = ((hue % 360.0) + 360.0) % 360.0
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs(((h / 60.0) % 2.0) - 1.0))
    m = l - c / 2.0
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return "#{:02x}{:02x}{:02x}".format(
        js_round((r + m) * 255), js_round((g + m) * 255), js_round((b + m) * 255)
    )


def arc_render(seed, t, scale, id_, opacity=1.0):
    """Project an inclined 3D circle orthographically; split front/back for depth."""
    spin = seed["phase"] + t * seed["speed"] * TAU
    cu = math.cos(seed["tilt"])
    su = math.sin(seed["tilt"])
    kz = math.sqrt(max(0.0, 1.0 - seed["k"] * seed["k"]))

    N = 64
    span = seed["sweep"] * TAU
    front = ""
    back = ""
    prev = None

    for i in range(N + 1):
        th = spin + (i / N) * span
        ct = math.cos(th)
        st = math.sin(th)
        x = seed["a"] * (ct * cu + st * -su * seed["k"]) + seed["cx"]
        y = seed["a"] * (ct * su + st * cu * seed["k"]) + seed["cy"]
        z = seed["a"] * st * kz

        behind = z < 0.0
        sx = js_str(r2(x * scale))
        sy = js_str(r2(y * scale))
        cmd = "M" if behind != prev else "L"
        if behind:
            back += cmd + sx + " " + sy
        else:
            front += cmd + sx + " " + sy
        prev = behind

    gx = math.cos(seed["tilt"]) * seed["a"] * scale
    gy = math.sin(seed["tilt"]) * seed["a"] * scale
    return {
        "id": id_,
        "front": front,
        "back": back,
        "width": seed["width"] * scale,
        "opacity": opacity,
        "grad": {
            "x1": r2(seed["cx"] * scale - gx),
            "y1": r2(seed["cy"] * scale - gy),
            "x2": r2(seed["cx"] * scale + gx),
            "y2": r2(seed["cy"] * scale + gy),
            "stops": [
                wheel(seed["hue"]),
                wheel(seed["hue"] + seed["hueSpan"] * 0.5),
                wheel(seed["hue"] + seed["hueSpan"]),
            ],
        },
    }


RING_RNG = create_rng(0xA11CE)
RINGS = []
for _i in range(6):
    RINGS.append({
        "a": 1.3 + RING_RNG() * 0.1,
        "k": 0.05 + RING_RNG() * 0.4,
        "tilt": (_i / 6) * math.pi + RING_RNG() * 0.5,
        "speed": 3 + RING_RNG() * 0.7,
        "phase": RING_RNG() * TAU,
        "sweep": 0.6 + RING_RNG() * 0.25,
        "hue": (_i * 360) / 6 + RING_RNG() * 30,
        "hueSpan": 60 + RING_RNG() * 60,
        "width": 0.05 + RING_RNG() * 0.012,
        "cx": 0.0,
        "cy": 0.1,
    })

SWOOSH = []
for _i in range(4):
    SWOOSH.append({
        "a": 0.78 + _i * 0.2,
        "k": 0.05 + _i * 0.02,
        "tilt": -0.62 + _i * 0.05,
        "speed": 0.3,
        "phase": 0.06 * _i,
        "sweep": 0.4,
        "hue": 95 + _i * 62,
        "hueSpan": 100,
        "width": 0.05,
        "cx": 0.0,
        "cy": -0.12,
    })

# Measured x: -0.557 / -0.013 / +0.532, y = 0.
DOT_X = [-0.557, -0.013, 0.532]
DOT_R = 0.165
DOT_PEAK = 1.25

P_RNG = create_rng(0xBEEF)
PARTICLES = []
for _i in range(5):
    PARTICLES.append({"birth": _i * 0.2, "angle": P_RNG() * TAU, "rho": 0.58 + P_RNG() * 0.18})


def particles(t, scale):
    """Burst particles spiral toward the centre, growing, passing behind the core."""
    out = []
    for p in PARTICLES:
        u = t - p["birth"]
        if u < 0.0 or u > 0.62:
            continue
        rho = p["rho"] * math.pow(0.75, u * 10.0)
        a = p["angle"] + (u * 100.0 * math.pi) / 180.0
        out.append({
            "x": math.cos(a) * rho * scale,
            "y": math.sin(a) * rho * scale,
            "r": (0.04 + 0.028 * clamp(u / 0.55)) * scale,
            "depth": clamp(1.0 - rho / 0.8),
            "opacity": clamp(u / 0.06) * clamp((0.62 - u) / 0.08),
        })
    return out


COMET_RNG = create_rng(0xC0E7)
COMET_RIBBONS = []
for _i in range(4):
    d = _i - 1.5
    COMET_RIBBONS.append({
        "a": 0.85 * (1 + d * 0.03),
        "k": (0.15 / 0.85) * (1 + d * 0.16),
        "tilt": (34 * math.pi) / 180 + d * 0.035,
        "speed": 210 / 360,
        "phase": -_i * 0.045 + COMET_RNG() * 0.012,
        "sweep": 0.34,
        "hue": _i * 85 + COMET_RNG() * 20,
        "hueSpan": 80,
        "width": 0.095,
        "cx": 0.0,
        "cy": 0.0,
    })

# Comet dot radius, measured at 0.129.
COMET_DOT = 0.129

NOTIF_BLUE = "#2496e8"
# The pastille sits exactly on the circumference, at -42deg.
NOTIF_ANGLE = -42
NOTIF_DIST = 1.003
NOTIF_R = 0.15
NOTIF_POP = 1.14
NOTIF_MARGIN = 0.054
