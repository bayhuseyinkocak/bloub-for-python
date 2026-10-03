"""Assemble rasterised frames into an animated GIF with Pillow."""

import io

from .png import rasterize


def svg_frames_to_gif(svg_frames, size, fps, background=None, progress=None):
    from PIL import Image

    imgs = []
    for i, svg in enumerate(svg_frames):
        png = rasterize(svg, size)
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        if background is not None:
            bg = Image.new("RGBA", img.size, background)
            img = Image.alpha_composite(bg, img).convert("RGB")
        imgs.append(img)
        if progress is not None:
            progress(i + 1, len(svg_frames))

    buf = io.BytesIO()
    duration_ms = max(2, round(1000 / fps))
    if background is not None:
        imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:],
                     duration=duration_ms, loop=0, optimize=False)
    else:
        imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:],
                     duration=duration_ms, loop=0, transparency=0, disposal=2, optimize=False)
    return buf.getvalue()
