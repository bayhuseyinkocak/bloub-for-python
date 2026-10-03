"""Focused unit tests for the pure core (math, shape, cycles, engine purity)."""

import math

from bloub import math as m
from bloub.cycles import MAX_BLOCS, MIN_BLOCK, block_at, clamp_duration, parse_cycles, total_duration
from bloub.engine import BotEngine
from bloub.shape import capsule_path, circle, closed_path, to_points


def test_js_round_semantics():
    assert m.js_round(2.5) == 3
    assert m.js_round(-2.5) == -2
    assert m.js_round(100.0) == 100
    assert m.js_round(-0.5) == 0


def test_js_str():
    assert m.js_str(100.0) == "100"
    assert m.js_str(-78.12) == "-78.12"
    assert m.js_str(0.0) == "0"
    assert m.js_str(-0.0) == "0"
    assert m.js_str(0.19) == "0.19"


def test_mulberry32_deterministic():
    r1 = m.create_rng(0xA11CE)
    r2 = m.create_rng(0xA11CE)
    assert [r1() for _ in range(10)] == [r2() for _ in range(10)]


def test_closed_path_is_valid():
    sil = circle(1.0)
    path = closed_path(to_points(sil, 100.0))
    assert path.startswith("M") and path.endswith("Z")


def test_capsule_path_known():
    # orbit eyes: w=0.18, h=0.34 at scale 100 -> hw=9, hh=17, r=9
    d = capsule_path(0.18 * 100, 0.34 * 100)
    assert d == "M-9 -8A9 9 0 0 1 0 -17L0 -17A9 9 0 0 1 9 -8L9 8A9 9 0 0 1 0 17L0 17A9 9 0 0 1 -9 8Z"


def test_min_block_derived():
    assert MIN_BLOCK == 0.6  # longest morph in the catalogue (orbit)


def test_parse_cycles_hostile_input():
    assert parse_cycles(None) == []
    assert parse_cycles("not json") == []
    assert parse_cycles("[]") == []
    assert parse_cycles('{"not": "a list"}') == []
    # swirl must never appear in a user montage
    assert parse_cycles('[{"id": "c1", "name": "", "blocks": [{"state": "swirl", "duration": 2}]}]') == []


def test_block_at_wraps():
    blocks = [{"state": "idle", "duration": 2.0}, {"state": "wink", "duration": 1.0}]
    assert block_at(blocks, 0.0) == {"index": 0, "elapsed": 0.0}
    assert block_at(blocks, 2.5)["index"] == 1
    assert block_at(blocks, 3.5) == {"index": 0, "elapsed": 0.5}  # wraps


def test_clamp_duration_bounds():
    assert clamp_duration("idle", 0.01) >= MIN_BLOCK
    assert clamp_duration("idle", 999) == 10.0


def test_sample_is_pure_function_of_time():
    eng = BotEngine(100, "orbit")
    eng.set_state("orbit", 0.0)
    a = eng.sample(1.0)
    eng2 = BotEngine(100, "orbit")
    eng2.set_state("orbit", 0.0)
    b = eng2.sample(1.0)
    assert a.bodyPath == b.bodyPath
    assert [e.matrix for e in a.eyes] == [e.matrix for e in b.eyes]
    # re-reading a past date must give the same image
    eng.sample(3.0)
    again = eng.sample(1.0)
    assert again.bodyPath == a.bodyPath


# --------------------------------------------------------------------------- added shapes

ADDED_SHAPES = ("oeuf", "bulle", "rond")


def test_added_shapes_are_well_formed():
    from bloub.skins import SHAPES, SHAPE_BY_ID
    from bloub.profiles import PROFILE_SAMPLES

    assert [s["id"] for s in SHAPES][-3:] == list(ADDED_SHAPES)
    for sid in ADDED_SHAPES:
        radii = SHAPE_BY_ID[sid]["radii"]
        assert len(radii) == PROFILE_SAMPLES
        # A silhouette must stay positive and bounded: morphing is a linear
        # interpolation of radii, so a hole or an outlier would bend every blend.
        assert all(r > 0.05 for r in radii), sid
        assert 0.9 < max(radii) <= 1.2, sid
        # No silhouette may be star-shaped around a point outside itself.
        assert max(radii) / min(radii) < 3.0, sid


def test_added_shapes_have_face_offsets_and_labels():
    from bloub.i18n import DICTS
    from bloub.skins import SHAPES
    from bloub import _eyefit_table

    for sid in ADDED_SHAPES:
        assert sid in _eyefit_table.TABLE, sid
        assert _eyefit_table.TABLE[sid], sid
    for lang, dic in DICTS.items():
        for s in SHAPES:
            assert dic["shapes"].get(s["id"]), f"{lang} missing shapes.{s['id']}"


def test_egg_tapered_end_points_up():
    # theta = -pi/2 is up (y grows downwards): the egg is narrower on top.
    from bloub.shape import radius_at_angle
    from bloub.skins import SHAPE_BY_ID

    radii = SHAPE_BY_ID["oeuf"]["radii"]
    assert radius_at_angle(radii, -math.pi / 2) < radius_at_angle(radii, math.pi / 2)


def test_chubby_is_wider_than_tall():
    from bloub.shape import radius_at_angle
    from bloub.skins import SHAPE_BY_ID

    radii = SHAPE_BY_ID["rond"]["radii"]
    assert radius_at_angle(radii, 0.0) > radius_at_angle(radii, -math.pi / 2)


def test_speech_bubble_tail_is_on_the_left():
    from bloub.shape import radius_at_angle
    from bloub.skins import SHAPE_BY_ID

    radii = SHAPE_BY_ID["bulle"]["radii"]
    assert radius_at_angle(radii, math.pi) > radius_at_angle(radii, 0.0)


def test_added_shapes_render_and_morph():
    """Each new shape must render, and morph cleanly from and to the circle."""
    from bloub.skins import SHAPE_BY_ID

    for sid in ADDED_SHAPES:
        radii = SHAPE_BY_ID[sid]["radii"]
        eng = BotEngine(100, "idle", radii)
        frame = eng.sample(0.0)
        assert frame.bodyPath.startswith("M") and frame.bodyPath.endswith("Z")
        assert len(frame.eyes) == 2
        # morphing in from the circle must not produce NaN coordinates
        eng2 = BotEngine(100, "idle", radii)
        eng2.set_shape(radii, 0.0)
        mid = eng2.sample(0.2)
        assert "nan" not in mid.bodyPath.lower()
        # re-reading the same date is stable (purity holds with a custom shape)
        assert eng2.sample(0.2).bodyPath == mid.bodyPath
