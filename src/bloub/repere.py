"""The frame of reference of everything the engine renders.

engine.sample() outputs coordinates in viewBox units; these two numbers are
their definition. They used to live in the Vue component (out of reach of the
engine); they are here because src/bot/ is what gets read and consumed from the
outside.
"""

# Radius of the ball at rest, in viewBox units. Chosen, not measured: it is the
# unit of work, and everything else is expressed as a fraction of it.
RAYON = 100

# Half-side of the displayed viewBox. The margin beyond the radius houses the
# orbit rings (up to 1.4x the radius, i.e. 140). The RINGS / SWOOSH tables in
# decor.py keep everything under 158; a test locks it.
DEMI_VIEWBOX = 158
