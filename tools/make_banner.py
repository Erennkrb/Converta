"""Generate assets/banner.svg: the logo with its arrows turning, next to the name, 3:1."""
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "banner.svg")

ACCENT = "#005FB8"  # same blue as tools/make_logo.py
C, RADIUS, WIDTH = 512, 300, 96  # logo geometry in its 1024 unit space
TURN_SECONDS = 2.4  # the arrows look identical after half a turn, so this loops seamlessly


def arrow(start, end):
    """One arc with its arrowhead, same shape as the PNG logo."""
    mid = RADIUS - WIDTH / 2
    def point(deg, r=mid):
        a = math.radians(deg)
        return C + r * math.cos(a), C + r * math.sin(a)
    x0, y0 = point(start)
    x1, y1 = point(end)
    a = math.radians(end)
    tx, ty, nx, ny = -math.sin(a), math.cos(a), math.cos(a), math.sin(a)
    head_len, head_w = WIDTH * 1.35, WIDTH * 1.25
    tip = (x1 + tx * head_len, y1 + ty * head_len)
    left = (x1 + nx * head_w, y1 + ny * head_w)
    right = (x1 - nx * head_w, y1 - ny * head_w)
    head = " ".join(f"{x:.1f},{y:.1f}" for x, y in (tip, left, right))
    return (f'<path d="M{x0:.1f} {y0:.1f} A{mid} {mid} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" '
            f'stroke="#fff" stroke-width="{WIDTH}"/><polygon points="{head}" fill="#fff"/>')


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400" role="img" aria-label="Converta">
  <rect width="1200" height="400" fill="#121212"/>
  <g transform="translate(110 90) scale(0.2148)">
    <rect width="1024" height="1024" rx="200" fill="{ACCENT}"/>
    <g id="arrows">
      {arrow(195, 330)}
      {arrow(15, 150)}
      <animateTransform attributeName="transform" type="rotate" from="0 {C} {C}" to="180 {C} {C}" dur="{TURN_SECONDS}s" repeatCount="indefinite"/>
    </g>
  </g>
  <text x="390" y="202" fill="#f3f3f3" font-family="Segoe UI, Inter, Helvetica, Arial, sans-serif" font-size="92" font-weight="600" letter-spacing="-1.5">Converta</text>
  <text x="393" y="262" fill="#adaaa6" font-family="Segoe UI, Inter, Helvetica, Arial, sans-serif" font-size="32">Convert any supported file with a right click.</text>
</svg>
'''
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(svg)
