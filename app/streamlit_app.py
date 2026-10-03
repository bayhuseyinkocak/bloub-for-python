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
import time

import streamlit as st

from bloub.bot import Bot
from bloub.cycles import clamp_duration, default_cycle, make_block, next_cycle_id, total_duration
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


def _montage_engine_at(blocks, t, shape_id, expr_id):
    """Engine of the current avatar, replayed up to `t` of the montage.

    Shape and expression are the user's settled settings; only the STATE morphs
    along the montage — exactly like the original scene.
    """
    from bloub.cycles import block_at, offset_of
    radii = SHAPE_BY_ID.get(shape_id, SHAPE_BY_ID["cercle"])["radii"]
    expr = EXPRESSION_BY_ID.get(expr_id)
    idx = block_at(blocks, t)["index"]
    eng = BotEngine(RAYON, blocks[idx]["state"], radii, expr)
    for j in range(idx + 1):
        off = offset_of(blocks, j)
        stt = blocks[j]["state"]
        if j == 0:
            if eng.state != stt:
                eng.reset(stt, off)
        else:
            eng.set_state(stt, off)
    return eng


def _frame_svg_at(blocks, t, size, color, uid, shape_id="cercle", expr_id="neutre"):
    return render_svg(_montage_engine_at(blocks, t, shape_id, expr_id).sample(t),
                      size=size, viewbox_half=DEMI_ECRAN, color=color, paper=PAPER, uid=uid)


def _tile_svg(state, size, color, uid, shape_id="cercle", expr_id="neutre"):
    """A block's frozen pose, matching the original BloubBot `frozen-at`."""
    radii = SHAPE_BY_ID.get(shape_id, SHAPE_BY_ID["cercle"])["radii"]
    expr = EXPRESSION_BY_ID.get(expr_id)
    eng = BotEngine(RAYON, state, radii, expr)
    return render_svg(eng.sample(POSES[state]), size=size, viewbox_half=DEMI_CADRE,
                      color=color, paper=PAPER, uid=uid)


def _cycle_svgs(blocks, size, color, shape_id="cercle", expr_id="neutre"):
    total = total_duration(blocks)
    n = max(1, round(total * 20))
    return [_frame_svg_at(blocks, (i / n) * total, size, color, "c", shape_id, expr_id)
            for i in range(n)]


def _mmss(t):
    s = max(0, int(t))
    return f"{s // 60}:{s % 60:02d}"


def _nom_cycle(c):
    return c["name"] or t("cycles.defaultName", lang)


def _init_montage_state():
    if "cycles" not in st.session_state:
        st.session_state.cycles = [default_cycle()]
    if "active_id" not in st.session_state:
        st.session_state.active_id = st.session_state.cycles[0]["id"]
    st.session_state.setdefault("playing", False)
    st.session_state.setdefault("t_anchor", 0.0)
    st.session_state.setdefault("wall_anchor", 0.0)


def _active_cycle():
    cycles = st.session_state.cycles
    return next((c for c in cycles if c["id"] == st.session_state.active_id), cycles[0])


def _now_t(blocks):
    total = total_duration(blocks) or 1.0
    if st.session_state.playing:
        return (st.session_state.t_anchor + time.perf_counter() - st.session_state.wall_anchor) % total
    return st.session_state.t_anchor % total


def _timeline_html(blocks, pos):
    total = total_duration(blocks) or 1.0
    cells = []
    for b in blocks:
        w = b["duration"] / total * 100.0
        cells.append(
            f'<div style="flex:{w:.6f}%;min-width:0;background:#0a0a0c1f;'
            f'border-right:2px solid #f9f9f9;padding:2px 5px;overflow:hidden;'
            f'white-space:nowrap;font-size:10px;line-height:20px;'
            f'color:#0a0a0c">{t("states." + b["state"], lang)}</div>'
        )
    pct = (pos / total) * 100.0
    return (
        '<div style="position:relative;height:26px;background:#ececec;border-radius:6px;overflow:hidden">'
        '<div style="display:flex;height:100%;width:100%">' + "".join(cells) + "</div>"
        f'<div style="position:absolute;top:0;bottom:0;left:{pct:.3f}%;width:2px;background:#0a0a0c"></div>'
        "</div>"
    )


def _render_player(blocks, t, total, size, color, uid, shape_id, expr_id):
    st.components.v1.html(_frame_svg_at(blocks, t, size, color, uid, shape_id, expr_id),
                          height=size + 40, scrolling=False)
    st.markdown(
        f"<div style='font-variant-numeric:tabular-nums;font-size:16px;color:#0a0a0c'>"
        f"{_mmss(t)} / {_mmss(total)}</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(1.0, t / total if total else 1.0))
    st.markdown(_timeline_html(blocks, t), unsafe_allow_html=True)


@st.fragment(run_every=0.08)
def _live_fragment(blocks, size, color, shape_id, expr_id):
    total = total_duration(blocks) or 1.0
    _render_player(blocks, _now_t(blocks), total, size, color, "live", shape_id, expr_id)


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
    _init_montage_state()
    st.markdown("### " + t("rail.animations", lang))

    cycles = st.session_state.cycles

    left, right = st.columns([1, 1.25], gap="large")

    # ============================ left: cycles + block editor + export
    with left:
        # -- cycle menu (select / create / rename / delete) --
        names = [_nom_cycle(c) for c in cycles]
        active = _active_cycle()
        c1, c2, c3, c4 = st.columns([2.4, 1, 1, 1])
        with c1:
            sel = st.selectbox(t("cycles.defaultName", lang), range(len(cycles)),
                               format_func=lambda i: names[i], index=cycles.index(active),
                               key="cycle_sel", label_visibility="collapsed")
            st.session_state.active_id = cycles[sel]["id"]
        active = _active_cycle()
        blocks = active["blocks"]
        total = total_duration(blocks)
        with c2:
            if st.button("＋", key="cycle_new", help=t("cycles.menuNew", lang), use_container_width=True):
                st.session_state.name_mode = "create"
        with c3:
            if st.button("✎", key="cycle_rename", help=t("dialog.nameRenameTitle", lang), use_container_width=True):
                st.session_state.name_mode = "rename"
        with c4:
            if st.button("🗑", key="cycle_del", help=t("cycles.menuRemoveAria", lang, {"name": _nom_cycle(active)}),
                         disabled=len(cycles) <= 1, use_container_width=True):
                st.session_state.del_confirm = True

        # -- name dialog (create / rename) --
        if st.session_state.get("name_mode"):
            mode = st.session_state.name_mode
            title = t("dialog.nameRenameTitle", lang) if mode == "rename" else t("dialog.nameCreateTitle", lang)
            st.markdown("**" + title + "**")
            default_val = active["name"] if mode == "rename" else t("cycles.newName", lang)
            name = st.text_input(t("dialog.nameField", lang), value=default_val, key="name_input")
            n1, n2 = st.columns(2)
            with n1:
                if st.button(t("dialog.nameCreate", lang) if mode == "create" else t("dialog.nameRename", lang), key="name_ok"):
                    if mode == "create":
                        cycles.append({"id": next_cycle_id(cycles), "name": name.strip(),
                                       "blocks": [make_block("idle")]})
                        st.session_state.active_id = cycles[-1]["id"]
                    else:
                        active["name"] = name.strip()
                    del st.session_state.name_mode
                    st.rerun()
            with n2:
                if st.button(t("dialog.cancel", lang), key="name_cancel"):
                    del st.session_state.name_mode
                    st.rerun()

        # -- delete confirmation --
        if st.session_state.get("del_confirm"):
            st.warning(t("dialog.removeTitle", lang, {"name": _nom_cycle(active)}))
            d1, d2 = st.columns(2)
            with d1:
                if st.button(t("dialog.removeConfirm", lang), key="del_ok"):
                    cycles[:] = [c for c in cycles if c["id"] != active["id"]]
                    if not cycles:
                        cycles.append(default_cycle())
                    st.session_state.active_id = cycles[0]["id"]
                    del st.session_state.del_confirm
                    st.rerun()
            with d2:
                if st.button(t("dialog.cancel", lang), key="del_cancel"):
                    del st.session_state.del_confirm
                    st.rerun()

        # -- add animation palette --
        st.markdown("**" + t("timeline.addAnimation", lang) + "**")
        for r in range(0, len(SEQUENCE), 4):
            pal = st.columns(4)
            for c, sid in enumerate(SEQUENCE[r:r + 4]):
                with pal[c]:
                    if st.button(t("states." + sid, lang), key=f"add_{sid}", use_container_width=True):
                        blocks.append(make_block(sid))
                        st.rerun()

        # -- block list (reorder / resize / remove) --
        st.markdown("**" + _nom_cycle(active) + "**")
        remove_i = None
        move = None
        for i, b in enumerate(blocks):
            row = st.columns([0.7, 2.6, 1.0, 0.55, 0.55, 0.55])
            with row[0]:
                st.components.v1.html(_tile_svg(b["state"], 44, color_hex, f"b{i}", shape, expression),
                                      height=52, scrolling=False)
            with row[1]:
                st.markdown("**" + t("states." + b["state"], lang) + "**")
            with row[2]:
                dur = st.number_input("s", min_value=0.1, max_value=10.0, value=float(b["duration"]),
                                      step=0.1, key=f"dur{i}", label_visibility="collapsed")
                clamped = clamp_duration(b["state"], dur)
                if clamped != b["duration"]:
                    b["duration"] = clamped
            with row[3]:
                if st.button("◀", key=f"mvL{i}", disabled=(i == 0), help="←", use_container_width=True):
                    move = (i, i - 1)
            with row[4]:
                if st.button("▶", key=f"mvR{i}", disabled=(i == len(blocks) - 1), help="→", use_container_width=True):
                    move = (i, i + 1)
            with row[5]:
                if st.button("✕", key=f"rm{i}", disabled=(len(blocks) <= 1),
                             help=t("timeline.blockRemoveAria", lang, {"state": t("states." + b["state"], lang), "duration": ""}).strip(),
                             use_container_width=True):
                    remove_i = i
        if remove_i is not None:
            blocks.pop(remove_i)
            st.rerun()
        if move is not None:
            a, b2 = move
            blocks[a], blocks[b2] = blocks[b2], blocks[a]
            st.rerun()

        # -- export montage (format + background + progress) --
        st.markdown("---")
        st.markdown("**" + t("timeline.export", lang) + "**")
        fmt = st.radio(t("export.cycleFormat", lang), ["mp4", "gif"],
                       format_func=lambda x: t("export.cycle_" + x, lang),
                       index=0, key="cycle_fmt", horizontal=True)
        bg = "#ffffff"
        if fmt == "gif":
            fond = st.radio(t("export.gifBackground", lang), ["blanc", "transparent"],
                            format_func=lambda x: t("export.fond_" + x, lang),
                            index=0, key="cycle_fond", horizontal=True)
            bg = "#ffffff" if fond == "blanc" else None

        if st.button("⬇ " + t("timeline.export", lang), key="cycle_export", type="primary"):
            try:
                with st.spinner(t("export.cycleProgress", lang)):
                    if fmt == "mp4":
                        svgs = _cycle_svgs(blocks, CYCLE_TAILLE["mp4"], color_hex, shape, expression)
                        data = svg_frames_to_mp4(svgs, CYCLE_TAILLE["mp4"], CYCLE_FPS["mp4"], background="#ffffff")
                        st.session_state.export_bytes = data
                        st.session_state.export_name = "bloub-cycle.mp4"
                        st.session_state.export_mime = "video/mp4"
                    else:
                        svgs = _cycle_svgs(blocks, CYCLE_TAILLE["gif"], color_hex, shape, expression)
                        data = svg_frames_to_gif(svgs, CYCLE_TAILLE["gif"], CYCLE_FPS["gif"], background=bg)
                        st.session_state.export_bytes = data
                        st.session_state.export_name = "bloub-cycle.gif"
                        st.session_state.export_mime = "image/gif"
            except Exception as ex:  # noqa: BLE001
                st.warning(t("export.failed", lang) + ": " + str(ex)[:120])

        if "export_bytes" in st.session_state:
            st.download_button(t("export.gifConfirm", lang), st.session_state.export_bytes,
                               file_name=st.session_state.export_name,
                               mime=st.session_state.export_mime, key="cycle_dl")

    # ============================ right: live player
    with right:
        st.markdown("**" + t("timeline.preview", lang) + "**")
        playing = st.session_state.playing

        if playing:
            _live_fragment(blocks, 340, color_hex, shape, expression)
        else:
            _render_player(blocks, _now_t(blocks), total, 340, color_hex, "still", shape, expression)

        pc1, pc2, pc3 = st.columns([1.3, 1, 3.5])
        with pc1:
            if st.button(("⏸ " + t("timeline.pause", lang)) if playing else ("▶ " + t("timeline.play", lang)),
                         key="toggle_play", use_container_width=True):
                if playing:
                    st.session_state.t_anchor = _now_t(blocks)
                    st.session_state.playing = False
                else:
                    if st.session_state.t_anchor >= total - 0.001:
                        st.session_state.t_anchor = 0.0
                    st.session_state.wall_anchor = time.perf_counter()
                    st.session_state.playing = True
                st.rerun()
        with pc2:
            if st.button("↺", key="restart", help="0:00", use_container_width=True):
                st.session_state.t_anchor = 0.0
                st.session_state.wall_anchor = time.perf_counter()
                st.rerun()
        with pc3:
            val = st.slider("seek", 0.0, max(total, 0.1),
                            min(float(st.session_state.t_anchor), total),
                            step=0.1, key="seek_slider", label_visibility="collapsed")
            if abs(val - st.session_state.t_anchor) > 0.001:
                st.session_state.t_anchor = val
                if playing:
                    st.session_state.wall_anchor = time.perf_counter()
                st.rerun()

# --------------------------------------------------------------------------- Settings

with tabs[3]:
    st.markdown("### " + t("settings.title", lang))
    st.markdown("**" + t("settings.language", lang) + "**: " + lang_names[lang])
    st.markdown(t("settings.credits", lang, {"name": "Jérémy Perret"}))
    st.markdown("[GitHub](https://github.com/jeremy-prt/bloub) · [bu port](https://github.com/bayhuseyinkocak/bloub-for-python)")
    st.caption(t("app.title", lang))
