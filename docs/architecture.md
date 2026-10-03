# Architecture (Python port)

## The engine has no framework and no clock

`engine.sample(t)` is a pure function of time. That is what makes frozen
poses, the state board, and DOM-less tests possible.

So `src/bloub/` must not gain internal state that depends on real time, nor a
clock read, nor a Streamlit import. UI-only helpers live in `app/` or in the
`bloub.bot.Bot` convenience wrapper.

A state change landing inside a fade blends from the frozen frame (the engine
keeps one slot of history; `set_state` freezes the composite pose and blends
from it, so the transition is continuous however many changes are chained).

`sample()` must not mutate either. Purging a "stale" previous state makes the
engine non-replayable: re-reading a date from before the end of a fade would no
longer find it.

## The montage holds or cuts, it never scales time

`cycles.py` stretches a block by letting the state run longer and shortens it
by cutting. It never multiplies local time by a speed factor.

- `MIN_BLOCK`, DERIVED from the longest morph in the catalogue (orbit, 0.6 s),
  not written by hand.
- `StateDef.minDuration`: the date at which the animation resolves.

## Every silhouette shares the same angular sampling

All profiles are sampled at the same 64 angles (`PROFILE_SAMPLES`), so any two
shapes have points that correspond one to one and a transition reduces to a
linear interpolation of radii. That is why there is no path-morphing library.

## Two sources of shapes, not to be mixed

`profiles.py` is generated from the video and drives the animated states.
`skins.py` holds the customiser's shapes, built analytically. A shape the user
picks only replaces the body on states flagged `baseBody`: idle, wink, wide,
notify and swirl. Everywhere else the silhouette IS the animation.

## The eyes are holes in a <mask>

Not white shapes laid on top. A hole shows whatever is drawn behind it, and the
back half of the rings and the burst particles ARE drawn behind the body to be
occluded by it — so the body is backed by an opaque path in the paper colour.

## Anything sitting "on" the body must follow its real radius

The eyes live on a sphere of radius 1; on a non-circular shape they leave the
silhouette and the mask cuts them. Hence `shape.radius_at_angle`, applied by the
engine to the eyes and the notification pastille.

That pro-rata places the eye's CENTRE correctly, and that is not enough: the eye
has a size. So a common offset (a translation, hence an isometry) is added to
both eyes, only when a customiser shape replaced the body.

### The offset is a table, not a solver

`eyefit.py` solves the problem ONCE at build time and commits a table (see
`src/bloub/_eyefit_table.py`). The engine reads the table on the BOUNDARIES of
each morph and interpolates with that morph's own easeOutQuint. This is pose
space deformation (Lewis, Cordner & Fong, SIGGRAPH 2000).

Solving inside the render loop produced visible artefacts every time: an
active-set change when the nearest edge switches, a non-smooth objective (min is
C0 but not C1), and chattering from a per-frame feedback loop.

## States declare ArcSpec, the engine rasterises

Geometry in ArcSpec is expressed in ball-radius units; only the engine knows the
viewBox scale. The rings are 3D circles in orthographic projection: the z
component splits each arc in two, and the back half is drawn BEFORE the body so
the body occludes it.

## Springs are local and deliberate

Transitions are exponential ease-outs and the body never overshoots. The one
spring effect is the notification pastille's pop (NOTIF_POP = 1.14).

## Numerical parity

See AGENTS.md. The generated SVG path strings match the TypeScript original byte
for byte thanks to js_round / js_str / the 32-bit mulberry32 emulation.
