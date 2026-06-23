# src/docsynthfab/latex/image_cleanup.py
# Recommended version ranges:
# - Python>=3.10,<3.14
# - Pillow>=10,<12

from __future__ import annotations

from PIL import Image, ImageChops

from .errors import LatexRenderError


def crop_rgba_to_alpha_bbox(
    image: Image.Image,
    pad: int = 4,
    *,
    white_threshold: int = 248,
    ink_threshold: int = 7,
) -> Image.Image:
    """
    Crop renderer output to the visible LaTeX ink region.

    Some HTTP renderers return a full white-page PNG with a fully opaque alpha
    channel. A pure alpha-bbox crop is not enough in that case. This function
    detects ink by comparing pixels against a white background, converts the
    background to transparency, and returns black glyphs on transparent alpha.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    if image.width <= 1 or image.height <= 1:
        return image

    rgb = image.convert("RGB")
    white = Image.new("RGB", rgb.size, (255, 255, 255))

    diff = ImageChops.difference(rgb, white).convert("L")
    ink_mask = diff.point(lambda pixel: 255 if pixel > ink_threshold else 0)
    bbox = ink_mask.getbbox()

    if bbox is None:
        raise LatexRenderError("render/latex-empty-ink")

    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(image.width, x1 + pad)
    y1 = min(image.height, y1 + pad)

    cropped_rgb = rgb.crop((x0, y0, x1, y1))
    cropped_diff = ImageChops.difference(
        cropped_rgb,
        Image.new("RGB", cropped_rgb.size, (255, 255, 255)),
    ).convert("L")

    soft_alpha = cropped_diff.point(lambda pixel: max(0, min(255, int(pixel) * 4)))
    near_white_kill = cropped_rgb.convert("L").point(
        lambda pixel: 0 if pixel >= white_threshold else 255
    )

    alpha = ImageChops.multiply(soft_alpha, near_white_kill)

    output = Image.new("RGBA", cropped_rgb.size, (0, 0, 0, 0))
    black = Image.new("RGBA", cropped_rgb.size, (0, 0, 0, 255))
    output.paste(black, (0, 0), alpha)
    output.putalpha(alpha)

    final_bbox = output.getchannel("A").getbbox()

    if final_bbox is None:
        raise LatexRenderError("render/latex-empty-alpha-after-cleanup")

    cropped = output.crop(final_bbox)

    if pad <= 0:
        return cropped

    padded = Image.new(
        "RGBA",
        (cropped.width + 2 * pad, cropped.height + 2 * pad),
        (0, 0, 0, 0),
    )
    padded.paste(cropped, (pad, pad), cropped)
    return padded



