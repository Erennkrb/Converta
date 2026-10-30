"""Linux right-click integration, per user and without root.

Every file manager has its own format, so each gets its writer below. Only
managers that are present get files. A desktop entry adds "Open with" for
everything else, which opens the format picker.
"""
import glob
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

from . import APP_NAME
from .formats import SEP, all_source_exts, group_of, menu_label, targets_for
from .i18n import tr
from .paths import app_dir, asset, frozen

PREFIX = "converta"

# MIME names differ between shared-mime-info versions, so list the known aliases
EXT_MIMES = {
    ".png": ["image/png"], ".jpg": ["image/jpeg"], ".jpeg": ["image/jpeg"],
    ".jfif": ["image/jpeg", "image/pjpeg"], ".webp": ["image/webp"], ".avif": ["image/avif"],
    ".bmp": ["image/bmp", "image/x-bmp"], ".gif": ["image/gif"], ".tif": ["image/tiff"],
    ".tiff": ["image/tiff"], ".ico": ["image/vnd.microsoft.icon", "image/x-icon"],
    ".mp3": ["audio/mpeg"], ".wav": ["audio/x-wav", "audio/wav", "audio/vnd.wave"],
    ".flac": ["audio/flac", "audio/x-flac"],
    ".ogg": ["audio/ogg", "audio/x-vorbis+ogg", "audio/x-flac+ogg", "application/ogg"],
    ".m4a": ["audio/mp4", "audio/x-m4a"], ".aac": ["audio/aac", "audio/x-aac"],
    ".opus": ["audio/x-opus+ogg", "audio/opus"], ".wma": ["audio/x-ms-wma"],
    ".aif": ["audio/x-aiff", "audio/aiff"], ".aiff": ["audio/x-aiff", "audio/aiff"],
    ".mp4": ["video/mp4"], ".mkv": ["video/x-matroska"], ".webm": ["video/webm"],
    ".mov": ["video/quicktime"], ".avi": ["video/x-msvideo", "video/vnd.avi"],
    ".wmv": ["video/x-ms-wmv"], ".flv": ["video/x-flv"], ".m4v": ["video/x-m4v"],
    ".mpg": ["video/mpeg"], ".mpeg": ["video/mpeg"], ".3gp": ["video/3gpp"],
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ".doc": ["application/msword"], ".odt": ["application/vnd.oasis.opendocument.text"],
    ".rtf": ["application/rtf", "text/rtf"],
    ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    ".xls": ["application/vnd.ms-excel"], ".ods": ["application/vnd.oasis.opendocument.spreadsheet"],
    ".pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
    ".ppt": ["application/vnd.ms-powerpoint"],
    ".odp": ["application/vnd.oasis.opendocument.presentation"],
    ".stl": ["model/stl", "application/sla", "model/x.stl-binary", "model/x.stl-ascii"],
    ".obj": ["model/obj", "application/prs.wavefront-obj"],
    ".3mf": ["model/3mf", "application/vnd.ms-3mfdocument"],
    ".ply": ["application/ply", "model/ply"], ".off": ["model/off", "application/off"],
    ".glb": ["model/gltf-binary"], ".gltf": ["model/gltf+json"],
    ".step": ["model/step", "application/step", "application/x-step"],
    ".stp": ["model/step", "application/step", "application/x-step"],
    ".iges": ["model/iges", "application/iges", "application/x-iges"],
    ".igs": ["model/iges", "application/iges", "application/x-iges"],
    ".dxf": ["image/vnd.dxf", "application/dxf", "image/x-dxf"],
}


def is_admin():
    return True  # everything lives in the user's home


def relaunch_as_admin(args):
    return True


def _argv():
    """How file managers start us: AppImage, packaged binary, or from source."""
    if os.environ.get("APPIMAGE"):
        return [os.environ["APPIMAGE"]]
    if frozen():
        return [sys.executable]
    return [sys.executable, os.path.join(app_dir(), "main.py")]


def _shell_command(*args):
    return " ".join(shlex.quote(a) for a in _argv()) + "".join(f" {a}" for a in args)


def _desktop_exec(*args):
    """Exec= value: reserved characters quoted per the Desktop Entry spec."""
    def quote(arg):
        if not any(c in arg for c in ' \t"`$\\\'&;<>()*?#~|'):
            return arg.replace("%", "%%")
        escaped = arg.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
        return f'"{escaped}"'.replace("%", "%%")
    return " ".join(quote(a) for a in _argv()) + "".join(f" {a}" for a in args)


def _data_home():
    return os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")


def _config_home():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def _write(path, text, executable=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if executable:
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _remove(pattern):
    for path in glob.glob(pattern):
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path) or os.path.islink(path):
            os.remove(path)


def _present(command, *config_dirs):
    """Installed now, or used before. Tests can force everything with an env var."""
    if os.environ.get("CONVERTA_ALL_FILE_MANAGERS"):
        return True
    return shutil.which(command) is not None or any(os.path.isdir(d) for d in config_dirs)


def _actions():
    """Flat menu entries: [(label, target, exts)], one per distinct label and format."""
    entries = {}
    for ext in all_source_exts():
        group = group_of("x" + ext)
        for target in targets_for(ext):
            if target is SEP:
                continue
            key = (menu_label(group, target), target)
            entries.setdefault(key, []).append(ext)
    return [(label, target, exts) for (label, target), exts in entries.items()]


def _patterns(exts):
    return ";".join(f"*{e};*{e.upper()}" for e in exts)


# --- writers ------------------------------------------------------------------

def _write_dolphin():
    """KDE service menus, one file per set of targets, in a Converta submenu."""
    sets = {}
    for ext in all_source_exts():
        targets = tuple(t for t in targets_for(ext) if t is not SEP)
        sets.setdefault((group_of("x" + ext), targets), []).append(ext)
    folders = (os.path.join(_data_home(), "kio", "servicemenus"),         # KDE 6
               os.path.join(_data_home(), "kservices5", "ServiceMenus"))  # KDE 5
    for i, ((group, targets), exts) in enumerate(sets.items()):
        mimes = sorted({m for e in exts for m in EXT_MIMES[e]})
        lines = ["[Desktop Entry]", "Type=Service", "ServiceTypes=KonqPopupMenu/Plugin",
                 f"MimeType={';'.join(mimes)};", f"Actions={';'.join(targets)};",
                 f"X-KDE-Submenu={APP_NAME}", f"Icon={PREFIX}", ""]
        for target in targets:
            lines += [f"[Desktop Action {target}]", f"Name={menu_label(group, target)}",
                      f"Icon={PREFIX}", f"Exec={_desktop_exec('--to', target, '%F')}", ""]
        for folder in folders:
            _write(os.path.join(folder, f"{PREFIX}-{i:02d}.desktop"), "\n".join(lines), True)


def _write_nemo():
    folder = os.path.join(_data_home(), "nemo", "actions")
    for i, (label, target, exts) in enumerate(_actions()):
        _write(os.path.join(folder, f"{PREFIX}-{i:03d}.nemo_action"), "\n".join([
            "[Nemo Action]", f"Name={APP_NAME}: {label}", f"Comment={label}",
            f"Exec={_shell_command('--to', target, '%F')}", f"Icon-Name={PREFIX}",
            "Selection=notnone", f"Extensions={';'.join(e[1:] for e in exts)};",
            "Quote=double", ""]))


def _write_file_manager_actions():
    """The freedesktop actions format, read by PCManFM, PCManFM-Qt and others."""
    folder = os.path.join(_data_home(), "file-manager", "actions")
    for i, (label, target, exts) in enumerate(_actions()):
        _write(os.path.join(folder, f"{PREFIX}-{i:03d}.desktop"), "\n".join([
            "[Desktop Entry]", "Type=Action", f"Name={APP_NAME}: {label}", f"Icon={PREFIX}",
            "Profiles=main;", "", "[X-Action-Profile main]",
            f"Exec={_desktop_exec('--to', target, '%F')}",
            f"Basenames={_patterns(exts)};", "SelectionCount=>0", ""]))


def _thunar_file():
    return os.path.join(_config_home(), "Thunar", "uca.xml")


def _thunar_without_ours():
    """Parsed uca.xml with our entries gone. Other custom actions stay untouched."""
    path = _thunar_file()
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        return ET.Element("actions")
    for action in list(root):
        uid = action.findtext("unique-id") or ""
        if uid.startswith(f"{PREFIX}-"):
            root.remove(action)
    return root


def _save_thunar(root):
    ET.indent(root)
    os.makedirs(os.path.dirname(_thunar_file()), exist_ok=True)
    ET.ElementTree(root).write(_thunar_file(), encoding="UTF-8", xml_declaration=True)


def _write_thunar():
    root = _thunar_without_ours()
    for i, (label, target, exts) in enumerate(_actions()):
        action = ET.SubElement(root, "action")
        for tag, value in (("icon", PREFIX), ("name", label), ("submenu", APP_NAME),
                           ("unique-id", f"{PREFIX}-{i:03d}"),
                           ("command", _shell_command("--to", target, "%F")),
                           ("description", ""), ("patterns", _patterns(exts))):
            ET.SubElement(action, tag).text = value
        for kind in ("audio-files", "image-files", "other-files", "text-files", "video-files"):
            ET.SubElement(action, kind)
    _save_thunar(root)


def _write_scripts():
    """Nautilus and Caja scripts menu: opens the picker for the selected files."""
    script = "\n".join([
        "#!/bin/sh",
        'paths="${NAUTILUS_SCRIPT_SELECTED_FILE_PATHS:-$CAJA_SCRIPT_SELECTED_FILE_PATHS}"',
        "set -f", "IFS='", "'", f"exec {_shell_command('$paths')}", ""])
    if _present("nautilus", os.path.join(_data_home(), "nautilus")):
        _write(os.path.join(_data_home(), "nautilus", "scripts", APP_NAME), script, True)
    if _present("caja", os.path.join(_config_home(), "caja")):
        _write(os.path.join(_config_home(), "caja", "scripts", APP_NAME), script, True)


NAUTILUS_EXTENSION = '''"""Converta submenu for Nautilus. Generated by "converta --install"."""
import os
import subprocess
import urllib.parse

import gi

for version in ("4.1", "4.0", "3.0"):
    try:
        gi.require_version("Nautilus", version)
        break
    except ValueError:
        pass
from gi.repository import GObject, Nautilus

COMMAND = __COMMAND__
MENU = __MENU__


def path_of(item):
    uri = item.get_uri()
    return urllib.parse.unquote(uri[7:]) if uri.startswith("file://") else None


class ConvertaMenu(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):  # Nautilus 3 also passes the window first
        files = args[-1]
        paths = [path_of(f) for f in files]
        if not paths or None in paths:
            return []
        menus = [MENU.get(os.path.splitext(p)[1].lower()) for p in paths]
        if None in menus:
            return []
        shared = [entry for entry in menus[0] if all(entry in m for m in menus)]
        if not shared:
            return []
        top = Nautilus.MenuItem(name="Converta::top", label="Converta")
        submenu = Nautilus.Menu()
        top.set_submenu(submenu)
        for label, target in shared:
            item = Nautilus.MenuItem(name=f"Converta::{target}", label=label)
            item.connect("activate", self.run, target, paths)
            submenu.append_item(item)
        return [top]

    def run(self, _item, target, paths):
        subprocess.Popen(COMMAND + ["--to", target] + paths)
'''


def _write_nautilus_extension():
    menu = {}
    for ext in all_source_exts():
        group = group_of("x" + ext)
        menu[ext] = [(menu_label(group, t), t) for t in targets_for(ext) if t is not SEP]
    code = (NAUTILUS_EXTENSION.replace("__COMMAND__", repr(_argv()))
            .replace("__MENU__", repr(json.loads(json.dumps(menu)))))
    _write(os.path.join(_data_home(), "nautilus-python", "extensions", f"{PREFIX}_menu.py"), code)


def _write_open_with():
    """Always there: "Open with" in any file manager, plus the app icon."""
    icon = os.path.join(_data_home(), "icons", "hicolor", "512x512", "apps", f"{PREFIX}.png")
    os.makedirs(os.path.dirname(icon), exist_ok=True)
    shutil.copyfile(asset("converta.png"), icon)
    mimes = sorted({m for values in EXT_MIMES.values() for m in values})
    _write(os.path.join(_data_home(), "applications", f"{PREFIX}.desktop"), "\n".join([
        "[Desktop Entry]", "Type=Application", f"Name={APP_NAME}",
        "Comment=" + tr("Convert this file to another format", "Diese Datei in ein anderes Format umwandeln"),
        f"Exec={_desktop_exec('%F')}", f"Icon={PREFIX}", "Terminal=false", "NoDisplay=true",
        "Categories=Utility;", f"MimeType={';'.join(mimes)};", ""]))
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", os.path.join(_data_home(), "applications")],
                       capture_output=True, check=False)


def install():
    uninstall()
    done = []
    data, config = _data_home(), _config_home()
    if _present("dolphin", os.path.join(data, "kio"), os.path.join(data, "kservices5")):
        _write_dolphin()
        done.append("Dolphin")
    if _present("nautilus", os.path.join(data, "nautilus")):
        _write_nautilus_extension()
        done.append("Nautilus")
    if _present("nemo", os.path.join(data, "nemo")):
        _write_nemo()
        done.append("Nemo")
    if _present("thunar", os.path.join(config, "Thunar")):
        _write_thunar()
        done.append("Thunar")
    if _present("caja", os.path.join(config, "caja")):
        done.append("Caja")
    if _present("pcmanfm", os.path.join(data, "file-manager")) or _present("pcmanfm-qt"):
        _write_file_manager_actions()
        done.append("PCManFM")
    _write_scripts()
    _write_open_with()
    return done


def uninstall(refresh=True):
    data, config = _data_home(), _config_home()
    for pattern in (
        (data, "kio", "servicemenus", f"{PREFIX}-*.desktop"),
        (data, "kservices5", "ServiceMenus", f"{PREFIX}-*.desktop"),
        (data, "nemo", "actions", f"{PREFIX}-*.nemo_action"),
        (data, "file-manager", "actions", f"{PREFIX}-*.desktop"),
        (data, "nautilus-python", "extensions", f"{PREFIX}_menu.py"),
        (data, "nautilus", "scripts", APP_NAME),
        (config, "caja", "scripts", APP_NAME),
        (data, "applications", f"{PREFIX}.desktop"),
        (data, "icons", "hicolor", "512x512", "apps", f"{PREFIX}.png"),
    ):
        _remove(os.path.join(*pattern))
    if os.path.exists(_thunar_file()):
        _save_thunar(_thunar_without_ours())
