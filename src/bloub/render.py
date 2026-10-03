"""SVG rendering: turn a BotFrame into a standalone SVG document.

This is the pure-string equivalent of the BloubBot.vue template: a <mask> whose
holes are the eyes (and the notification notch), layered orbit arcs split
front/back, and the body painted paper-colour with an ink fill masked by the
holes.
"""

from .decor import NOTIF_BLUE
from .math import js_str
from .repere import DEMI_VIEWBOX, RAYON
from .skins import mix_hex


def _dot(dot, ink, paper):
    fill = dot.get("color") or (ink if "depth" not in dot else mix_hex(paper, ink, dot["depth"]))
    if "d" in dot:
        return (
            '<path d="' + dot["d"] + '" fill="' + fill + '" opacity="' + js_str(dot["opacity"])
            + '" transform="translate(' + js_str(dot["x"]) + " " + js_str(dot["y"])
            + ") rotate(" + js_str(dot.get("rot", 0.0)) + ") scale(" + js_str(RAYON) + ')"/>'
        )
    return (
        '<circle cx="' + js_str(dot["x"]) + '" cy="' + js_str(dot["y"]) + '" r="' + js_str(dot["r"])
        + '" fill="' + fill + '" opacity="' + js_str(dot["opacity"]) + '"/>'
    )


def render_svg(frame, *, size=320, viewbox_half=DEMI_VIEWBOX, color="#0a0a0c",
               paper="#f9f9f9", uid="bloub", aria_label=""):
    """Serialize a BotFrame to a standalone SVG string."""
    vb = viewbox_half
    mask_id = "bot-mask-" + uid
    p = []
    p.append(
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + js_str(size) + '" height="' + js_str(size)
        + '" viewBox="' + js_str(-vb) + " " + js_str(-vb) + " " + js_str(vb * 2) + " " + js_str(vb * 2)
        + '" role="img" aria-label="' + aria_label + '">'
    )
    p.append("<defs>")
    p.append(
        '<mask id="' + mask_id + '" maskUnits="userSpaceOnUse" x="' + js_str(-vb) + '" y="' + js_str(-vb)
        + '" width="' + js_str(vb * 2) + '" height="' + js_str(vb * 2) + '">'
    )
    p.append('<path d="' + frame.bodyPath + '" fill="#fff"/>')
    for eye in frame.eyes:
        p.append('<path d="' + eye.d + '" transform="' + eye.matrix + '" opacity="' + js_str(eye.alpha) + '" fill="#000"/>')
    if frame.notch is not None:
        p.append('<circle cx="' + js_str(frame.notch["x"]) + '" cy="' + js_str(frame.notch["y"])
                 + '" r="' + js_str(frame.notch["r"]) + '" fill="#000"/>')
    p.append("</mask>")
    for arc in frame.arcs:
        gid = uid + "-" + arc["id"]
        stops = "".join(
            '<stop offset="' + js_str(i / (len(arc["grad"]["stops"]) - 1)) + '" stop-color="' + c + '"/>'
            for i, c in enumerate(arc["grad"]["stops"])
        )
        p.append(
            '<linearGradient id="' + gid + '" gradientUnits="userSpaceOnUse" x1="' + js_str(arc["grad"]["x1"])
            + '" y1="' + js_str(arc["grad"]["y1"]) + '" x2="' + js_str(arc["grad"]["x2"])
            + '" y2="' + js_str(arc["grad"]["y2"]) + '">' + stops + "</linearGradient>"
        )
    p.append("</defs>")

    p.append('<g fill="none" stroke-linecap="round">')
    for arc in frame.arcs:
        gid = uid + "-" + arc["id"]
        p.append('<path d="' + arc["back"] + '" stroke="url(#' + gid + ')" stroke-width="' + js_str(arc["width"])
                 + '" opacity="' + js_str(arc["opacity"]) + '"/>')
    p.append("</g>")

    if frame.dotsBehind:
        p.append("<g>")
        for dot in frame.dots:
            p.append(_dot(dot, color, paper))
        p.append("</g>")

    p.append('<g opacity="' + js_str(frame.bodyAlpha) + '">')
    p.append('<path d="' + frame.bodyPath + '" fill="' + paper + '"/>')
    p.append('<g mask="url(#' + mask_id + ')">')
    p.append('<rect x="' + js_str(-vb) + '" y="' + js_str(-vb) + '" width="' + js_str(vb * 2)
             + '" height="' + js_str(vb * 2) + '" fill="' + color + '"/>')
    p.append("</g></g>")

    if not frame.dotsBehind:
        p.append("<g>")
        for dot in frame.dots:
            p.append(_dot(dot, color, paper))
        p.append("</g>")

    if frame.notif is not None:
        p.append('<circle cx="' + js_str(frame.notif["x"]) + '" cy="' + js_str(frame.notif["y"])
                 + '" r="' + js_str(frame.notif["r"]) + '" fill="' + NOTIF_BLUE + '"/>')

    p.append('<g fill="none" stroke-linecap="round">')
    for arc in frame.arcs:
        gid = uid + "-" + arc["id"]
        p.append('<path d="' + arc["front"] + '" stroke="url(#' + gid + ')" stroke-width="' + js_str(arc["width"])
                 + '" opacity="' + js_str(arc["opacity"]) + '"/>')
    p.append("</g>")
    p.append("</svg>")
    return "".join(p)
