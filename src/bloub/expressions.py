"""The bot's rest expressions.

The face is only two capsules, so everything plays on four levers: head
orientation, eye spread, proportions, and each eye's own tilt (the last one
enables anger and sadness, which need mirrored tilts).

Only the idle state carries this expression; the expressive states of the video
keep their own.
"""

from .face import EYE_H, EYE_SPLIT, EYE_W, REST_GAZE
from .math import lerp


def _eye(w, h, tilt=0.0, open=1.0):
    return {"w": w, "h": h, "tilt": tilt, "open": open}


def _pair(w, h, tilt=0.0, open=1.0):
    return [_eye(w, h, tilt, open), _eye(w, h, -tilt, open)]


EXPRESSIONS = [
    {"id": "neutre", "gaze": dict(REST_GAZE), "split": EYE_SPLIT, "eyes": [_eye(EYE_W, EYE_H), _eye(EYE_W, EYE_H)]},
    {"id": "attentif", "gaze": {"yaw": 4, "pitch": 5, "roll": -4}, "split": 16, "eyes": _pair(0.21, 0.44)},
    {"id": "surpris", "gaze": {"yaw": 3, "pitch": -3, "roll": 0}, "split": 19, "eyes": _pair(0.45, 0.47)},
    {"id": "excite", "gaze": {"yaw": 6, "pitch": -14, "roll": 0}, "split": 19.5, "eyes": _pair(0.4, 0.56, -10)},
    {"id": "heureux", "gaze": {"yaw": 5, "pitch": 9, "roll": 0}, "split": 17, "eyes": _pair(0.27, 0.17, 14)},
    {"id": "hilare", "gaze": {"yaw": 4, "pitch": 14, "roll": 0}, "split": 18, "eyes": _pair(0.34, 0.13, 20)},
    {"id": "colere", "gaze": {"yaw": 3, "pitch": 7, "roll": 0}, "split": 17, "eyes": _pair(0.34, 0.15, 30)},
    {"id": "triste", "gaze": {"yaw": 3, "pitch": -13, "roll": 0}, "split": 16, "eyes": _pair(0.22, 0.4, -28)},
    {"id": "effraye", "gaze": {"yaw": 2, "pitch": -20, "roll": 0}, "split": 20.5, "eyes": _pair(0.4, 0.6)},
    {"id": "mefiant", "gaze": {"yaw": 12, "pitch": 6, "roll": -6}, "split": 16, "eyes": [_eye(0.21, 0.4), _eye(0.22, 0.15)]},
    {"id": "confus", "gaze": {"yaw": -14, "pitch": 3, "roll": 8}, "split": 16.5, "eyes": [_eye(0.2, 0.44, -18), _eye(0.28, 0.17, 14)]},
    {"id": "curieux", "gaze": {"yaw": 16, "pitch": -9, "roll": -15}, "split": 16.5, "eyes": [_eye(0.24, 0.46, -8), _eye(0.2, 0.38, -8)]},
    {"id": "fier", "gaze": {"yaw": 5, "pitch": 17, "roll": 0}, "split": 17, "eyes": _pair(0.3, 0.15, 18)},
    {"id": "timide", "gaze": {"yaw": -19, "pitch": -14, "roll": -7}, "split": 14, "eyes": _pair(0.17, 0.3)},
    {"id": "blase", "gaze": {"yaw": -22, "pitch": 2, "roll": 0}, "split": 16, "eyes": _pair(0.3, 0.12)},
    {"id": "somnolent", "gaze": {"yaw": 6, "pitch": -9, "roll": -3}, "split": 16, "eyes": _pair(0.2, 0.42, 0, 0.42)},
]

EXPRESSION_BY_ID = {e["id"]: e for e in EXPRESSIONS}
DEFAULT_EXPRESSION = "neutre"


def _lerp_eye(a, b, t):
    return {
        "w": lerp(a["w"], b["w"], t),
        "h": lerp(a["h"], b["h"], t),
        "tilt": lerp(a.get("tilt", 0.0), b.get("tilt", 0.0), t),
        "open": lerp(a["open"], b["open"], t),
    }


def blend_expression(a, b, t):
    """Interpolate two expressions: the change happens by sliding."""
    return {
        "id": b["id"],
        "gaze": {
            "yaw": lerp(a["gaze"]["yaw"], b["gaze"]["yaw"], t),
            "pitch": lerp(a["gaze"]["pitch"], b["gaze"]["pitch"], t),
            "roll": lerp(a["gaze"]["roll"], b["gaze"]["roll"], t),
        },
        "split": lerp(a["split"], b["split"], t),
        "eyes": [_lerp_eye(a["eyes"][0], b["eyes"][0], t), _lerp_eye(a["eyes"][1], b["eyes"][1], t)],
    }
