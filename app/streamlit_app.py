"""bloub — Streamlit interface.

Run with:
    streamlit run app/streamlit_app.py

The live preview and the states board are rendered as inline SVG (no binary
dependencies). PNG / GIF / MP4 exports require a rasteriser (resvg-py or
cairosvg) plus Pillow (and imageio-ffmpeg for MP4); install the "export" extra.
"""

import sys
from pathlib import Path

# Make the src/ layout importable when running directly from a checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import io

import streamlit as st

from bloub.bot import Bot
from bloub.cycles import default_cycle, make_block, total_duration
from bloub.engine import BotEngine
from bloub.expressions import EXPRESSIONS, EXPRESSION_BY_ID
from bloub.export import (
    ANIM_CLES_PAR_SEC,
    ANIM_IMAGES,
    ANIM_PAS,
    ANIM_SECONDES,
    CYCLE_FPS,
    CYCLE_TAILLE,
    DEMI_CADRE,
    DEMI_ECRAN,
    GIF_FPS,
    GIF_PAS,
    GIF_TAILLE,
    cycle_images,
    cycle_pas,
    viewbox_export,
)
from bloub.export.gif import svg_frames_to_gif
from bloub.export.mp4 import svg_frames_to_mp4
from bloub.export.png import rasterize
from bloub.export.svg import animated_svg
from bloub.i18n import LANGUES, t
from bloub.repere import RAYON
from bloub.render import render_svg
from bloub.skins import COLORS, COLOR_BY_ID, SHAPES, SHAPE_BY_ID
from bloub.states import POSES, SEQUENCE, STATES, STATE_BY_ID

st.set_page_config(page_title="bloub", page_icon="⚫", layout="wide")

PAPER = "#f9f9f9"


# --------------------------------------------------------------------------- helpers

def _lang_id(l):
    return l["id"]


def _svg_download_button(label, svg_str, filename, key):
    return st.download_button(label, svg_str.encode("utf-8"), file_name=filename,
                              mime="image/svg+xml", key=key)


def _render_avatar(bot, time=1.0, size=320, viewbox_half=DEMI_CADRE, uid="av"):
    return render_svg(bot.engine.sample(time), size=size, viewbox_half=viewbox_half,
                      color=bot.color_hex, paper=PAPER, uid=uid, aria_label=t("app.botAria", lang))


def _animated_avatar_svg(bot, size=320, viewbox_half=DEMI_CADRE, uid="av"):
    eng = bot.engine
    base = None
    matrices = []
    for i in range(ANIM_IMAGES):
        frame = eng.sample(i * ANIM_PAS)
        if i == 0:
            base = render_svg(frame, size=size, viewbox_half=viewbox_half,
                              color=bot.color_hex, paper=PAPER, uid=uid, aria_label=t("app.botAria", lang))
        matrices.append([e.matrix for e in frame.eyes])
    duration = round((ANIM_IMAGES - 1) * ANIM_PAS, 3)
    return animated_svg(base, matrices, duration)


def _avatar_gif(bot, size=GIF_TAILLE, background=None):
    frames = []
    for i in range(GIF_FPS * ANIM_SECONDES):
        t = i * GIF_PAS
        frames.append(render_svg(bot.engine.sample(t), size=size, viewbox_half=DEMI_CADRE,
                                 color=bot.color_hex, paper=PAPER, uid="g"))
    return svg_frames_to_gif(frames, size, GIF_FPS, background=background)


def _cycle_svgs(blocks, size, background=None):
    total = total_duration(blocks)
    fps = 20
    n = max(1, round(total * fps))
    out = []
    from bloub.cycles import block_at, offset_of
    for i in range(n):
        t = (i / n) * total
        idx = block_at(blocks, t)["index"]
        eng = BotEngine(RAYON, blocks[idx]["state"])
        for j in range(idx + 1):
            off = offset_of(blocks, j)
            stt = blocks[j]["state"]
            if j == 0:
                if eng.state != stt:
                    eng.reset(stt, off)
            else:
                eng.set_state(stt, off)
        out.append(render_svg(eng.sample(t), size=size, viewbox_half=DEMI_ECRAN,
                              color=color_hex, paper=PAPER, uid="c"))
    return out


# --------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown("### bloub")
    lang_names = {l["id"]: l["nom"] + " " + l["emoji"] for l in LANGUES}
    lang = st.radio(
        t("settings.language", "en"),
        options=[l["id"] for l in LANGUES],
        format_func=lambda x: lang_names[x],
        index=[l["id"] for l in LANGUES].index("tr"),
        key="lang",
    )
    st.caption(t("app.title", lang))

tabs = st.tabs([
    t("rail.customize", lang),
    t("panel.animations", lang) + " — " + t("states.idle", lang) + "…",
    t("rail.animations", lang),
    t("rail.settings", lang),
])

# --------------------------------------------------------------------------- Avatar

with tabs[0]:
    col_a, col_b = st.columns([1, 1.6], gap="large")

    with col_a:
        shape = st.selectbox(
            t("panel.shape", lang), [s["id"] for s in SHAPES],
            format_func=lambda x: t("shapes." + x, lang), key="shape",
        )
        color = st.selectbox(
            t("panel.color", lang), [c["id"] for c in COLORS],
            format_func=lambda x: t("colors." + x, lang), key="color",
        )
        expression = st.selectbox(
            t("panel.expression", lang), [e["id"] for e in EXPRESSIONS],
            format_func=lambda x: t("expressions." + x, lang), key="expression",
        )

        bot = Bot(shape=shape, color=color, expression=expression, paper=PAPER)
        color_hex = bot.color_hex

    with col_b:
        st.caption("● " + t("app.botAria", lang))
        live_svg = _animated_avatar_svg(bot, size=360, viewbox_half=DEMI_CADRE, uid="live")
        st.components.v1.html(live_svg, height=400, scrolling=False)

    st.markdown("---")
    st.markdown("### " + t("export.more", lang))
    c1, c2, c3, c4, c5 = st.columns(5)
    static_svg = _render_avatar(bot, time=1.0, size=1024, viewbox_half=DEMI_CADRE, uid="dl")

    with c1:
        _svg_download_button(t("export.svg", lang), static_svg, "bloub-" + shape + "-" + color + ".svg", "d_svg")
    with c2:
        _svg_download_button(t("export.anime", lang), live_svg, "bloub-" + shape + "-" + color + "-anime.svg", "d_anime")
    with c3:
        try:
            png = rasterize(static_svg, 1024)
            st.download_button(t("export.png", lang), png, file_name="bloub-" + shape + "-" + color + ".png",
                               mime="image/png", key="d_png")
        except Exception as ex:  # noqa: BLE001
            st.warning(t("export.failed", lang) + " (PNG): " + str(ex)[:120])
    with c4:
        try:
            gif_bytes = _avatar_gif(bot, background="#ffffff")
            st.download_button(t("export.gif", lang), gif_bytes,
                               file_name="bloub-" + shape + "-" + color + ".gif", mime="image/gif", key="d_gif")
        except Exception as ex:  # noqa: BLE001
            st.warning(t("export.failed", lang) + " (GIF): " + str(ex)[:120])
    with c5:
        st.markdown("")

# --------------------------------------------------------------------------- States

with tabs[1]:
    st.markdown("### " + t("panel.animations", lang))
    cards = []
    for sid in SEQUENCE:
        eng = BotEngine(RAYON, sid)
        svg = render_svg(eng.sample(POSES[sid]), size=150, viewbox_half=DEMI_CADRE,
                         color="#0a0a0c", paper=PAPER, uid="st-" + sid, aria_label=t("states." + sid, lang))
        cards.append((t("states." + sid, lang), svg))
    cols = st.columns(7)
    for i, (label, svg) in enumerate(cards):
        with cols[i % 7]:
            st.components.v1.html(svg, height=170, scrolling=False)
            st.caption(label)

# --------------------------------------------------------------------------- Animations

with tabs[2]:
    st.markdown("### " + t("rail.animations", lang))
    if "blocks" not in st.session_state:
        st.session_state.blocks = default_cycle()["blocks"]

    left, right = st.columns([1, 1.4], gap="large")
    with left:
        st.markdown("**" + t("timeline.addAnimation", lang) + "**")
        add_state = st.selectbox(
            t("panel.animations", lang), SEQUENCE,
            format_func=lambda x: t("states." + x, lang), key="add_state",
        )
        add_dur = st.number_input("⏱ " + t("units.seconds", lang, {"n": ""}).strip(),
                                  min_value=0.1, max_value=10.0, value=2.0, step=0.1, key="add_dur")
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("➕ " + t("timeline.addAnimation", lang), key="btn_add"):
                from bloub.cycles import clamp_duration
                st.session_state.blocks = st.session_state.blocks + [{"state": add_state, "duration": clamp_duration(add_state, add_dur)}]
        with b2:
            if st.button("✂️ " + t("dialog.cancel", lang) + " (son blok)", key="btn_pop"):
                if st.session_state.blocks:
                    st.session_state.blocks = st.session_state.blocks[:-1]
        with b3:
            if st.button("↺ " + t("cycles.defaultName", lang), key="btn_reset"):
                st.session_state.blocks = default_cycle()["blocks"]

        st.markdown("**" + t("timeline.export", lang) + "**")
        for i, b in enumerate(st.session_state.blocks):
            st.markdown(f"{i + 1}. **{t('states.' + b['state'], lang)}** — {b['duration']:.1f}s")

    with right:
        blocks = st.session_state.blocks
        if blocks:
            preview_fps = 20
            preview_n = min(40, max(1, round(total_duration(blocks) * preview_fps)))
            svgs = []
            from bloub.cycles import block_at, offset_of
            total = total_duration(blocks)
            for i in range(preview_n):
                tt = (i / preview_n) * total
                idx = block_at(blocks, tt)["index"]
                eng = BotEngine(RAYON, blocks[idx]["state"])
                for j in range(idx + 1):
                    off = offset_of(blocks, j)
                    stt = blocks[j]["state"]
                    if j == 0:
                        if eng.state != stt:
                            eng.reset(stt, off)
                    else:
                        eng.set_state(stt, off)
                svgs.append(render_svg(eng.sample(tt), size=240, viewbox_half=DEMI_ECRAN,
                                       color=color_hex, paper=PAPER, uid="pv"))
            try:
                preview_gif = svg_frames_to_gif(svgs, 240, preview_fps, background="#ffffff")
                st.image(preview_gif, width=300)
            except Exception as ex:  # noqa: BLE001
                st.warning(t("export.failed", lang) + " (önizleme): " + str(ex)[:120])

            st.markdown("---")
            e1, e2 = st.columns(2)
            with e1:
                try:
                    cyc_svgs = _cycle_svgs(blocks, CYCLE_TAILLE["gif"], background="#ffffff")
                    gif_bytes = svg_frames_to_gif(cyc_svgs, CYCLE_TAILLE["gif"], CYCLE_FPS["gif"], background="#ffffff")
                    st.download_button(t("export.cycle_gif", lang), gif_bytes,
                                       file_name="bloub-cycle.gif", mime="image/gif", key="d_cyc_gif")
                except Exception as ex:  # noqa: BLE001
                    st.warning(t("export.failed", lang) + " (GIF): " + str(ex)[:120])
            with e2:
                try:
                    cyc_svgs = _cycle_svgs(blocks, CYCLE_TAILLE["mp4"], background="#ffffff")
                    mp4_bytes = svg_frames_to_mp4(cyc_svgs, CYCLE_TAILLE["mp4"], CYCLE_FPS["mp4"], background="#ffffff")
                    st.download_button(t("export.cycle_mp4", lang), mp4_bytes,
                                       file_name="bloub-cycle.mp4", mime="video/mp4", key="d_cyc_mp4")
                except Exception as ex:  # noqa: BLE001
                    st.warning(t("export.failed", lang) + " (MP4): " + str(ex)[:120])
        else:
            st.info(t("dialog.cancel", lang))

# --------------------------------------------------------------------------- Settings

with tabs[3]:
    st.markdown("### " + t("settings.title", lang))
    st.markdown("**" + t("settings.language", lang) + "**: " + lang_names[lang])
    st.markdown(t("settings.credits", lang, {"name": "Jérémy Perret"}))
    st.markdown("[GitHub](https://github.com/jeremy-prt/bloub) · [bu port](https://github.com/bayhuseyinkocak/bloub-for-python)")
    st.caption(t("app.title", lang))
