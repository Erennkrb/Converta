"""Image conversions with Pillow."""
from PIL import Image

from .paths import output_path

PIL_FORMATS = {
    "png": "PNG", "jpg": "JPEG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP",
    "gif": "GIF", "tiff": "TIFF", "ico": "ICO", "pdf": "PDF",
}

# formats that keep all frames of an animated source. Not PNG: Windows shows
# only the first frame of an animated PNG, so PNG gets a chosen frame instead.
ANIMATED_FORMATS = {"GIF", "WEBP", "AVIF"}
# formats without an alpha channel
OPAQUE_FORMATS = {"JPEG", "BMP", "PDF"}


def is_animated(path):
    try:
        with Image.open(path) as img:
            return getattr(img, "is_animated", False)
    except Exception:
        return False


def _options(pil_format, img):
    if pil_format == "JPEG":
        return {"quality": 92, "optimize": True}
    if pil_format == "WEBP":
        return {"quality": 90, "method": 6}
    if pil_format == "AVIF":
        return {"quality": 80}
    if pil_format == "PDF":
        return {"resolution": 150}
    if pil_format == "ICO":
        return {"sizes": [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)
                          if s <= max(img.size)] or [(16, 16)]}
    return {}


def _save(img, dst, target):
    pil_format = PIL_FORMATS[target]
    if pil_format in OPAQUE_FORMATS and img.mode not in ("RGB", "L"):
        # flatten transparency onto white
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, (255, 255, 255))
        img.paste(rgba, mask=rgba.getchannel("A"))
    elif img.mode == "P" and pil_format not in ("PNG", "GIF", "BMP"):
        img = img.convert("RGBA")
    elif img.mode == "CMYK" and pil_format not in ("JPEG", "TIFF"):
        img = img.convert("RGB")
    img.save(dst, pil_format, **_options(pil_format, img))


def convert(src, target, progress=None):
    dst = output_path(src, target)
    with Image.open(src) as img:
        pil_format = PIL_FORMATS[target]
        if getattr(img, "is_animated", False) and pil_format in ANIMATED_FORMATS:
            img.save(dst, pil_format, save_all=True, **_options(pil_format, img))
        else:
            _save(img, dst, target)
    return dst


def save_frame(frame, src, target):
    """Save one already chosen picture (animation frame, video still) next to src."""
    dst = output_path(src, target)
    _save(frame, dst, target)
    return dst
