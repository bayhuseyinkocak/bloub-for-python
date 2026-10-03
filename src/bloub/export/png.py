"""Rasterise an SVG to PNG."""


class RasteriserUnavailable(RuntimeError):
    pass


def rasterize(svg_str, size=None):
    """Render an SVG string to PNG bytes.

    Tries resvg first (self-contained, full mask/gradient support), then
    cairosvg as a fallback. Neither is bundled with the pure core: install the
    export extra with: pip install bloub-python[export]
    """
    svg_bytes = svg_str.encode("utf-8")
    errors = []
    try:
        from resvg_py import Resvg  # type: ignore

        img = Resvg(svg_bytes).render()
        return img.as_png()
    except ImportError as e:
        errors.append("resvg-py: " + str(e))
    try:
        import cairosvg  # type: ignore

        return cairosvg.svg2png(bytestring=svg_bytes, output_width=size, output_height=size)
    except ImportError as e:
        errors.append("cairosvg: " + str(e))
    raise RasteriserUnavailable(
        "No SVG rasteriser available. Install one with 'pip install resvg-py' "
        "(recommended) or 'pip install cairosvg' plus a system libcairo. ("
        + "; ".join(errors) + ")"
    )


def to_png(svg_str, size=None):
    return rasterize(svg_str, size)
