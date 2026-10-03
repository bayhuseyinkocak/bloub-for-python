"""Encode frames into an MP4 video via imageio + the bundled ffmpeg.

Video is always OPAQUE: MP4 has no alpha channel.
"""

import io
import os
import tempfile

from .png import rasterize


def svg_frames_to_mp4(svg_frames, size, fps, background="#ffffff", progress=None):
    import numpy as np
    from PIL import Image
    import imageio.v2 as imageio

    frames = []
    for i, svg in enumerate(svg_frames):
        png = rasterize(svg, size)
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        bg = Image.new("RGBA", img.size, background)
        img = Image.alpha_composite(bg, img).convert("RGB")
        frames.append(np.asarray(img))
        if progress is not None:
            progress(i + 1, len(svg_frames))

    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:
        writer = imageio.get_writer(path, fps=fps, codec="libx264", output_params=["-crf", "12"])
        for f in frames:
            writer.append_data(f)
        writer.close()
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(path):
            os.unlink(path)
