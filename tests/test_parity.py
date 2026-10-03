"""Cross-language parity: the Python engine reproduces the TypeScript reference
exactly (golden fixtures generated from the original repo, in tests/fixtures/)."""

import json
from pathlib import Path

import pytest

from bloub.cycles import block_at, offset_of
from bloub.engine import BotEngine

FIXTURES = Path(__file__).parent / "fixtures"


def _frame_to_dict(f):
    return {
        "bodyPath": f.bodyPath,
        "bodyAlpha": f.bodyAlpha,
        "eyes": [{"d": e.d, "matrix": e.matrix, "alpha": e.alpha} for e in f.eyes],
        "dots": f.dots,
        "dotsBehind": f.dotsBehind,
        "arcs": f.arcs,
        "notif": f.notif,
        "notch": f.notch,
    }


def _cmp(a, b, path="", tol=1e-7):
    if isinstance(a, str) or isinstance(b, str):
        assert a == b, f"{path}: {a!r} != {b!r}"
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        assert abs(a - b) <= tol, f"{path}: {a!r} != {b!r} (diff {abs(a - b):.2e})"
    elif a is None or b is None:
        assert a is None and b is None, f"{path}: {a!r} != {b!r}"
    elif isinstance(a, bool) and isinstance(b, bool):
        assert a == b, f"{path}: {a!r} != {b!r}"
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), f"{path}: len {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _cmp(x, y, f"{path}[{i}]", tol)
    elif isinstance(a, dict) and isinstance(b, dict):
        assert set(a.keys()) == set(b.keys()), f"{path}: keys {list(a.keys())} vs {list(b.keys())}"
        for k in a:
            _cmp(a[k], b[k], f"{path}.{k}", tol)
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


def _load(name):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def test_constants():
    c = _load("constants.json")
    from bloub import decor, face, profiles, repere, skins
    from bloub import expressions as expr_mod
    from bloub import states as st_mod
    from bloub import cycles

    def close(a, b, tol=1e-9):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) <= tol
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
        return a == b

    assert close(profiles.PROFILES, c["PROFILES"])
    assert close(decor.RINGS, c["RINGS"])
    assert close(decor.SWOOSH, c["SWOOSH"])
    assert close(decor.COMET_RIBBONS, c["COMET_RIBBONS"])
    assert close(decor.DOT_X, c["DOT_X"])
    assert face.EYE_SPLIT == c["EYE_SPLIT"]
    # Analytically-built shapes differ from JS by <=1 ULP (libm vs V8); invisible after r2 rounding.
    assert close({s["id"]: s["radii"] for s in skins.SHAPES}, {s["id"]: s["radii"] for s in c["SHAPES"]})
    assert skins.COLORS == c["COLORS"]
    exp = [{"id": x["id"], "gaze": x["gaze"], "split": x["split"], "eyes": x["eyes"]} for x in expr_mod.EXPRESSIONS]
    assert close(exp, c["EXPRESSIONS"])
    st_meta = [{"id": s["id"], "duration": s["duration"], "minDuration": s.get("minDuration"),
                "morph": s["morph"], "blinkIn": s["blinkIn"], "baseBody": s["baseBody"],
                "baseFace": s["baseFace"]} for s in st_mod.STATES]
    assert close(st_meta, c["STATES"])
    assert st_mod.SEQUENCE == c["SEQUENCE"]
    assert close(st_mod.POSES, c["POSES"])
    assert cycles.MIN_BLOCK == c["MIN_BLOCK"]
    assert close(cycles.default_cycle(), c["defaultCycle"])


@pytest.mark.parametrize("state_id", list(json.load(open(FIXTURES / "frames.json"))))
def test_per_state_frames(state_id):
    frames = _load("frames.json")[state_id]
    eng = BotEngine(100, state_id)
    for t_str, expected in frames.items():
        got = _frame_to_dict(eng.sample(float(t_str)))
        _cmp(got, expected, f"{state_id}@{t_str}")


def test_transitions():
    trans = _load("transitions.json")
    eng = BotEngine(100, "idle")
    eng.set_state("idle", 0)
    eng.set_state("orbit", 0.2)
    eng.set_state("burst", 1.4)
    for t_str, expected in trans.items():
        got = _frame_to_dict(eng.sample(float(t_str)))
        _cmp(got, expected, f"trans@{t_str}")


def test_cycle():
    cyc = _load("cycle.json")
    blocs = cyc["blocks"]

    def rend_at(t):
        idx = block_at(blocs, t)["index"]
        eng = BotEngine(100, blocs[idx]["state"])
        for i in range(idx + 1):
            off = offset_of(blocs, i)
            st = blocs[i]["state"]
            if i == 0:
                if eng.state != st:
                    eng.reset(st, off)
            else:
                eng.set_state(st, off)
        return eng.sample(t)

    for t_str, expected in cyc["frames"].items():
        got = _frame_to_dict(rend_at(float(t_str)))
        _cmp(got, expected, f"cycle@{t_str}")


def test_eyefit():
    e = _load("eyefit.json")
    from bloub import eyefit
    from bloub.skins import SHAPE_BY_ID
    for shape_id, row in e.items():
        radii = SHAPE_BY_ID[shape_id]["radii"]
        for key, v in row.items():
            state, expr = key.split("|")
            got = eyefit.decalage_des_yeux(radii, state, expr or None)
            assert abs(got["x"] - v["x"]) <= 1e-9 and abs(got["y"] - v["y"]) <= 1e-9, f"{shape_id} {key}"
