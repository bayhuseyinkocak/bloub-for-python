"""Standalone SVG and the SMIL-animated SVG (eyes animated in CSS)."""

import re

from ..math import js_str


def standalone_svg(frame, *, size, viewbox_half, color, paper, uid="bloub", aria_label="", render_svg):
    """Alias of render_svg kept here so the export path is explicit."""
    return render_svg(
        frame, size=size, viewbox_half=viewbox_half, color=color, paper=paper, uid=uid, aria_label=aria_label
    )


def animated_svg(base, matrices, duration):
    """Inject eye animation into an already-rendered SVG.

    The body is not animated: at rest the silhouette moves only ~1.5px over
    three seconds. All the weight of the animation is in the gaze. Interpolation
    is done by the browser, so the animation is smooth at screen rate.
    """
    if len(matrices) < 2:
        raise ValueError("at least two keyframes required")
    m = re.search(r"<mask[\s\S]*?</mask>", base)
    if not m:
        raise ValueError("mask not found")
    mask = m.group(0)

    counter = [0]

    def repl(_m):
        cls = 'class="oeil' + str(counter[0]) + '"'
        counter[0] += 1
        return cls

    mask_anime = re.sub(r'transform="matrix\([^)]*\)"', repl, mask)
    n = counter[0]
    if n == 0:
        raise ValueError("no eye to animate")
    if len(matrices[0]) != n:
        raise ValueError(f"{n} eyes in mask, {len(matrices[0])} per keyframe")

    pas = 100.0 / (len(matrices) - 1)
    regles = []
    for oeil in range(n):
        etapes = "".join(
            str(round(i * pas, 3)) + "%{transform:" + mtx[oeil] + "}" for i, mtx in enumerate(matrices)
        )
        regles.append("@keyframes oeil" + str(oeil) + "{" + etapes + "}")

    style = (
        "<style>"
        ".oeil0,.oeil1{transform-box:view-box;transform-origin:0 0;"
        "animation-duration:" + js_str(duration) + "s;animation-iteration-count:infinite;"
        "animation-timing-function:linear;animation-direction:alternate}"
        + "".join(".oeil" + str(i) + "{animation-name:oeil" + str(i) + "}" for i in range(n))
        + "".join(regles)
        + "</style>"
    )
    return base.replace(mask, mask_anime).replace("</svg>", style + "</svg>")
