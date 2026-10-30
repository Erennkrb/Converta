#!/bin/sh
# Removes the right-click menu and the program installed by install.sh.
set -eu
BIN="$HOME/.local/bin/converta"
[ -x "$BIN" ] && "$BIN" --uninstall --quiet
rm -f "$BIN"
rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/converta"
echo "Converta is removed."
