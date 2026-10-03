"""The eyes are painted on a sphere, not laid flat.

Measured off the video: the eye nearest the edge is 0.69x the width of the
other, and its area 0.663x - exactly the depth factor (z = 0.669) of a sphere
point at that distance from the centre. So a real head orientation is modelled:
each eye recovers the sphere's tangent frame, projected orthographically.
"""

import math

from .math import clamp, create_rng, loop_noise

# Half-spread of the eyes on the sphere, in degrees (total separation ~31deg).
EYE_SPLIT = 15.46
# Eye size at rest, in ball-radius units.
EYE_W = 0.186
EYE_H = 0.412

# Head orientation at rest, fitted on the reference frames.
REST_GAZE = {"yaw": 28.49, "pitch": 28.62, "roll": -13.0}


def _deg(d):
    return d * math.pi / 180.0


def _spin(u, v, angle):
    """Rotate two orthonormal vectors in their common plane."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        [u[0] * c + v[0] * s, u[1] * c + v[1] * s, u[2] * c + v[2] * s],
        [v[0] * c - u[0] * s, v[1] * c - u[1] * s, v[2] * c - u[2] * s],
    )


def eye_poses(gaze, scale, split=EYE_SPLIT):
    """Head frame then the two eyes. Screen frame: x right, y down, z toward viewer."""
    f = [0.0, 0.0, 1.0]
    right = [1.0, 0.0, 0.0]
    down = [0.0, 1.0, 0.0]

    f, right = _spin(f, right, _deg(gaze["yaw"]))
    down, f = _spin(down, f, _deg(gaze["pitch"]))
    right, down = _spin(right, down, _deg(gaze["roll"]))

    def build(side):
        ef, er = _spin(f, right, _deg(split * side))
        return {
            "x": ef[0] * scale,
            "y": ef[1] * scale,
            "a": er[0],
            "b": er[1],
            "c": down[0],
            "d": down[1],
            "depth": ef[2],
        }

    return (build(-1), build(1))


# Blink schedule, pre-drawn: deterministic and stateless.
BLINK_RNG = create_rng(0x5EED)
BLINKS = []
_t = 1.4
while _t < 900.0:
    BLINKS.append(_t)
    _t += 1.9 + BLINK_RNG() * 2.7
    if BLINK_RNG() < 0.18:
        BLINKS.append(_t)
        _t += 0.24

# Measured: 1 to 2 frames at 10 fps.
BLINK_DUR = 0.18


def blink_lid(t):
    for start in BLINKS:
        if t < start:
            break
        k = (t - start) / BLINK_DUR
        if 0.0 <= k <= 1.0:
            return (1.0 - k / 0.45) if k < 0.45 else ((k - 0.45) / 0.55)
    return 1.0


def liveliness(t, wander=1.0, blink=True, float_=True):
    """Rest life: slow gaze drift, saccades, blinks. Pure function of time."""
    return {
        "dYaw": (loop_noise(t, 11.3, 0.4) * 5.5 + loop_noise(t, 3.7, 2.1) * 1.6) * wander,
        "dPitch": (loop_noise(t, 9.1, 1.3) * 4.2 + loop_noise(t, 4.3, 0.7) * 1.3) * wander,
        "dRoll": loop_noise(t, 13.7, 3.2) * 2.2 * wander,
        "lid": blink_lid(t) if blink else 1.0,
        "driftX": loop_noise(t, 7.9, 1.9) * 0.006 if float_ else 0.0,
        "driftY": loop_noise(t, 5.3, 0.3) * 0.007 if float_ else 0.0,
        "breath": 1.0 + math.sin((t / 3.4) * math.pi * 2.0) * 0.005 if float_ else 1.0,
    }


def blink_scale(lid):
    """Blink is a vertical squash in screen space around the eye centre."""
    return 0.06 + 0.94 * clamp(lid)
