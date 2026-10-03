"""bloub — a pure-Python, framework-free recreation of the x.ai bot avatar.

The engine is a pure function of time (no clock, no framework, no DOM)::

    from bloub import BotEngine
    engine = BotEngine(scale=100, initial="idle")
    frame = engine.sample(0.0)

For a convenient wrapper that also knows about shapes/colours/expressions and
can render SVG, use :class:`bloub.bot.Bot`::

    from bloub import Bot
    svg = Bot(shape="cercle", color="encre").svg(t=1.0, size=320)
"""

from .engine import BotEngine, BotFrame, RenderedEye
from .bot import Bot
from .render import render_svg
from .repere import DEMI_VIEWBOX, RAYON

__version__ = "0.1.0"

__all__ = [
    "Bot",
    "BotEngine",
    "BotFrame",
    "RenderedEye",
    "render_svg",
    "RAYON",
    "DEMI_VIEWBOX",
    "__version__",
]
