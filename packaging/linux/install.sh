#!/bin/sh
# Installs Converta for the current user. No root needed.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${XDG_DATA_HOME:-$HOME/.local/share}/converta/app"
BIN="$HOME/.local/bin"

rm -rf "$TARGET"
mkdir -p "$(dirname "$TARGET")" "$BIN"
cp -a "$HERE/converta" "$TARGET"
ln -sf "$TARGET/converta" "$BIN/converta"
"$BIN/converta" --install --quiet

echo "Converta is installed. Right-click a file to use it."
echo "You may need to restart your file manager."
