"""The 14 states (plus the swirl interface transition).

Each state declares a pose as a function of its local time. The engine is the
only place that interpolates between poses.
"""

import math

from .decor import (
    COMET_DOT,
    COMET_RIBBONS,
    DOT_PEAK,
    DOT_R,
    DOT_X,
    NOTIF_ANGLE,
    NOTIF_DIST,
    NOTIF_MARGIN,
    NOTIF_POP,
    NOTIF_R,
    RINGS,
    SWOOSH,
    particles,
)
from .face import EYE_H, EYE_SPLIT, EYE_W, REST_GAZE
from .math import TAU, EASINGS, clamp
from .shape import (
    Silhouette,
    circle,
    hull_of_circles,
    poly_path,
    profile_from_polygon,
    silhouette,
)

easeOutCubic = EASINGS["easeOutCubic"]
easeInOutCubic = EASINGS["easeInOutCubic"]
easeOutQuint = EASINGS["easeOutQuint"]


def _pair(w, h):
    return [{"w": w, "h": h, "open": 1.0}, {"w": w, "h": h, "open": 1.0}]


def _base(over=None):
    pose = {
        "sil": circle(1.0),
        "offX": 0.0,
        "offY": 0.0,
        "gaze": dict(REST_GAZE),
        "split": EYE_SPLIT,
        "eyes": _pair(EYE_W, EYE_H),
        "eyeAlpha": 1.0,
        "bodyAlpha": 1.0,
        "dots": [],
        "arcs": [],
        "notif": None,
        "dotsBehind": False,
    }
    if over:
        pose.update(over)
    return pose


# ---- non-radial shapes ----

BAR_UPRIGHT_CY = -0.1875
BAR_UPRIGHT = profile_from_polygon(hull_of_circles(0, -0.505, 0.132, 0, 0.13, 0.075), 0, BAR_UPRIGHT_CY)
BAR_ITALIC = profile_from_polygon(hull_of_circles(0, -0.2535, 0.1345, 0, 0.2535, 0.1345), 0, 0)


def _bar_upright(**pose):
    return Silhouette(list(BAR_UPRIGHT), cy=BAR_UPRIGHT_CY, **pose)


def _bar_italic(**pose):
    return Silhouette(list(BAR_ITALIC), **pose)


# The italic "!" dot is a teardrop, not a disk.
TEAR = poly_path(hull_of_circles(0, 0, 0.118, 0, 0.172, 0.012))

# The triangle does not spin on itself: its centre describes a circle of radius
# 0.213 around the origin (measured).
TRI_ORBIT = 0.213


def _spinning_triangle(rot):
    return silhouette("triangle", rot=rot, cx=-TRI_ORBIT * math.sin(rot), cy=TRI_ORBIT * math.cos(rot))


# Pulse wave travelling left to right across the three dots.
def _dot_pulse(t, index):
    p = ((((t - index * 0.5) / 1.5) % 1.0) + 1.0) % 1.0
    k = 0.5 - 0.5 * math.cos(p * TAU) if p < 0.5 else 0.0
    return clamp(k * 2.0)


STATES = [
    {
        "id": "idle",
        "duration": 2.4,
        "morph": 0.45,
        "blinkIn": False,
        "baseFace": True,
        "baseBody": True,
        "pose": lambda t: _base(),
    },
    {
        "id": "thinking",
        "duration": 2.6,
        "morph": 0.4,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _base({
            "sil": circle(DOT_R * (1 + (DOT_PEAK - 1) * _dot_pulse(t, 1)), cx=DOT_X[1]),
            "eyeAlpha": 0.0,
            "dots": [
                {
                    "x": DOT_X[i] * (0.3 + 0.7 * easeOutCubic(clamp(t / 0.3))),
                    "y": 0.0,
                    "r": DOT_R * (1 + (DOT_PEAK - 1) * _dot_pulse(t, i)),
                    "opacity": 0.55 + 0.45 * _dot_pulse(t, i),
                }
                for i in (0, 2)
            ],
        }),
    },
    {
        "id": "wink",
        "duration": 1.6,
        "morph": 0.3,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": True,
        "pose": lambda t: _base({
            "gaze": {"yaw": -5.37, "pitch": 4.55, "roll": 6.7},
            "split": 16.25,
            "eyes": [{"w": 0.236, "h": 0.464, "open": 1.0}, {"w": 0.447, "h": 0.089, "open": 1.0}],
        }),
    },
    {
        "id": "wide",
        "duration": 1.8,
        "morph": 0.55,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": True,
        "pose": lambda t: _base({
            "gaze": {"yaw": 6.92, "pitch": -21.96, "roll": 11.6},
            "split": 18.43,
            "eyes": _pair(0.356, 0.875),
        }),
    },
    {
        "id": "alert",
        "duration": 2.4,
        "minDuration": 2,
        "morph": 0.45,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _alert_pose(t),
    },
    {
        "id": "notify",
        "duration": 2.2,
        "morph": 0.5,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": True,
        "pose": lambda t: _notify_pose(t),
    },
    {
        "id": "exclaim",
        "duration": 2,
        "morph": 0.45,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _base({
            "sil": _bar_upright(),
            "eyeAlpha": 0.0,
            "dots": [{"x": -0.012, "y": 0.526, "r": 0.113, "opacity": 1.0}],
        }),
    },
    {
        "id": "sleep",
        "duration": 2.4,
        "morph": 0.5,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _base({
            "sil": circle(0.1585, cy=0.11 + math.sin(t * (TAU / 0.6)) * 0.19),
            "eyeAlpha": 0.0,
        }),
    },
    {
        "id": "egg",
        "duration": 1.8,
        "morph": 0.4,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _base({
            "sil": silhouette("egg"),
            "gaze": {"yaw": 19.97, "pitch": 26.01, "roll": -17.1},
            "split": 11.07,
            "eyes": _pair(0.164, 0.385),
        }),
    },
    {
        "id": "hexagon",
        "duration": 1.6,
        "morph": 0.4,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _base({
            "sil": silhouette("hexagon"),
            "gaze": {"yaw": 23.11, "pitch": 24.42, "roll": -13.3},
            "split": 13.37,
            "eyes": _pair(0.177, 0.411),
        }),
    },
    {
        "id": "play",
        "duration": 2,
        "morph": 0.5,
        "blinkIn": True,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _play_pose(t),
    },
    {
        "id": "orbit",
        "duration": 3.4,
        "minDuration": 2.5,
        "morph": 0.6,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _orbit_pose(t),
    },
    {
        "id": "swirl",
        "duration": 1.3,
        "minDuration": 1.3,
        "morph": 0.3,
        "blinkIn": True,
        "baseFace": True,
        "baseBody": True,
        "pose": lambda t: _base({
            "arcs": [
                {
                    "id": "sw" + str(i),
                    "seed": s,
                    "t": t,
                    "opacity": clamp((t - i * 0.06) / 0.14) * clamp((1.22 - t) / 0.34),
                }
                for i, s in enumerate(RINGS[:3])
            ],
        }),
    },
    {
        "id": "burst",
        "duration": 2.6,
        "minDuration": 2.4,
        "morph": 0.4,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _burst_pose(t),
    },
    {
        "id": "comet",
        "duration": 2.4,
        "minDuration": 2.4,
        "morph": 0.45,
        "blinkIn": False,
        "baseFace": False,
        "baseBody": False,
        "pose": lambda t: _comet_pose(t),
    },
]


def _alert_pose(t):
    p = clamp(t / 1.5)
    travel = easeInOutCubic(p) * 0.82 - 0.087
    back = clamp((t - 1.6) / 0.4) if t > 1.6 else 0.0
    x = travel * (1 - back) + 0.1 * back
    buzz = math.sin(t * 2.5 * TAU) * 0.005
    tilt = (17.7 * math.pi) / 180.0
    return _base({
        "sil": _bar_italic(rot=tilt, cx=x, cy=-0.325 - buzz),
        "eyeAlpha": 0.0,
        "dots": [{
            "x": x - math.sin(tilt) * 0.58,
            "y": -0.325 + math.cos(tilt) * 0.58 + buzz * 2.8,
            "r": 0.118,
            "d": TEAR,
            "rot": (tilt * 180.0) / math.pi,
            "opacity": 1.0,
        }],
    })


def _notify_pose(t):
    p = clamp(t / 0.45)
    pop = 1 + (NOTIF_POP - 1) * math.sin(p * math.pi) * (1 - p * 0.35)
    r = NOTIF_R * (pop if p < 1 else 1.0)
    a = (NOTIF_ANGLE * math.pi) / 180.0
    return _base({
        "gaze": {"yaw": -21.94, "pitch": -5.82, "roll": -12.2},
        "split": 18.89,
        "eyes": _pair(0.505, 0.498),
        "notif": {
            "x": math.cos(a) * NOTIF_DIST,
            "y": math.sin(a) * NOTIF_DIST,
            "r": r,
            "notch": r + NOTIF_MARGIN,
        },
    })


def _play_pose(t):
    fade = clamp(t / 0.35) * clamp((2.2 - t) / 0.5)
    return _base({
        "sil": _spinning_triangle(0.0),
        "gaze": {"yaw": 12, "pitch": -8, "roll": -6},
        "split": 15,
        "eyes": _pair(0.18, 0.34),
        "arcs": [
            {
                "id": "sw" + str(i),
                "seed": dict(s, cx=0.45 - t * 0.42),
                "t": t,
                "opacity": fade,
            }
            for i, s in enumerate(SWOOSH)
        ],
    })


def _orbit_pose(t):
    ramp = easeInOutCubic(clamp(t / 0.35))
    rot = -TAU * 1.25 * t * ramp
    back = easeInOutCubic(clamp((t - 1.6) / 0.9))
    tri = _spinning_triangle(rot)
    ball = circle(1.0, rot=rot)
    sil = Silhouette(
        radii=[r + (ball.radii[i] - r) * back for i, r in enumerate(tri.radii)],
        rot=rot,
        cx=tri.cx * (1 - back),
        cy=tri.cy * (1 - back),
        sx=1.0,
        sy=1.0,
    )
    fade = clamp(t / 0.8) * clamp((3.6 - t) / 0.9)
    return _base({
        "sil": sil,
        "gaze": {
            "yaw": REST_GAZE["yaw"] + math.sin(t * 6.5) * 65 * (1 - back),
            "pitch": -4 + back * 32,
            "roll": -13,
        },
        "eyes": _pair(0.18, 0.34 + back * 0.07),
        "arcs": [
            {
                "id": "rg" + str(i),
                "seed": s,
                "t": t,
                "opacity": fade * clamp((t - i * 0.13) / 0.3),
            }
            for i, s in enumerate(RINGS)
        ],
    })


def _burst_pose(t):
    collapse = 1 - 0.834 * easeOutQuint(clamp(t / 0.7))
    regrow = easeOutQuint(clamp((t - 1.7) / 0.7))
    return _base({
        "sil": circle(collapse + (1 - collapse) * regrow),
        "eyeAlpha": clamp((t - 1.85) / 0.4),
        "dots": particles(t, 1),
        "dotsBehind": True,
    })


def _comet_pose(t):
    collapse = 1 - (1 - COMET_DOT) * easeOutQuint(clamp(t / 0.55))
    regrow = easeOutQuint(clamp((t - 1.85) / 0.6))
    fade = clamp((t - 0.15) / 0.25) * clamp((1.95 - t) / 0.3)
    return _base({
        "sil": circle(collapse + (1 - collapse) * regrow, cy=math.sin(clamp(t / 1.7) * math.pi) * 0.035),
        "eyeAlpha": clamp((t - 2) / 0.35),
        "arcs": [
            {"id": "cm" + str(i), "seed": s, "t": t, "opacity": fade}
            for i, s in enumerate(COMET_RIBBONS)
        ],
    })


STATE_BY_ID = {s["id"]: s for s in STATES}

# Playback order of the full sequence, matching the reference video.
SEQUENCE = [
    "idle", "thinking", "wink", "wide", "alert", "notify", "exclaim",
    "sleep", "egg", "hexagon", "play", "orbit", "burst", "comet",
]

# Local-time date where each state is most readable (thumbnails, board).
POSES = {
    "idle": 1,
    "thinking": 1.1,
    "wink": 0.8,
    "wide": 0.8,
    "alert": 0.75,
    "notify": 0.9,
    "exclaim": 0.8,
    "sleep": 0.45,
    "egg": 0.8,
    "hexagon": 0.8,
    "play": 0.9,
    "orbit": 1.2,
    "swirl": 0.5,
    "burst": 0.45,
    "comet": 1.15,
}
