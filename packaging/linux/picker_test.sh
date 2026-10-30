#!/bin/sh
# Opens the real frame picker on a virtual screen, picks frame 3 of 3 with the keyboard
# and checks the saved picture. Run under xvfb-run.
# Usage: picker_test.sh PYTHON_WITH_PILLOW anim.gif COMMAND...
set -eu
PY=$1
GIF=$2
shift 2
OUT="${GIF%.gif}.png"
rm -f "$OUT"

"$@" --to png "$GIF" &
PID=$!
if ! timeout 60 xdotool search --sync --onlyvisible --name "Converta" windowfocus; then
  echo "FAIL: picker window did not open"; kill "$PID" 2>/dev/null || true; exit 1
fi
sleep 2
xdotool key Right
sleep 1
xdotool key Right
sleep 1
xdotool key Return
timeout 30 tail --pid="$PID" -f /dev/null || { echo "FAIL: picker did not close"; kill "$PID"; exit 1; }
wait "$PID"

"$PY" - "$OUT" <<'EOF'
import sys

from PIL import Image

img = Image.open(sys.argv[1])
r, g, b = img.convert("RGB").getpixel((5, 5))
assert getattr(img, "n_frames", 1) == 1, "saved all frames"
assert b > 200 and r < 60 and g < 60, f"wrong frame saved: {(r, g, b)}"
print("ok: frame picker saved the chosen frame", (r, g, b))
EOF
