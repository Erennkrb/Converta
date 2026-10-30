#!/bin/sh
# Runs inside a distro container. Usage: smoke_test.sh TARBALL FIXTURES_DIR
# Installs from the tar.gz like a user would, converts real files, checks the menus.
set -eu
TARBALL=$1
FIXTURES=$2

WORK=$(mktemp -d)
export HOME="$WORK/home"
export CONVERTA_ALL_FILE_MANAGERS=1
unset DISPLAY WAYLAND_DISPLAY || true
mkdir -p "$HOME" "$WORK/files"
cp "$FIXTURES"/* "$WORK/files/"

tar -xzf "$TARBALL" -C "$WORK"
sh "$WORK"/converta-*/install.sh
BIN="$HOME/.local/bin/converta"

check_output() {
  [ -s "$WORK/files/$2" ] || { echo "FAIL: $1 did not produce $2"; exit 1; }
  echo "ok: $1 -> $2"
}
convert() {
  "$BIN" --to "$2" "$WORK/files/$1"
  check_output "$1" "$3"
}

convert sample.png webp sample.webp
convert sample.png jpg sample.jpg
convert sample.png avif sample.avif
convert sample.png ico sample.ico
convert sample.png pdf "sample (1).pdf"
convert anim.gif webp anim.webp
convert sample.pdf docx "sample (1).docx"
convert sample.pdf txt sample.txt
convert sample.pdf png "sample (1).png"
convert box.stl 3mf box.3mf
convert box.stl obj box.obj
convert part.step stl part.stl
convert plan.dxf pdf plan.pdf
convert plan.dxf svg plan.svg

# without FFmpeg, audio/video must explain itself instead of crashing
if ! command -v ffmpeg >/dev/null 2>&1; then
  : > "$WORK/files/song.mp3"
  if MSG=$("$BIN" --to wav "$WORK/files/song.mp3" 2>&1); then
    echo "FAIL: expected an error without ffmpeg"; exit 1
  fi
  case "$MSG" in *ffmpeg*) echo "ok: missing ffmpeg is explained" ;; *) echo "FAIL: $MSG"; exit 1 ;; esac
fi

# menu files for every file manager
DATA="$HOME/.local/share"
for pattern in \
  "$DATA/kio/servicemenus/converta-00.desktop" \
  "$DATA/kservices5/ServiceMenus/converta-00.desktop" \
  "$DATA/nemo/actions/converta-000.nemo_action" \
  "$DATA/file-manager/actions/converta-000.desktop" \
  "$DATA/nautilus-python/extensions/converta_menu.py" \
  "$DATA/nautilus/scripts/Converta" \
  "$DATA/applications/converta.desktop" \
  "$HOME/.config/caja/scripts/Converta" \
  "$HOME/.config/Thunar/uca.xml"; do
  [ -e "$pattern" ] || { echo "FAIL: missing $pattern"; exit 1; }
done
grep -q "$BIN\|converta" "$HOME/.config/Thunar/uca.xml"
echo "ok: menus written"

"$BIN" --uninstall --quiet
[ ! -e "$DATA/nemo/actions/converta-000.nemo_action" ] || { echo "FAIL: uninstall left files"; exit 1; }
[ ! -e "$DATA/applications/converta.desktop" ] || { echo "FAIL: uninstall left files"; exit 1; }
if grep -q "<unique-id>converta-" "$HOME/.config/Thunar/uca.xml"; then echo "FAIL: Thunar entries left"; exit 1; fi
echo "ok: uninstall is clean"
echo "ALL PASSED"
