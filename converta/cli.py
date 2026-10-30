"""Command line entry: what Explorer and the installer call."""
import argparse
import os
import socket
import sys

from . import APP_NAME, documents, images, media, models, shell, ui
from .formats import LABELS, SINGLE_FRAME_IMAGES, VIDEO_KEYS, group_of
from .i18n import tr
from .paths import frozen

# Explorer starts one process per selected file; they meet on this port so
# the first one handles the whole selection one after another.
IPC_PORT = 47653
if hasattr(os, "getuid"):
    IPC_PORT += os.getuid() % 10000  # other users on this machine must not get our file list
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
    raise ValueError("Unsupported file type")


def needs_ffmpeg(path, target):
    return group_of(path) in ("audio", "video") or target in VIDEO_KEYS


def ensure_ffmpeg():
    """Get ffmpeg on first use. Returns an error text, or None when it's ready."""
    if media.find_ffmpeg():
        return None
    if not media.can_download_ffmpeg():
        return media.missing_ffmpeg_text()
    errors = ui.run_jobs([("FFmpeg", media.download_ffmpeg)], show_window=True)
    if media.find_ffmpeg():
        return None
    return (tr("Couldn't download FFmpeg. Please check your internet connection.\n\n",
               "FFmpeg konnte nicht heruntergeladen werden. Bitte Internetverbindung prüfen.\n\n")
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


def install_message(names):
    if sys.platform == "win32":
        return tr("Context menu installed.", "Kontextmenü installiert.")
    where = ", ".join(names) if names else tr("no supported file manager found",
                                              "kein unterstützter Dateimanager gefunden")
    text = tr(f"Converta is set up: {where}.\n\nRight-click a file to use it. In other file "
              "managers use \"Open with\". You may need to restart your file manager.",
              f"Converta ist eingerichtet: {where}.\n\nRechtsklicke eine Datei, um es zu nutzen. "
              "In anderen Dateimanagern geht es über \"Öffnen mit\". Eventuell musst du den "
              "Dateimanager neu starten.")
    if shell.needs_nautilus_python():
        text += tr("\n\nFor the Converta submenu in GNOME Files, install the \"nautilus-python\" "
                   "package (Debian/Ubuntu: \"python3-nautilus\"), run this setup again and "
                   "restart Files. Until then it is under Scripts.",
                   "\n\nFür das Converta-Untermenü in GNOME Dateien installiere das Paket "
                   "\"nautilus-python\" (Debian/Ubuntu: \"python3-nautilus\"), führe diese "
                   "Einrichtung erneut aus und starte Dateien neu. Bis dahin steht es unter Skripte.")
    return text


def report(errors):
    if errors:
        ui.message(tr("Conversion failed:\n\n", "Umwandlung fehlgeschlagen:\n\n")
                   + "\n".join(errors), error=True)
        sys.exit(1)


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
            ui.message(tr("This needs administrator rights.",
                          "Dafür werden Administratorrechte benötigt."), error=True)
            sys.exit(1)
    elif args.install:
        names = shell.install()
        if not args.quiet:
            ui.message(install_message(names))
    elif args.uninstall:
        shell.uninstall()
        if not args.quiet:
            ui.message(tr("Context menu removed.", "Kontextmenü entfernt."))
    elif args.to and args.files:
        files = collect_files([os.path.abspath(f) for f in args.files])
        if files is None:
            return
        report(convert_files(files, args.to))
    elif args.files and not ui.has_display():
        parser.error(tr("no display available, choose a format with --to",
                        "kein Bildschirm verfügbar, wähle ein Format mit --to"))
    elif args.files:
        # "Open with" and the scripts menu: ask for the format first
        files = collect_files([os.path.abspath(f) for f in args.files])
        if files is None:
            return
        target = ui.pick_target(files)
        if target:
            report(convert_files(files, target))
    elif frozen() and sys.platform != "win32":
        # double-clicking the AppImage sets everything up
        ui.message(install_message(shell.install()))
    else:
        parser.print_help()
