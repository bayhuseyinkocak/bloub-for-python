"""Radial silhouettes: every shape is a radial profile r(theta) plus a pose.

All profiles are sampled at the SAME number of angles (PROFILE_SAMPLES, 64), so
any two shapes have points that correspond one to one, and a transition reduces
to a linear interpolation of radii. That is why there is no path-morphing
library here.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .math import TAU, js_str, lerp, r2
from .profiles import PROFILES, PROFILE_SAMPLES


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Silhouette:
    radii: List[float]
    rot: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    sx: float = 1.0
    sy: float = 1.0


_ANGLES = [(i / PROFILE_SAMPLES) * TAU for i in range(PROFILE_SAMPLES)]
_COS = [math.cos(a) for a in _ANGLES]
_SIN = [math.sin(a) for a in _ANGLES]


def silhouette(name, **pose):
    return Silhouette(list(PROFILES[name]), **pose)


def circle(radius, **pose):
    """Perfect circle: neutral base (point, bubble, fade target)."""
    return Silhouette([radius] * PROFILE_SAMPLES, **pose)


def blend(a, b, t, out=None):
    """Interpolate two silhouettes. out is reused to avoid allocating at 60 fps."""
    dst = out if out is not None else Silhouette([0.0] * PROFILE_SAMPLES)
    for i in range(PROFILE_SAMPLES):
        dst.radii[i] = lerp(a.radii[i], b.radii[i], t)
    # Rotation by the shortest path.
    d_rot = b.rot - a.rot
    while d_rot > math.pi:
        d_rot -= TAU
    while d_rot < -math.pi:
        d_rot += TAU
    dst.rot = a.rot + d_rot * t
    dst.cx = lerp(a.cx, b.cx, t)
    dst.cy = lerp(a.cy, b.cy, t)
    dst.sx = lerp(a.sx, b.sx, t)
    dst.sy = lerp(a.sy, b.sy, t)
    return dst


def to_points(s, scale, out=None):
    """Project a silhouette to screen points. scale = ball radius in viewBox units."""
    if out is None:
        out = [Point() for _ in range(PROFILE_SAMPLES)]
    cr = math.cos(s.rot)
    sr = math.sin(s.rot)
    for i in range(PROFILE_SAMPLES):
        r = s.radii[i]
        x = r * _COS[i]
        y = r * _SIN[i]
        rx = x * cr - y * sr
        ry = x * sr + y * cr
        p = out[i]
        p.x = (rx * s.sx + s.cx) * scale
        p.y = (ry * s.sy + s.cy) * scale
    return out


def closed_path(pts, tension=1.0 / 6.0):
    """Closed polyline -> Catmull-Rom cubics."""
    n = len(pts)
    if n < 3:
        return ""
    first = pts[0]
    d = "M" + js_str(r2(first.x)) + " " + js_str(r2(first.y))
    for i in range(n):
        p0 = pts[(i - 1 + n) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1x = p1.x + (p2.x - p0.x) * tension
        c1y = p1.y + (p2.y - p0.y) * tension
        c2x = p2.x - (p3.x - p1.x) * tension
        c2y = p2.y - (p3.y - p1.y) * tension
        d += (
            "C" + js_str(r2(c1x)) + " " + js_str(r2(c1y)) + " "
            + js_str(r2(c2x)) + " " + js_str(r2(c2y)) + " "
            + js_str(r2(p2.x)) + " " + js_str(r2(p2.y))
        )
    return d + "Z"


def profile_from_polygon(poly, cx, cy):
    """Arbitrary polygon -> radial profile, by ray casting from center."""
    radii = [0.0] * PROFILE_SAMPLES
    n = len(poly)
    for k in range(PROFILE_SAMPLES):
        dx = _COS[k]
        dy = _SIN[k]
        best = 0.0
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            ex = b.x - a.x
            ey = b.y - a.y
            den = dx * ey - dy * ex
            if abs(den) < 1e-9:
                continue
            px = a.x - cx
            py = a.y - cy
            t = (px * ey - py * ex) / den
            u = (px * dy - py * dx) / den
            if t > best and 0.0 <= u <= 1.0:
                best = t
        radii[k] = best
    return radii


def hull_of_circles(x1, y1, r1, x2, y2, r2v, steps=96):
    """Convex hull of two circles: the tapered bar of the vertical "!"."""
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy) or 1e-6
    base = math.atan2(dy, dx)
    spread = math.acos(max(-1.0, min(1.0, (r1 - r2v) / dist)))
    pts = []
    half = steps // 2
    for i in range(half + 1):
        a = base + spread + ((TAU - 2.0 * spread) * i) / half
        pts.append(Point(x1 + math.cos(a) * r1, y1 + math.sin(a) * r1))
    for i in range(half + 1):
        a = base - spread + ((2.0 * spread) * i) / half
        pts.append(Point(x2 + math.cos(a) * r2v, y2 + math.sin(a) * r2v))
    return pts


def radius_at_angle(radii, angle):
    """Profile radius in an arbitrary direction, interpolated between samples."""
    n = len(radii)
    t = ((((angle / TAU) % 1.0) + 1.0) % 1.0) * n
    i = math.floor(t)
    return lerp(radii[i % n], radii[(i + 1) % n], t - i)


def superellipse_profile(n, sx=1.0, sy=1.0):
    """|x/sx|^n + |y/sy|^n = 1. n ~ 4 gives the customiser's squircle."""
    out = []
    for i in range(PROFILE_SAMPLES):
        c = abs(_COS[i] / sx) ** n
        s = abs(_SIN[i] / sy) ** n
        out.append((c + s) ** (-1.0 / n))
    return out


def union_of_circles_profile(circles):
    """Radial profile of the UNION of disks: r(theta) = farthest ray/circle hit."""
    out = [0.0] * PROFILE_SAMPLES
    for i in range(PROFILE_SAMPLES):
        dx = _COS[i]
        dy = _SIN[i]
        best = 0.0
        for c in circles:
            b = dx * c["x"] + dy * c["y"]
            disc = b * b - (c["x"] * c["x"] + c["y"] * c["y"] - c["r"] * c["r"])
            if disc < 0:
                continue
            t = b + math.sqrt(disc)
            if t > best:
                best = t
        out[i] = best
    return out


def _rounded_polygon(verts, rc, arc_steps=10):
    out = []

    def normal(a, b):
        dx = b.x - a.x
        dy = b.y - a.y
        length = math.hypot(dx, dy) or 1.0
        return math.atan2(-dx / length, dy / length)

    n = len(verts)
    for i in range(n):
        prev = verts[(i - 1 + n) % n]
        cur = verts[i]
        nxt = verts[(i + 1) % n]
        a0 = normal(prev, cur)
        a1 = normal(cur, nxt)
        d = a1 - a0
        while d > math.pi:
            d -= TAU
        while d < -math.pi:
            d += TAU
        for k in range(arc_steps + 1):
            a = a0 + (d * k) / arc_steps
            out.append(Point(cur.x + math.cos(a) * rc, cur.y + math.sin(a) * rc))
    return out


def regular_polygon_profile(sides, radius, rc, rotation_deg=0.0):
    """Regular polygon with rounded corners, inscribed in radius."""
    rot = (rotation_deg * math.pi) / 180.0
    verts = []
    for i in range(sides):
        a = rot + (i / sides) * TAU
        verts.append(Point(math.cos(a) * (radius - rc), math.sin(a) * (radius - rc)))
    return profile_from_polygon(_rounded_polygon(verts, rc), 0.0, 0.0)


def poly_path(pts, scale=1.0):
    """Exact closed polyline: keeps straight segments (unlike closed_path)."""
    if len(pts) < 3:
        return ""
    d = ""
    for i in range(len(pts)):
        p = pts[i]
        prefix = "M" if i == 0 else "L"
        d += prefix + js_str(r2(p.x * scale)) + " " + js_str(r2(p.y * scale))
    return d + "Z"


def capsule_path(w, h):
    """Capsule (stadium) centred on the origin: the exact eye shape."""
    hw = max(w, 0.01) / 2.0
    hh = max(h, 0.01) / 2.0
    r = min(hw, hh)
    return (
        "M" + js_str(r2(-hw)) + " " + js_str(r2(-hh + r))
        + "A" + js_str(r2(r)) + " " + js_str(r2(r)) + " 0 0 1 " + js_str(r2(-hw + r)) + " " + js_str(r2(-hh))
        + "L" + js_str(r2(hw - r)) + " " + js_str(r2(-hh))
        + "A" + js_str(r2(r)) + " " + js_str(r2(r)) + " 0 0 1 " + js_str(r2(hw)) + " " + js_str(r2(-hh + r))
        + "L" + js_str(r2(hw)) + " " + js_str(r2(hh - r))
        + "A" + js_str(r2(r)) + " " + js_str(r2(r)) + " 0 0 1 " + js_str(r2(hw - r)) + " " + js_str(r2(hh))
        + "L" + js_str(r2(-hw + r)) + " " + js_str(r2(hh))
        + "A" + js_str(r2(r)) + " " + js_str(r2(r)) + " 0 0 1 " + js_str(r2(-hw)) + " " + js_str(r2(hh - r)) + "Z"
    )
