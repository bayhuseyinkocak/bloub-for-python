"""Export helpers: standalone SVG, PNG, animated SVG, GIF and MP4."""

import math

from ..repere import RAYON
from ..skins import SHAPES

# Margin around the widest shape (8%): lets a circular profile-picture crop
# avoid biting into the silhouette.
MARGE = 1.08

# Radius of the widest shape, in ball-radius units (computed, not hardcoded).
RAYON_MAX = max(max(s["radii"]) for s in SHAPES)

# Half-side of the export frame, in viewBox units. Tighter than the screen
# viewBox (158), because the screen margin only houses the animated states'
# rings.
DEMI_CADRE = math.ceil(RAYON * RAYON_MAX * MARGE)

# Half-side of the viewBox needed to export a CYCLE (rings reach 1.4x the radius).
DEMI_ECRAN = 158


def viewbox_export(demi=None):
    if demi is None:
        demi = DEMI_CADRE
    return " ".join(str(v) for v in (-demi, -demi, demi * 2, demi * 2))


# Avatar (rest) animation: 30 keys/sec over 3 seconds.
ANIM_CLES_PAR_SEC = 30
ANIM_SECONDES = 3
ANIM_IMAGES = ANIM_CLES_PAR_SEC * ANIM_SECONDES
ANIM_PAS = 1 / ANIM_CLES_PAR_SEC

# GIF: 20 fps is its useful ceiling (delay counts in hundredths of a second).
GIF_FPS = 20
GIF_IMAGES = GIF_FPS * ANIM_SECONDES
GIF_PAS = 1 / GIF_FPS
GIF_TAILLE = 320

# Cycle export formats, fps and size SEPARATED per format.
CYCLE_FPS = {"gif": 20, "mp4": 30}
CYCLE_TAILLE = {"gif": 320, "mp4": 1024}


def cycle_pas(format_):
    return 1 / CYCLE_FPS[format_]


def cycle_images(duree, format_):
    return max(1, round(duree * CYCLE_FPS[format_]))
