"""Audio and video conversions with ffmpeg."""
import glob
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from PIL import Image

from .i18n import tr
from .paths import app_dir, data_dir, output_path, tool_kwargs

FFMPEG_EXE = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

_EVEN = ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"]  # x264 needs even dimensions
_H264 = ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k"] + _EVEN

VIDEO_ARGS = {
    "mp4": _H264 + ["-movflags", "+faststart"],
    "mov": _H264 + ["-movflags", "+faststart"],
    "mkv": _H264,
    # yuva420p: VP9 can't take GIF's RGBA directly, and this keeps transparency
    "webm": ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1",
             "-pix_fmt", "yuva420p", "-c:a", "libopus", "-b:a", "128k"],
    "avi": ["-c:v", "mpeg4", "-q:v", "3", "-c:a", "libmp3lame", "-q:a", "3"] + _EVEN,
    "gif": ["-an", "-vf", "fps=12,scale='min(480,iw)':-2:flags=lanczos,"
                          "split[a][b];[a]palettegen[p];[b][p]paletteuse", "-loop", "0"],
}

AUDIO_ARGS = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
    "opus": ["-c:a", "libopus", "-b:a", "128k"],
    "aac": ["-c:a", "aac", "-b:a", "192k"],
    "wma": ["-c:a", "wmav2", "-b:a", "192k"],
}


# ffmpeg isn't shipped with the installer; it's fetched once on first use.
# Pinned build, verified by hash.
FFMPEG_URL = ("https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/"
              "ffmpeg-9.0.2-essentials_build.zip")
FFMPEG_SHA256 = "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"


class ToolMissing(Exception):
    pass


def downloaded_ffmpeg():
    return os.path.join(data_dir(), "bin", FFMPEG_EXE)


def can_download_ffmpeg():
    return sys.platform == "win32"  # on Linux it comes from the distro's packages


def find_ffmpeg():
    """Bundled copy, then our download, then PATH, then a winget install. None if absent."""
    for path in (os.path.join(app_dir(), "bin", FFMPEG_EXE), downloaded_ffmpeg()):
        if os.path.exists(path):
            return path
    found = shutil.which(FFMPEG_EXE)
    if found or sys.platform != "win32":
        return found
    # Explorer keeps its old PATH until the next sign-in, so look for winget's copy
    winget = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet")
    for pattern in (os.path.join(winget, "Links", FFMPEG_EXE),
                    os.path.join(winget, "Packages", "Gyan.FFmpeg*", "*", "bin", FFMPEG_EXE)):
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    return None


def missing_ffmpeg_text():
    return tr("Audio and video need FFmpeg. Please install the \"ffmpeg\" package with your "
              "package manager, for example:\n\n"
              "sudo apt install ffmpeg\nsudo dnf install ffmpeg-free\nsudo pacman -S ffmpeg",
              "Für Audio und Video wird FFmpeg benötigt. Bitte installiere das Paket \"ffmpeg\" "
              "mit deinem Paketmanager, zum Beispiel:\n\n"
              "sudo apt install ffmpeg\nsudo dnf install ffmpeg-free\nsudo pacman -S ffmpeg")


def ffmpeg():
    path = find_ffmpeg()
    if not path:
        raise ToolMissing(missing_ffmpeg_text())
    return path


def download_ffmpeg(progress=None):
    """Fetch the pinned ffmpeg build into Converta's data folder."""
    target = downloaded_ffmpeg()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    archive = target + ".zip.part"
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(FFMPEG_URL, timeout=30) as response, \
                open(archive, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total, tr("Downloading FFmpeg (only once)…",
                                              "FFmpeg wird einmalig heruntergeladen…"))
        if digest.hexdigest() != FFMPEG_SHA256:
            raise RuntimeError(tr("The download is damaged (checksum mismatch).",
                                  "Download beschädigt (Prüfsumme stimmt nicht)."))
        with zipfile.ZipFile(archive) as zf:
            member = next(n for n in zf.namelist() if n.endswith("/bin/ffmpeg.exe"))
            with zf.open(member) as src, open(target + ".part", "wb") as dst:
                shutil.copyfileobj(src, dst)
        os.replace(target + ".part", target)
    finally:
        for leftover in (archive, target + ".part"):
            if os.path.exists(leftover):
                os.remove(leftover)
    return target


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, **tool_kwargs(), **kwargs)


def duration(src):
    """Length in seconds from ffmpeg's input summary, or None if unknown."""
    result = _run([ffmpeg(), "-hide_banner", "-i", src])
    match = re.search(rb"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        return None
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def grab_frame(src, seconds):
    """One video frame as a PIL image."""
    result = _run([ffmpeg(), "-hide_banner", "-loglevel", "error",
                   "-ss", f"{seconds:.3f}", "-i", src, "-frames:v", "1",
                   "-f", "image2pipe", "-c:v", "png", "-"])
    if not result.stdout:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip()
                           or tr("No picture found", "Kein Bild gefunden"))
    return Image.open(io.BytesIO(result.stdout)).convert("RGB")


def convert(src, target, progress=None):
    if target in VIDEO_ARGS:
        args = VIDEO_ARGS[target]
    else:
        args = ["-vn"] + AUDIO_ARGS[target]
    dst = output_path(src, target)
    total = duration(src)

    cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", src,
           *args, "-map_metadata", "0", "-progress", "pipe:1", "-nostats", dst]
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors,
                                **tool_kwargs(), text=True,
                                encoding="utf-8", errors="replace")
        try:
            for line in proc.stdout:
                if progress and total and line.startswith("out_time_us="):
                    try:
                        progress(min(int(line.split("=")[1]) / 1e6 / total, 1.0))
                    except ValueError:
                        pass
            proc.wait()
        except BaseException:
            proc.kill()
            proc.wait()
            if os.path.exists(dst):
                os.remove(dst)
            raise
        if proc.returncode != 0:
            if os.path.exists(dst):
                os.remove(dst)
            errors.seek(0)
            detail = errors.read().decode("utf-8", "replace").strip().splitlines()
            raise RuntimeError(detail[-1] if detail else f"ffmpeg: {proc.returncode}")
    return dst
