"""A convenient, high-level wrapper tying engine + skins + rendering together.

This is what the Streamlit app (and any other consumer) uses.
"""

from .engine import BotEngine
from .expressions import EXPRESSION_BY_ID
from .repere import DEMI_VIEWBOX, RAYON
from .render import render_svg
from .skins import COLOR_BY_ID, SHAPE_BY_ID


class Bot:
    def __init__(self, shape="cercle", color="encre", expression="neutre", scale=RAYON, paper="#f9f9f9"):
        self.shape_id = shape
        self.color_id = color
        self.expression_id = expression
        self.scale = scale
        self.paper = paper
        self.engine = BotEngine(
            scale, "idle",
            SHAPE_BY_ID.get(shape, SHAPE_BY_ID["cercle"])["radii"],
            EXPRESSION_BY_ID.get(expression),
        )

    @property
    def color_hex(self):
        return COLOR_BY_ID.get(self.color_id, COLOR_BY_ID["encre"])["hex"]

    def frame(self, t=0.0):
        return self.engine.sample(t)

    def svg(self, t=0.0, size=320, viewbox_half=DEMI_VIEWBOX, uid="bloub", aria_label=""):
        return render_svg(
            self.engine.sample(t),
            size=size,
            viewbox_half=viewbox_half,
            color=self.color_hex,
            paper=self.paper,
            uid=uid,
            aria_label=aria_label,
        )
