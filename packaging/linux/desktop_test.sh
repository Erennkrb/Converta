#!/bin/sh
# Runs on Ubuntu with a virtual screen. Usage: desktop_test.sh TARBALL APPIMAGE DEB FIXTURES_DIR
# Covers what containers can't: real windows, FFmpeg, LibreOffice, the package install, Nautilus.
set -eu
TARBALL=$1
APPIMAGE=$2
DEB=$3
FIXTURES=$4

WORK=$(mktemp -d)
mkdir -p "$WORK/files"
cp "$FIXTURES"/* "$WORK/files/"
tar -xzf "$TARBALL" -C "$WORK"
BIN=$(echo "$WORK"/converta-*/converta/converta)

convert() {
  timeout 300 xvfb-run -a "$BIN" --to "$2" "$WORK/files/$1"
  [ -s "$WORK/files/$3" ] || { echo "FAIL: $1 -> $3"; exit 1; }
  echo "ok: $1 -> $3"
}
ffmpeg -hide_banner -loglevel error -f lavfi -i "sine=duration=1" "$WORK/files/song.wav"
ffmpeg -hide_banner -loglevel error -f lavfi -i "testsrc=duration=1:size=160x120:rate=10" "$WORK/files/clip.mp4"

convert song.wav mp3 song.mp3
convert clip.mp4 webm clip.webm
convert clip.mp4 mp3 clip.mp3
convert sample.docx pdf "sample (1).pdf"
convert sample.docx odt sample.odt
convert part.step 3mf part.3mf

# the AppImage runs by itself
chmod +x "$APPIMAGE"
"$APPIMAGE" --appimage-extract-and-run --to jpg "$WORK/files/sample.png"
[ -s "$WORK/files/sample.jpg" ] || { echo "FAIL: AppImage"; exit 1; }
echo "ok: AppImage converts"

# the .deb installs and sets up the menu
sudo apt-get install -y -qq "$DEB" >/dev/null
[ -x /usr/bin/converta ] && [ -e /etc/xdg/autostart/converta-setup.desktop ]
/usr/bin/converta --to bmp "$WORK/files/sample.png"
[ -s "$WORK/files/sample.bmp" ] || { echo "FAIL: deb"; exit 1; }
echo "ok: .deb installs and converts"

# the Nautilus extension loads against the real library and builds the submenu
HOME="$WORK/home" CONVERTA_ALL_FILE_MANAGERS=1 /usr/bin/converta --install --quiet
EXT="$WORK/home/.local/share/nautilus-python/extensions"
xvfb-run -a /usr/bin/python3 - "$EXT" <<'EOF'
import sys

sys.path.insert(0, sys.argv[1])
import converta_menu


class File:
    def __init__(self, uri):
        self.uri = uri

    def get_uri(self):
        return self.uri


provider = converta_menu.ConvertaMenu()
items = provider.get_file_items([File("file:///tmp/a%20b.png"), File("file:///tmp/c.png")])
assert len(items) == 1, items
labels = [i.get_property("label") for i in items[0].get_property("menu").get_items()]
assert any("WEBP" in label for label in labels) and not any("PNG" in label for label in labels), labels
assert provider.get_file_items([File("file:///tmp/a.txt")]) == []
print("ok: Nautilus extension", labels)
EOF

sudo apt-get remove -y -qq converta >/dev/null
[ ! -e /usr/bin/converta ] || { echo "FAIL: deb remove"; exit 1; }
echo "ok: .deb removes cleanly"
echo "ALL PASSED"
