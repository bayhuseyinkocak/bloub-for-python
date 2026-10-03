# AGENTS.md — guidance for AI agents working on this repository

bloub-for-python is a faithful Python port of
[jeremy-prt/bloub](https://github.com/jeremy-prt/bloub) — an SVG recreation of
the x.ai bot avatar — with a Streamlit interface on top.

## Layout

- src/bloub/ — the package. Core is pure stdlib; no framework, no clock, no DOM.
- app/streamlit_app.py — the Streamlit UI (a consumer of the engine).
- tests/ — pytest; tests/fixtures/ holds golden JSON generated from the TS repo.
- tools/ — extract_profiles.py and build_eyefit.py (regenerate committed data).

## The one invariant that matters most

**engine.sample(t) is a pure function of time.** Pause, resume, slow motion,
jumping to an arbitrary date, and re-reading a past date must all produce the
same image. The engine never reads a clock, never imports a framework, and never
mutates while sampling. State enters through timestamped setters
(set_state / set_shape / set_expression / set_look), never through a variable
read during sample.

## Numerical parity with the TypeScript original

The engine reproduces the TS output byte for byte. Three JS behaviours must be
preserved or the path strings diverge:

- **Math.round rounds halves toward +infinity** (Python round is banker's). Use
  math.js_round(x) = floor(x + 0.5).
- **String(number) drops a trailing .0** (String(100) is "100", not "100.0").
  Use math.js_str(x) when building SVG strings.
- **Math.imul / >>> 0 are 32-bit unsigned.** math.create_rng emulates mulberry32
  with & 0xFFFFFFFF; the RINGS/SWOOSH/COMET/PARTICLES/BLINKS sequences depend on
  it and are locked by tests/test_parity.py.

All silhouettes are sampled at the same 64 angles, so morphing is a linear
interpolation of radii. New shapes must go through a radial profile, or through
shape.profile_from_polygon.

## Architectural rules (ported from the original architecture doc)

- **The montage holds or cuts, never scales time.** cycles.MIN_BLOCK is DERIVED
  from the longest morph in the catalogue (do not hand-write it). A block shorter
  than the next state's morph would jump instead of blending.
- **Anything sitting "on" the body follows its real radius.** Eyes and the
  notification pastille use shape.radius_at_angle. New elements anchored to the
  outline need the same treatment.
- **The eye offset is a table, not a per-frame solver** (pose space deformation).
  It is computed once by eyefit.build_table() and committed as
  src/bloub/_eyefit_table.py. Never solve per frame — it produces visible motion
  artefacts (chattering, active-set flips). Read the table on the boundaries of
  each morph and interpolate with easeOutQuint.
- **The eyes are holes in a <mask>, not white shapes.** The body is backed by an
  opaque paper-colour path so the back half of the rings and the burst particles
  (drawn behind) stay occluded through the holes.
- **States declare ArcSpec, the engine rasterises.** Don't call arc_render from
  states. The rings are 3D circles in orthographic projection; the z component
  splits each arc front/back for depth sorting.
- **Springs are local and deliberate.** Transitions are exponential ease-outs;
  the body never overshoots. There is no spring engine.
- **Catalogue ids, not labels.** states/skins/expressions carry ids only; labels
  resolve through i18n.t(). Every id must have a label in all four languages
  (fr/en/zh/tr) — the parity of a language map is not compiler-checked here, so
  keep them in sync by hand.
- **Two sources of shapes, never mixed.** profiles.py is measured from the video
  (animation states); skins.py is analytic (customiser). A user shape only
  replaces the body on states flagged baseBody.

## What not to retry

The original repo documents several fixes that were tried and failed; do not
reintroduce them: per-frame eye fitting, bounding each eye separately, scaling
the face, Math.min over the two eyes, one offset per shape, giving up when
nothing fits, and re-solving on the interpolated radius array.

## Testing

- tests/test_parity.py compares the Python engine against golden fixtures from
  the TypeScript repo (byte-for-byte on path strings). Run with pytest.
- The analytic shapes (galet/squircle/capsule/triangle/hexagone/nuage/goutte)
  differ from JS by <=1 ULP (libm vs V8); this is invisible after r2 rounding to
  2 decimals. Measured profiles and all RNG-driven decor are bit-exact.

## Regenerating fixtures and committed data

- Golden fixtures: run the dumper in the original TS repo (npx tsx) and copy
  tests/fixtures/*.json.
- profiles.py: tools/extract_profiles.py (needs numpy + Pillow + reference frames).
- _eyefit_table.py: tools/build_eyefit.py.

## Export

PNG/GIF/MP4 need a rasteriser (resvg-py recommended, cairosvg fallback) plus
Pillow (and imageio-ffmpeg for MP4). The core and the SVG output are pure.
