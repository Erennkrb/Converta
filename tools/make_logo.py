"""Generate the Converta logo: assets/converta.png and assets/converta.ico."""
import math
import os

from PIL import Image, ImageDraw

SIZE = 1024  # drawn large, scaled down for smooth edges
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

ACCENT = (0, 95, 184)  # Windows 11 default accent blue, #005FB8


def arrow_arc(draw, c, r, width, start, end):
    """Clockwise arc from start to end (degrees, PIL convention) with an arrowhead at end."""
    draw.arc((c - r, c - r, c + r, c + r), start, end, fill="white", width=width)
    a = math.radians(end)
    # point on the arc's centre line, tangent (clockwise) and outward normal
    rm = r - width / 2
    px, py = c + rm * math.cos(a), c + rm * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    head_len, head_w = width * 1.35, width * 1.25
    tip = (px + tx * head_len, py + ty * head_len)
    left = (px + nx * head_w, py + ny * head_w)
    right = (px - nx * head_w, py - ny * head_w)
    draw.polygon([tip, left, right], fill="white")


def main():
    os.makedirs(OUT, exist_ok=True)

    logo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=200, fill=255)
    logo.paste(Image.new("RGB", (SIZE, SIZE), ACCENT), mask=mask)

    draw = ImageDraw.Draw(logo)
    c, r, width = SIZE // 2, 300, 96
    arrow_arc(draw, c, r, width, 195, 330)  # top arc, pointing right/down
    arrow_arc(draw, c, r, width, 15, 150)   # bottom arc, pointing left/up

    logo.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "converta.png"))
    logo.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "converta.ico"),
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
