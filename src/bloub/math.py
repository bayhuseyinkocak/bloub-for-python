"""Deterministic math primitives shared by the whole engine.

These mirror src/bot/math.ts exactly, including JS-specific behaviours that
would otherwise diverge:

* Math.round rounds halves toward +infinity (Python's round is banker's), so we
  use floor(x + 0.5).
* Math.imul / >>> 0 are 32-bit unsigned operations; create_rng emulates them
  with & 0xFFFFFFFF so the mulberry32 sequence is bit-identical.
* String(number) drops a trailing .0 on integers; js_str reproduces that so the
  generated SVG path strings match the TypeScript original byte for byte.
"""

import math

TAU = math.tau  # 2 * pi


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def js_round(x):
    """Math.round: half rounds toward +infinity (not banker's)."""
    return math.floor(x + 0.5)


def r2(v):
    """Short rounding: divides by ~2 the weight of 60 fps path strings."""
    return js_round(v * 100.0) / 100.0


def js_str(x):
    """Format a number the way JavaScript String(number) does.

    In particular, integers print without a trailing ".0" (String(100) is
    "100", not "100.0"), and -0 prints as "0".
    """
    if x != x:  # NaN
        return "NaN"
    if x == float("inf"):
        return "Infinity"
    if x == float("-inf"):
        return "-Infinity"
    if x == 0:
        return "0"
    if x == math.floor(x) and abs(x) < 1e21:
        return str(int(x))
    return repr(x)


def r2s(v):
    """r2(v) formatted as JavaScript would stringify it."""
    return js_str(r2(v))


def ease_out_cubic(t):
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t):
    return 4.0 * t ** 3 if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_out_quint(t):
    return 1.0 - (1.0 - t) ** 5


# Keyed by the original camelCase names, as used in states.py.
EASINGS = {
    "easeOutCubic": ease_out_cubic,
    "easeInOutCubic": ease_in_out_cubic,
    "easeOutQuint": ease_out_quint,
}


def loop_noise(t, period, seed=0.0):
    """1D periodic noise: seamless loop over period, used for gaze drift."""
    p = (t / period) * TAU
    return (
        0.55 * math.sin(p + seed)
        + 0.3 * math.sin(2.0 * p + seed * 1.7 + 1.1)
        + 0.15 * math.sin(3.0 * p + seed * 2.3 + 2.4)
    )


def create_rng(seed):
    """Deterministic mulberry32 PRNG: same sequence on every run.

    Emulates JS 32-bit unsigned arithmetic (>>> 0, Math.imul) with
    & 0xFFFFFFFF so the sequence is bit-identical to the TypeScript original.
    """
    a = seed & 0xFFFFFFFF

    def next_():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        imul2 = ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF
        t = (((t + imul2) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        t = (t ^ (t >> 14)) & 0xFFFFFFFF
        return t / 4294967296.0

    return next_
