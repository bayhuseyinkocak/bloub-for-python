"""The clock-free engine: sample(t) is a pure function of time.

Consequence: pause, resume, slow motion and jumping to an arbitrary date all
produce exactly the same image, and the render is testable with no DOM.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .decor import arc_render
from .expressions import blend_expression
from .eyefit import decalage_des_yeux
from .face import blink_scale, eye_poses, liveliness
from .math import EASINGS, clamp, js_str, lerp, r2
from .profiles import PROFILE_SAMPLES
from .shape import Point, Silhouette, blend, capsule_path, closed_path, radius_at_angle, to_points
from .states import STATE_BY_ID

easeOutQuint = EASINGS["easeOutQuint"]


@dataclass
class RenderedEye:
    d: str
    matrix: str
    alpha: float


@dataclass
class BotFrame:
    bodyPath: str
    bodyAlpha: float
    eyes: List[RenderedEye]
    dots: list
    dotsBehind: bool
    arcs: list
    notif: Optional[dict]
    notch: Optional[dict]


NO_LOOK = {"yaw": 0.0, "pitch": 0.0, "mix": 0.0, "spin": 0.0, "wander": 1.0}


def _lerp_look(a, b, t):
    return {
        "yaw": lerp(a["yaw"], b["yaw"], t),
        "pitch": lerp(a["pitch"], b["pitch"], t),
        "mix": lerp(a["mix"], b["mix"], t),
        "spin": lerp(a["spin"], b["spin"], t),
        "wander": lerp(a["wander"], b["wander"], t),
    }


def _lerp_eye(a, b, t):
    return {
        "w": lerp(a["w"], b["w"], t),
        "h": lerp(a["h"], b["h"], t),
        "open": lerp(a["open"], b["open"], t),
        "tilt": lerp(a.get("tilt", 0.0), b.get("tilt", 0.0), t),
    }


def _blend_pose(a, b, t):
    """Interpolate two poses. The decor cross-fades in opacity, not geometry."""
    out = 1.0 - t
    return {
        "sil": blend(a["sil"], b["sil"], t),
        "offX": lerp(a["offX"], b["offX"], t),
        "offY": lerp(a["offY"], b["offY"], t),
        "gaze": {
            "yaw": lerp(a["gaze"]["yaw"], b["gaze"]["yaw"], t),
            "pitch": lerp(a["gaze"]["pitch"], b["gaze"]["pitch"], t),
            "roll": lerp(a["gaze"]["roll"], b["gaze"]["roll"], t),
        },
        "split": lerp(a["split"], b["split"], t),
        "eyes": [_lerp_eye(a["eyes"][0], b["eyes"][0], t), _lerp_eye(a["eyes"][1], b["eyes"][1], t)],
        "eyeAlpha": lerp(a["eyeAlpha"], b["eyeAlpha"], t),
        "bodyAlpha": lerp(a["bodyAlpha"], b["bodyAlpha"], t),
        "dots": [
            dict(d, opacity=d["opacity"] * out) for d in a["dots"]
        ] + [
            dict(d, opacity=d["opacity"] * t) for d in b["dots"]
        ],
        "arcs": [
            dict(r, id="a" + r["id"], opacity=r["opacity"] * out) for r in a["arcs"]
        ] + [
            dict(r, id="b" + r["id"], opacity=r["opacity"] * t) for r in b["arcs"]
        ],
        "notif": a["notif"] if t < 0.5 else b["notif"],
        "dotsBehind": a["dotsBehind"] if t < 0.5 else b["dotsBehind"],
    }


class BotEngine:
    """Engine without a clock: sample(t) is a pure function of time."""

    SHAPE_MORPH = 0.45
    LOOK_MORPH = 0.24

    def __init__(self, scale=100.0, initial="idle", shape=None, expression=None):
        self.scale = scale
        self.cur = initial
        self.prev = None
        self.departFige = None
        self.tCur = 0.0
        self.tPrev = 0.0
        self.blinkAt = -10.0
        self.pts = [Point() for _ in range(PROFILE_SAMPLES)]
        self.shape = shape
        self.shapePrev = None
        self.shapeAt = -10.0
        self.expr = expression
        self.exprPrev = None
        self.exprAt = -10.0
        self.look = dict(NO_LOOK)
        self.lookPrev = dict(NO_LOOK)
        self.lookAt = -10.0
        self.lookMorph = BotEngine.LOOK_MORPH

    # -- expression / shape / look (timestamped setters, never read during sample) --

    def set_expression(self, expression, now=0.0):
        if expression is self.expr:
            return
        self.exprPrev = self.expr
        self.expr = expression
        self.exprAt = now

    def _expr_at_time(self, now):
        to = self.expr
        from_ = self.exprPrev
        if to is None or from_ is None:
            return to
        k = (now - self.exprAt) / BotEngine.SHAPE_MORPH
        if k >= 1:
            return to
        return blend_expression(from_, to, easeOutQuint(clamp(k)))

    def set_shape(self, radii, now=0.0):
        if radii is self.shape:
            return
        self.shapePrev = self.shape
        self.shape = radii
        self.shapeAt = now

    def _shape_at_time(self, now):
        to = self.shape
        from_ = self.shapePrev
        if to is None or from_ is None:
            return to
        k = (now - self.shapeAt) / BotEngine.SHAPE_MORPH
        if k >= 1:
            return to
        t = easeOutQuint(clamp(k))
        return [lerp(from_[i], r, t) for i, r in enumerate(to)]

    def set_look(self, look, now, morph=None):
        if morph is None:
            morph = BotEngine.LOOK_MORPH
        if look is not None:
            s = look["yaw"] + look["pitch"] + look["mix"] + look["spin"] + look["wander"]
            if not math.isfinite(s):
                return
        self.lookPrev = self._look_at_time(now)
        self.look = look if look is not None else dict(NO_LOOK)
        self.lookAt = now
        self.lookMorph = morph

    def _look_at_time(self, now):
        k = (now - self.lookAt) / self.lookMorph
        if k >= 1:
            return self.look
        return _lerp_look(self.lookPrev, self.look, easeOutQuint(clamp(k)))

    # -- pose construction --

    def _posed(self, def_, t, shape, expr):
        pose = def_["pose"](t)
        if def_["baseBody"] and shape is not None:
            sil = pose["sil"]
            pose = dict(pose, sil=Silhouette(shape, rot=sil.rot, cx=sil.cx, cy=sil.cy, sx=sil.sx, sy=sil.sy))
        if def_["baseFace"] and expr is not None:
            pose = dict(pose, gaze=expr["gaze"], split=expr["split"], eyes=expr["eyes"])
        return pose

    def _decalage_at_time(self, now, state):
        def sur_axe(debut, duree, a, b):
            k = (now - debut) / duree
            if k >= 1:
                return b
            t = easeOutQuint(clamp(k))
            return {"x": lerp(a["x"], b["x"], t), "y": lerp(a["y"], b["y"], t)}

        def par_forme(radii):
            return sur_axe(
                self.exprAt,
                BotEngine.SHAPE_MORPH,
                decalage_des_yeux(radii, state, self.exprPrev["id"] if self.exprPrev is not None else None),
                decalage_des_yeux(radii, state, self.expr["id"] if self.expr is not None else None),
            )

        return sur_axe(
            self.shapeAt,
            BotEngine.SHAPE_MORPH,
            par_forme(self.shapePrev),
            par_forme(self.shape),
        )

    @property
    def state(self):
        return self.cur

    def reset(self, id_, now):
        """Restart on id with NO previous state, as a fresh engine."""
        self.cur = id_
        self.prev = None
        self.departFige = None
        self.tCur = now
        self.tPrev = now
        self.blinkAt = -10.0

    def _origine(self, now, shape, expr):
        if self.departFige is not None:
            return self.departFige
        if self.prev is None:
            return None
        prev_def = STATE_BY_ID[self.prev]
        return self._posed(prev_def, max(0.0, now - self.tPrev), shape, expr)

    def _pose_composee(self, now):
        def_ = STATE_BY_ID[self.cur]
        shape = self._shape_at_time(now)
        expr = self._expr_at_time(now)
        pose = self._posed(def_, max(0.0, now - self.tCur), shape, expr)
        since = now - self.tCur
        if since >= def_["morph"]:
            return pose
        origine = self._origine(now, shape, expr)
        if origine is None:
            return pose
        return _blend_pose(origine, pose, easeOutQuint(clamp(since / def_["morph"])))

    def set_state(self, id_, now):
        if id_ == self.cur:
            return
        morph = STATE_BY_ID[self.cur]["morph"]
        en_plein_fondu = self.prev is not None and (now - self.tCur) < morph
        self.departFige = self._pose_composee(now) if en_plein_fondu else None
        self.prev = self.cur
        self.tPrev = self.tCur
        self.cur = id_
        self.tCur = now
        if STATE_BY_ID[id_].get("blinkIn"):
            self.blinkAt = now

    def sample(self, now):
        R = self.scale
        def_ = STATE_BY_ID[self.cur]
        shape = self._shape_at_time(now)
        expr = self._expr_at_time(now)
        pose = self._posed(def_, max(0.0, now - self.tCur), shape, expr)
        decalage = self._decalage_at_time(now, self.cur)

        # -- transition --
        since = now - self.tCur
        origine = self._origine(now, shape, expr) if since < def_["morph"] else None
        if origine is not None:
            ratio = easeOutQuint(clamp(since / def_["morph"]))
            pose = _blend_pose(origine, pose, ratio)
            quitte = self.prev
            if quitte is not None:
                avant = self._decalage_at_time(now, quitte)
                decalage = {"x": lerp(avant["x"], decalage["x"], ratio), "y": lerp(avant["y"], decalage["y"], ratio)}

        # -- rest life --
        alive = pose["eyeAlpha"] > 0.01
        look = self._look_at_time(now)
        life = liveliness(now, wander=(look["wander"] if alive else 0.0), blink=alive)

        gaze = {
            "yaw": lerp(pose["gaze"]["yaw"], look["yaw"], look["mix"]) + life["dYaw"] - look["spin"],
            "pitch": lerp(pose["gaze"]["pitch"], look["pitch"], look["mix"]) + life["dPitch"],
            "roll": pose["gaze"]["roll"] + life["dRoll"],
        }

        forced = clamp((now - self.blinkAt) / 0.2)
        forced_lid = abs(forced * 2.0 - 1.0) if forced < 1.0 else 1.0
        lid = min(life["lid"], forced_lid)

        offX = pose["offX"] + life["driftX"]
        offY = pose["offY"] + life["driftY"]

        # -- body --
        sil = Silhouette(
            radii=list(pose["sil"].radii),
            rot=pose["sil"].rot,
            cx=pose["sil"].cx + offX,
            cy=pose["sil"].cy + offY,
            sx=pose["sil"].sx,
            sy=pose["sil"].sy * life["breath"],
        )
        body_path = closed_path(to_points(sil, R, self.pts))

        # -- eyes --
        def body_radius(x, y):
            return radius_at_angle(pose["sil"].radii, math.atan2(y, x) - pose["sil"].rot)

        eyes = []
        if pose["eyeAlpha"] > 0.01:
            poses = eye_poses(gaze, R, pose["split"])
            for i in range(2):
                e = poses[i]
                if e["depth"] <= 0.02:
                    continue
                cfg = pose["eyes"][i]
                fit = body_radius(e["x"], e["y"])
                phi = (cfg.get("tilt", 0.0) * math.pi) / 180.0
                cp = math.cos(phi)
                sp = math.sin(phi)
                ax = e["a"] * cp + e["c"] * sp
                ay = e["b"] * cp + e["d"] * sp
                cx2 = -e["a"] * sp + e["c"] * cp
                cy2 = -e["b"] * sp + e["d"] * cp
                k = blink_scale(min(lid, cfg["open"]))
                eyes.append(RenderedEye(
                    d=capsule_path(cfg["w"] * R, cfg["h"] * R),
                    matrix="matrix("
                    + js_str(r2(ax)) + ","
                    + js_str(r2(ay * k)) + ","
                    + js_str(r2(cx2)) + ","
                    + js_str(r2(cy2 * k)) + ","
                    + js_str(r2(e["x"] * fit + (offX + decalage["x"]) * R)) + ","
                    + js_str(r2(e["y"] * fit + (offY + decalage["y"]) * R))
                    + ")",
                    alpha=pose["eyeAlpha"] * clamp(e["depth"] / 0.12),
                ))

        # -- decor --
        dots = [
            dict(p, x=(p["x"] + offX) * R, y=(p["y"] + offY) * R, r=p["r"] * R)
            for p in pose["dots"] if p["opacity"] > 0.01 and p["r"] > 0.0005
        ]

        if pose["notif"] is not None:
            n_fit = body_radius(pose["notif"]["x"], pose["notif"]["y"])
            nx = (pose["notif"]["x"] * n_fit + offX) * R
            ny = (pose["notif"]["y"] * n_fit + offY) * R
            notif = {"x": nx, "y": ny, "r": pose["notif"]["r"] * R}
            notch = {"x": nx, "y": ny, "r": pose["notif"]["notch"] * R}
        else:
            notif = None
            notch = None

        return BotFrame(
            bodyPath=body_path,
            bodyAlpha=pose["bodyAlpha"],
            eyes=eyes,
            dots=dots,
            dotsBehind=pose["dotsBehind"],
            arcs=[arc_render(a["seed"], a["t"], R, a["id"], a["opacity"]) for a in pose["arcs"] if a["opacity"] > 0.01],
            notif=notif,
            notch=notch,
        )
