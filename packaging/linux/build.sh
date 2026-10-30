#!/bin/sh
# Builds the Linux release into dist/linux: AppImage, tar.gz, .deb and .rpm.
# Runs inside an old Debian container so the result works on as many distros as possible.
# Needs: python with tkinter, curl. Usage: packaging/linux/build.sh
set -eu
cd "$(dirname "$0")/../.."

VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' converta/__init__.py)
ARCH=$(uname -m)
case "$ARCH" in
  x86_64) NFPM_ARCH=amd64; NFPM_ASSET=x86_64 ;;
  aarch64) NFPM_ARCH=arm64; NFPM_ASSET=arm64 ;;
  *) echo "unsupported architecture: $ARCH"; exit 1 ;;
esac
NFPM_VERSION=2.41.3
OUT=dist/linux
rm -rf "$OUT" build/linux
mkdir -p "$OUT" build/linux

python -m pip install --quiet --disable-pip-version-check -r requirements.txt

# same exclusions as the Windows build: optional AI layout analysis, unused libraries
python -m PyInstaller --noconfirm --clean --onedir --name converta \
  --add-data "$PWD/assets:assets" \
  --collect-data pdf2docx --collect-data trimesh --collect-data ezdxf \
  --collect-binaries cascadio --hidden-import networkx \
  --exclude-module pymupdf.layout --exclude-module onnxruntime \
  --exclude-module matplotlib --exclude-module scipy --exclude-module pandas \
  --distpath build/linux/app --workpath build/linux/work --specpath build/linux \
  main.py
rm -f build/linux/app/converta/_internal/cv2/opencv_videoio_ffmpeg*
APP=build/linux/app/converta

# --- tar.gz, for any distro, installs without root
TAR_DIR=build/linux/converta-$VERSION
mkdir -p "$TAR_DIR"
cp -a "$APP" "$TAR_DIR/converta"
cp packaging/linux/install.sh packaging/linux/uninstall.sh "$TAR_DIR/"
tar -C build/linux -czf "$OUT/converta-$VERSION-linux-$ARCH.tar.gz" "converta-$VERSION"

# --- AppImage
APPDIR=build/linux/Converta.AppDir
mkdir -p "$APPDIR/usr/lib"
cp -a "$APP" "$APPDIR/usr/lib/converta"
cp packaging/linux/AppRun "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp packaging/linux/converta.desktop "$APPDIR/converta.desktop"
cp assets/converta.png "$APPDIR/converta.png"
curl -fsSL -o build/linux/appimagetool \
  "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
chmod +x build/linux/appimagetool
ARCH=$ARCH build/linux/appimagetool --appimage-extract-and-run "$APPDIR" \
  "$OUT/Converta-$VERSION-$ARCH.AppImage"

# --- .deb and .rpm
curl -fsSL "https://github.com/goreleaser/nfpm/releases/download/v$NFPM_VERSION/nfpm_${NFPM_VERSION}_Linux_$NFPM_ASSET.tar.gz" \
  | tar -xz -C build/linux nfpm
VERSION=$VERSION NFPM_ARCH=$NFPM_ARCH build/linux/nfpm package -f packaging/linux/nfpm.yaml -p deb -t "$OUT/"
VERSION=$VERSION NFPM_ARCH=$NFPM_ARCH build/linux/nfpm package -f packaging/linux/nfpm.yaml -p rpm -t "$OUT/"

ls -la "$OUT"
