"""Command line entry: what Explorer and the installer call."""
import argparse
import os
import socket
import sys

from . import APP_NAME, documents, images, media, models, shell, ui
from .formats import LABELS, SINGLE_FRAME_IMAGES, VIDEO_KEYS, group_of

# Explorer starts one process per selected file; they meet on this port so
# the first one handles the whole selection one after another.
IPC_PORT = 47653
COLLECT_SECONDS = 0.6

# groups whose conversions take long enough to deserve a progress window
SLOW_GROUPS = {"audio", "video", "pdf", "word", "sheet", "slides", "model", "cad", "dxf"}


def collect_files(files):
    """Return the whole selection, or None if another process is already handling it."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", IPC_PORT))
    except OSError:
        server.close()
        try:
            with socket.create_connection(("127.0.0.1", IPC_PORT), timeout=2) as conn:
                conn.sendall("\n".join(files).encode("utf-8"))
            return None
        except OSError:
            return files  # owner went away, just handle our own files
    server.listen()
    server.settimeout(COLLECT_SECONDS)
    collected = list(files)
    while True:
        try:
            conn, _ = server.accept()
        except socket.timeout:
            break
        with conn:
            data = b""
            while chunk := conn.recv(65536):
                data += chunk
        collected += [p for p in data.decode("utf-8").split("\n") if p]
    server.close()
    return list(dict.fromkeys(collected))


def needs_frame_choice(path, target):
    group = group_of(path)
    if group == "video":
        return target in ("png", "jpg")
    return group == "image" and target in SINGLE_FRAME_IMAGES and images.is_animated(path)


def converter_for(path, target):
    group = group_of(path)
    if group == "image":
        if target in VIDEO_KEYS:
            return media.convert  # animated GIF -> video
        return images.convert
    if group in ("audio", "video"):
        return media.convert
    if group == "pdf":
        return documents.from_pdf
    if group in ("word", "sheet", "slides"):
        return documents.office_convert
    if group in ("model", "cad"):
        return models.convert
    if group == "dxf":
        return models.dxf_convert
    raise ValueError("Dateityp wird nicht unterstützt")


def needs_ffmpeg(path, target):
    return group_of(path) in ("audio", "video") or target in VIDEO_KEYS


def ensure_ffmpeg():
    """Download ffmpeg on first use. Returns an error text, or None when it's ready."""
    if media.find_ffmpeg():
        return None
    errors = ui.run_jobs([("FFmpeg", media.download_ffmpeg)], show_window=True)
    if media.find_ffmpeg():
        return None
    return ("FFmpeg konnte nicht heruntergeladen werden. Bitte Internetverbindung prüfen.\n\n"
            + "\n".join(errors)).strip()


def convert_files(files, target):
    if any(needs_ffmpeg(path, target) for path in files):
        problem = ensure_ffmpeg()
        if problem:
            return [problem]

    jobs = []
    for path in files:
        if needs_frame_choice(path, target):
            try:
                frame = ui.pick_frame(path, LABELS[target])
            except Exception as e:
                ui.message(f"{os.path.basename(path)}:\n\n{e}", error=True)
                continue
            if frame is not None:
                jobs.append((path, lambda p, path=path, frame=frame:
                             images.save_frame(frame, path, target)))
            continue
        try:
            convert = converter_for(path, target)
        except ValueError:
            continue
        jobs.append((path, lambda p, path=path, convert=convert: convert(path, target, p)))

    slow = any(group_of(path) in SLOW_GROUPS or target in VIDEO_KEYS for path, _ in jobs)
    return ui.run_jobs(jobs, show_window=slow)


def main():
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--install", action="store_true", help="register the context menu")
    parser.add_argument("--uninstall", action="store_true", help="remove the context menu")
    parser.add_argument("--quiet", action="store_true", help="no message boxes on (un)install")
    parser.add_argument("--to", choices=sorted(LABELS), help="target format")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    if (args.install or args.uninstall) and not shell.is_admin():
        forwarded = ["--install" if args.install else "--uninstall"]
        if args.quiet:
            forwarded.append("--quiet")
        if not shell.relaunch_as_admin(forwarded):
            ui.message("Dafür werden Administratorrechte benötigt.", error=True)
            sys.exit(1)
    elif args.install:
        shell.install()
        if not args.quiet:
            ui.message("Kontextmenü installiert.")
    elif args.uninstall:
        shell.uninstall()
        if not args.quiet:
            ui.message("Kontextmenü entfernt.")
    elif args.to and args.files:
        files = collect_files([os.path.abspath(f) for f in args.files])
        if files is None:
            return
        errors = convert_files(files, args.to)
        if errors:
            ui.message("Umwandlung fehlgeschlagen:\n\n" + "\n".join(errors), error=True)
            sys.exit(1)
    else:
        parser.print_help()
