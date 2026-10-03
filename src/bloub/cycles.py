"""A cycle is a montage: a list of blocks, each a state held for a chosen duration.

Pure data, no clock, no framework import: the same cycle can be read by the
tests, the player and the timeline.
"""

import json
import math

from .math import js_round
from .states import SEQUENCE, STATE_BY_ID, STATES

# Common floor to all blocks, DERIVED from the catalogue (not written by hand).
MIN_BLOCK = max(s["morph"] for s in STATES)
MAX_BLOCK = 10
MAX_BLOCS = 200
MAX_CYCLES = 50
STEP = 0.1

DEFAULT_CYCLE_ID = "defaut"


def min_duration_of(state):
    d = STATE_BY_ID.get(state)
    md = d.get("minDuration") if d else None
    return max(MIN_BLOCK, md if md is not None else MIN_BLOCK)


def clamp_duration(state, seconds):
    snapped = js_round(seconds / STEP) * STEP
    bounded = min(MAX_BLOCK, max(min_duration_of(state), snapped))
    return js_round(bounded * 100.0) / 100.0


def make_block(state):
    d = STATE_BY_ID.get(state)
    return {"state": state, "duration": clamp_duration(state, d["duration"] if d else 2)}


def default_cycle():
    return {"name": "", "id": DEFAULT_CYCLE_ID, "blocks": [make_block(s) for s in SEQUENCE]}


def total_duration(blocks):
    return sum(b["duration"] for b in blocks)


def offset_of(blocks, index):
    acc = 0.0
    for i in range(min(index, len(blocks))):
        acc += blocks[i]["duration"]
    return acc


def block_at(blocks, t):
    total = total_duration(blocks)
    if not blocks or total <= 0:
        return {"index": 0, "elapsed": 0.0}
    wrapped = t if (t >= 0 and t < total) else ((t % total) + total) % total
    acc = 0.0
    for i, b in enumerate(blocks):
        end = acc + b["duration"]
        if wrapped < end:
            return {"index": i, "elapsed": wrapped - acc}
        acc = end
    return {"index": len(blocks) - 1, "elapsed": 0.0}


def blocks_with(blocks, state):
    if len(blocks) >= MAX_BLOCS:
        return blocks
    return blocks + [make_block(state)]


def move_block(blocks, from_, to):
    nxt = list(blocks)
    moved = nxt.pop(from_)
    nxt.insert(min(max(to, 0), len(nxt)), moved)
    return nxt


def unique_name(base, cycles):
    taken = {c["name"] for c in cycles}
    if base not in taken:
        return base
    n = 2
    while base + " " + str(n) in taken:
        n += 1
    return base + " " + str(n)


def next_cycle_id(cycles):
    taken = {c["id"] for c in cycles}
    n = 1
    while "c" + str(n) in taken:
        n += 1
    return "c" + str(n)


def _parse_block(raw):
    if not isinstance(raw, dict):
        return None
    state = raw.get("state")
    duration = raw.get("duration")
    if not isinstance(state, str) or state not in SEQUENCE:
        return None
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(duration):
        return None
    return {"state": state, "duration": clamp_duration(state, duration)}


def _parse_cycle(raw, seen):
    if not isinstance(raw, dict):
        return None
    id_ = raw.get("id")
    name = raw.get("name")
    blocks = raw.get("blocks")
    if not isinstance(id_, str) or not id_:
        return None
    if not isinstance(name, str):
        return None
    if not isinstance(blocks, list):
        return None
    kept = []
    for b in blocks[:MAX_BLOCS]:
        pb = _parse_block(b)
        if pb is not None:
            kept.append(pb)
    if not kept:
        return None
    if any(c["id"] == id_ for c in seen):
        return None
    return {"id": id_, "name": name, "blocks": kept}


def parse_cycles(raw):
    """Storage is user-editable, so it is not trusted: anything unreadable is
    silently dropped rather than breaking the app at startup."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data[:MAX_CYCLES]:
        c = _parse_cycle(item, out)
        if c:
            out.append(c)
    return out
