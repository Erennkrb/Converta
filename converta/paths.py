"""Where Converta lives on disk and where its output goes."""
import os
import sys


def frozen():
    return getattr(sys, "frozen", False)


def app_dir():
    """Folder holding the .exe (installed) or the project root (from source)."""
    if frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset(name):
    # PyInstaller unpacks bundled data next to the code in _MEIPASS
    base = getattr(sys, "_MEIPASS", app_dir())
    return os.path.join(base, "assets", name)


def data_dir():
    if sys.platform == "win32":
        path = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Converta")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(base, "converta")
    os.makedirs(path, exist_ok=True)
    return path


def tool_kwargs():
    """subprocess arguments for external tools (ffmpeg, LibreOffice)."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    # PyInstaller points the library path at its own bundle, which breaks system tools
    env = dict(os.environ)
    original = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if original is not None:
        env["LD_LIBRARY_PATH"] = original
    elif frozen():
        env.pop("LD_LIBRARY_PATH", None)
    return {"env": env}


def unique_path(path):
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(path):
        path = f"{base} ({n}){ext}"
        n += 1
    return path


def output_path(src, ext, suffix=""):
    """Free path next to src with a new extension, never overwriting anything."""
    return unique_path(os.path.splitext(src)[0] + suffix + "." + ext.lstrip("."))
